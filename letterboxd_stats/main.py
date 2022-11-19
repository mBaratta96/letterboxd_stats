from letterboxd_stats.tmdb import get_person
from letterboxd_stats.data import read_watched_films
from letterboxd_stats.cli import render_table
import os


if __name__ == '__main__':
    df, name = get_person("akira kurosawa")
    path = os.path.join(os.environ['ROOT_FOLDER'], 'static', 'watched.csv')
    df = read_watched_films(df, path)
    render_table(df, name)
