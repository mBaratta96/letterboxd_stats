import pandas as pd
from pandarallel import pandarallel
from tmdbv3api.exceptions import TMDbException
from tmdbv3api.objs.account import AsObj
from typing import Any, Tuple
from tmdbv3api import TMDb, Person, Movie, Search

POSTER_URL_PREFIX = "https://www.themoviedb.org/t/p/w600_and_h900_bestv2"


class TMDbAPI:
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
    def get_tmdb_poster_url(poster_path: str):
        """
        Construct the full URL for a movie poster.
        """
        if poster_path is None:
            return None
        return POSTER_URL_PREFIX + poster_path

    def get_movie_runtime(self, tmdb_id: int) -> int:
        """
        Fetch the runtime of a movie using its TMDB ID.
        """

        try:
            runtime = self.movie.details(tmdb_id).runtime  # type: ignore
        except TMDbException:
            runtime = 0
        return runtime

    def search_tmdb_people(self, person_query: str) -> Any | AsObj:
        """
        Search for people on TMDB by name. Returns all search results.
        """
        print(f"Searching for '{person_query}'")
        search_results = self.search.people({"query": person_query})
        if len([result.name for result in search_results]) == 0:
            raise Exception("No results found for your TMDB person search.")
        return search_results

    def search_tmdb_movies(self, movie_query: str) -> Any | AsObj:
        """Search TMDB's Movie database. Return results.
        """
        print(f"Searching for movie '{movie_query}'")
        search_results = self.search.movies({"query": movie_query})
        if len([f"{result.title} ({result.release_date})" for result in search_results]) == 0:
            raise Exception("No results found for your TMDB movie search.")
        return search_results

    def get_tmdb_person_and_movies(self, tmdb_person_id: str) -> Tuple[pd.DataFrame, str, str]:
        """
        Fetch detailed information about a person. Returns list of movies, name, and most known-for department.
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


    def get_all_tmdb_movie_details(self, tmdb_id: int, letterboxd_url=None) -> dict:
        """Creates dict of movie details fetched from TMDB API. Optionally include Letterboxd URL
        """
        movie_details = self.movie.details(tmdb_id)

        selected_details = {
            "Title": movie_details["title"],
            "Original Title": movie_details["original_title"],
            "Runtime": movie_details["runtime"],
            "Overview": movie_details["overview"],
            "Release Date": movie_details["release_date"],
        }

        poster_url = self.get_tmdb_poster_url(movie_details.get("poster_path"))

        if poster_url:
            selected_details["Poster"] = poster_url
        
        if letterboxd_url:
            selected_details["Letterboxd URL"] = letterboxd_url

        return selected_details