import logging

from ulauncher.api.client.Extension import Extension
from ulauncher.api.client.EventListener import EventListener
from ulauncher.api.shared.event import KeywordQueryEvent
from ulauncher.api.shared.event import ItemEnterEvent
from ulauncher.api.shared.item.ExtensionResultItem import ExtensionResultItem
from ulauncher.api.shared.action.RenderResultListAction import RenderResultListAction
from ulauncher.api.shared.action.HideWindowAction import HideWindowAction
from ulauncher.api.shared.action.OpenUrlAction import OpenUrlAction
from ulauncher.api.shared.action.ExtensionCustomAction import ExtensionCustomAction

from supernotes import SupernotesApi

logger = logging.getLogger(__name__)

class SupernotesExtension(Extension):

    def __init__(self):
        super(SupernotesExtension, self).__init__()
        self.subscribe(KeywordQueryEvent, KeywordQueryEventListener())
        self.subscribe(ItemEnterEvent, ItemEnterEventListener())


class KeywordQueryEventListener(EventListener):

    def fetch(self, search, limit, api_key):

        logger.info('Requesting results for query "%s"' % search)
        
        api = SupernotesApi(api_key)
        response = api.select(search, limit)

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
        arg_str = event.get_argument() if event.get_argument() else ""

        items = []

        if api_key:

            data = {
                "action": "push",
                "name": arg_str
            }
            items.append(ExtensionResultItem(icon='images/supernotes.png',
                                            name="Create new card",
                                            description=arg_str,
                                            on_enter=ExtensionCustomAction(data)))

            result = self.fetch(
                arg_str, 
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
                                                description=markup,
                                                on_enter=OpenUrlAction(url_builder(id))))
        else:                    
            items.append(ExtensionResultItem(icon='images/supernotes.png',
                                            name='No API key',
                                            description='Provide your API key in extension settings',
                                            on_enter=HideWindowAction()))


        return RenderResultListAction(items)


class ItemEnterEventListener(EventListener):

    def push(self, name, api_key):    
        logger.info('Creating new card with name "%s"' % name)

        api = SupernotesApi(api_key)
        response = api.create(name)

        return response.json()

    def on_event(self, event, extension):
        data = event.get_data()
        if data['action'] == 'push':
            self.push(data['name'], extension.preferences['api_key'])
        

if __name__ == '__main__':
    SupernotesExtension().run()
