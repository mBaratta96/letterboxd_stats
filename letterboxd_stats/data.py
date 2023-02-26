import pandas as pd
import numpy as np
from letterboxd_stats.cli import render_table, select_sort, select_range


def read_watched_films(df: pd.DataFrame, path: str, name: str):
    df_profile = pd.read_csv(path)
    df.insert(0, "watched", np.where(df["title"].isin(df_profile["Name"]), "[X]", "[ ]"))
    render_table(df, name)


def show_wishlist(path: str, shuffle: bool, limit=None):
    df = pd.read_csv(path)
    df["Year"] = df["Year"].fillna(0).astype(int)
    if shuffle:
        df = df.sample(frac=1)
    if limit is not None:
        df = df.iloc[:limit, :]
    render_table(df, "Wishlist")
    return df


def show_diary(path: str, limit=None):
    df = pd.read_csv(path)
    df["Year"] = df["Year"].fillna(0).astype(int)
    df["Watched Date"] = pd.to_datetime(df["Watched Date"])
    sort_column = select_sort(df.columns.values.tolist())
    df.sort_values(by=sort_column, ascending=False, inplace=True)
    df = df.drop("Rewatch", axis=1)
    df = df.drop("Tags", axis=1)
    if limit is not None:
        df = df.iloc[:limit, :]
    render_table(df, "Diary")
    return df


def show_ratings(path: str, limit=None):
    df = pd.read_csv(path)
    df["Year"] = df["Year"].fillna(0).astype(int)
    df["Date"] = pd.to_datetime(df["Date"])
    sort_column = select_sort(df.columns.values.tolist())
    df.sort_values(by=sort_column, ascending=False, inplace=True)
    if sort_column == "Rating":
        options = df["Rating"].unique().tolist()
        rating_range = select_range(options=options)
        df = df[df["Rating"].isin(rating_range)]
    if limit is not None:
        df = df.iloc[:limit, :]
    render_table(df, "Ratings")
    return df
