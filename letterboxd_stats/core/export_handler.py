import os
import numpy as np
import pandas as pd
from tqdm import tqdm
from pandarallel import pandarallel

from .letterboxd_connector import LBConnector

tqdm.pandas(desc="Fetching ids...")
pandarallel.initialize(progress_bar=False, verbose=1)

DATA_FILES = {
    "Watchlist": "watchlist.csv", 
    "Diary": "diary.csv", 
    "Ratings": "ratings.csv",
    "Watched": "watched.csv", 
    "Lists": "lists"
    }


def get_export_path(downloads_folder: str, export_type: str) -> str:
    if export_type not in DATA_FILES:
        raise ValueError(f"Invalid export type: {export_type}. Available types: {list(DATA_FILES.keys())}")
    
    path = os.path.expanduser(os.path.join(downloads_folder, "static", DATA_FILES[export_type]))
    
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"No Letterboxd data was found in {path}. Make sure the path is correct or run -d to download your data"
        )
        
    return path

def check_if_watched(watched_csv_df: pd.DataFrame, film_row: pd.Series, lb_connector: LBConnector) -> bool:
    """watched.csv hasn't the TMDB id, so comparison can be done only by title.
    This creates the risk of mismatch when two films have the same title. To avoid this,
    we must retrieve the TMDB id of the watched film.
    """

    if film_row["Title"] in watched_csv_df["Name"].values:
        watched_films_same_name = watched_csv_df[watched_csv_df["Name"] == film_row["Title"]]
        for _, film in watched_films_same_name.iterrows():
            film_id = lb_connector.get_tmdb_id_from_lb_page(film["Letterboxd URI"])
            if film_id == film_row.name:
                return True
    return False


def add_lb_watched_status_column(df: pd.DataFrame, watched_csv: str, lb_connector: LBConnector) -> pd.DataFrame:
    """Check which film of a director you have seen. Add a column to show on the CLI.
    """
    
    df_profile = pd.read_csv(watched_csv)
    df.insert(
        0,
        "watched",
        np.where(
            [check_if_watched(df_profile, row, lb_connector) for _, row in df.iterrows()],
            "[X]",
            "[ ]",
        ),
    )
    df["Release Date"] = pd.to_datetime(df["Release Date"])
    df.sort_values(by="Release Date", inplace=True)
    return df

def get_list_name(list_csv_path: str) -> str:
    df = pd.read_csv(list_csv_path, header=1)
    return df["Name"].iloc[0]
