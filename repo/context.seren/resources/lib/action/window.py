from abc import ABCMeta
from urllib.parse import quote
from urllib.parse import urlencode

from resources.lib.action import ContextAction
from resources.lib.action import SEREN_ADDON_ID
from resources.lib.tools import url_quoted_action_args


class ContextWindowAction(ContextAction, metaclass=ABCMeta):
    @property
    def action_type(self):
        return "ActivateWindow(Videos,{path},return)"

    @property
    def keys_to_pop(self):
        return ["season", "trakt_season_id"]

    def handle_path(self):
        args = {"action": self.action, "action_args": url_quoted_action_args(self.action_args)}
        self.action_path = f"plugin://{SEREN_ADDON_ID}/?{urlencode(args, quote_via=quote)}"


class BrowseSeason(ContextWindowAction):
    @property
    def action(self):
        return "seasonEpisodes"

    @property
    def keys_to_pop(self):
        return ["season"]

    def handle_args(self, *args, **kwargs):
        self.action_args.update({"mediatype": "episode", "trakt_id": self.action_args.pop("trakt_season_id", None)})


class BrowseShow(ContextWindowAction):
    @property
    def action(self):
        return "showSeasons"

    def handle_args(self, *args, **kwargs):
        self.action_args.update(
            {
                "mediatype": "season",
                "trakt_id": self.action_args.pop("trakt_show_id", self.action_args.get("trakt_id", None)),
            }
        )


class FindSimilar(ContextWindowAction):
    def __init__(self):
        super().__init__()
        self.media_type = self.action_args.get("mediatype")

    @property
    def action(self):
        return "showsRelated" if self.media_type == "tvshow" else "moviesRelated"

    def handle_args(self, *args, **kwargs):
        self.action_args = kwargs.get("trakt_id")
