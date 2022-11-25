from tmdbv3api import TMDb, Person
import pandas as pd
from letterboxd_stats.cli import select_department
from config import config

tmdb = TMDb()
tmdb.api_key = config['TMDB']['api_key']
person = Person()


def get_person(name: str):
    search_result = person.search(name)[0]
    return search_result


def create_person_dataframe(search_result):
    p = person.details(search_result["id"])
    known_for_department = p['known_for_department']
    movie_credits = person.movie_credits(search_result["id"])
    list_of_films = [{
        "title": movie.get('title'),
        "release_date": movie.get('release_date'),
        "department": movie.get('department'),
    } for movie in movie_credits["crew"]]
    df = pd.DataFrame(list_of_films)
    department = select_department(
        df['department'].unique(), p['name'], known_for_department
    )
    df = df[df['department'] == department]
    df['release_date'] = pd.to_datetime(df['release_date'])
    df.sort_values(by="release_date", inplace=True)
    return df
