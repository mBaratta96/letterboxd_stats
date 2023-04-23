from letterboxd_stats import tmdb
from letterboxd_stats import data
from letterboxd_stats import web_scraper as ws
import os
from letterboxd_stats import args, config

DATA_FILES = {"Watchlist": "watchlist.csv", "Diary": "diary.csv", "Ratings": "ratings.csv", "Lists": "lists"}


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
            tmdb.get_movie_detail(id, letterboxd_url)


def search_person(args_search: str):
    df, name = tmdb.get_person(args_search)
    path = os.path.expanduser(os.path.join(config["root_folder"], "static", "watched.csv"))
    check_path(path)
    movie_id, search_film = data.read_watched_films(df, path, name)
    letterboxd_url = ws.search_film(search_film)
    if movie_id is not None:
        tmdb.get_movie_detail(movie_id, ws.create_movie_url(letterboxd_url, "film_page"))


def search_film(args_search_film: str):
    film_url = ws.search_film(args_search_film, True)
    film_page_url = ws.create_movie_url(film_url, "film_page")
    tmdb.get_movie_detail(ws.get_tmdb_id(film_page_url, False), film_page_url)  # type: ignore
    answer = ws.select_optional_operation()
    if answer != "Exit":
        downloader = ws.Downloader()
        downloader.login()
        downloader.perform_operation(answer, film_url)


def get_data(args_limit, args_ascending, data_type):
    path = os.path.expanduser(os.path.join(config["root_folder"], "static", DATA_FILES[data_type]))
    check_path(path)
    letterboxd_url = (
        data.open_file(data_type, path, args_limit, args_ascending)
        if data_type != "Lists"
        else data.open_list(path, args_limit, args_ascending)
    )
    get_movie_detail_from_url(letterboxd_url, data_type == "Diary")


def main():
    if args.download:
        try_command(download_data, ())
    if args.search:
        try_command(search_person, (args.search,))
    if args.search_film:
        try_command(search_film, (args.search_film,))
    if args.watchlist:
        try_command(get_data, (args.limit, config["CLI"]["ascending"], "Watchlist"))
    if args.diary:
        try_command(get_data, (args.limit, config["CLI"]["ascending"], "Diary"))
    if args.ratings:
        try_command(get_data, (args.limit, config["CLI"]["ascending"], "Ratings"))
    if args.lists:
        try_command(get_data, (args.limit, config["CLI"]["ascending"], "Lists"))


if __name__ == "__main__":
    main()
