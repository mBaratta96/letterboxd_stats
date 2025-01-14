"""
LetterboxdCLI Module
====================

This module provides a command-line interface (CLI) for managing and interacting with Letterboxd and The Movie Database (TMDb).
The `LetterboxdCLI` class integrates multiple components to enable users to view, update, and explore their Letterboxd data
directly from the terminal. It includes features for managing metadata (e.g., ratings, liked status, watched status, diary entries)
and detailed exploration of private lists and film searches.

Classes:
--------
- `LetterboxdCLI`: Main class for accessing Letterboxd data, managing metadata, and interacting with exports.

Key Features:
-------------
1. **Interactive CLI for Letterboxd**:
   - Update film metadata directly from the CLI, including:
     - Marking films as watched or unwatched.
     - Adding or removing films from the watchlist.
     - Liking or unliking films.
     - Updating film ratings.
     - Adding detailed diary entries, including tags and reviews.

2. **Detailed Viewing and Management**:
   - Explore and interact with lists, diary entries, watchlists, and ratings.
   - Enrich lists with runtime data fetched from TMDb.

3. **Search Functionality**:
   - Search for films on Letterboxd and fetch their metadata.
   - Search for people (e.g., directors, actors) on TMDb, view their filmography, and check watched status.

4. **TMDb and Letterboxd Integration**:
   - Fetch detailed movie metadata, including runtime, poster, release date, and overview, from TMDb.
   - Seamlessly integrate Letterboxd and TMDb data for a comprehensive viewing experience.

5. **Export Management**:
   - View Letterboxd export files (e.g., Diary, Watchlist, Ratings, Lists).
   - Enrich searches with export data (e.g. displaying Watched status when searching a Director)

"""
import logging
import os

import pandas as pd

from ..lb.auth_connector import LBAuthConnector
from ..lb.utilities import LB_OPERATIONS, create_lb_operation_url_with_title
from ..utils.renderer import CLIRenderer
from ..utils.tmdb_connector import TMDbAPI
from .export_viewer import ExportViewer
from .user_input_handler import UserInputHandler

logger = logging.getLogger(__name__)

