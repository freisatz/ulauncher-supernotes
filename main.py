import json
import logging
import requests

from ulauncher.api.client.Extension import Extension
from ulauncher.api.client.EventListener import EventListener
from ulauncher.api.shared.event import KeywordQueryEvent
from ulauncher.api.shared.item.ExtensionResultItem import ExtensionResultItem
from ulauncher.api.shared.action.RenderResultListAction import RenderResultListAction
from ulauncher.api.shared.action.HideWindowAction import HideWindowAction
from ulauncher.api.shared.action.OpenUrlAction import OpenUrlAction

logger = logging.getLogger(__name__)

class SupernotesExtension(Extension):

    def __init__(self):
        super(SupernotesExtension, self).__init__()
        self.subscribe(KeywordQueryEvent, KeywordQueryEventListener())


class KeywordQueryEventListener(EventListener):

    DESC_MAX_LENGTH = 60

    def fetch(self, search, limit, api_key):    
        logger.info('Requesting results for query "%s"' % search)

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
            'Accept-Charset': 'UTF-8',
            'Api-Key': api_key
        }
        response = requests.post(url, data=json.dumps(payload), headers=headers)
        return response.json()

    @staticmethod
    def get_url_builder(open_in):

        def open_in_app_noteboard(id):
            return "supernotes:/v/card/%s" % id

        def open_in_app_preview(id):
            return "supernotes:/?preview=%s" % id

        def open_in_web_noteboard(id):
            return "https://my.supernotes.app/v/card/%s" % id

        def open_in_web_preview(id):
            return "https://my.supernotes.app/?preview=%s" % id

        switch = {
            "app_nb": open_in_app_noteboard, 
            "app_pv": open_in_app_preview,
            "web_nb": open_in_web_noteboard, 
            "web_pv": open_in_web_preview
        }

        return switch.get(open_in)


    def on_event(self, event, extension):

        api_key = extension.preferences['api_key']

        items = []

        if api_key:
            result = self.fetch(
                event.get_argument(), 
                extension.preferences['limit'], 
                api_key
            )
            
            url_builder = KeywordQueryEventListener.get_url_builder(extension.preferences['open_in'])
            max_rows = int(extension.preferences['max_rows'])

            for id in result:
                data = result.get(id).get('data')
                name = data.get('name')
                markup = data.get('markup')

                array = markup.splitlines()
                array = array[0:min(len(array), max_rows)]

                markup = "\n".join(array)

                items.append(ExtensionResultItem(icon='images/supernotes.png',
                                                name=name,
                                                # description=(markup[:self.DESC_MAX_LENGTH] + '...') if len(markup) > self.DESC_MAX_LENGTH else markup,
                                                description=markup,
                                                on_enter=OpenUrlAction(url_builder(id))))
        else:                    
            items.append(ExtensionResultItem(icon='images/supernotes.png',
                                            name='No API key',
                                            description='Provide your API key in extension settings',
                                            on_enter=HideWindowAction()))


        return RenderResultListAction(items)


if __name__ == '__main__':
    SupernotesExtension().run()
