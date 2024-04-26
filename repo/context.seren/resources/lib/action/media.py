from abc import ABCMeta
from urllib.parse import quote
from urllib.parse import urlencode

from resources.lib.action import ContextAction
from resources.lib.action import SEREN_ADDON_ID
from resources.lib.tools import get_query_params
from resources.lib.tools import url_quoted_action_args


class ContextMediaAction(ContextAction, metaclass=ABCMeta):
    @property
    def action_type(self):
        return "PlayMedia({path})"


class SourceSelect(ContextMediaAction):
    def __init__(self, reload="false", source_select="true"):
        super().__init__()
        self.seren_reload = reload
        self.source_select = source_select

    @property
    def action(self):
        return "getSources"

    def handle_path(self):
        args = {
            "action": self.action,
            "action_args": url_quoted_action_args(self.action_args),
        }
        if self.seren_reload == "true":
            args['seren_reload'] = "true"
        if self.source_select == "true":
            args['source_select'] = "true"

        self.action_path = f"plugin://{SEREN_ADDON_ID}/?{urlencode(args, quote_via=quote)}"


class RescrapeItem(SourceSelect):
    def __init__(self):
        super().__init__(reload="true", source_select="false")
        self.action_query = get_query_params(self.action_path).get("action")

    @property
    def action(self):
        return self.action_query


class RescrapeAndSourceSelect(SourceSelect):
    def __init__(self):
        super().__init__(reload="true", source_select="true")
