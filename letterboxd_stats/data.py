import pandas as pd
import numpy as np
from letterboxd_stats import cli


def read_watched_films(df: pd.DataFrame, path: str, name: str):
    df_profile = pd.read_csv(path)
    df.insert(0, "watched", np.where(df["title"].isin(df_profile["Name"]), "[X]", "[ ]"))
    cli.render_table(df, name)
    movie_id = cli.select_movie_id(df[["id", "title"]])
    return movie_id


def open_file(filetype: str, path: str, limit, ascending):
    df = pd.read_csv(path)
    df.rename(columns={"Name": "Title", "Letterboxd URI": "Url"}, inplace=True)
    df["Year"] = df["Year"].fillna(0).astype(int)
    df = FILE_OPERATIONS[filetype](df, ascending)
    if limit is not None:
        df = df.iloc[:limit, :]
    cli.render_table(df, filetype)
    return cli.select_movie(df[["Title", "Url"]])


def _show_watchlist(df: pd.DataFrame, ascending: bool):
    sort_column = cli.select_value(
        df.columns.values.tolist() + ["Shuffle"], "Select the order of your watchlist entries:"
    )
    if sort_column == "Shuffle":
        df = df.sample(frac=1)
    else:
        df.sort_values(by=sort_column, ascending=ascending, inplace=True)
    return df


def _show_diary(df: pd.DataFrame, ascending: bool):
    df["Watched Date"] = pd.to_datetime(df["Watched Date"])
    sort_column = cli.select_value(df.columns.values.tolist(), "Select the order of your diary entries:")
    df.sort_values(by=sort_column, ascending=ascending, inplace=True)
    df = df.drop("Rewatch", axis=1)
    df = df.drop("Tags", axis=1)
    return df


def _show_ratings(df: pd.DataFrame, ascending: bool):
    df["Date"] = pd.to_datetime(df["Date"])
    sort_column = cli.select_value(df.columns.values.tolist(), "Select the order of your ratings:")
    df.sort_values(by=sort_column, ascending=ascending, inplace=True)
    if sort_column == "Rating":
        options = df["Rating"].unique().tolist()
        rating_range = cli.select_range(options=options)
        df = df[df["Rating"].isin(rating_range)]
    return df


FILE_OPERATIONS = {"Diary": _show_diary, "Watchlist": _show_watchlist, "Ratings": _show_ratings}
