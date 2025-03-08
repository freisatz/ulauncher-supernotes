import logging
import re

from ulauncher.api.client.Extension import Extension
from ulauncher.api.client.EventListener import EventListener
from ulauncher.api.shared.event import KeywordQueryEvent
from ulauncher.api.shared.event import ItemEnterEvent
from ulauncher.api.shared.item.ExtensionResultItem import ExtensionResultItem
from ulauncher.api.shared.action.RenderResultListAction import RenderResultListAction
from ulauncher.api.shared.action.HideWindowAction import HideWindowAction
from ulauncher.api.shared.action.OpenUrlAction import OpenUrlAction
from ulauncher.api.shared.action.ExtensionCustomAction import ExtensionCustomAction

from supernotes import SupernotesApi, SupernotesUrlFactory

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

        result = []

        if response.status_code == 200:
            result = response.json()

        return result

    def on_event(self, event: KeywordQueryEvent, extension: SupernotesExtension):

        api_key = extension.preferences["api_key"]
        arg_str = event.get_argument() if event.get_argument() else ""

        items = []

        if api_key:
            desc = ""
            if len(arg_str) == 0:
                desc = "Type in a card title and press Enter..."
            data = {"action": "push", "name": arg_str}
            items.append(
                ExtensionResultItem(
                    icon="images/supernotes.png",
                    name="Create new card",
                    description=desc,
                    on_enter=ExtensionCustomAction(data),
                )
            )

            result = self.fetch(arg_str, extension.preferences["limit"], api_key)

            max_rows = int(extension.preferences["max_rows"]) if extension.preferences["max_rows"].isdigit() else 3

            url_factory = SupernotesUrlFactory(extension.preferences["open_in"])

            for id in result:
                data = result.get(id).get("data")
                name = data.get("name")
                markup = data.get("markup")

                array = markup.splitlines()
                array = array[0 : min(len(array), max_rows)]

                markup = "\n".join(array)

                items.append(
                    ExtensionResultItem(
                        icon="images/supernotes.png",
                        name=name,
                        description=markup,
                        on_enter=OpenUrlAction(url_factory.create(id)),
                    )
                )
        else:
            items.append(
                ExtensionResultItem(
                    icon="images/supernotes.png",
                    name="No API key",
                    description="Provide your API key in extension settings",
                    on_enter=HideWindowAction(),
                )
            )

        return RenderResultListAction(items)


class ItemEnterEventListener(EventListener):

    def push(self, name, tags, api_key):
        logger.info(f'Creating new card with name "{name}"')

        api = SupernotesApi(api_key)
        response = api.create(name, tags)

        return response.json()

    def read_tags(self, string):
        p = re.compile(r"^[\w_\- ]+$")
        return [tag.strip() for tag in string.split(",") if p.match(tag)]

    def on_push_action(self, event: ItemEnterEvent, extension: SupernotesExtension):
        data = event.get_data()
        self.push(
            data["name"],
            self.read_tags(extension.preferences["tags"]),
            extension.preferences["api_key"],
        )

    def on_event(self, event: ItemEnterEvent, extension: SupernotesExtension):
        data = event.get_data()
        switch = {"push": self.on_push_action}
        switch.get(data["action"])(event, extension)


if __name__ == "__main__":
    SupernotesExtension().run()
