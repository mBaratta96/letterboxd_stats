import os
import sys

from letterboxd_stats import tmdb
from letterboxd_stats import data
from letterboxd_stats import web_scraper as ws
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
    """Download exported data you find in the import/export section of your Letterboxd profile"""

    connector = ws.Connector()
    connector.login()
    connector.download_stats()


def search_person(args_search: str):
    """Search for a director, list his/her films and check if you have watched them."""

    df, name = tmdb.get_person(args_search)
    path = os.path.expanduser(os.path.join(config["root_folder"], "static", "watched.csv"))
    check_path(path)
    df = data.read_watched_films(df, path, name)
    film = data.select_film_of_person(df)
    # We want to print the link of the selected film. This has to be retrieved from the search page.
    while film is not None:
        search_film_query = f"{film['Title']} {film['Release Date'].year}"  # type: ignore
        title_url = ws.get_lb_title(search_film_query)
        tmdb.get_movie_detail(int(film.name), ws.create_lb_url(title_url, "film_page"))  # type: ignore
        film = data.select_film_of_person(df)


def search_film(args_search_film: str):
    title_url = ws.get_lb_title(args_search_film, True)
    film_url = ws.create_lb_url(title_url, "film_page")
    tmdb.get_movie_detail(ws.get_tmdb_id(film_url), film_url)  # type: ignore
    answer = ws.select_optional_operation()
    if answer != "Exit":
        connector = ws.Connector()
        connector.login()
        connector.perform_operation(answer, title_url)


def display_data(args_limit: int, args_ascending: bool, data_type: str):
    """Load and show on the CLI different .csv files that you have downloaded with the -d flag."""

    path = os.path.expanduser(os.path.join(config["root_folder"], "static", DATA_FILES[data_type]))
    check_path(path)
    letterboxd_url = (
        data.open_file(data_type, path, args_limit, args_ascending)
        if data_type != "Lists"
        else data.open_list(path, args_limit, args_ascending)
    )
    # If you select a film, show its details.
    if letterboxd_url is not None:
        id = ws.get_tmdb_id(letterboxd_url, data_type == "diary")
        if id is not None:
            tmdb.get_movie_detail(id, letterboxd_url)


def main():
    try:
        if args.download:
            try_command(download_data, ())
        if args.search:
            try_command(search_person, (args.search,))
        if args.search_film:
            try_command(search_film, (args.search_film,))
        if args.watchlist:
            try_command(display_data, (args.limit, config["CLI"]["ascending"], "Watchlist"))
        if args.diary:
            try_command(display_data, (args.limit, config["CLI"]["ascending"], "Diary"))
        if args.ratings:
            try_command(display_data, (args.limit, config["CLI"]["ascending"], "Ratings"))
        if args.lists:
            try_command(display_data, (args.limit, config["CLI"]["ascending"], "Lists"))
        
    except KeyboardInterrupt:
        print('\nProgram interrupted. Exiting.')
        sys.exit(0)


if __name__ == "__main__":
    main()
