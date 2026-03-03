"""
Anime menus module for Seren.
Provides dedicated anime TV shows and movies browsing functionality using Trakt's anime genre filter.
Mirrors the Discover TV Shows/Movies menu structure with both media types.
"""

import datetime
from functools import cached_property

from resources.lib.modules.globals import g


class Menus:
    """Anime menus class providing anime browsing functionality."""

    def __init__(self):
        self.page_limit = g.get_int_setting("item.limit")
        self.page_start = (g.PAGE - 1) * self.page_limit
        self.page_end = g.PAGE * self.page_limit
        self.anime_genre = "anime"

    @cached_property
    def shows_database(self):
        from resources.lib.database.trakt_sync.shows import TraktSyncDatabase

        return TraktSyncDatabase()

    @cached_property
    def movies_database(self):
        from resources.lib.database.trakt_sync.movies import TraktSyncDatabase

        return TraktSyncDatabase()

    @cached_property
    def list_builder(self):
        from resources.lib.modules.list_builder import ListBuilder

        return ListBuilder()

    ######################################################
    # DISCOVER ANIME - Main Menu (TV Shows + Movies)
    ######################################################

    def discover_anime(self):
        """Main discover anime menu with both TV shows and movies."""
        # Popular
        g.add_directory_item(
            g.get_language_string(30682),  # "Popular (TV Shows)"
            action="animeShowsPopular",
            description=g.get_language_string(30696),
            menu_item=g.create_icon_dict("shows_popular", g.ICONS_PATH),
        )
        g.add_directory_item(
            g.get_language_string(30683),  # "Popular (Movies)"
            action="animeMoviesPopular",
            description=g.get_language_string(30697),
            menu_item=g.create_icon_dict("movies_popular", g.ICONS_PATH),
        )
        # Popular Recent
        g.add_directory_item(
            g.get_language_string(30710),  # "Popular Recent (TV Shows)"
            action="animeShowsPopularRecent",
            description=g.get_language_string(30714),
            menu_item=g.create_icon_dict("shows_recent", g.ICONS_PATH),
        )
        g.add_directory_item(
            g.get_language_string(30711),  # "Popular Recent (Movies)"
            action="animeMoviesPopularRecent",
            description=g.get_language_string(30715),
            menu_item=g.create_icon_dict("movies_recent", g.ICONS_PATH),
        )
        # Trending
        g.add_directory_item(
            g.get_language_string(30684),  # "Trending (TV Shows)"
            action="animeShowsTrending",
            description=g.get_language_string(30698),
            menu_item=g.create_icon_dict("shows_trending", g.ICONS_PATH),
        )
        g.add_directory_item(
            g.get_language_string(30685),  # "Trending (Movies)"
            action="animeMoviesTrending",
            description=g.get_language_string(30699),
            menu_item=g.create_icon_dict("movies_trending", g.ICONS_PATH),
        )
        # Trending Recent
        g.add_directory_item(
            g.get_language_string(30712),  # "Trending Recent (TV Shows)"
            action="animeShowsTrendingRecent",
            description=g.get_language_string(30716),
            menu_item=g.create_icon_dict("shows_recent", g.ICONS_PATH),
        )
        g.add_directory_item(
            g.get_language_string(30713),  # "Trending Recent (Movies)"
            action="animeMoviesTrendingRecent",
            description=g.get_language_string(30717),
            menu_item=g.create_icon_dict("movies_recent", g.ICONS_PATH),
        )
        # New
        g.add_directory_item(
            g.get_language_string(30686),  # "New (TV Shows)"
            action="animeShowsNew",
            description=g.get_language_string(30700),
            menu_item=g.create_icon_dict("shows_new", g.ICONS_PATH),
        )
        g.add_directory_item(
            g.get_language_string(30687),  # "New (Movies)"
            action="animeMoviesNew",
            description=g.get_language_string(30701),
            menu_item=g.create_icon_dict("movies_new", g.ICONS_PATH),
        )
        # Most Played
        g.add_directory_item(
            g.get_language_string(30688),  # "Most Played (TV Shows)"
            action="animeShowsPlayed",
            description=g.get_language_string(30702),
            menu_item=g.create_icon_dict("shows_played", g.ICONS_PATH),
        )
        g.add_directory_item(
            g.get_language_string(30689),  # "Most Played (Movies)"
            action="animeMoviesPlayed",
            description=g.get_language_string(30703),
            menu_item=g.create_icon_dict("movies_played", g.ICONS_PATH),
        )
        # Most Watched
        g.add_directory_item(
            g.get_language_string(30690),  # "Most Watched (TV Shows)"
            action="animeShowsWatched",
            description=g.get_language_string(30704),
            menu_item=g.create_icon_dict("shows_watched", g.ICONS_PATH),
        )
        g.add_directory_item(
            g.get_language_string(30691),  # "Most Watched (Movies)"
            action="animeMoviesWatched",
            description=g.get_language_string(30705),
            menu_item=g.create_icon_dict("movies_watched", g.ICONS_PATH),
        )
        # Most Collected
        g.add_directory_item(
            g.get_language_string(30692),  # "Most Collected (TV Shows)"
            action="animeShowsCollected",
            description=g.get_language_string(30706),
            menu_item=g.create_icon_dict("shows_collected", g.ICONS_PATH),
        )
        g.add_directory_item(
            g.get_language_string(30693),  # "Most Collected (Movies)"
            action="animeMoviesCollected",
            description=g.get_language_string(30707),
            menu_item=g.create_icon_dict("movies_collected", g.ICONS_PATH),
        )
        # Anticipated
        if not g.get_bool_setting("general.hideUnAired"):
            g.add_directory_item(
                g.get_language_string(30694),  # "Anticipated (TV Shows)"
                action="animeShowsAnticipated",
                description=g.get_language_string(30708),
                menu_item=g.create_icon_dict("shows_anticipated", g.ICONS_PATH),
            )
            g.add_directory_item(
                g.get_language_string(30695),  # "Anticipated (Movies)"
                action="animeMoviesAnticipated",
                description=g.get_language_string(30709),
                menu_item=g.create_icon_dict("movies_anticipated", g.ICONS_PATH),
            )
        g.close_directory(g.CONTENT_MENU)

    ######################################################
    # ANIME TV SHOWS ENDPOINTS
    ######################################################

    def anime_shows_popular(self):
        """List popular anime TV shows."""
        trakt_list = self.shows_database.extract_trakt_page(
            "shows/popular",
            genres=self.anime_genre,
            page=g.PAGE,
            extended="full",
        )
        if trakt_list is None:
            g.cancel_directory()
            return
        self.list_builder.show_list_builder(trakt_list, next_args=self.anime_genre)

    def anime_shows_trending(self):
        """List trending anime TV shows."""
        trakt_list = self.shows_database.extract_trakt_page(
            "shows/trending",
            genres=self.anime_genre,
            page=g.PAGE,
            extended="full",
        )
        if trakt_list is None:
            g.cancel_directory()
            return
        self.list_builder.show_list_builder(trakt_list, next_args=self.anime_genre)

    def anime_shows_popular_recent(self):
        """List recently aired popular anime TV shows."""
        year = datetime.datetime.now().year
        trakt_list = self.shows_database.extract_trakt_page(
            "shows/popular",
            genres=self.anime_genre,
            years=f"{year - 1}-{year}",
            page=g.PAGE,
            extended="full",
        )
        if trakt_list is None:
            g.cancel_directory()
            return
        self.list_builder.show_list_builder(trakt_list, next_args=self.anime_genre)

    def anime_shows_trending_recent(self):
        """List recently aired trending anime TV shows."""
        year = datetime.datetime.now().year
        trakt_list = self.shows_database.extract_trakt_page(
            "shows/trending",
            genres=self.anime_genre,
            years=f"{year - 1}-{year}",
            page=g.PAGE,
            extended="full",
        )
        if trakt_list is None:
            g.cancel_directory()
            return
        self.list_builder.show_list_builder(trakt_list, next_args=self.anime_genre)

    def anime_shows_new(self):
        """List new anime TV shows (premiering this year)."""
        year = datetime.datetime.now().year
        trakt_list = self.shows_database.extract_trakt_page(
            "shows/popular",
            genres=self.anime_genre,
            years=str(year),
            page=g.PAGE,
            extended="full",
        )
        if trakt_list is None:
            g.cancel_directory()
            return
        self.list_builder.show_list_builder(trakt_list, next_args=self.anime_genre)

    def anime_shows_played(self):
        """List most played anime TV shows."""
        trakt_list = self.shows_database.extract_trakt_page(
            "shows/played",
            genres=self.anime_genre,
            page=g.PAGE,
            extended="full",
        )
        if trakt_list is None:
            g.cancel_directory()
            return
        self.list_builder.show_list_builder(trakt_list, next_args=self.anime_genre)

    def anime_shows_watched(self):
        """List most watched anime TV shows."""
        trakt_list = self.shows_database.extract_trakt_page(
            "shows/watched",
            genres=self.anime_genre,
            page=g.PAGE,
            extended="full",
        )
        if trakt_list is None:
            g.cancel_directory()
            return
        self.list_builder.show_list_builder(trakt_list, next_args=self.anime_genre)

    def anime_shows_collected(self):
        """List most collected anime TV shows."""
        trakt_list = self.shows_database.extract_trakt_page(
            "shows/collected",
            genres=self.anime_genre,
            page=g.PAGE,
            extended="full",
        )
        if trakt_list is None:
            g.cancel_directory()
            return
        self.list_builder.show_list_builder(trakt_list, next_args=self.anime_genre)

    def anime_shows_anticipated(self):
        """List anticipated anime TV shows."""
        trakt_list = self.shows_database.extract_trakt_page(
            "shows/anticipated",
            genres=self.anime_genre,
            page=g.PAGE,
            extended="full",
        )
        if trakt_list is None:
            g.cancel_directory()
            return
        self.list_builder.show_list_builder(trakt_list, next_args=self.anime_genre)

    ######################################################
    # ANIME MOVIES ENDPOINTS
    ######################################################

    def anime_movies_popular(self):
        """List popular anime movies."""
        trakt_list = self.movies_database.extract_trakt_page(
            "movies/popular",
            genres=self.anime_genre,
            page=g.PAGE,
            extended="full",
        )
        if trakt_list is None:
            g.cancel_directory()
            return
        self.list_builder.movie_menu_builder(trakt_list, next_args=self.anime_genre)

    def anime_movies_trending(self):
        """List trending anime movies."""
        trakt_list = self.movies_database.extract_trakt_page(
            "movies/trending",
            genres=self.anime_genre,
            page=g.PAGE,
            extended="full",
        )
        if trakt_list is None:
            g.cancel_directory()
            return
        self.list_builder.movie_menu_builder(trakt_list, next_args=self.anime_genre)

    def anime_movies_popular_recent(self):
        """List recently released popular anime movies."""
        year = datetime.datetime.now().year
        trakt_list = self.movies_database.extract_trakt_page(
            "movies/popular",
            genres=self.anime_genre,
            years=f"{year - 1}-{year}",
            page=g.PAGE,
            extended="full",
        )
        if trakt_list is None:
            g.cancel_directory()
            return
        self.list_builder.movie_menu_builder(trakt_list, next_args=self.anime_genre)

    def anime_movies_trending_recent(self):
        """List recently released trending anime movies."""
        year = datetime.datetime.now().year
        trakt_list = self.movies_database.extract_trakt_page(
            "movies/trending",
            genres=self.anime_genre,
            years=f"{year - 1}-{year}",
            page=g.PAGE,
            extended="full",
        )
        if trakt_list is None:
            g.cancel_directory()
            return
        self.list_builder.movie_menu_builder(trakt_list, next_args=self.anime_genre)

    def anime_movies_new(self):
        """List new anime movies (released this year)."""
        year = datetime.datetime.now().year
        trakt_list = self.movies_database.extract_trakt_page(
            "movies/popular",
            genres=self.anime_genre,
            years=str(year),
            page=g.PAGE,
            extended="full",
        )
        if trakt_list is None:
            g.cancel_directory()
            return
        self.list_builder.movie_menu_builder(trakt_list, next_args=self.anime_genre)

    def anime_movies_played(self):
        """List most played anime movies."""
        trakt_list = self.movies_database.extract_trakt_page(
            "movies/played",
            genres=self.anime_genre,
            page=g.PAGE,
            extended="full",
        )
        if trakt_list is None:
            g.cancel_directory()
            return
        self.list_builder.movie_menu_builder(trakt_list, next_args=self.anime_genre)

    def anime_movies_watched(self):
        """List most watched anime movies."""
        trakt_list = self.movies_database.extract_trakt_page(
            "movies/watched",
            genres=self.anime_genre,
            page=g.PAGE,
            extended="full",
        )
        if trakt_list is None:
            g.cancel_directory()
            return
        self.list_builder.movie_menu_builder(trakt_list, next_args=self.anime_genre)

    def anime_movies_collected(self):
        """List most collected anime movies."""
        trakt_list = self.movies_database.extract_trakt_page(
            "movies/collected",
            genres=self.anime_genre,
            page=g.PAGE,
            extended="full",
        )
        if trakt_list is None:
            g.cancel_directory()
            return
        self.list_builder.movie_menu_builder(trakt_list, next_args=self.anime_genre)

    def anime_movies_anticipated(self):
        """List anticipated anime movies."""
        trakt_list = self.movies_database.extract_trakt_page(
            "movies/anticipated",
            genres=self.anime_genre,
            page=g.PAGE,
            extended="full",
        )
        if trakt_list is None:
            g.cancel_directory()
            return
        self.list_builder.movie_menu_builder(trakt_list, next_args=self.anime_genre)
