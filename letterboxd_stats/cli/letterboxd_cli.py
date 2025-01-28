"""
LetterboxdCLI Module
====================

This module provides a command-line interface (CLI) for managing and interacting
with Letterboxd and The Movie Database (TMDb). The `LetterboxdCLI` class
integrates multiple components to enable users to view, update, and explore
their Letterboxd data directly from the terminal. It includes features for
managing metadata (e.g., ratings, liked status, watched status, diary entries)
and detailed exploration of private lists and film searches.

Classes:
--------
- `LetterboxdCLI`:
    Main class for accessing Letterboxd data, managing metadata, and interacting with exports.

Key Features:
-------------
1. **Interactive CLI for Letterboxd**:
   - Update film metadata directly from the CLI, including:
     - Marking films as watched or unwatched.
     - Adding or removing films from the watchlist.
     - Liking or un-liking films.
     - Updating film ratings.
     - Adding detailed diary entries, including tags and reviews.

2. **Detailed Viewing and Management**:
   - Explore and interact with lists, diary entries, watchlist, and ratings.
   - Enrich lists with runtime data fetched from TMDb.

3. **Search Functionality**:
   - Search for films on Letterboxd and fetch their metadata.
   - Search for people (e.g., directors, actors) on TMDb,
        view their filmography, and check watched status.

4. **TMDb and Letterboxd Integration**:
   - Fetch detailed movie metadata, including runtime,
        poster, release date, and overview, from TMDb.
   - Seamlessly integrate Letterboxd and TMDb data for a
        comprehensive viewing experience.

5. **Export Management**:
   - View Letterboxd export files (e.g., Diary, Watchlist, Ratings, Lists).
   - Enrich searches with export data (e.g. displaying Watched status when searching a Director)

"""

import logging
import os

import pandas as pd
from requests import RequestException

from ..lb.auth_connector import LBAuthConnector
from ..lb.utilities import LB_OPERATIONS, create_lb_operation_url_with_title
from .export_viewer import ExportViewer, get_list_name
from .renderer import CLIRenderer
from .tmdb_api import TMDbAPI
from .user_input_handler import (user_choose_film_from_dataframe,
                                 user_choose_film_from_list,
                                 user_choose_option,
                                 user_choose_option_search_result,
                                 user_choose_rating,
                                 user_create_diary_entry_payload)

logger = logging.getLogger(__name__)


