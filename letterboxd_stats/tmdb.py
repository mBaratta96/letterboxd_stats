from tmdbv3api import TMDb, Person, Movie
import pandas as pd
from letterboxd_stats import config
from typing import Tuple

tmdb = TMDb()
tmdb.api_key = config["TMDB"]["api_key"]
person = Person()
movie = Movie()


def get_person(name: str):
    print(f"Searching for '{name}'")
    search_results = person.search(name)
    if len(search_results) == 0:
        raise Exception("No results for your search")
    return search_results


def get_movie(movie_query: str):
    print(f"Searching for movie '{movie_query}'")
    search_results = movie.search(movie_query)
    if len(search_results) == 0:
        raise Exception("No results for your search")
    return search_results


def create_person_dataframe(search_result) -> Tuple[pd.DataFrame, str]:
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
    df["release_date"] = pd.to_datetime(df["release_date"])
    df.sort_values(by="release_date", inplace=True)
    return df, known_for_department


def get_movie_detail(movie_id: int):
    movie_details = movie.details(movie_id)
    selected_details = {
        "title": movie_details["title"],
        "original_title": movie_details["original_title"],
        "runtime": movie_details["runtime"],
        "overview": movie_details["overview"],
        "release_date": movie_details["release_date"],
        "poster": movie_details.get("poster"),
    }
    return selected_details
