import logging
import re
import datetime

from ulauncher.api.client.Extension import Extension
from ulauncher.api.client.EventListener import EventListener
from ulauncher.api.shared.event import KeywordQueryEvent
from ulauncher.api.shared.event import ItemEnterEvent
from ulauncher.api.shared.item.ExtensionResultItem import ExtensionResultItem
from ulauncher.api.shared.action.RenderResultListAction import RenderResultListAction
from ulauncher.api.shared.action.DoNothingAction import DoNothingAction
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

    api = SupernotesApi()

    def fetch(self, search, limit):

        logger.info('Requesting results for query "%s"' % search)

        response = self.api.select(search, limit)

        result = {}

        if response.ok:
            result = response.json()

        return result

    def on_event(self, event: KeywordQueryEvent, extension: SupernotesExtension):

        self.api.api_key = extension.preferences["api_key"]
        arg_str = event.get_argument()

        items = []

        if self.api.api_key:

            # add item "Create new card"
            desc_create = "Type in a card title and press Enter..."
            action_create = DoNothingAction()
            
            if arg_str:
                desc_create = ""
                data_create = {"action": "push", "name": arg_str}
                action_create = ExtensionCustomAction(data_create)

            items.append(
                ExtensionResultItem(
                    icon="images/supernotes.png",
                    name="Create new card",
                    description=desc_create,
                    on_enter=action_create,
                )
            )

            # add item "Add to daily note"
            if re.match("%d", extension.preferences["daily_pattern"]):
                desc_daily = "Type in your thoughts and press Enter..."
                action_daily = DoNothingAction()

                if arg_str:
                    desc_daily = ""
                    data_daily = {"action": "daily", "append": arg_str}
                    action_daily = ExtensionCustomAction(data_daily)

                items.append(
                    ExtensionResultItem(
                        icon="images/supernotes.png",
                        name="Add to daily note",
                        description=desc_daily,
                        on_enter=action_daily,
                    )
                )
            else:
                logger.info("Invalid pattern for daily note title given. Hiding item.")

            # add search results
            result = self.fetch(arg_str, extension.preferences["limit"])

            max_rows = 0
            if extension.preferences["max_rows"].isdigit():
                max_rows = int(extension.preferences["max_rows"])
            else:
                logger.warning("Number of max rows need to be set to an integer.")

            url_factory = SupernotesUrlFactory(extension.preferences["open_in"])

            for id in result:
                entry: dict = result.get(id)
                data: dict = entry.get("data")
                name: str = data.get("name")
                markup: str = data.get("markup")

                lines = [line for line in markup.splitlines() if line]
                lines = lines[0 : min(len(lines), max_rows)]

                desc = "\n".join(lines)

                items.append(
                    ExtensionResultItem(
                        icon="images/supernotes.png",
                        name=name,
                        description=desc,
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

    api = SupernotesApi()

    def _compile_daily_note_title(self, title_pattern, date_style):
        today = datetime.date.today()
        date = ""

        if date_style == "iso":
            date = today.strftime("%Y-%m-%d")  # 2025-05-04
        elif date_style == "slashes":
            date = today.strftime("%Y/%m/%d")  # 2025/05/04
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

    def append_daily(self, string, tags, title_pattern, date_style, append_style):

        name = self._compile_daily_note_title(title_pattern, date_style)
        append = self._compile_daily_note_append(string, append_style)

        logger.info(f'Append string to daily note "{name}"')

        response = self.api.select(
            "",
            1,
            filter_group={
                "operator": "and",
                "filters": [{"type": "name", "operator": "equals", "arg": name}],
            },
        )

        if response.ok:
            result = response.json()

            if len(result) > 0:
                item = list(result.values())[0].get("data")
                id = item["id"]
                markup = f"{item['markup']}\n{append}"
                response = self.api.update(id, markup)

                if not response.ok:
                    logger.error(response.json())

            else:
                response = self.api.create(name, tags, markup=f"{append}")
                if not response.ok:
                    logger.error(response.json())
        else:
            logger.error(response.json())

    def push(self, name, tags):
        logger.info(f'Creating new card with name "{name}"')

        response = self.api.create(name, tags)

        return response.json()

    def read_tags(self, string):
        p = re.compile(r"^[\w_\- ]+$")
        return [tag.strip() for tag in string.split(",") if p.match(tag)]

    def on_push_action(self, event: ItemEnterEvent, extension: SupernotesExtension):
        data = event.get_data()
        self.push(
            data["name"],
            self.read_tags(extension.preferences["tags"]),
        )

    def on_daily_action(self, event: ItemEnterEvent, extension: SupernotesExtension):
        data = event.get_data()
        self.append_daily(
            data["append"],
            self.read_tags(extension.preferences["tags"]),
            extension.preferences["daily_pattern"],
            extension.preferences["daily_date_style"],
            extension.preferences["daily_append_style"],
        )

    def on_event(self, event: ItemEnterEvent, extension: SupernotesExtension):
        self.api.api_key = extension.preferences["api_key"]
        action = event.get_data().get("action")
        switch = {"push": self.on_push_action, "daily": self.on_daily_action}
        switch.get(action)(event, extension)


if __name__ == "__main__":
    SupernotesExtension().run()
