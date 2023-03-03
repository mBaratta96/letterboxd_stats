from letterboxd_stats import tmdb
from letterboxd_stats import data
from letterboxd_stats import cli
from letterboxd_stats.web_scraper import Downloader, get_tmdb_id
import os
from letterboxd_stats import args, config

MOVIE_OPERATIONS = {
    "Add to diary": "add_film_diary",
    "Add to watchlist": "add_watchlist",
    "Remove from watchlist": "remove_watchlist",
}


def get_movie_detail_from_url(df, is_diary=False):
    df.rename(columns={"Name": "title", "Letterboxd URI": "url"}, inplace=True)
    link = cli.select_movie(df[["title", "url"]])
    id = get_tmdb_id(link, is_diary)
    if id is not None:
        selected_details = tmdb.get_movie_detail(id)
        if selected_details["poster"] is not None:
            cli.download_poster(selected_details["poster"])
        cli.print_film(selected_details)


def search_person(args_search: str):
    search_results = tmdb.get_person(args_search)
    names = [result.name for result in search_results]  # type: ignore
    result_index = cli.select_search_result(names)  # type: ignore
    name = search_results[result_index]["name"]
    try:
        df, known_for_department = tmdb.create_person_dataframe(search_results[result_index])
    except ValueError as e:
        print(e)
        return
    department = cli.select_value(df["department"].unique(), f"Select a department for {name}", known_for_department)
    df = df[df["department"] == department]
    df = df.drop("department", axis=1)
    path = os.path.join(config["root_folder"], "static", "watched.csv")
    df = data.read_watched_films(df, path, name)
    cli.render_table(df, name)
    movie_id = cli.select_movie_id(df[["id", "title"]])
    if movie_id is not None:
        tmdb.get_movie_detail(movie_id)


def search_film(args_search_film: str):
    search_results = tmdb.get_movie(args_search_film)
    titles = [result.title for result in search_results]  # type: ignore
    result_index = cli.select_search_result(titles)  # type: ignore
    movie_id = search_results[result_index]["id"]
    tmdb.get_movie_detail(movie_id)
    answer = cli.select_value(["Exit"] + list(MOVIE_OPERATIONS.keys()), "Select operation:")
    if answer != "Exit":
        ws = Downloader()
        ws.login()
        getattr(ws, MOVIE_OPERATIONS[answer])(search_results[result_index]["title"])


def get_wishlist(args_random, args_limit):
    path = os.path.join(config["root_folder"], "static", "watchlist.csv")
    df = data.show_wishlist(path, args_random, args_limit)
    cli.render_table(df, "Wishlist")
    get_movie_detail_from_url(df)


def get_diary(args_limit):
    path = os.path.join(config["root_folder"], "static", "diary.csv")
    df = data.show_diary(path, args_limit)
    sort_column = cli.select_value(df.columns.values.tolist(), "Select the order of your diary entries:")
    df.sort_values(by=sort_column, ascending=False, inplace=True)
    cli.render_table(df, "Diary")
    get_movie_detail_from_url(df, True)


def get_ratings(args_limit):
    path = os.path.join(config["root_folder"], "static", "ratings.csv")
    df = data.show_ratings(path, args_limit)
    sort_column = cli.select_value(df.columns.values.tolist(), "Select the order of your ratings:")
    df.sort_values(by=sort_column, ascending=False, inplace=True)
    if sort_column == "Rating":
        options = df["Rating"].unique().tolist()
        rating_range = cli.select_range(options=options)
        df = df[df["Rating"].isin(rating_range)]
    cli.render_table(df, "Ratings")
    get_movie_detail_from_url(df)


def main():
    if args.download:
        ws = Downloader()
        ws.login()
        ws.download_stats()
    if args.search:
        search_person(args.search)
    if args.search_film:
        search_film(args.search_film)
    if args.wishlist:
        get_wishlist(args.random, args.limit)
    if args.diary:
        get_diary(args.limit)
    if args.ratings:
        get_ratings(args.limit)


if __name__ == "__main__":
    main()
