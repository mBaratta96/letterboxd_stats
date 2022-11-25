import pandas as pd
import numpy as np


def read_watched_films(df: pd.DataFrame, path: str) -> pd.DataFrame:
    df_profile = pd.read_csv(path)
    df.insert(0, "watched", np.where(df["title"].isin(df_profile["Name"]), "[X]", "[ ]"))
    return df
