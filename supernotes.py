import requests

class SupernotesApi:

    api_key = ""

    def __init__(self, api_key):
        self.api_key = api_key

    def select(self, search, limit):
        url = 'https://api.supernotes.app/v1/cards/get/select'
        payload = {
            'include_membership_statuses': [ 
                0,
                1,
                2 
            ],
            'search': search,
            'include': [],
            'exclude': [],
            'sort_type': 0,
            'sort_ascending': False,
            'limit': limit
        }
        headers = {
            'content-type': 'application/json',
            'Api-Key': self.api_key
        }
        return requests.post(url, json=payload, headers=headers)
    
    def create(self, name):
        url = "https://api.supernotes.app/v1/cards/simple"
        payload = {
            "name": name,
            "markup": "",
            "color": None,
            "icon": None,
            "tags": ["saved on the go"],
            "parent_ids": [],
            "source": None,
            "meta": {}
        }
        headers = {
            "Api-Key": self.api_key,
            "Content-Type": "application/json"
        }
        return requests.request("POST", url, json=payload, headers=headers)