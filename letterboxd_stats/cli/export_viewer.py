import os
import pandas as pd
from tqdm import tqdm
from pandarallel import pandarallel


from ..utils.render import CLIRenderer
from ..utils.tmdb_connector import TMDbAPI
from ..lb.auth_connector import LBAuthConnector
from ..lb.public_connector import LBPublicConnector


from .user_input_handler import UserInputHandler

tqdm.pandas(desc="Fetching ids...")
pandarallel.initialize(progress_bar=False, verbose=1)

LB_DATA_FILES = {
    "Watchlist": "watchlist.csv", 
    "Diary": "diary.csv", 
    "Ratings": "ratings.csv",
    "Watched": "watched.csv", 
    "Lists": "lists"
    }



class ExportViewer:
    
    def __init__(self, root_folder: str, renderer:CLIRenderer, get_list_runtimes: bool = False, tmdb_api:TMDbAPI=None, lb_connector:LBAuthConnector=None):
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
        self.renderer = renderer
        self.exports_folder = os.path.expanduser(os.path.join(root_folder, "static"))

        self.get_list_runtimes = get_list_runtimes
        
        if self.get_list_runtimes:
            self.lb_connector = lb_connector or LBPublicConnector()
            self.tmdb_api = tmdb_api              
        
        self.user_operations_by_export_type = {
            "Diary": self._process_diary_df,
            "Watchlist": self._process_watchlist_df,
            "Ratings": self._process_ratings_df,
            "Lists": self._process_lists_df,
        }
    
    @staticmethod
    def _process_diary_df(diary_df: pd.DataFrame, sort_ascending: bool = False) -> pd.DataFrame:
        diary_df["Watched Date"] = pd.to_datetime(diary_df["Watched Date"])
        sort_column = UserInputHandler.user_choose_option(diary_df.columns.values.tolist(), "Select the order of your diary entries:")
        diary_df.sort_values(by=sort_column, ascending=sort_ascending, inplace=True)
        diary_df = diary_df.drop(["Rewatch", "Tags"], axis=1)
        return diary_df

    @staticmethod
    def _process_watchlist_df(df: pd.DataFrame, sort_ascending: bool = False) -> pd.DataFrame:
        sort_column = UserInputHandler.user_choose_option(
            df.columns.values.tolist() + ["Shuffle"],
            "Select the order of your watchlist entries:",
        )
        if sort_column == "Shuffle":
            df = df.sample(frac=1)
        else:
            df.sort_values(by=sort_column, ascending=sort_ascending, inplace=True)
        return df

    @staticmethod
    def _process_ratings_df(df: pd.DataFrame, sort_ascending: bool = False) -> pd.DataFrame:
        df["Date"] = pd.to_datetime(df["Date"])
        sort_column = UserInputHandler.user_choose_option(df.columns.values.tolist(), "Select the order of your ratings:")
        df.sort_values(by=sort_column, ascending=sort_ascending, inplace=True)
        if sort_column == "Rating":
            options = df["Rating"].unique().tolist()
            rating_range = UserInputHandler.user_choose_options_multiple(options=options)
            df = df[df["Rating"].isin(rating_range)]
        return df

    def _process_lists_df(self, df: pd.DataFrame, sort_ascending: bool = False) -> pd.DataFrame:
        
        ratings_path = self.get_export_path("Ratings")
        df_ratings = pd.read_csv(ratings_path)
        df_ratings.rename(columns={"Letterboxd URI": "URL"}, inplace=True)
        df = df.merge(df_ratings[["URL", "Rating"]], on="URL", how="inner")
        df.rename(columns={"URL": "Url"}, inplace=True)
        df = df.drop("Description", axis=1)
        df["Rating"] = df["Rating"].astype(float)
        sort_column = UserInputHandler.user_choose_option(df.columns.values.tolist(), "Select the order of your diary entries:")
        df.sort_values(by=sort_column, ascending=sort_ascending, inplace=True)
        avg = {"Rating Mean": "{:.2f}".format(df["Rating"].mean())}
        
        if self.get_list_runtimes is True:
            print("Fetching movie runtimes...")
            ids = df["Url"].parallel_map(self.lb_connector.get_tmdb_id_from_lb_page)
            df["Duration"] = ids.parallel_map(self.tmdb_api.fetch_movie_runtime)  # type: ignore
            avg["Time-weighted Rating Mean"] = "{:.2f}".format(
                ((df["Duration"] / df["Duration"].sum()) * df["Rating"]).sum()
            )
        
        self.renderer.render_dict(avg, expand=False)
        return df
    
    def view_lb_export_lists_directory(self, lists_dir_path: str, limit: int = None) -> str:
        """Select a list from the saved ones."""

        list_names = {
            get_list_name(os.path.join(lists_dir_path, letterboxd_list)): letterboxd_list for letterboxd_list in os.listdir(lists_dir_path)
        }
        name = UserInputHandler.user_choose_option_lb_lists(sorted(list(list_names.keys())))
        return self.view_lb_export_csv("Lists", os.path.join(lists_dir_path, list_names[name]), limit, header=3)

    def view_lb_export_csv(self, export_type: str, path: str, limit: int = None, header=0) -> str:
        """There are some operations that are the same for all the .csv files. So isolate those similar operations,
        and then we proceed to perform the particular operation for a certain file (watchlist, list, diary...).
        OPERATIONS_BY_EXPORT_TYPE selects those particular operations according to the file we opened. Mainly they do
        ordering and column filtering operations.
        """
        df = pd.read_csv(path, header=header)
        df.rename(columns={"Name": "Title", "Letterboxd URI": "Url"}, inplace=True)

        df["Year"] = df["Year"].fillna(0).astype(int)
        
        df = self.user_operations_by_export_type[export_type](df, self.renderer.sort_ascending)

        #print("Test", df)

        if limit is not None:
            df = df.iloc[:limit, :]
        self.renderer.render_table(df, export_type)
        return UserInputHandler.user_choose_film_from_list(df["Title"], df["Url"])
    

    # def _check_if_watched(self, watched_csv_df: pd.DataFrame, film_row: pd.Series) -> bool:
    #     """watched.csv hasn't the TMDB id, so comparison can be done only by title.
    #     This creates the risk of mismatch when two films have the same title. To avoid this,
    #     we must retrieve the TMDB id of the watched film.
    #     """

    #     matched_films = watched_csv_df[watched_csv_df["Name"] == film_row["Title"]]
    #     for _, film in matched_films.iterrows():
    #         film_id = self.lb_connector.get_tmdb_id_from_lb_page(film["Letterboxd URI"])
    #         if film_id == film_row.name:
    #             return True
            
    #     return False


    def add_lb_watched_status_column(self, df: pd.DataFrame, watched_csv: str) -> pd.DataFrame:
        """Check which film of a director you have seen. Add a column to show on the CLI.
        """
        
        df_profile = pd.read_csv(watched_csv)
        
        matching_watched_films = df_profile[df_profile["Name"].isin(df["Title"])].copy()      
        matching_watched_films["TMDB_ID"] = matching_watched_films["Letterboxd URI"].map(
            lambda uri: self.lb_connector.get_tmdb_id_from_lb_page(uri)
        )
        
        watched_ids = set(matching_watched_films["TMDB_ID"].dropna())
        
        df["watched"] = df.index.map(lambda idx: "[X]" if idx in watched_ids else "[ ]")
        
        df["Release Date"] = pd.to_datetime(df["Release Date"])
        df.sort_values(by="Release Date", inplace=True)
        return df
    

    def get_export_path(self, export_type: str) -> str:
        if export_type not in LB_DATA_FILES:
            raise ValueError(f"Invalid export type: {export_type}. Available types: {list(LB_DATA_FILES.keys())}")
        
        path = os.path.expanduser(os.path.join(self.exports_folder, LB_DATA_FILES[export_type]))
        
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
        for file_name in LB_DATA_FILES.values():
            file_path = os.path.join(self.exports_folder, file_name)  # Update path if needed
            if not os.path.exists(file_path):
                return False
        return True

def get_list_name(list_csv_path: str) -> str:
    df = pd.read_csv(list_csv_path, header=1)
    if "Name" not in df.columns or df.empty:
            raise ValueError(f"The list CSV at {list_csv_path} is missing a 'Name' column or is empty.")
    return df["Name"].iloc[0]

