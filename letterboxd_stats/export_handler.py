import numpy as np
import pandas as pd
from tqdm import tqdm
from pandarallel import pandarallel
from letterboxd_stats.web_scraper import get_tmdb_id_from_lb

tqdm.pandas(desc="Fetching ids...")
pandarallel.initialize(progress_bar=False, verbose=1)


def check_if_watched(df: pd.DataFrame, row: pd.Series) -> bool:
    """watched.csv hasn't the TMDB id, so comparison can be done only by title.
    This creates the risk of mismatch when two films have the same title. To avoid this,
    we must retrieve the TMDB id of the watched film.
    """

    if row["Title"] in df["Name"].values:
        watched_films_same_name = df[df["Name"] == row["Title"]]
        for _, film in watched_films_same_name.iterrows():
            film_id = get_tmdb_id_from_lb(film["Letterboxd URI"])
            if film_id == row.name:
                return True
    return False


def add_lb_watched_status_column(df: pd.DataFrame, watched_csv: str) -> pd.DataFrame:
    """Check which film of a director you have seen. Add a column to show on the CLI.
    """
    
    df_profile = pd.read_csv(watched_csv)
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
    return df


