from letterboxd_stats import tmdb
from letterboxd_stats import data
from letterboxd_stats import web_scraper as ws
import os
from letterboxd_stats import args, config


def try_command(command, args):
    try:
        command(*args)
    except Exception as e:
        print(e)


def check_path(path: str):
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"No Letterboxd data was found in {path}. Make sure the path is correct or run -d to download your data"
        )


def download_data():
    downloader = ws.Downloader()
    downloader.login()
    downloader.download_stats()


def get_movie_detail_from_url(letterboxd_url, is_diary=False):
    if letterboxd_url is not None:
        id = ws.get_tmdb_id(letterboxd_url, is_diary)
        if id is not None:
            tmdb.get_movie_detail(id)


def search_person(args_search: str):
    df, name = tmdb.get_person(args_search)
    path = os.path.expanduser(os.path.join(config["root_folder"], "static", "watched.csv"))
    check_path(path)
    movie_id = data.read_watched_films(df, path, name)
    if movie_id is not None:
        tmdb.get_movie_detail(movie_id)


def search_film(args_search_film: str):
    tmdb_id, film_url, film_title = ws.search_film(args_search_film)
    tmdb.get_movie_detail(tmdb_id, film_url)  # type: ignore
    answer = ws.select_optional_operation()
    if answer != "Exit":
        downloader = ws.Downloader()
        downloader.login()
        downloader.perform_operation(answer, film_url, film_title)


def get_wishlist(args_limit, args_ascending):
    path = os.path.expanduser(os.path.join(config["root_folder"], "static", "watchlist.csv"))
    check_path(path)
    letterboxd_url = data.open_file("Watchlist", path, args_limit, args_ascending)
    get_movie_detail_from_url(letterboxd_url)


def get_diary(args_limit, args_ascending):
    path = os.path.expanduser(os.path.join(config["root_folder"], "static", "diary.csv"))
    check_path(path)
    letterboxd_url = data.open_file("Diary", path, args_limit, args_ascending)
    get_movie_detail_from_url(letterboxd_url, True)


def get_ratings(args_limit, args_ascending):
    path = os.path.expanduser(os.path.join(config["root_folder"], "static", "ratings.csv"))
    check_path(path)
    letterboxd_url = data.open_file("Ratings", path, args_limit, args_ascending)
    get_movie_detail_from_url(letterboxd_url)


def get_lists(args_limit, args_ascending):
    path = os.path.expanduser(os.path.join(config["root_folder"], "static", "lists"))
    check_path(path)
    letterboxd_url = data.open_list(path, args_limit, args_ascending)
    get_movie_detail_from_url(letterboxd_url)


def main():
    if args.download:
        try_command(download_data, ())
    if args.search:
        try_command(search_person, (args.search,))
    if args.search_film:
        try_command(search_film, (args.search_film,))
    if args.wishlist:
        try_command(get_wishlist, (args.limit, config["CLI"]["ascending"]))
    if args.diary:
        try_command(get_diary, (args.limit, config["CLI"]["ascending"]))
    if args.ratings:
        try_command(get_ratings, (args.limit, config["CLI"]["ascending"]))
    if args.lists:
        try_command(get_lists, (args.limit, config["CLI"]["ascending"]))


if __name__ == "__main__":
    main()
