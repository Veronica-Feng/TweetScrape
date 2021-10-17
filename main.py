# from searchtweets import load_credentials, gen_request_parameters, collect_results, ResultStream

# Press the green button in the gutter to run the script.
from city_falcon.city_falcon import CityFalcon
import pandas as pd

if __name__ == '__main__':
    df = pd.read_csv("./data/S&P.csv")
    symbols = df["Symbol"]
    city_falcon = CityFalcon("https://api.cityfalcon.com/v0.2/", "stories",
                             "981189688c1e03f8f32afc7ebf19633623c05c7da33e846aeff0c5d340d00a84")
    symbol_col = []
    uuids = []
    times = []
    titles = []
    descriptions = []
    assetTags = []
    searchTags = []
    for symbol in symbols:
        print(f"Generate Stories for {symbol}:")
        params = {"identifier_type": "tickers", "identifiers": symbol,
                  "domains": "bbc.co.uk, bbc.com, ft.com, bloomberg.com, "
                             "economist.com, reuters.com, wsj.com, forbes.com,"
                             "marketwatch.com, money.cnn.com, cnbc.com, ibtimes.com, fortune.com, morningstar.com",
                  "languages": "en"}
        try:
            stories = city_falcon.get(params)
            for story in stories:
                symbol_col.append(symbol)
                uuids.append(story["uuid"])
                times.append(story["publishTime"])
                titles.append(story["title"])
                descriptions.append(story["description"])
                assetTags.append("-".join(story["assetTags"]))
                searchTags.append("-".join(story["searchTags"]))
        except:
            print(f"Error {symbol}")

    results_df = pd.DataFrame(data={"Symbol": symbol_col, "UUID": uuids, "PublishTime":times,
                                    "Title": titles, "Description": descriptions,
                                    "AssetTags": assetTags, "SearchTags": searchTags})
    results_df.to_csv("./stories.csv", index=False, quotechar='"')

# See PyCharm help at https://www.jetbrains.com/help/pycharm/
