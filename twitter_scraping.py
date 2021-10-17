from graphviz import *
import tweepy
import pandas as pd
import numpy as np
import yaml
from time import sleep

class Tweet:
    def add_child(self, child):
        self.children.append(child)

    def __init__(self, tweet_status, is_retweet):
        self.is_retweet = is_retweet
        self.children = []
        self.parent = None
        self.id = tweet_status.id
        self.text = tweet_status.text
        self.user = tweet_status.user

class cascade_maker():

    def __init__(self, environment_name=None):
        self.environment_name = environment_name
        with open(environment_name) as f:
            secrets = yaml.safe_load(f)["search_tweets_api"]

            auth = tweepy.OAuthHandler(secrets["consumer_key"], secrets["consumer_secret"])
            auth.set_access_token(secrets["access_token"], secrets["access_token_secret"])

            self.api = tweepy.API(auth)
        self.root_nodes = []

    def get_retweets(self, tweet, user=None, count=100, results_per_call=100):
        '''
        If premium is true (which it should only be if the number of retweets exceeds 100), 
        then the tweet argument should be the text of the tweet - otherwise it should be the tweet id itself.

        The premium search works by looking for the text of the tweet, and filtering for cases where the tweet is a retweet of the original
        tweeting user.
        '''
        results = []
        ids = set()
        while True:
            retweets_list = self.api.retweets(tweet.id, count)
            retweets_list = list(filter(lambda x: x.id not in ids, retweets_list))
            if len(retweets_list) > 0:
                for retweet in retweets_list:
                    retweet_obj = Tweet(retweet, True)
                    results.append(retweet_obj)
                    ids.add(retweet.id)
                # print(retweet.user.screen_name)
            else:
                break

        # truncation = 128 - len(' retweets_of:') - len(user)  # query needs to be under 128 chars
        # query = f'"{tweet.text[:truncation]}" retweets_of:{user}'
        # rts = []
        # for page in tweepy.Cursor(self.api.search, q=search_words, since=date_since).pages():
        #     rts += page
        #
        # return rts

        return results

    def follows(self, user1, user2):
        '''
        Returns bool tuple to indicate if user1 follows user2 and vice-versa respectively. 
        Usernames or userids can be used
        '''
        friendship = self.api.show_friendship(source_id=user1, target_id=user2)
        return friendship[0].following, friendship[1].following


    def cascade_structure(self, tweets, seconds_per_query=5):
        for tweet in tweets:
            root_tweet = Tweet(tweet, False)
            self.root_nodes.append(root_tweet)
            retweets = self.get_retweets(root_tweet, user=root_tweet.user.screen_name)

            parents = [root_tweet]
            while True:
                if len(parents) == 0 or len([x for x in retweets if x.parent == None]) == 0:
                    break
                parent = parents.pop()
                for i, rid in enumerate(retweets):
                    if rid.parent != None:
                        continue
                    if self.follows(rid.user.id, parent.user.id)[0]:
                        child_tweet = retweets[i]
                        child_tweet.parent = parent
                        parent.add_child(child_tweet)
                        parents.append(child_tweet)
                    sleep(seconds_per_query)
                parents = sorted(parents, key=lambda x: int(x.user.followers_count))

            self.visualize()

    def visualize(self):
        def to_label(node):
            if node.is_retweet:
                return node.user.screen_name
            else:
                return node.text

        saved_nodes = set()
        color_options = {}
        untouched_nodes = []
        dot = Graph()
        for node in self.root_nodes:
            untouched_nodes.append(node)
            while len(untouched_nodes) > 0:
                node = untouched_nodes.pop(0)
                node_key = str(node.id)
                if node_key not in saved_nodes:
                    label = to_label(node)
                    if node_key in color_options:
                        dot.node(node_key, label, style="filled", fillcolor=color_options[node_key])
                    else:
                        dot.node(node_key, label)
                    saved_nodes.add(node_key)
                else:
                    continue
                for x in range(len(node.children)):
                    child = node.children[x]
                    child_key = str(child.id)
                    dot.edge(node_key, child_key)
                    if child_key not in saved_nodes:
                        untouched_nodes.append(child)
        dot.render('./graph/shrink.gv', view=True)

    def get_tweet(self, id):
        return self.api.get_status(id)

    def create_edge_list(self, root_userid, retweets, seconds_per_query=5, verbose=True):
        '''
        Given the root user id number and the associated retweets, construct the edge list based on follower relationships.
        If a user has retweeted without a follower relationship, we discard the retweet. We could assign it to the root, but this is not necessarily sensible
        if one of the retweeters has a larger following than the root.

        root_userid should be int, but probably works with string, and should also work with the username as well.
        retweets should be the direct result from the api, not a dataframe
        seconds_per_query is required to prevent exceeding the rate limit. 5 is the default, which is safe for the standard api, but very slow for large cascades.

        Returns a dataframe edge_list.
        '''
        children = [{'user_id': r.user.id, 'parent': None, 'followers_count': r.user.followers_count} for r in retweets]
        parents = [root_userid]
        while True:
            if len(parents) == 0 or len([x for x in children if x['parent'] == None]) == 0:
                break
            parent = parents.pop()
            for i, rid in enumerate(children):
                if verbose:
                    print(f'Current parent: {parent}. Parents remaining: {len(parents)}. Child: {i}',' '*10, end='.\r')
                if rid['parent'] != None:
                    continue

                if self.follows(rid['user_id'], parent)[0]:
                    children[i]['parent'] = parent
                    parents.append(rid['user_id'])
                sleep(seconds_per_query)
            parents = pd.Series({c['user_id']:c['followers_count'] for c in children if c['user_id'] in parents}).sort_values().index.tolist()
        
        edf = pd.DataFrame(children).dropna()
        edf['user_id'] = edf['user_id'].astype(np.int64)
        edf['parent'] = edf['parent'].astype(np.int64)
        return edf

if __name__ == '__main__':
    # Okay so we need to be a little clever:
    # Twint does not make it particularly feasible for us to construct the retweet network
    # BUT it does seem like we can search for URLs, and we can filter to users who have been
    # retweeted a certain number of times
    # We should also be able to get the followers of those users (TODO)
    # We can then, in theory combine twint with the twitter api through tweepy or whatever to find the retweets
    # Again use twint to get their follower networks - and thus we can construct a cascade
    # with very minimal number of requests
    
    cm = cascade_maker('./twitter_keys.yaml')
    # for tweet in tweepy.Cursor(cm.api.search, q='#covid', result_type='popular').items(5):
    #     print(tweet)
    tweet = cm.get_tweet(849813577770778624)
    cm.cascade_structure([tweet])
    print("here")
    
    # print(pd.read_csv('test.csv').iloc[0]['user_id'])
    # # we can find the quoted tweets with this method!
    # c = twint.Config()
    # c.Search = 'https://twitter.com/coinbureau/status/1353777914404331521'
    # c.Pandas = True
    # twint.run.Search(c)
    # df = twint.storage.panda.Tweets_df
    # print(df)

