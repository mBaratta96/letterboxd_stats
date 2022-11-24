from letterboxd_stats.tmdb import get_person, create_person_dataframe
from letterboxd_stats.data import read_watched_films
from letterboxd_stats.cli import render_table
from letterboxd_stats import web_scraper as ws
import argparse
import os

parser = argparse.ArgumentParser(
    prog='Letterboxd Stats', description="CLI tool to display Letterboxd statistics")
parser.add_argument('-s', '--search', help="Search for a director")
parser.add_argument('-d', '--download',
                    help="Download letterboxd data from your account", action="store_true")

if __name__ == '__main__':
    args = parser.parse_args()
    if args.download:
        ws.login()
        ws.download_stats()
        ws.extract_data()
    search_result = get_person(args.search)
    name = search_result["name"]
    df = create_person_dataframe(search_result)
    path = os.path.join(os.environ['ROOT_FOLDER'], 'static', 'watched.csv')
    df = read_watched_films(df, path)
    render_table(df, name)