class LetterboxdCLI:
    def __init__(
        self,
        tmdb_api_key: str,
        lb_username: str=None,
        lb_password: str=None,
        root_folder: str = "/tmp",
        cli_poster_columns: int=80,
        cli_ascending: bool=False,
        tmdb_get_list_runtimes: bool=False,
        limit: int = None,
    ):
        """
        Initializes the LetterboxdCLI instance with optional configurations for
        interacting with Letterboxd and TMDb APIs, as well as rendering and exporting data.

        Args:
            tmdb_api_key (str): API key for accessing The Movie Database (TMDb) API.
            lb_username (str, optional): Letterboxd username for authentication. Defaults to None.
            lb_password (str, optional): Letterboxd password for authentication. Defaults to None.
            root_folder (str, optional): Base directory for storing temporary files and exports. Defaults to "/tmp".
            cli_poster_columns (int, optional): Number of columns used for rendering posters in the CLI. Defaults to 80.
            cli_ascending (bool, optional): Whether to sort rendered lists in ascending order. Defaults to False.
            tmdb_get_list_runtimes (bool, optional): Flag to enable runtime fetching for TMDb lists. Defaults to False.
            limit (int, optional): Maximum number of items to process or display in the CLI. Defaults to None (no limit).

        Attributes:
            root_folder (str): Resolved root folder path for temporary files and exports.
            lb_connector (LBAuthConnector): Connector for managing Letterboxd authentication and operations.
            tmdb_api (TMDbAPI): Instance of the TMDb API wrapper for fetching with movie data.
            renderer (CLIRenderer): Renderer for displaying content in the CLI with specified configurations.
            export_viewer (ExportViewer): Handles exporting and viewing data with runtime fetching as needed.

        Raises:
            ValueError: If `tmdb_api_key` is invalid or not provided.
        """

        logger.info("Initializing LetterboxdCLI")
        self.root_folder = os.path.expanduser(root_folder)
        logger.debug("Root folder set to: %s", self.root_folder)

        self.lb_connector = LBAuthConnector(lb_username, lb_password, os.path.join(self.root_folder,"cache.db"))
        logger.info("LBAuthConnector initialized")
        self.tmdb_api = TMDbAPI(tmdb_api_key)
        logger.info("TMDbAPI initialized with provided API key")
        self.renderer = CLIRenderer(limit, cli_poster_columns, cli_ascending)
        logger.info("CLIRenderer initialized with poster columns: %d, ascending: %s", cli_poster_columns, cli_ascending)
        self.export_viewer = ExportViewer(self.root_folder, self.renderer, tmdb_get_list_runtimes, self.tmdb_api, self.lb_connector)
        logger.info("ExportViewer initialized with runtime fetching: %s", tmdb_get_list_runtimes)


    def download_stats(self):
        dir = self.lb_connector.download_stats(os.path.expanduser(os.path.join(self.root_folder, "static")))
        self.renderer.render_string(f"Data successfully downloaded in {dir}")
        return dir


    def fetch_all_film_metadata(self, letterboxd_title: str):
        logger.info("Fetching metadata for film: %s", letterboxd_title)
        try:
            film_url = create_lb_operation_url_with_title(letterboxd_title, "film_page")
            tmdb_id = self.lb_connector.get_tmdb_id_from_lb_page(film_url)
            selected_details = {}

            if tmdb_id:
                logger.debug("TMDb ID found: %d", tmdb_id)
                tmdb_details = self.tmdb_api.fetch_movie_details(tmdb_id, film_url)  # type: ignore
                selected_details.update(tmdb_details)
            if self.lb_connector and self.lb_connector.auth.logged_in:
                lb_data = self.lb_connector.fetch_lb_film_user_metadata(letterboxd_title)
                selected_details.update(lb_data)
            return selected_details
        except Exception as e:
            logger.error("Error fetching film metadata for '%s': %s", letterboxd_title, e)
            raise

    def search_person(self, search_query: str):
        """Search for a director, list his/her films and check if you have watched them."""
        self.renderer.render_string(f"Searching TMDB for person named '{search_query}'")
        search_results = self.tmdb_api.search_tmdb_people(search_query)
        search_result = search_results[UserInputHandler.user_choose_option_search_result([result.name for result in search_results])]  # Get User Input
        df, name, known_for_department = self.tmdb_api.fetch_person_details(search_result['id'])
        logger.debug("Person found: %s, Known for: %s", name, known_for_department)
        department = UserInputHandler.user_choose_option(
            df["Department"].unique(), f"Select a department for {name}", known_for_department
        )
        df = df[df["Department"] == department]
        df = df.drop("Department", axis=1)
        # person.details provides movies without time duration. If the user wants<S-D-A>
        # (since this slows down the process) get with the movie.details API.

        if self.export_viewer.get_list_runtimes is True:
            self.renderer.render_string(f"Fetching movie runtimes...")
            df["Duration"] = df.index.to_series().parallel_map(self.tmdb_api.fetch_movie_runtime)  # type: ignore
            logger.info("Fetched movie runtimes for the selected films.")

        df = df.drop_duplicates()

        if self.export_viewer.export_exists():
            logger.info("Checking watched status from exports")
            df = self.export_viewer.add_lb_watched_status_column(df)
            df["Release Date"] = pd.to_datetime(df["Release Date"])
            df.sort_values(by="Release Date", inplace=True)
            logger.debug("Added watched status and sorted by release date.")
        self.renderer.render_table(df, name)

        selected_film = UserInputHandler.user_choose_film_from_dataframe(df)

        # We want to print the link of the selected film. This has to be retrieved from the search page.
        while selected_film is not None:
            search_film_query = f"{selected_film['Title']} {selected_film['Release Date'].year}"  # type: ignore
            letterboxd_title = self.search_for_lb_title(search_film_query)
            film_details = self.fetch_all_film_metadata(letterboxd_title)
            self.renderer.render_film_details(film_details)
            logger.info("Displayed details for film: %s (%s)", selected_film["Title"], selected_film["Release Date"])

            selected_film = UserInputHandler.user_choose_film_from_dataframe(df)

    def search_film(self, search_query: str):
        logger.info("Searching for film: %s", search_query)
        letterboxd_title = self.search_for_lb_title(search_query, True)
        if not letterboxd_title:
            logger.warning("No results found for film: %s", search_query)
            return
        film_details = self.fetch_all_film_metadata(letterboxd_title)
        self.renderer.render_film_details(film_details)

        while True:
            answer = UserInputHandler.user_choose_option(["Exit"] + list(LB_OPERATIONS.keys()), "Select operation:")
            if answer == "Exit":
                break

            # Dynamically determine additional arguments based on the operation
            extra_args = []
            if answer == "Update film rating":
                stars = UserInputHandler.user_choose_rating()
                extra_args = [stars]
            elif answer == "Add to diary":
                self.renderer.render_string("Set all the info for the diary entry:")
                diary_payload = UserInputHandler.user_create_diary_entry_payload()
                extra_args = [diary_payload]

            try:
                self.lb_connector.perform_operation(answer, letterboxd_title, *extra_args)
                self.renderer.render_string(f"Successfully updated {letterboxd_title}.")
            except Exception as e:
                # Handle the exception here, e.g., log it or display an error message
                logger.warning(f"An error occurred while performing the operation: {e}")

    def search_for_lb_title(self, title: str, allow_selection=False) -> str:
        """Search a film and get its Letterboxd link.
        For reference: https://letterboxd.com/search/seven+samurai/?adult
        """
        logger.debug("Searching for Letterboxd title: %s", title)
        try:
            search_results = self.lb_connector.search_lb_by_title(title)
            # If we want to select films from the search page, get more data to print the selection prompt.
            if allow_selection:
                selected_film = UserInputHandler.user_choose_option(
                    list(search_results.keys()), "Select your film"
                )
                title_url = search_results[selected_film].split("/")[-2]
            else:
                selected_film = list(search_results.keys())[0]
                title_url = search_results[selected_film].split("/")[-2]
            logger.info("Letterboxd title found: %s", selected_film)
            return title_url
        except ValueError as e:
            logger.warning("No results found for title '%s': %s", title, e)
            return None  # Return None or handle the error as needed
        except ConnectionError as e:
            logger.error("Failed to retrieve results for title '%s': %s", title, e)
            return None  # Return None or handle the error as needed
        except Exception as e:
            logger.error("An unexpected error occurred: %s", e)
            return None

    def view_exported_lb_data(self, export_type: str):
        """
        Load and display data from exported Letterboxd .csv files in the CLI.

        Parameters:
            export_type (str): The type of export to view (e.g., "Diary", "Watchlist", "Lists").
        """
        logger.debug("Viewing LB export: %s", export_type)
        path = self.export_viewer.get_export_path(export_type)

        if export_type == "Lists":
            logger.debug("Processing 'Lists' export type.")
            letterboxd_url = self.export_viewer.view_lb_export_lists_directory(path, self.renderer.list_print_limit)
        else:
            logger.debug("Processing '%s' export type.", export_type)
            letterboxd_url = self.export_viewer.view_lb_export_csv(export_type, path, self.renderer.list_print_limit)

        if letterboxd_url:
            is_diary = export_type.lower() == "diary"
            tmdb_id = self.lb_connector.get_tmdb_id_from_lb_page(letterboxd_url, is_diary)
            if tmdb_id:
                film_details = self.tmdb_api.fetch_movie_details(tmdb_id, letterboxd_url)
                logger.info("Fetched film details for TMDB ID: %s", tmdb_id)
                self.renderer.render_film_details(film_details)
