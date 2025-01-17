"""
ExportViewer Module
===================

This module provides functionality for managing, processing, and visualizing
Letterboxd export data in a CLI environment. The `ExportViewer` class handles
operations such as loading export files (e.g., diary, watchlist, ratings),
processing them, and rendering the results in a user-friendly format using
the `CLIRenderer`.

Classes:
--------
- ExportViewer: Core class for managing Letterboxd exports, including processing and rendering.

Functions:
----------
- `get_list_name(list_csv_path: str) -> str`:
    Retrieves the name of a list from a Letterboxd export CSV file.

Features:
---------
1. **Export Management**:
   - Validates the existence of export data files.
   - Provides utilities for retrieving export file paths.

2. **Data Processing**:
   - Includes specific processing for Diary, Watchlist, Ratings, and Lists exports.
   - Supports filtering, sorting, and data enrichment (e.g., adding watched status).

3. **CLI Visualization**:
   - Utilizes `CLIRenderer` for rendering tables and dictionaries in the terminal.
   - Allows interactive selection of films and processing options via user input.

4. **TMDb Integration**:
   - Optionally fetches additional metadata (e.g., runtimes) using the TMDb API.
   - Leverages the Letterboxd connector for retrieving film IDs and managing data.

5. **User Interaction**:
   - Provides prompts to let users choose sorting options, filter criteria, and specific films.

"""

import logging
import os

import pandas as pd
from pandarallel import pandarallel
from tqdm import tqdm

from ..lb.public_connector import LBPublicConnector
from ..utils.renderer import CLIRenderer
from ..utils.tmdb_api import TMDbAPI
from .user_input_handler import (user_choose_film_from_list,
                                 user_choose_option,
                                 user_choose_option_lb_lists,
                                 user_choose_options_multiple)

logger = logging.getLogger(__name__)

tqdm.pandas(desc="Fetching ids...")
pandarallel.initialize(progress_bar=False, verbose=1)

LB_DATA_FILES = {
    "Watchlist": "watchlist.csv",
    "Diary": "diary.csv",
    "Ratings": "ratings.csv",
    "Watched": "watched.csv",
    "Lists": "lists",
}


