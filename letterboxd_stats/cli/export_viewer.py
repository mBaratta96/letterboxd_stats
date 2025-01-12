import os
import pandas as pd
from .user_input_handler import UserInputHandler
from ..core.export_handler import get_export_path, get_list_name
from ..core.render import CLIRenderer
from ..core.letterboxd_connector import LBConnector
from ..core.tmdb_connector import TMDbAPI


class ExportViewer:
    
    def __init__(self, root_folder: str, renderer:CLIRenderer, get_list_runtimes: bool = False, tmdb_api:TMDbAPI=None, lb_connector:LBConnector=None):
        """
        Initialize the LetterboxdCLI with optional configuration.
        """
        self.renderer = renderer
        self.root_folder = root_folder

        self.get_list_runtimes = get_list_runtimes
        
        if self.get_list_runtimes:
            self.lb_connector = lb_connector or LBConnector()
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
        
        ratings_path = get_export_path(self.root_folder, "Ratings")
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
            df["Duration"] = ids.parallel_map(self.tmdb_api.get_movie_runtime)  # type: ignore
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

    def view_lb_export_csv(self, filetype: str, path: str, limit: int = None, header=0) -> str:
        """There are some operations that are the same for all the .csv files. So isolate those similar operations,
        and then we proceed to perform the particular operation for a certain file (watchlist, list, diary...).
        OPERATIONS_BY_EXPORT_TYPE selects those particular operations according to the file we opened. Mainly they do
        ordering and column filtering operations.
        """
        df = pd.read_csv(path, header=header)
        df.rename(columns={"Name": "Title", "Letterboxd URI": "Url"}, inplace=True)

        df["Year"] = df["Year"].fillna(0).astype(int)
        
        df = self.user_operations_by_export_type[filetype](df, self.renderer.sort_ascending)

        print("Test", df)

        if limit is not None:
            df = df.iloc[:limit, :]
        self.renderer.render_table(df, filetype)
        return UserInputHandler.user_choose_film_from_list(df["Title"], df["Url"])
    
