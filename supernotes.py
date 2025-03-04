import requests

class SupernotesUrlFactory:
    
    def _open_in_app_noteboard(id):
        return "supernotes:/v/card/%s" % id

    def _open_in_app_preview(id):
        return "supernotes:/?preview=%s" % id

    def _open_in_web_noteboard(id):
        return "https://my.supernotes.app/v/card/%s" % id

    def _open_in_web_preview(id):
        return "https://my.supernotes.app/?preview=%s" % id
    
    func = None
    
    def __init__(self, open_in):
        
        switch = {
            "app_nb": SupernotesUrlFactory._open_in_app_noteboard, 
            "app_pv": SupernotesUrlFactory._open_in_app_preview,
            "web_nb": SupernotesUrlFactory._open_in_web_noteboard, 
            "web_pv": SupernotesUrlFactory._open_in_web_preview
        }

        self.func = switch.get(open_in)
    
    def create(self, id):
        return self.func(id)


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
    
    def create(self, name, tags):
        url = "https://api.supernotes.app/v1/cards/simple"
        payload = {
            "name": name,
            "markup": "",
            "color": None,
            "icon": None,
            "tags": tags,
            "parent_ids": [],
            "source": None,
            "meta": {}
        }
        headers = {
            "Api-Key": self.api_key,
            "Content-Type": "application/json"
        }
        return requests.request("POST", url, json=payload, headers=headers)