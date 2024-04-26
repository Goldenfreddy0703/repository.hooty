import sys


def context(argv):
    arg = argv[1]

    if arg == "quickResume":
        from resources.lib.action.plugin import QuickResume

        QuickResume().execute()
    elif arg == "shuffle":
        from resources.lib.action.plugin import ShufflePlay

        ShufflePlay().execute()
    elif arg == "playFromRandomPoint":
        from resources.lib.action.plugin import PlayFromRandomPoint

        PlayFromRandomPoint().execute()
    elif arg == "rescrape":
        from resources.lib.action.media import RescrapeItem

        RescrapeItem().execute()
    elif arg == "rescrape_ss":
        from resources.lib.action.media import RescrapeAndSourceSelect

        RescrapeAndSourceSelect().execute()
    elif arg == "sourceSelect":
        from resources.lib.action.media import SourceSelect

        SourceSelect().execute()
    elif arg == "findSimilar":
        from resources.lib.action.window import FindSimilar

        FindSimilar().execute()
    elif arg == "traktManager":
        from resources.lib.action.plugin import TraktManager

        TraktManager().execute()
    elif arg == "browseShow":
        from resources.lib.action.window import BrowseShow

        BrowseShow().execute()
    elif arg == "browseSeason":
        from resources.lib.action.window import BrowseSeason

        BrowseSeason().execute()
    else:
        from resources.lib.tools import log_error

        log_error(f"No context action found for {arg}.")


if __name__ == "__main__":
    context(sys.argv)
