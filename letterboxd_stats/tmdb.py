from tmdbv3api import TMDb, Person, Movie, Search
import pandas as pd
from letterboxd_stats import cli
from letterboxd_stats import config

tmdb = TMDb()
tmdb.api_key = config["TMDB"]["api_key"]
person = Person()
movie = Movie()
search = Search()


def get_person(name: str):
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
            "Title": m.title,
            "Release Date": m.release_date,
            "Department": m.department,
            "Id": m.id,
        }
        for m in movie_credits["crew"]
    ]
    if len(list_of_films) == 0:
        raise ValueError("The selected person doesn't have any film.")
    df = pd.DataFrame(list_of_films)
    department = cli.select_value(
        df["Department"].unique(), f"Select a department for {p['name']}", known_for_department
    )
    df = df[df["Department"] == department]
    df = df.drop("Department", axis=1)
    if config["TMDB"]["get_list_runtimes"] is True:
        df["Duration"] = df.apply(lambda row: movie.details(row["Id"]).runtime, axis=1)  # type: ignore
    return df, p["name"]


def get_movie(movie_query: str):
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


def get_film_duration(film: str, year: int):
    search_results = search.movies({"query": film, "year": year})
    if len(search_results) > 0:
        first_result = search_results[0]
        return movie.details(first_result.id).runtime  # type: ignore
    return 0
