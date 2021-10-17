import requests
import json


class CityFalcon:

    def post(self, params):
        pass

    def get(self, params):
        params["access_token"] = self.token
        response = requests.get(self.url + self.endpoint, params=params)
        response_dict = json.loads(response.text)
        stories = response_dict["stories"]
        return stories

    def __init__(self, url, endpoint, token):
        self.url = url
        self.endpoint = endpoint
        self.token = token