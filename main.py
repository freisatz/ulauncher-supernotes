import logging
import re
import datetime

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
            desc_create = ""
            desc_daily = ""
            if len(arg_str) == 0:
                desc_create = "Type in a card title and press Enter..."
                desc_daily = "Type in something to capture and press Enter..."
            data = {"action": "push", "name": arg_str}
            items.append(
                ExtensionResultItem(
                    icon="images/supernotes.png",
                    name="Create new card",
                    description=desc_create,
                    on_enter=ExtensionCustomAction(data),
                )
            )

            if re.match("%d", extension.preferences["daily_pattern"]):
                data = {"action": "daily", "append": arg_str}
                items.append(
                    ExtensionResultItem(
                        icon="images/supernotes.png",
                        name="Add to daily note",
                        description=desc_daily,
                        on_enter=ExtensionCustomAction(data),
                    )
                )

            result = self.fetch(arg_str, extension.preferences["limit"], api_key)

            max_rows = (
                int(extension.preferences["max_rows"])
                if extension.preferences["max_rows"].isdigit()
                else 3
            )

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

    def _compile_daily_note_title(self, title_pattern, date_style):
        today = datetime.date.today()
        date = ""
        
        if date_style == "iso":
            date = today.strftime("%Y-%m-%d")  # 2025-05-04
        elif date_style == "european":
            date = today.strftime("%d.%m.%Y")  # 04.05.2025
        elif date_style == "american":
            date = today.strftime("%m/%d/%Y")  # 05/04/2025
        elif date_style == "traditional":
            suffix = {1: "st", 2: "nd", 3: "rd"}.get(today.day % 20, "th")
            month_names = {
                1: "January",
                2: "February",
                3: "March",
                4: "April",
                5: "May",
                6: "June",
                7: "July",
                8: "August",
                9: "September",
                10: "October",
                11: "November",
                12: "December",
            }

            date = f"{month_names.get(today.month)} {today.day}{suffix}, {today.year}"  # May 4st, 2025
        else:
            logger.warning("Date style not recognized.")

        return re.sub("%d", date, title_pattern)

    def _compile_daily_note_append(self, string, append_style):

        prefix = ""
        if append_style == "bullet":
            prefix = "- "
        elif append_style == "todo":
            prefix = "- [ ] "
        elif append_style == "plain":
            pass
        else:
            logger.warning("Append style not recognized.")

        return f"{prefix}{string}"

    def append_daily(
        self, string, tags, title_pattern, date_style, append_style, api_key
    ):

        name = self._compile_daily_note_title(title_pattern, date_style)
        append = self._compile_daily_note_append(string, append_style)

        logger.info(f'Append string to daily note "{name}"')

        api = SupernotesApi(api_key)
        response = api.select(name, 1)

        if response.status_code < 400:
            result = response.json()

            if len(result) > 0:
                item = list(result.values())[0].get("data")
                id = item["id"]
                markup = f"{item['markup']}\n{append}"
                response = api.update(id, markup)

                if response.status_code >= 400:
                    logger.error(response.json())

            else:
                response = api.create(name, tags, markup=f"{append}")
                if response.status_code >= 400:
                    logger.error(response.json())
        else:
            logger.error(response.json())

    def push(self, name, tags, api_key):
        logger.info(f"Creating new card with name \"{name}\"")

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

    def on_daily_action(self, event: ItemEnterEvent, extension: SupernotesExtension):
        data = event.get_data()
        self.append_daily(
            data["append"],
            self.read_tags(extension.preferences["tags"]),
            extension.preferences["daily_pattern"],
            extension.preferences["daily_date_style"],
            extension.preferences["daily_append_style"],
            extension.preferences["api_key"],
        )

    def on_event(self, event: ItemEnterEvent, extension: SupernotesExtension):
        data = event.get_data()
        switch = {"push": self.on_push_action, "daily": self.on_daily_action}
        switch.get(data["action"])(event, extension)


if __name__ == "__main__":
    SupernotesExtension().run()
