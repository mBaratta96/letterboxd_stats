from typing import Any, Tuple
from tmdbv3api import TMDb, Person, Movie, Search
from tmdbv3api.exceptions import TMDbException
import pandas as pd
from tmdbv3api.objs.account import AsObj
from letterboxd_stats import cli
from letterboxd_stats import config

tmdb = TMDb()
tmdb.api_key = config["TMDB"]["api_key"]
person = Person()
movie = Movie()
search = Search()


def get_person(name: str) -> Tuple[pd.DataFrame, str]:
    """Search the director with the TMDB api. Get all the movies.
    https://developer.themoviedb.org/reference/person-details
    https://developer.themoviedb.org/reference/person-movie-credits
    """

    print(f"Searching for '{name}'")
    search_results = search.people({"query": name})
    names = [result.name for result in search_results]  # type: ignore
    if len(names) == 0:
        raise Exception("No results for your search")
    result_index = cli.select_search_result(names)  # type: ignore
    search_result = search_results[result_index]
    p = person.details(search_result["id"])
    known_for_department = p["known_for_department"]
    movie_credits = person.movie_credits(search_result["id"])
    list_of_films = [
        {
            "Id": m.id,
            "Title": m.title,
            "Release Date": m.release_date,
            "Department": m.department,
        }
        for m in movie_credits["crew"]
    ]
    if len(list_of_films) == 0:
        raise ValueError("The selected person doesn't have any film.")
    df = pd.DataFrame(list_of_films).set_index("Id")
    department = cli.select_value(
        df["Department"].unique(), f"Select a department for {p['name']}", known_for_department
    )
    df = df[df["Department"] == department]
    df = df.drop("Department", axis=1)
    # person.details provides movies without time duration. If the user wants<S-D-A>
    # (since this slows down the process) get with the movie.details API.
    if config["TMDB"]["get_list_runtimes"] is True:
        df["Duration"] = df.index.to_series().map(get_film_duration)  # type: ignore
    return df, p["name"]


def get_movie(movie_query: str) -> Any | AsObj:
    print(f"Searching for movie '{movie_query}'")
    search_results = search.movies({"query": movie_query})
    titles = [f"{result.title} ({result.release_date})" for result in search_results]  # type: ignore
    if len(titles) == 0:
        raise Exception("No results for your search")
    result_index = cli.select_search_result(titles)  # type: ignore
    movie_id = search_results[result_index]["id"]
    get_movie_detail(movie_id)
    return search_results[result_index]


def get_movie_detail(movie_id: int, letterboxd_url=None):
    movie_details = movie.details(movie_id)
    poster = movie_details.get("poster_path")
    if poster is not None:
        cli.download_poster(poster)
    selected_details = {
        "Title": movie_details["title"],
        "Original Title": movie_details["original_title"],
        "Runtime": movie_details["runtime"],
        "Overview": movie_details["overview"],
        "Release Date": movie_details["release_date"],
    }
    if letterboxd_url:
        selected_details["Letterboxd Url"] = letterboxd_url
    cli.print_film(selected_details)


def get_film_duration(tmdb_id: int) -> int:
    """Get film duration from the TMDB api.
    https://developer.themoviedb.org/reference/movie-details
    """

    try:
        runtime = movie.details(tmdb_id).runtime  # type: ignore
    except TMDbException:
        runtime = 0
    return runtime