class ExportViewer:

    def __init__(
        self,
        root_folder: str,
        renderer: CLIRenderer,
        get_list_runtimes: bool = False,
        tmdb_api: TMDbAPI = None,
        lb_connector: LBPublicConnector = None,
    ):
        """
        Initialize the ExportViewer with optional configuration.

        Args:
            root_folder (str): The root directory where Letterboxd export files are located.
            renderer (CLIRenderer): An instance of `CLIRenderer` responsible for managing
                command-line interface output.
            get_list_runtimes (bool, optional): Flag indicating whether to retrieve runtime
                information for movies in lists using the TMDB API. Defaults to `False`.
            tmdb_api (TMDbAPI, optional): An instance of `TMDbAPI` used to interact with The
                Movie Database (TMDB) API. Only required if `get_list_runtimes` is set to `True`.
                If not provided, this should be initialized elsewhere in the application.
            lb_connector (LBConnector, optional): An instance of `LBConnector` used for managing
                connections to Letterboxd data. Only required if `get_list_runtimes` is set to `True`.
                Defaults to a new instance of `LBConnector` if not provided.

        Attributes:
            renderer (CLIRenderer): Stores the provided `CLIRenderer` instance for output handling.
            root_folder (str): Stores the root directory path for Letterboxd export files.
            get_list_runtimes (bool): Indicates whether runtime retrieval is enabled.
            lb_connector (LBConnector): Instance of `LBConnector` for managing Letterboxd connections.
                Only initialized if `get_list_runtimes` is `True`.
            tmdb_api (TMDbAPI): Instance of `TMDbAPI` for accessing TMDB data.
                Only initialized if `get_list_runtimes` is `True`.
            user_operations_by_export_type (dict): A mapping of export types (e.g., "Diary",
                "Watchlist") to the corresponding processing functions.
        """
        logger.info("Initializing ExportViewer")
        self.renderer = renderer

        self.get_list_runtimes = get_list_runtimes
        self.exports_folder = os.path.expanduser(os.path.join(root_folder, "static"))
        logger.debug("Export folder set to: %s", self.exports_folder)

        self.lb_connector = lb_connector
        self.tmdb_api = tmdb_api

        if self.get_list_runtimes:
            logger.info("Runtime fetching enabled")
        else:
            logger.info("Runtime fetching disabled")

        self.user_operations_by_export_type = {
            "Diary": self._process_diary_df,
            "Watchlist": self._process_watchlist_df,
            "Ratings": self._process_ratings_df,
            "Lists": self._process_lists_df,
        }

    @staticmethod
    def _process_diary_df(
        diary_df: pd.DataFrame, sort_ascending: bool = False
    ) -> pd.DataFrame:
        diary_df["Watched Date"] = pd.to_datetime(diary_df["Watched Date"])
        sort_column = user_choose_option(
            diary_df.columns.values.tolist(), "Select the order of your diary entries:"
        )
        diary_df.sort_values(by=sort_column, ascending=sort_ascending, inplace=True)
        diary_df = diary_df.drop(["Rewatch", "Tags"], axis=1)
        logging.info(
            "Diary DataFrame processed. Sorted by %s, ascending=%s.",
            sort_column,
            sort_ascending,
        )
        return diary_df

    @staticmethod
    def _process_watchlist_df(
        df: pd.DataFrame, sort_ascending: bool = False
    ) -> pd.DataFrame:
        sort_column = user_choose_option(
            df.columns.values.tolist() + ["Shuffle"],
            "Select the order of your watchlist entries:",
        )
        if sort_column == "Shuffle":
            df = df.sample(frac=1)
            logging.info("Watchlist DataFrame shuffled.")
        else:
            df.sort_values(by=sort_column, ascending=sort_ascending, inplace=True)
            logging.info(
                "Watchlist DataFrame sorted by %s, ascending=%s.",
                sort_column,
                sort_ascending,
            )
        return df

    @staticmethod
    def _process_ratings_df(
        df: pd.DataFrame, sort_ascending: bool = False
    ) -> pd.DataFrame:
        df["Date"] = pd.to_datetime(df["Date"])
        sort_column = user_choose_option(
            df.columns.values.tolist(), "Select the order of your ratings:"
        )
        df.sort_values(by=sort_column, ascending=sort_ascending, inplace=True)
        logging.info(
            "Ratings DataFrame sorted by %s, ascending=%s.", sort_column, sort_ascending
        )
        if sort_column == "Rating":
            options = df["Rating"].unique().tolist()
            rating_filter = user_choose_options_multiple(options=options)
            df = df[df["Rating"].isin(rating_filter)]
            logging.info(
                "Filtered Ratings DataFrame to include ratings: %s.", rating_filter
            )
        return df

    def _process_lists_df(
        self, list_df: pd.DataFrame, sort_ascending: bool = False
    ) -> pd.DataFrame:

        ratings_path = self.get_export_path("Ratings")
        ratings_df = pd.read_csv(ratings_path)
        ratings_df.rename(columns={"Letterboxd URI": "URL"}, inplace=True)
        list_df = list_df.merge(ratings_df[["URL", "Rating"]], on="URL", how="inner")
        list_df.rename(columns={"URL": "Url"}, inplace=True)
        list_df = list_df.drop("Description", axis=1)
        list_df["Rating"] = list_df["Rating"].astype(float)
        sort_column = user_choose_option(
            list_df.columns.values.tolist(), "Select the order of your diary entries:"
        )
        list_df.sort_values(by=sort_column, ascending=sort_ascending, inplace=True)

        logging.info(
            "Lists DataFrame processed. Sorted by %s, ascending=%s.",
            sort_column,
            sort_ascending,
        )

        averages = {"Rating Mean": f"{list_df['Rating'].mean():.2f}"}

        if self.get_list_runtimes is True:
            self.renderer.render_text("Fetching movie runtimes...")
            tmdb_ids = list_df["Url"].parallel_map(
                self.lb_connector.get_tmdb_id_from_lb
            )

            list_df["Duration"] = tmdb_ids.parallel_map(self.tmdb_api.fetch_movie_runtime)
            duration_sum = list_df["Duration"].sum()
            weighted_ratings = (list_df["Duration"] / duration_sum) * list_df["Rating"]
            time_weighted_mean = weighted_ratings.sum()

            averages["Time-weighted Rating Mean"] = f"{time_weighted_mean:.2f}"

            logging.info("Fetched runtimes and calculated time-weighted rating mean.")

        self.renderer.render_dict(averages, expand=False)
        logging.info("Averages calculated: %s.", averages)
        return list_df

    def view_lb_export_lists_directory(
        self, lists_dir_path: str, limit: int = None
    ) -> str:
        """Select a list from the saved ones."""
        logger.info("Viewing Letterboxd exports directory: %s", lists_dir_path)

        list_names = {
            get_list_name(
                os.path.join(lists_dir_path, letterboxd_list)
            ): letterboxd_list
            for letterboxd_list in os.listdir(lists_dir_path)
        }
        name = user_choose_option_lb_lists(sorted(list(list_names.keys())))
        return self.view_lb_export_csv(
            "Lists", os.path.join(lists_dir_path, list_names[name]), limit, header=3
        )

    def view_lb_export_csv(
        self, export_type: str, path: str, limit: int = None, header=0
    ) -> str:
        """There are some operations that are the same for all the .csv files.
        Isolate those similar operations,and then perform the particular operation
        for a certain file (watchlist, list, diary...). OPERATIONS_BY_EXPORT_TYPE
        selects those particular operations according to the file we opened.
        Mainly they do ordering and column filtering operations.
        """
        logger.info("Viewing Letterboxd export: %s", export_type)
        logger.debug("Path to CSV: %s", path)
        try:
            df = pd.read_csv(path, header=header)

            # df = self.add_lb_watched_status_column(df)
            df.rename(columns={"Name": "Title", "Letterboxd URI": "Url"}, inplace=True)

            df["Year"] = df["Year"].fillna(0).astype(int)

            df = self.user_operations_by_export_type[export_type](
                df, self.renderer.sort_ascending
            )

            if limit is not None:
                logger.debug("Applying limit: %d", limit)
                df = df.iloc[:limit, :]

            list_name = export_type
            if export_type == "Lists":
                list_name = get_list_name(path)
            self.renderer.render_table(df, list_name)
            selected_film = user_choose_film_from_list(df["Title"], df["Url"])
            logger.info("Selected film: %s", selected_film)
            return selected_film
        except FileNotFoundError as e:
            logger.error("Export file not found: %s", e)
            raise
        except Exception as e:
            logger.exception("An error occurred while processing the export: %s", e)
            raise

    def add_lb_watched_status_column(self, df: pd.DataFrame) -> pd.DataFrame:
        """Check which film of a director you have seen. Add a column to show on the CLI."""
        logger.info("Adding watched status column")
        watched_csv = self.get_export_path("Watched")
        try:
            df_profile = pd.read_csv(watched_csv)
            logger.debug("Loaded watched data from: %s", watched_csv)
            matching_watched_films = df_profile[
                df_profile["Name"].isin(df["Title"])
            ].copy()
            matching_watched_films["TMDB_ID"] = matching_watched_films[
                "Letterboxd URI"
            ].map(self.lb_connector.get_tmdb_id_from_lb)

            watched_ids = set(matching_watched_films["TMDB_ID"].dropna())
            df["watched"] = df.index.map(
                lambda idx: "[X]" if idx in watched_ids else "[ ]"
            )
            logger.info("Watched status column added successfully")
            return df
        except Exception as e:
            logger.exception("Failed to add watched status column. %s", e)
            raise

    def get_export_path(self, export_type: str) -> str:
        logger.debug("Fetching export path for: %s", export_type)
        if export_type not in LB_DATA_FILES:
            raise ValueError(
                f"Invalid export type: {export_type}. Available types: {list(LB_DATA_FILES.keys())}"
            )

        path = os.path.expanduser(
            os.path.join(self.exports_folder, LB_DATA_FILES[export_type])
        )

        if not os.path.exists(path):
            raise FileNotFoundError(
                f"No Letterboxd data was found in {path}. Make sure the path is correct or run -d to download your data"
            )

        return path

    def export_exists(self) -> bool:
        """
        Check if the export data has already been downloaded and extracted.
        Returns:
            bool: True if all expected files are present, False otherwise.
        """
        logger.info("Checking if exports exist")
        for file_name in LB_DATA_FILES.values():
            file_path = os.path.join(
                self.exports_folder, file_name
            )  # Update path if needed
            if not os.path.exists(file_path):
                logger.warning("Missing export file: %s", file_path)
                return False
        logger.info("All export files are present")
        return True


def get_list_name(list_csv_path: str) -> str:
    df = pd.read_csv(list_csv_path, header=1)
    if "Name" not in df.columns or df.empty:
        raise ValueError(
            f"The list CSV at {list_csv_path} is missing a 'Name' column or is empty."
        )
    return df["Name"].iloc[0]
