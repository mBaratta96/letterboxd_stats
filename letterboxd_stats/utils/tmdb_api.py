"""
TMDbAPI Module
==============

This module provides a wrapper around the TMDb API to facilitate fetching and
managing data related to movies, people, and their associated details. It uses
the `tmdbv3api` library for API interactions and pandas for data handling.

Classes:
--------
- TMDbAPI: A wrapper around the TMDb API providing utility methods for fetching
    movie details, person details, and performing searches.

Features:
---------
1. **Movie Details**:
   - Fetch runtime and detailed metadata for movies using TMDb IDs.
   - Construct URLs for poster images.

2. **Person Details**:
   - Search for people by name.
   - Fetch detailed information about a person, including their movie credits.

3. **Search Functionality**:
   - Perform searches for movies and people using TMDb's search endpoints.

"""

import logging
from typing import Any, Tuple

import pandas as pd
from pandarallel import pandarallel
from tmdbv3api import Movie, Person, Search, TMDb
from tmdbv3api.exceptions import TMDbException
from tmdbv3api.objs.account import AsObj

logger = logging.getLogger(__name__)


POSTER_URL_PREFIX = "https://www.themoviedb.org/t/p/w600_and_h900_bestv2"

class TMDbAPI:

    """
    A wrapper around the TMDb API, providing utility methods for fetching movie and
    person details, performing searches, and constructing URLs for movie posters.

    Attributes:
    -----------
    - tmdb: Instance of the `TMDb` class for API configuration.
    - person: Instance of the `Person` class for fetching person-related data.
    - movie: Instance of the `Movie` class for fetching movie-related data.
    - search: Instance of the `Search` class for performing TMDb searches.

    Methods:
    --------
    - __init__(api_key: str):
        Initialize the TMDb API wrapper with the provided API key.

    - _get_tmdb_poster_url(poster_path: str) -> str | None:
        Construct the full URL for a movie poster.

    - fetch_movie_runtime(tmdb_id: int) -> int:
        Fetch the runtime of a movie using its TMDb ID. Returns 0 if not found.

    - fetch_person_details(tmdb_person_id: str) -> Tuple[pd.DataFrame, str, str]:
        Fetch detailed information about a person, including their list of movies,
        name, and most known-for department.

    - fetch_movie_details(tmdb_id: int, letterboxd_url: str | None = None) -> dict:
        Fetch detailed metadata for a movie by its TMDb ID.

    - search_tmdb_people(person_query: str) -> Any | AsObj:
        - Search for people in TMDb by name.
        - Returns all search results or raises ValueError if none are found.

    - search_tmdb_movies(movie_query: str) -> Any | AsObj:
        - Search for movies in TMDb by title.
        - Returns all search results or raises ValueError if none are found.
    """
    def __init__(self, api_key: str):
        """
        Initialize the TMDb API wrapper and related objects.
        """
        self.tmdb = TMDb()
        self.tmdb.api_key = api_key
        self.person = Person()
        self.movie = Movie()
        self.search = Search()
        pandarallel.initialize(progress_bar=False, verbose=1)

    @staticmethod
    def _get_tmdb_poster_url(poster_path: str):
        """
        Construct the full URL for a movie poster.
        """
        if poster_path is None:
            return None
        return POSTER_URL_PREFIX + poster_path

    def fetch_movie_runtime(self, tmdb_id: int) -> int:
        """
        Fetch the runtime of a movie using its TMDB ID.
        """
        try:
            runtime=getattr(self.movie.details(tmdb_id), "runtime", None)
        except TMDbException:
            runtime = 0
        return runtime

    def fetch_person_details(self, tmdb_person_id: str) -> Tuple[pd.DataFrame, str, str]:
        """
        Fetch detailed information about a person.
        Returns list of movies, name, and most known-for department.

        https://developer.themoviedb.org/reference/person-details
        https://developer.themoviedb.org/reference/person-movie-credits
        """

        person_ = self.person.details(tmdb_person_id)
        movie_credits = self.person.movie_credits(tmdb_person_id)
        list_of_movies = [
            {
                "Id": movie_.id,
                "Title": movie_.title,
                "Release Date": movie_.release_date,
                "Department": movie_.department,
            }
            for movie_ in movie_credits["crew"]
        ]
        if len(list_of_movies) == 0:
            raise ValueError("The selected person doesn't have any film.")
        df = pd.DataFrame(list_of_movies).set_index("Id")
        return df, person_["name"], person_["known_for_department"]


    def fetch_movie_details(self, tmdb_id: int, letterboxd_url=None) -> dict:
        """
        Creates dict of movie details fetched from TMDB API.
        Optionally include Letterboxd URL
        """
        movie_details = self.movie.details(tmdb_id)

        selected_details = {
            "Title": movie_details["title"],
            "Original Title": movie_details["original_title"],
            "Runtime": movie_details["runtime"],
            "Overview": movie_details["overview"],
            "Release Date": movie_details["release_date"],
        }

        poster_url = self._get_tmdb_poster_url(movie_details.get("poster_path"))

        if poster_url:
            selected_details["Poster"] = poster_url

        if letterboxd_url:
            selected_details["Letterboxd URL"] = letterboxd_url

        return selected_details

    def search_tmdb_people(self, person_query: str) -> Any | AsObj:
        """
        Search for people on TMDB by name. Returns all search results.
        """
        logger.info("Searching TMDB for person named '%s'", person_query)
        search_results = self.search.people({"query": person_query})
        if len([result.name for result in search_results]) == 0:
            raise ValueError("No results found for your TMDB person search.")
        return search_results

    def search_tmdb_movies(self, movie_query: str) -> Any | AsObj:
        """Search TMDB's Movie database by title. Return results.
        """
        logger.info("Searching TMDB for movie '%s'",movie_query)
        search_results = self.search.movies({"query": movie_query})
        if len([f"{result.title} ({result.release_date})" for result in search_results]) == 0:
            raise ValueError("No results found for your TMDB movie search.")
        return search_results
