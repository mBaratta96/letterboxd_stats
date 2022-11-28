from letterboxd_stats.tmdb import get_person, create_person_dataframe
from letterboxd_stats.data import read_watched_films, show_wishlist, show_diary
from letterboxd_stats.cli import render_table
from letterboxd_stats.web_scraper import FirefoxWebDriver
import argparse
import os
from config import config

parser = argparse.ArgumentParser(
    prog="Letterboxd Stats",
    description="CLI tool to display Letterboxd statistics",
)
parser.add_argument("-s", "--search", help="Search for a director")
parser.add_argument(
    "-d",
    "--download",
    help="Download letterboxd data from your account",
    action="store_true",
)
parser.add_argument("-w", "--wishlist", help="show wishlist", action="store_true")
parser.add_argument("-l", "--limit", help="limit the number of items of your wishlist/diary", type=int)
parser.add_argument("-r", "--random", help="shuffle wishlist", action="store_true")
parser.add_argument("-D", "--diary", help="show diary", action="store_true")

if __name__ == "__main__":
    args = parser.parse_args()
    if args.download:
        ws = FirefoxWebDriver()
        ws.login()
        ws.download_stats()
        ws.close_webdriver()
    if args.search:
        search_result = get_person(args.search)
        name = search_result["name"]
        df = create_person_dataframe(search_result)
        path = os.path.join(config["root_folder"], "static", "watched.csv")
        df = read_watched_films(df, path)
        render_table(df, name)
    if args.wishlist:
        path = os.path.join(config["root_folder"], "static", "watchlist.csv")
        show_wishlist(path, args.random, args.limit)
    if args.diary:
        path = os.path.join(config["root_folder"], "static", "diary.csv")
        show_diary(path, args.limit)
