import pandas as pd
from pandarallel import pandarallel
import numpy as np
from letterboxd_stats import cli
from letterboxd_stats.web_scraper import get_tmdb_id
from letterboxd_stats import tmdb
import os
from letterboxd_stats import config
from tqdm import tqdm

tqdm.pandas(desc="Fetching ids...")
pandarallel.initialize(progress_bar=False, verbose=1)


def check_if_watched(df: pd.DataFrame, row: pd.Series) -> bool:
    """watched.csv hasn't the TMDB id, so comparison can be done only by title.
    This creates the risk of mismatch when two movies have the same title. To avoid this,
    we must retrieve the TMDB id of the watched movie.
    """

    if row["Title"] in df["Name"].values:
        watched_films_same_name = df[df["Name"] == row["Title"]]
        for _, film in watched_films_same_name.iterrows():
            film_id = get_tmdb_id(film["Letterboxd URI"])
            if film_id == row.name:
                return True
    return False


def read_watched_films(df: pd.DataFrame, path: str, name: str) -> pd.DataFrame:
    """Check which film of a director you have seen. Add a column to show on the CLI."""

    df_profile = pd.read_csv(path)
    df.insert(
        0,
        "watched",
        np.where(
            [check_if_watched(df_profile, row) for _, row in df.iterrows()],
            "[X]",
            "[ ]",
        ),
    )
    df["Release Date"] = pd.to_datetime(df["Release Date"])
    df.sort_values(by="Release Date", inplace=True)
    cli.render_table(df, name)
    return df


def select_film_of_person(df: pd.DataFrame) -> pd.Series | None:
    movie_id = cli.select_movie(df["Title"], df.index.to_series())
    if movie_id is None:
        return None
    movie_row = df.loc[movie_id]
    return movie_row


def get_list_name(path: str) -> str:
    df = pd.read_csv(path, header=1)
    return df["Name"].iloc[0]


def open_list(path: str, limit: int, ascending: bool) -> str:
    """Select a list from the saved ones."""

    list_names = {
        get_list_name(os.path.join(path, letterboxd_list)): letterboxd_list for letterboxd_list in os.listdir(path)
    }
    name = cli.select_list(sorted(list(list_names.keys())))
    return open_file("Lists", os.path.join(path, list_names[name]), limit, ascending, header=3)


def open_file(filetype: str, path: str, limit, ascending, header=0) -> str:
    """There are some operations that are the same for all the .csv files. So isolate those similar operations,
    and then we proceed to perform the particular operation for a certain file (watchlist, list, diary...).
    FILE_OPERATIONS selects those particular operations according to the file we opened. Mainly they do
    ordering and column filtering operations.
    """

    df = pd.read_csv(path, header=header)
    df.rename(columns={"Name": "Title", "Letterboxd URI": "Url"}, inplace=True)
    df["Year"] = df["Year"].fillna(0).astype(int)
    df = FILE_OPERATIONS[filetype](df, ascending)
    if limit is not None:
        df = df.iloc[:limit, :]
    cli.render_table(df, filetype)
    return cli.select_movie(df["Title"], df["Url"])


def _show_lists(df: pd.DataFrame, ascending: bool) -> pd.DataFrame:
    ratings_path = os.path.expanduser(os.path.join(config["root_folder"], "static", "ratings.csv"))
    df_ratings = pd.read_csv(ratings_path)
    df_ratings.rename(columns={"Letterboxd URI": "URL"}, inplace=True)
    df = df.merge(df_ratings[["URL", "Rating"]], on="URL", how="inner")
    df.rename(columns={"URL": "Url"}, inplace=True)
    df = df.drop("Description", axis=1)
    df["Rating"] = df["Rating"].astype(float)
    sort_column = cli.select_value(df.columns.values.tolist(), "Select the order of your diary entries:")
    df.sort_values(by=sort_column, ascending=ascending, inplace=True)
    avg = {"Rating Mean": "{:.2f}".format(df["Rating"].mean())}
    if config["TMDB"]["get_list_runtimes"] is True:
        ids = df["Url"].parallel_map(get_tmdb_id)
        df["Duration"] = ids.parallel_map(lambda id: tmdb.get_movie_duration(id))  # type: ignore
        avg["Time-weighted Rating Mean"] = "{:.2f}".format(
            ((df["Duration"] / df["Duration"].sum()) * df["Rating"]).sum()
        )
    cli.print_film(avg, expand=False)
    return df


def _show_watchlist(df: pd.DataFrame, ascending: bool) -> pd.DataFrame:
    sort_column = cli.select_value(
        df.columns.values.tolist() + ["Shuffle"],
        "Select the order of your watchlist entries:",
    )
    if sort_column == "Shuffle":
        df = df.sample(frac=1)
    else:
        df.sort_values(by=sort_column, ascending=ascending, inplace=True)
    return df


def _show_diary(df: pd.DataFrame, ascending: bool) -> pd.DataFrame:
    df["Watched Date"] = pd.to_datetime(df["Watched Date"])
    sort_column = cli.select_value(df.columns.values.tolist(), "Select the order of your diary entries:")
    df.sort_values(by=sort_column, ascending=ascending, inplace=True)
    df = df.drop(["Rewatch", "Tags"], axis=1)
    return df


def _show_ratings(df: pd.DataFrame, ascending: bool) -> pd.DataFrame:
    df["Date"] = pd.to_datetime(df["Date"])
    sort_column = cli.select_value(df.columns.values.tolist(), "Select the order of your ratings:")
    df.sort_values(by=sort_column, ascending=ascending, inplace=True)
    if sort_column == "Rating":
        options = df["Rating"].unique().tolist()
        rating_range = cli.select_range(options=options)
        df = df[df["Rating"].isin(rating_range)]
    return df


FILE_OPERATIONS = {
    "Diary": _show_diary,
    "Watchlist": _show_watchlist,
    "Ratings": _show_ratings,
    "Lists": _show_lists,
}
