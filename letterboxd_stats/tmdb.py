from tmdbv3api import TMDb, Person, Movie
import pandas as pd
from letterboxd_stats.cli import select_department, select_search_result, print_film
from letterboxd_stats import config
from ascii_magic import AsciiArt

tmdb = TMDb()
tmdb.api_key = config["TMDB"]["api_key"]
person = Person()
movie = Movie()
IMAGE_URL = "https://www.themoviedb.org/t/p/w600_and_h900_bestv2"


def get_person(name: str):
    print(f"Searching for '{name}'")
    search_results = person.search(name)
    names = [result.name for result in search_results]  # type: ignore
    if len(names) == 0:
        raise Exception("No results for your search")
    result_index = select_search_result(names)  # type: ignore
    return search_results[result_index]


def create_person_dataframe(search_result) -> pd.DataFrame:
    p = person.details(search_result["id"])
    known_for_department = p["known_for_department"]
    movie_credits = person.movie_credits(search_result["id"])
    list_of_films = [
        {"title": m.title, "release_date": m.release_date, "department": m.department, "id": m.id}
        for m in movie_credits["crew"]
    ]
    df = pd.DataFrame(list_of_films)
    department = select_department(df["department"].unique(), p["name"], known_for_department)
    df = df[df["department"] == department]
    df = df.drop("department", axis=1)
    df["release_date"] = pd.to_datetime(df["release_date"])
    df.sort_values(by="release_date", inplace=True)
    return df


def download_poster(poster: str):
    art = AsciiArt.from_url(IMAGE_URL + poster)
    art.to_terminal(columns=180)


def get_movie_detail(movie_id: int):
    movie_details = movie.details(movie_id)
    poster = movie_details.get("poster_path")
    if poster is not None:
       download_poster(poster) 
    selected_details = {
        "title": movie_details["title"],
        "original_title": movie_details["original_title"],
        "runtime": movie_details["runtime"],
        "overview": movie_details["overview"],
        "release_date": movie_details["release_date"],
    }
    print_film(selected_details)
