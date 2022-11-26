import pandas as pd
import numpy as np
from letterboxd_stats.cli import render_table


def read_watched_films(df: pd.DataFrame, path: str) -> pd.DataFrame:
    df_profile = pd.read_csv(path)
    df.insert(0, "watched", np.where(df["title"].isin(df_profile["Name"]), "[X]", "[ ]"))
    return df


def show_wishlist(path: str, shuffle: bool, limit=None):
    df = pd.read_csv(path)
    if shuffle:
        df = df.sample(frac=1)
    if limit:
        df = df.iloc[:limit, :]
    render_table(df, "Wishlist")
