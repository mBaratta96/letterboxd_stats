from letterboxd_stats.tmdb import get_person, create_person_dataframe, get_movie_detail
from letterboxd_stats import data
from letterboxd_stats.cli import select_movie_id, select_movie
from letterboxd_stats.web_scraper import Downloader, get_tmdb_id
import os
from letterboxd_stats import args, config


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


def main():
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


if __name__ == "__main__":
    main()
