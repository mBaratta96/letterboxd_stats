import pandas as pd
import numpy as np


def read_watched_films(df: pd.DataFrame, path: str, name: str):
    df_profile = pd.read_csv(path)
    df.insert(0, "watched", np.where(df["title"].isin(df_profile["Name"]), "[X]", "[ ]"))
    return df


def show_wishlist(path: str, shuffle: bool, limit=None):
    df = pd.read_csv(path)
    df["Year"] = df["Year"].fillna(0).astype(int)
    if shuffle:
        df = df.sample(frac=1)
    if limit is not None:
        df = df.iloc[:limit, :]
    return df


def show_diary(path: str, limit=None):
    df = pd.read_csv(path)
    df["Year"] = df["Year"].fillna(0).astype(int)
    df["Watched Date"] = pd.to_datetime(df["Watched Date"])
    df = df.drop("Rewatch", axis=1)
    df = df.drop("Tags", axis=1)
    if limit is not None:
        df = df.iloc[:limit, :]
    return df


def show_ratings(path: str, limit=None):
    df = pd.read_csv(path)
    df["Year"] = df["Year"].fillna(0).astype(int)
    df["Date"] = pd.to_datetime(df["Date"])
    if limit is not None:
        df = df.iloc[:limit, :]
    return df
