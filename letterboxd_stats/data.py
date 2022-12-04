import pandas as pd
import numpy as np
from letterboxd_stats.cli import render_table


def read_watched_films(df: pd.DataFrame, path: str, name: str):
    df_profile = pd.read_csv(path)
    df.insert(0, "watched", np.where(df["title"].isin(df_profile["Name"]), "[X]", "[ ]"))
    render_table(df, name)


def show_wishlist(path: str, shuffle: bool, limit=None):
    df = pd.read_csv(path)
    if shuffle:
        df = df.sample(frac=1)
    if limit is not None:
        df = df.iloc[:limit, :]
    render_table(df, "Wishlist")


def show_diary(path: str, limit=None):
    df = pd.read_csv(path)
    df["Watched Date"] = pd.to_datetime(df["Watched Date"])
    df.sort_values(by="Watched Date", ascending=False, inplace=True)
    if limit is not None:
        df = df.iloc[:limit, :]
    render_table(df, "Diary")
