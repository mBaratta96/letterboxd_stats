from letterboxd_stats.tmdb import get_person
from letterboxd_stats.data import read_watched_films
from letterboxd_stats.cli import render_table
from letterboxd_stats.web_scraper import login
import argparse
import os

parser = argparse.ArgumentParser(prog='Letterboxd Stats', description="CLI tool to display Letterboxd statistics")
parser.add_argument('-s', '--search')

if __name__ == '__main__':
    args = parser.parse_args()
    df, name = get_person(args.search)
    path = os.path.join(os.environ['ROOT_FOLDER'], 'static', 'watched.csv')
    df = read_watched_films(df, path)
    render_table(df, name)
    login()
