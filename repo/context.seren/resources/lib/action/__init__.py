import re
from abc import ABCMeta
from abc import abstractmethod
from urllib.parse import quote
from urllib.parse import urlencode

import xbmc

from resources.lib.tools import get_current_list_item_action_args
from resources.lib.tools import get_current_list_item_path
from resources.lib.tools import log
from resources.lib.tools import url_quoted_action_args

SEREN_ADDON_ID = "plugin.video.seren"


class ContextAction(metaclass=ABCMeta):
    def __init__(self):
        self.action_args = get_current_list_item_action_args()
        self.action_path = get_current_list_item_path()
        self.name = self._parse_name()

    @property
    def keys_to_pop(self):
        return []

    @property
    @abstractmethod
    def action(self):
        ...

    @property
    @abstractmethod
    def action_type(self):
        ...

    def _pop_keys(self):
        if isinstance(self.action_args, dict):
            for key in self.keys_to_pop:
                self.action_args.pop(key, None)

    def _parse_name(self):
        class_name = self.__class__.__name__
        return re.sub(r"([A-Z])", r" \1", class_name)[1:]

    def log_action(self, trakt_id):
        log(f"{self.name} ({trakt_id})")

    def log_error(self):
        log(f"Missing required trakt_id from arguments ({self.action_args})", xbmc.LOGERROR)

    def handle_args(self, *args, **kwargs):
        pass

    def handle_path(self):
        args = {"action": self.action, "action_args": url_quoted_action_args(self.action_args)}
        self.action_path = f"plugin://{SEREN_ADDON_ID}/?{urlencode(args, quote_via=quote)}"

    def execute(self):
        if trakt_id := self.action_args.get("trakt_id"):
            self.handle_args(trakt_id=trakt_id)
            self._pop_keys()
            self.handle_path()
            self.log_action(trakt_id)

            xbmc.executebuiltin(self.action_type.format(path=self.action_path))
        else:
            self.log_error()
