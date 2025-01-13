import os
from InquirerPy import inquirer

from ..utils.render import CLIRenderer
from ..utils.tmdb_connector import TMDbAPI
from ..lb.auth_connector import LBAuthConnector
from ..lb.utilities import LB_OPERATIONS, create_lb_operation_url_with_title

from .user_input_handler import UserInputHandler
from .export_viewer import ExportViewer



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
        Initialize the LetterboxdCLI with optional configuration.
        """
        self.root_folder = os.path.expanduser(root_folder)

        self.lb_connector = LBAuthConnector(lb_username, lb_password, self.root_folder+"tmp.db")
        self.tmdb_api = TMDbAPI(tmdb_api_key)
        self.renderer = CLIRenderer(limit, cli_poster_columns, cli_ascending)
        self.export_viewer = ExportViewer(self.root_folder, self.renderer, tmdb_get_list_runtimes, self.tmdb_api)


    def download_stats(self):
        dir = self.lb_connector.download_stats(os.path.expanduser(os.path.join(self.root_folder, "static")))
        print(f"Data successfully downloaded in {dir}")
        return dir
        
        
    def fetch_all_film_metadata(self, letterboxd_title: str):
        film_url = create_lb_operation_url_with_title(letterboxd_title, "film_page")
        tmdb_id = self.lb_connector.get_tmdb_id_from_lb_page(film_url)
        selected_details = {}
        
        if tmdb_id:
            tmdb_details = self.tmdb_api.fetch_all_movie_details(tmdb_id, film_url)  # type: ignore
            selected_details.update(tmdb_details)
        if self.lb_connector and self.lb_connector.auth.logged_in:
            lb_data = self.lb_connector.fetch_lb_film_user_metadata(letterboxd_title)
            selected_details.update(lb_data)
        return selected_details

    def search_person(self, search_query: str):
        """Search for a director, list his/her films and check if you have watched them."""
        search_results = self.tmdb_api.search_tmdb_people(search_query)
        search_result = search_results[UserInputHandler.user_choose_option_search_result([result.name for result in search_results])]  # Get User Input
        df, name, known_for_department = self.tmdb_api.fetch_tmdb_person_details(search_result['id'])
        department = UserInputHandler.user_choose_option(
            df["Department"].unique(), f"Select a department for {name}", known_for_department
        )
        df = df[df["Department"] == department]
        df = df.drop("Department", axis=1)
        # person.details provides movies without time duration. If the user wants<S-D-A>
        # (since this slows down the process) get with the movie.details API.
        
        if self.export_viewer.get_list_runtimes is True:
            print(f"Fetching movie runtimes...", end="", flush=True)
            df["Duration"] = df.index.to_series().parallel_map(self.tmdb_api.fetch_movie_runtime)  # type: ignore
            print("\rRetrieved all movie runtimes.")

        df = df.drop_duplicates()
        
        if self.export_viewer.export_exists():
            path = self.export_viewer.get_export_path("Watched")
            df = self.export_viewer.add_lb_watched_status_column(df, path)
        
        self.renderer.render_table(df, name)

        film = UserInputHandler.user_choose_film_from_dataframe(df)

        # We want to print the link of the selected film. This has to be retrieved from the search page.
        while film is not None:
            search_film_query = f"{film['Title']} {film['Release Date'].year}"  # type: ignore
            letterboxd_title = self.search_for_lb_title(search_film_query)
            film_details = self.fetch_all_film_metadata(letterboxd_title)            
            self.renderer.render_film_details(film_details)
            
            film = UserInputHandler.user_choose_film_from_dataframe(df)

    def search_film(self, search_query: str):
        letterboxd_title = self.search_for_lb_title(search_query, True)
        film_details = self.fetch_all_film_metadata(letterboxd_title)
        
        self.renderer.render_film_details(film_details)

        while True:
            answer = UserInputHandler.user_choose_option(["Exit"] + list(LB_OPERATIONS.keys()), "Select operation:")
            if answer == "Exit":
                break
            if answer == "Update film rating":
                stars = inquirer.number(  # type: ignore
                    message="How many stars? (Only values from 0 to 5)",
                    float_allowed=True,
                    min_allowed=0.0,
                    max_allowed=5.0,
                    validate=lambda n: (2 * float(n)).is_integer(),
                    invalid_message="Wrong value. Either an integer or a .5 float",
                    replace_mode=True,
                    filter=lambda n: int(2 * float(n)),
                ).execute()
                self.lb_connector.perform_operation(answer, letterboxd_title, stars)
            elif answer == "Add to diary":
                diary_payload = UserInputHandler.user_create_diary_entry_payload()
                self.lb_connector.perform_operation(answer, letterboxd_title, diary_payload)
            else:
                self.lb_connector.perform_operation(answer, letterboxd_title)

    def search_for_lb_title(self, title: str, allow_selection=False) -> str:
        """Search a film and get its Letterboxd link.
        For reference: https://letterboxd.com/search/seven+samurai/?adult
        """
        search_results=self.lb_connector.search_lb_by_title(title)
        
        
        
        # If we want to select films from the search page, get more data to print the selection prompt.
        if allow_selection:
            selected_film = UserInputHandler.user_choose_option(list(search_results.keys()), "Select your film")
            title_url = search_results[selected_film].split("/")[-2]
        else:
            selected_film = list(search_results.keys())[0]
            title_url = search_results[selected_film].split("/")[-2]
        return title_url

    def add_diary_entry(self, title: str):
        payload = UserInputHandler.user_create_diary_entry_payload()
        self.lb_connector.add_diary_entry(title, payload)
        
    def view_exported_lb_data(self, export_type: str):
        """Load and display CLI data from exported .csv files."""        

        path = self.export_viewer.get_export_path(export_type)

        if export_type == "Lists":
            letterboxd_url = self.export_viewer.view_lb_export_lists_directory(path, self.renderer.list_print_limit)
        else:
            letterboxd_url = self.export_viewer.view_lb_export_csv(export_type, path, self.renderer.list_print_limit)

        if letterboxd_url:
            tmdb_id = self.lb_connector.get_tmdb_id_from_lb_page(letterboxd_url, export_type.lower() == "diary")
            if tmdb_id:
                film_details = self.tmdb_api.fetch_all_movie_details(tmdb_id, letterboxd_url)
                self.renderer.render_film_details(film_details)