class LetterboxdCLI:
    def __init__(
        self,
        tmdb_api_key: str,
        lb_username: str = None,
        lb_password: str = None,
        root_folder: str = None,
        cli_poster_columns: int = 80,
        cli_ascending: bool = False,
        tmdb_get_list_runtimes: bool = False,
        limit: int = None,
    ):
        """
        Initializes the LetterboxdCLI instance with optional configurations for
        interacting with Letterboxd and TMDb APIs, as well as rendering and
        exporting data.

        Args:
            tmdb_api_key (str):
                API key for accessing The Movie Database (TMDb) API.
            lb_username (str, optional):
                Letterboxd username for authentication. Defaults to None.
            lb_password (str, optional):
                Letterboxd password for authentication. Defaults to None.
            root_folder (str, optional):
                Base directory for storing temporary files and exports. Defaults to "/tmp".
            cli_poster_columns (int, optional):
                Number of columns used for rendering posters in the CLI. Defaults to 80.
            cli_ascending (bool, optional):
                Whether to sort rendered lists in ascending order. Defaults to False.
            tmdb_get_list_runtimes (bool, optional):
                Flag to enable runtime fetching for TMDb lists. Defaults to False.
            limit (int, optional):
                Maximum number of items to process or display in the CLI. Defaults to None (no limit).

        Attributes:
            root_folder (str):
                Resolved root folder path for temporary files and exports.
            lb_connector (LBAuthConnector):
                Connector for managing Letterboxd authentication and operations.
            tmdb_api (TMDbAPI):
                Instance of the TMDb API wrapper for fetching with movie data.
            renderer (CLIRenderer):
                Renderer for displaying content in the CLI with specified configurations.
            export_viewer (ExportViewer):
                Handles exporting and viewing data with runtime fetching as needed.

        Raises:
            ValueError: If `tmdb_api_key` is invalid or not provided.
        """

        if not root_folder:
            root_folder = "/tmp"
            logger.info("Root folder set to %s", root_folder)

        logger.info("Initializing LetterboxdCLI")
        self.root_folder = os.path.expanduser(root_folder)
        logger.debug("Root folder set to: %s", self.root_folder)

        self.lb_connector = LBAuthConnector(
            lb_username, lb_password, os.path.join(self.root_folder, "cache.db")
        )
        logger.info("LBAuthConnector initialized")
        self.tmdb_api = TMDbAPI(tmdb_api_key)
        logger.info("TMDbAPI initialized with provided API key")
        self.renderer = CLIRenderer(limit, cli_poster_columns, cli_ascending)
        logger.info(
            "CLIRenderer initialized with poster columns: %d, ascending: %s",
            cli_poster_columns,
            cli_ascending,
        )
        self.export_viewer = ExportViewer(
            self.root_folder,
            self.renderer,
            tmdb_get_list_runtimes,
            self.tmdb_api,
            self.lb_connector,
        )
        logger.info(
            "ExportViewer initialized with runtime fetching: %s", tmdb_get_list_runtimes
        )

    def download_stats(self):
        download_dir = self.lb_connector.data_exporter.download_and_extract_data(
            os.path.expanduser(os.path.join(self.root_folder, "static"))
        )
        self.renderer.render_text(f"Data successfully downloaded in {download_dir}")
        return download_dir


    def fetch_all_film_metadata(self, letterboxd_title: str):
        logger.info("Fetching metadata for film: %s", letterboxd_title)
        try:
            film_url = create_lb_operation_url_with_title(letterboxd_title, "film_page")
            tmdb_id = self.lb_connector.get_tmdb_id_from_lb_url(film_url)
            selected_details = {}

            if tmdb_id:
                logger.debug("TMDb ID found: %d", tmdb_id)
                tmdb_details = self.tmdb_api.fetch_movie_details(tmdb_id, film_url)  # type: ignore
                if tmdb_details:
                    selected_details.update(tmdb_details)
            if self.lb_connector and self.lb_connector.auth.logged_in:
                lb_data = self.lb_connector.fetch_lb_film_user_metadata(
                    letterboxd_title
                )
                selected_details.update(lb_data)
            return selected_details
        except Exception as e:
            logger.error(
                "Error fetching film metadata for '%s': %s", letterboxd_title, e
            )
            raise

    def search_person(self, search_query: str):
        """Search for a director, list his/her films and check if you have watched them."""
        self.renderer.render_text(f"Searching TMDb for person named '{search_query}'")
        search_results = self.tmdb_api.search_tmdb_people(search_query)
        search_result = search_results[
            user_choose_option_search_result([result.name for result in search_results])
        ]  # Get User Input
        person_films_df, name, known_for_department = self.tmdb_api.fetch_person_details(
            search_result["id"]
        )
        logger.debug("Person found: %s, Known for: %s", name, known_for_department)


        department = user_choose_option(
            person_films_df["Department"].unique(),
            f"Select a department for {name}",
            known_for_department,
        )

        while department:
            department_films_df = person_films_df[person_films_df["Department"] == department]
            department_films_df = department_films_df.drop("Department", axis=1)
            # person.details provides movies without time duration. If the user wants<S-D-A>
            # (since this slows down the process) get with the movie.details API.

            if self.export_viewer.get_list_runtimes is True:
                self.renderer.render_text("Fetching movie runtimes...")
                department_films_df["Duration"] = department_films_df.index.to_series().parallel_map(self.tmdb_api.fetch_movie_runtime)  # type: ignore
                logger.info("Fetched movie runtimes for the selected films.")

            department_films_df = department_films_df.drop_duplicates()

            if self.export_viewer.export_exists():
                logger.info("Checking watched status from exports")
                department_films_df = self.export_viewer.add_lb_watched_status_column(department_films_df)
                department_films_df["Release Date"] = pd.to_datetime(department_films_df["Release Date"])
                department_films_df.sort_values(by="Release Date", inplace=True)
                logger.debug("Added watched status and sorted by release date.")
            self.renderer.render_table(department_films_df, name)

            selected_film = user_choose_film_from_dataframe(department_films_df)

            # We want to print the link of the selected film. This has to be retrieved from the search page.
            while selected_film is not None:
                search_film_query = f"{selected_film['Title']} {selected_film['Release Date'].year}"  # type: ignore
                #search_film_query = f"tmdb:{selected_film['Id']}"  # type: ignore
                letterboxd_title = self.interactive_lb_search(search_film_query, return_first_result=True)

                if not letterboxd_title:
                    logger.warning("No results selected for film: %s", search_query)
                    return
                self.interact_with_film(letterboxd_title)
                selected_film = user_choose_film_from_dataframe(person_films_df)

            department = user_choose_option(
                person_films_df["Department"].unique(),
                f"Select a department for {name}",
                known_for_department,
            )


    def search_film(self, search_query: str):
        logger.info("Searching for film: %s", search_query)

        letterboxd_title = self.interactive_lb_search(search_query)
        if not letterboxd_title:
            logger.warning("No results selected for film: %s", search_query)
            return
        return self.interact_with_film(letterboxd_title)


    def interact_with_film(self, letterboxd_title: str):

        film_details = self.fetch_all_film_metadata(letterboxd_title)

        local_metadata = film_details.copy()
        self.renderer.render_film_details(local_metadata)

        while True:
            answer = user_choose_option(
                ["Exit"] + list(self.filter_operations(local_metadata)), "Select operation:"
            )
            if not answer or answer == "Exit":
                break

            # Dynamically determine additional arguments based on the operation
            extra_args = []
            if answer == "Update film rating":
                stars = user_choose_rating()
                extra_args = [stars]
            elif answer == "Add to diary":
                self.renderer.render_text("Set all the info for the diary entry:")
                diary_payload = user_create_diary_entry_payload()
                extra_args = [diary_payload]
            try:
                self.lb_connector.perform_film_operation(answer, letterboxd_title, *extra_args)
                self.renderer.render_text(f"Successfully updated {letterboxd_title}.")

                # Update local metadata based on operation
                if answer == "Mark film as watched":
                    local_metadata["Watched"] = True
                elif answer == "Un-mark film as watched":
                    local_metadata["Watched"] = False
                elif answer == "Add to Liked films":
                    local_metadata["Liked"] = True
                elif answer == "Remove from liked films":
                    local_metadata["Liked"] = False
                elif answer == "Add to watchlist":
                    local_metadata["Watchlisted"] = True
                elif answer == "Remove from watchlist":
                    local_metadata["Watchlisted"] = False
                elif answer == "Update film rating":
                    local_metadata["Rating"] = stars
                    if stars > 0:
                        local_metadata["Watched"] = True

                #self.renderer.render_last_rows(local_metadata, 4)

            except ConnectionError as e:
                logger.error(e)



    @staticmethod
    def filter_operations(metadata):
        """Filters LB_OPERATIONS based on the film's metadata."""
        operations = {}

        if not metadata["Watched"]:
            operations["Mark film as watched"] = LB_OPERATIONS["Mark film as watched"]
        else:
            operations["Un-mark film as watched"] = LB_OPERATIONS["Un-mark film as watched"]

        if not metadata["Liked"]:
            operations["Add to Liked films"] = LB_OPERATIONS["Add to Liked films"]
        else:
            operations["Remove from liked films"] = LB_OPERATIONS["Remove from liked films"]

        if not metadata["Watchlisted"]:
            operations["Add to watchlist"] = LB_OPERATIONS["Add to watchlist"]
        else:
            operations["Remove from watchlist"] = LB_OPERATIONS["Remove from watchlist"]

        if metadata["Rating"] is None:
            operations["Update film rating"] = LB_OPERATIONS["Update film rating"]
        else:
            operations["Update film rating"] = LB_OPERATIONS["Update film rating"]

        # Always allow adding to the diary
        operations["Add to diary"] = LB_OPERATIONS["Add to diary"]

        return operations

    def interactive_lb_search(self, search_query: str, return_first_result=False) -> str:
        """Search a film and get its Letterboxd link.
        For reference: https://letterboxd.com/search/seven+samurai/?adult
        """
        try:
            search_results = self.lb_connector.search_lb(search_query)
            print(search_results)
            if not search_results:
                return None
            # If we want to select films from the search page, get more data to print the selection prompt.
            if return_first_result:
                selected_film = list(search_results.keys())[0]
            else:
                selected_film = user_choose_option(list(search_results.keys()), "Select your film")

            if not selected_film:
                logger.warning("No film selected.")
                return None

            title_url = search_results[selected_film].split("/")[-2]
            logger.info("Letterboxd title found: %s", selected_film)
            return title_url
        except ValueError as e:
            return None  # Return None or handle the error as needed
        except RequestException as e:
            logger.error("Failed to retrieve results for title '%s': %s", search_query, e)
            return None  # Return None or handle the error as needed
        except Exception as e:
            logger.error("An unexpected error occurred: %s", e)
            raise

    def view_exported_lb_data(self, export_type: str):
        """
        Load and display data from exported Letterboxd .csv files in the CLI.

        Parameters:
            export_type (str): The type of export to view (e.g., "Diary", "Watchlist", "Lists").
        """
        logger.debug("Viewing LB export: %s", export_type)
        exports_path = self.export_viewer.get_export_path(export_type)

        if export_type == "Lists":
            logger.debug("Processing 'Lists' export type.")
            list_path = self.export_viewer.choose_list_from_exports(exports_path)
            while list_path:
                self.view_lb_export_csv("Lists", os.path.join(exports_path, list_path), 100, header=3)
                list_path = self.export_viewer.choose_list_from_exports(exports_path)

        else:
            logger.debug("Processing '%s' export type.", export_type)
            self.view_lb_export_csv(export_type, exports_path, self.renderer.list_print_limit)


    def view_lb_export_csv(
        self, export_type: str, path: str, limit: int = None, header=0
    ):
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
            df = self.export_viewer.user_operations_by_export_type[export_type](
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

            while selected_film:
                lb_title = self.lb_connector.get_lb_title_from_lb_url(selected_film)
                if lb_title:
                    self.interact_with_film(lb_title)

                selected_film = user_choose_film_from_list(df["Title"], df["Url"])
                logger.info("Selected film: %s", selected_film)

            return
        except FileNotFoundError as e:
            logger.error("Export file not found: %s", e)
            raise
        except Exception as e:
            logger.exception("An error occurred while processing the export: %s", e)
            raise
