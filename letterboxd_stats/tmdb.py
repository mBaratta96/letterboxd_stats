from dotenv import load_dotenv
from tmdbv3api import Person 
import pandas as pd

person = Person()

def get_person(name):
    result = person.search(name)[0] 
    p = person.details(result["id"])
    known_department = p["known_for_department"]
    
    movie_credits = person.movie_credits(result["id"])
    list_of_films = [{
        "id": movie.get('id'),
        "department": movie.get('department'),
        "title": movie.get('title'),
        "release_date": movie.get('release_date'),
        "overview": movie.get('overview')
    } for movie in movie_credits["crew"]]
   
    df = pd.DataFrame(list_of_films)
    df['release_date'] = pd.to_datetime(df['release_date'])
    df.sort_values(by="release_date", inplace=True)
    df = df[df["department"] == known_department]
    return df
