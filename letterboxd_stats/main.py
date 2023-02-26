from letterboxd_stats.tmdb import get_person, create_person_dataframe, get_movie_detail
from letterboxd_stats import data
from letterboxd_stats.cli import select_movie_id, select_movie
from letterboxd_stats.web_scraper import Downloader, get_tmdb_id
import argparse
import os
from letterboxd_stats import config

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
parser.add_argument("-R", "--ratings", help="show rating", action="store_true")

def get_movie_detail_from_url(df, is_diary=False):
    df.rename(columns={"Name": "title", "Letterboxd URI": "url"}, inplace=True)
    link = select_movie(df[["title", "url"]]) 
    id = get_tmdb_id(link, is_diary)
    if id is not None:
        get_movie_detail(id)
        

def search_film(args_search: str):
    search_result = get_person(args_search)
    name = search_result["name"]
    df = create_person_dataframe(search_result)
    path = os.path.join(config["root_folder"], "static", "watched.csv")
    data.read_watched_films(df, path, name)
    movie_id = select_movie_id(df[["id", "title"]])
    if movie_id is not None:
        get_movie_detail(movie_id)

def get_wishlist(args_random, args_limit):
    path = os.path.join(config["root_folder"], "static", "watchlist.csv")
    df = data.show_wishlist(path, args_random, args_limit)
    get_movie_detail_from_url(df)

def get_diary(args_limit):
    path = os.path.join(config["root_folder"], "static", "diary.csv")
    df = data.show_diary(path, args_limit)
    get_movie_detail_from_url(df, True)

def get_ratings(args_limit):
    path = os.path.join(config["root_folder"], "static", "ratings.csv")
    df = data.show_ratings(path, args_limit)
    get_movie_detail_from_url(df)


if __name__ == "__main__":
    args = parser.parse_args()
    if args.download:
        ws = Downloader()
        ws.login()
        ws.download_stats()
    if args.search:
        search_film(args.search)
    if args.wishlist:
        get_wishlist(args.random, args.limit)
    if args.diary:
        get_diary(args.limit) 
    if args.ratings:
       get_ratings(args.limit) 

