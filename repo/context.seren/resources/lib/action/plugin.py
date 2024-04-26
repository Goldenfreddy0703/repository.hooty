from abc import ABCMeta
from urllib.parse import quote
from urllib.parse import urlencode

from resources.lib.action import ContextAction
from resources.lib.action import SEREN_ADDON_ID
from resources.lib.tools import url_quoted_action_args


class ContextPluginAction(ContextAction, metaclass=ABCMeta):
    @property
    def action_type(self):
        return "RunPlugin({path})"

    def handle_args(self, *args, **kwargs):
        pass


class PlayFromRandomPoint(ContextPluginAction):
    @property
    def action(self):
        return "playFromRandomPoint"


class QuickResume(ContextPluginAction):
    @property
    def action(self):
        return "forceResumeShow"


class TraktManager(ContextPluginAction):
    @property
    def action(self):
        return "traktManager"

    def handle_path(self):
        args = {"action": self.action, "action_args": url_quoted_action_args(self.action_args)}
        self.action_path = f"plugin://{SEREN_ADDON_ID}/?{urlencode(args, quote_via=quote)}"


class ShufflePlay(ContextPluginAction):
    @property
    def action(self):
        return "shufflePlay"
