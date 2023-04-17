import pandas as pd
import numpy as np
from letterboxd_stats import cli
from letterboxd_stats import tmdb
import os
from letterboxd_stats import config


def read_watched_films(df: pd.DataFrame, path: str, name: str):
    df_profile = pd.read_csv(path)
    df.insert(0, "watched", np.where(df["Title"].isin(df_profile["Name"]), "[X]", "[ ]"))
    df["Release Date"] = pd.to_datetime(df["Release Date"])
    df.sort_values(by="Release Date", inplace=True)
    cli.render_table(df, name)
    movie_id = cli.select_movie_id(df[["Id", "Title"]])
    movie_row = df.loc[df["Id"] == movie_id].iloc[0, :]
    return movie_id, f"{movie_row['Title']} {movie_row['Release Date'].year}"


def get_list_name(path: str):
    df = pd.read_csv(path, header=1)
    return df["Name"].iloc[0]


def open_list(path: str, limit, acending):
    list_names = {
        get_list_name(os.path.join(path, letterboxd_list)): letterboxd_list for letterboxd_list in os.listdir(path)
    }
    name = cli.select_value(sorted(list(list_names.keys())), message="Select your list")
    return open_file("Lists", os.path.join(path, list_names[name]), limit, acending, header=3)


def open_file(filetype: str, path: str, limit, ascending, header=0):
    df = pd.read_csv(path, header=header)
    df.rename(columns={"Name": "Title", "Letterboxd URI": "Url"}, inplace=True)
    df["Year"] = df["Year"].fillna(0).astype(int)
    df = FILE_OPERATIONS[filetype](df, ascending)
    if limit is not None:
        df = df.iloc[:limit, :]
    cli.render_table(df, filetype)
    return cli.select_movie(df[["Title", "Url"]])


def _show_lists(df: pd.DataFrame, ascending: bool):
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
        df["Duration"] = df.apply(lambda row: tmdb.get_film_duration(row["Title"], row["Year"]), axis=1)  # type: ignore
        avg["Time-weighted Rating Mean"] = "{:.2f}".format(
            ((df["Duration"] / df["Duration"].sum()) * df["Rating"]).sum()
        )
    cli.print_film(avg, expand=False)
    return df


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


FILE_OPERATIONS = {"Diary": _show_diary, "Watchlist": _show_watchlist, "Ratings": _show_ratings, "Lists": _show_lists}
