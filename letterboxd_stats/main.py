from letterboxd_stats.tmdb import get_person
from letterboxd_stats.data import read_watched_films
import os


if __name__ == '__main__':
    df = get_person("akira kurosawa")
    path = os.path.join(os.environ['ROOT_FOLDER'], 'static', 'watched.csv')
    df = read_watched_films(df, path)
    print(df)
