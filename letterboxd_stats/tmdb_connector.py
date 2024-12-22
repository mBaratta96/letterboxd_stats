import pandas as pd
from pandarallel import pandarallel
from tmdbv3api.exceptions import TMDbException
from tmdbv3api.objs.account import AsObj
from typing import Any, Tuple
from tmdbv3api import TMDb, Person, Movie, Search
from letterboxd_stats import config

POSTER_URL_PREFIX = "https://www.themoviedb.org/t/p/w600_and_h900_bestv2"

tmdb = TMDb()
tmdb.api_key = config["TMDB"]["api_key"]
person = Person()
movie = Movie()
search = Search()
pandarallel.initialize(progress_bar=False, verbose=1)

def get_tmdb_poster_url(poster_path: str):
    """Generate URL for TMDB poster.
    """
    return POSTER_URL_PREFIX + poster_path

def get_movie_duration(tmdb_id: int) -> int:
    """Get movie duration from the TMDB api.
    https://developer.themoviedb.org/reference/movie-details
    """

    try:
        runtime = movie.details(tmdb_id).runtime  # type: ignore
    except TMDbException:
        runtime = 0
    return runtime

def search_tmdb_people(person_query: str) -> Any | AsObj:
    """Search TMDB's People database. Return results.
    """
    print(f"Searching for '{person_query}'")
    search_results = search.people({"query": person_query})
    if len([result.name for result in search_results]) == 0:
        raise Exception("No results found for your TMDB person search.")
    return search_results

def search_tmdb_movies(movie_query: str) -> Any | AsObj:
    """Search TMDB's Movie database. Return results.
    """
    print(f"Searching for movie '{movie_query}'")
    search_results = search.movies({"query": movie_query})
    if len([f"{result.title} ({result.release_date})" for result in search_results]) == 0:
        raise Exception("No results found for your TMDB movie search.")
    return search_results

def get_tmdb_person_and_movies(tmdb_person_id: str) -> Tuple[pd.DataFrame, str, str]:
    """Get information for a Person with the TMDB api. Return list of movies, name, and most known-for department.
    https://developer.themoviedb.org/reference/person-details
    https://developer.themoviedb.org/reference/person-movie-credits
    """
    person_ = person.details(tmdb_person_id)
    movie_credits = person.movie_credits(tmdb_person_id)
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


def get_all_tmdb_movie_details(tmdb_id: int, letterboxd_url=None) -> dict:
    """Creates dict of movie details fetched from TMDB API. Optionally include Letterboxd URL
    """
    movie_details = movie.details(tmdb_id)
    selected_details = {
        "Poster URL": get_tmdb_poster_url(movie_details.get("poster_path")),
        "Title": movie_details["title"],
        "Original Title": movie_details["original_title"],
        "Runtime": movie_details["runtime"],
        "Overview": movie_details["overview"],
        "Release Date": movie_details["release_date"],
    }
    if letterboxd_url:
        selected_details["Letterboxd URL"] = letterboxd_url

    return selected_details