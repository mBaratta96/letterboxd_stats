from tmdbv3api import TMDb, Person, Movie
import pandas as pd
from letterboxd_stats import cli
from letterboxd_stats import config
from letterboxd_stats import web_scraper

tmdb = TMDb()
tmdb.api_key = config["TMDB"]["api_key"]
person = Person()
movie = Movie()


def get_person(name: str):
    print(f"Searching for '{name}'")
    search_results = person.search(name)
    names = [result.name for result in search_results]  # type: ignore
    if len(names) == 0:
        raise Exception("No results for your search")
    result_index = cli.select_search_result(names)  # type: ignore
    search_result = search_results[result_index]
    p = person.details(search_result["id"])
    known_for_department = p["known_for_department"]
    movie_credits = person.movie_credits(search_result["id"])
    list_of_films = [
        {"title": m.title, "release_date": m.release_date, "department": m.department, "id": m.id}
        for m in movie_credits["crew"]
    ]
    if len(list_of_films) == 0:
        raise ValueError("The selected person doesn't have any film.")
    df = pd.DataFrame(list_of_films)
    department = cli.select_value(
        df["department"].unique(), f"Select a department for {p['name']}", known_for_department
    )
    df = df[df["department"] == department]
    df = df.drop("department", axis=1)
    return df, p["name"]


def get_movie(movie_query: str):
    print(f"Searching for movie '{movie_query}'")
    search_results = movie.search(movie_query)
    titles = [f"{result.title} ({result.release_date})" for result in search_results]  # type: ignore
    if len(titles) == 0:
        raise Exception("No results for your search")
    result_index = cli.select_search_result(titles)  # type: ignore
    movie_id = search_results[result_index]["id"]
    get_movie_detail(movie_id)
    return search_results[result_index]


def get_movie_detail(movie_id: int):
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
        "Letterboxd URL": web_scraper.create_movie_url(movie_details["title"], "film_page"),
    }
    cli.print_film(selected_details)
