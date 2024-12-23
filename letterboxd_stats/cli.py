from rich.console import Console
from rich.table import Table
from rich import box
import pandas as pd
from InquirerPy import inquirer
from InquirerPy.base.control import Choice
from letterboxd_stats import config
from letterboxd_stats import letterboxd_connector as lbcon
from letterboxd_stats.tmdb_connector import get_movie_duration
from letterboxd_stats import tmdb_connector as tmdbcon
from letterboxd_stats import export_handler as eh
import os

from ascii_magic import AsciiArt
from datetime import datetime

# Utils
#################

def _validate_date(s: str) -> bool:
    try:
        datetime.strptime(s, "%Y-%m-%d")
    except ValueError:
        return False
    return True

def fetch_all_film_metadata(letterboxd_title: str, connector: lbcon.LBConnector = None):
    film_url = lbcon.create_lb_operation_url_with_title(letterboxd_title, "film_page")
    tmdb_id = lbcon.get_tmdb_id_from_lb(film_url)
    selected_details = {}
    if tmdb_id:
        tmdb_details = tmdbcon.get_all_tmdb_movie_details(tmdb_id, film_url)  # type: ignore
        selected_details.update(tmdb_details)
    if connector and connector.logged_in:
        lb_data = connector.fetch_lb_film_user_metadata(letterboxd_title)
        selected_details.update(lb_data)
    return selected_details

# Render to CLI
################

def render_generic_table(df: pd.DataFrame, name: str):
    df_str = df.astype(str)
    table = Table(title=name, box=box.SIMPLE)
    for col in df_str.columns:
        table.add_column(col)
    for _, row in df_str.iterrows():
        table.add_row(*row)
    console = Console()
    console.print(table)
    
def render_generic_dict(dict_: dict, expand=True):
    grid = Table.grid(expand=expand, padding=1)
    grid.add_column(style="bold yellow")
    grid.add_column()
    for k, v in dict_.items():
        grid.add_row(str(k), str(v))
    console = Console()
    console.print(grid)

def render_film_details(film_details: dict):
    if "Poster URL" in film_details and config["CLI"]["poster_columns"] > 0:
        render_ascii_poster(film_details["Poster URL"])
        del film_details["Poster URL"]  # Remove the Poster key after displaying it
    if ("Title" in film_details and "Original Title" in film_details) and film_details["Title"] == film_details["Original Title"]:
        del film_details["Original Title"]  # Remove Original Title if it matches Title
    render_generic_dict(film_details, False)

def render_ascii_poster(poster_url: str):
    art = AsciiArt.from_url(poster_url)
    art.to_terminal(columns=int(config["CLI"]["poster_columns"]))
    
def render_exported_lb_data(export_type: str, limit: int = None, ascending: bool = False):
    """Load and show on the CLI different .csv files that you have downloaded with the -d flag."""

    path = eh.generate_export_csv_path(export_type)
    eh.check_path_exists(path)
    letterboxd_url = (
        user_view_lb_export_csv(export_type, path, limit, ascending)
        if export_type != "Lists"
        else user_view_lb_export_lists_directory(path, limit, ascending)
    )
    # If you select a film, show its details.
    if letterboxd_url is not None:
        id = lbcon.get_tmdb_id_from_lb(letterboxd_url, export_type == "diary")
        if id is not None:
            selected_details = tmdbcon.get_all_tmdb_movie_details(id, letterboxd_url)
            render_film_details(selected_details)
            

# Allow User to interact with LB Exports
########################################

def user_view_lb_export_lists_directory(lists_dir_path: str, limit: int = None, ascending: bool = False) -> str:
    """Select a list from the saved ones."""

    list_names = {
        eh.get_list_name(os.path.join(lists_dir_path, letterboxd_list)): letterboxd_list for letterboxd_list in os.listdir(lists_dir_path)
    }
    name = user_choose_option_lists(sorted(list(list_names.keys())))
    return user_view_lb_export_csv("Lists", os.path.join(lists_dir_path, list_names[name]), limit, ascending, header=3)

def user_view_lb_export_csv(filetype: str, path: str, limit: int = None, ascending: bool = False, header=0) -> str:
    """There are some operations that are the same for all the .csv files. So isolate those similar operations,
    and then we proceed to perform the particular operation for a certain file (watchlist, list, diary...).
    OPERATIONS_BY_EXPORT_TYPE selects those particular operations according to the file we opened. Mainly they do
    ordering and column filtering operations.
    """

    df = pd.read_csv(path, header=header)
    df.rename(columns={"Name": "Title", "Letterboxd URI": "Url"}, inplace=True)
    df["Year"] = df["Year"].fillna(0).astype(int)
    df = USER_OPERATIONS_BY_EXPORT_TYPE[filetype](df, ascending)
    if limit is not None:
        df = df.iloc[:limit, :]
    render_generic_table(df, filetype)
    return user_choose_film_from_list(df["Title"], df["Url"])


def _user_process_diary_df(df: pd.DataFrame, ascending: bool = False) -> pd.DataFrame:
    df["Watched Date"] = pd.to_datetime(df["Watched Date"])
    sort_column = user_choose_option(df.columns.values.tolist(), "Select the order of your diary entries:")
    df.sort_values(by=sort_column, ascending=ascending, inplace=True)
    df = df.drop(["Rewatch", "Tags"], axis=1)
    return df

def _user_process_watchlist_df(df: pd.DataFrame, ascending: bool = False) -> pd.DataFrame:
    sort_column = user_choose_option(
        df.columns.values.tolist() + ["Shuffle"],
        "Select the order of your watchlist entries:",
    )
    if sort_column == "Shuffle":
        df = df.sample(frac=1)
    else:
        df.sort_values(by=sort_column, ascending=ascending, inplace=True)
    return df

def _user_process_ratings_df(df: pd.DataFrame, ascending: bool = False) -> pd.DataFrame:
    df["Date"] = pd.to_datetime(df["Date"])
    sort_column = user_choose_option(df.columns.values.tolist(), "Select the order of your ratings:")
    df.sort_values(by=sort_column, ascending=ascending, inplace=True)
    if sort_column == "Rating":
        options = df["Rating"].unique().tolist()
        rating_range = user_choose_options_multiple(options=options)
        df = df[df["Rating"].isin(rating_range)]
    return df

def _user_process_lists_df(df: pd.DataFrame, ascending: bool = False) -> pd.DataFrame:
    ratings_path = eh.generate_export_csv_path("Ratings")
    df_ratings = pd.read_csv(ratings_path)
    df_ratings.rename(columns={"Letterboxd URI": "URL"}, inplace=True)
    df = df.merge(df_ratings[["URL", "Rating"]], on="URL", how="inner")
    df.rename(columns={"URL": "Url"}, inplace=True)
    df = df.drop("Description", axis=1)
    df["Rating"] = df["Rating"].astype(float)
    sort_column = user_choose_option(df.columns.values.tolist(), "Select the order of your diary entries:")
    df.sort_values(by=sort_column, ascending=ascending, inplace=True)
    avg = {"Rating Mean": "{:.2f}".format(df["Rating"].mean())}
    if config["TMDB"]["get_list_runtimes"] is True:
        ids = df["Url"].parallel_map(lbcon.get_tmdb_id_from_lb)
        df["Duration"] = ids.parallel_map(lambda id: get_movie_duration(id))  # type: ignore
        avg["Time-weighted Rating Mean"] = "{:.2f}".format(
            ((df["Duration"] / df["Duration"].sum()) * df["Rating"]).sum()
        )
    render_generic_dict(avg, expand=False)
    return df

USER_OPERATIONS_BY_EXPORT_TYPE = {
    "Diary": _user_process_diary_df,
    "Watchlist": _user_process_watchlist_df,
    "Ratings": _user_process_ratings_df,
    "Lists": _user_process_lists_df,
}


# Get User Input
#################

def user_choose_option_lists(options: list[str]) -> str:
    result = inquirer.fuzzy(  # type: ignore
        message="Select your list:",
        mandatory=True,
        max_height="25%",
        choices=options,
        validate=lambda result: result in options,
    ).execute()
    return result

def user_choose_option_search_result(options: list[str]) -> int:
    choices = [Choice(i, name=r) for i, r in enumerate(options)]
    result = inquirer.select(  # type: ignore
        message="Result of your search. Please select one",
        choices=choices,
        default=choices[0],
    ).execute()
    return result


def user_choose_options_multiple(options: list[str]) -> list[str]:
    result = inquirer.checkbox(
        message="Pick a desired value (or select 'all'). Use space to toggle your choices. Press Enter to confirm.",
        choices=[Choice(option, enabled=True) for option in options],  # Pre-select all
        validate=lambda result: len(result) > 0,  # Ensure at least one option is selected
    ).execute()
    return result


def user_choose_option(options: list[str], message: str, default: str | None = None) -> str:
    result = inquirer.select(  # type: ignore
        message=message,
        choices=options,
        default=default or options[0],
    ).execute()
    return result


def user_choose_film_from_list(film_titles: pd.Series, film_ids: pd.Series) -> str:
    result = inquirer.fuzzy(  # type: ignore
        message="Select film for more information:",
        mandatory=False,
        max_height="25%",
        choices=[Choice(value=film_id, name=film_title) for film_id, film_title in zip(film_ids, film_titles)],
        keybindings={"skip": [{"key": "escape"}]},
        invalid_message="Input not in list of films.",
        validate=lambda selected_id: selected_id in film_ids.values,
    ).execute()
    return result

def user_choose_film_from_dataframe(df: pd.DataFrame) -> pd.Series | None:
    film_id = user_choose_film_from_list(df["Title"], df.index.to_series())
    if film_id is None:
        return None
    film_row = df.loc[film_id]
    return film_row

def user_search_person(connector: lbcon.LBConnector, search_query: str):
    """Search for a director, list his/her films and check if you have watched them."""
    search_results = tmdbcon.search_tmdb_people(search_query)
    search_result = search_results[user_choose_option_search_result([result.name for result in search_results])]  # Get User Input
    df, name, known_for_department = tmdbcon.get_tmdb_person_and_movies(search_result['id'])
    department = user_choose_option(
        df["Department"].unique(), f"Select a department for {name}", known_for_department
    )
    df = df[df["Department"] == department]
    df = df.drop("Department", axis=1)
    # person.details provides movies without time duration. If the user wants<S-D-A>
    # (since this slows down the process) get with the movie.details API.
    if config["TMDB"]["get_list_runtimes"] is True:
        df["Duration"] = df.index.to_series().parallel_map(get_movie_duration)  # type: ignore
    
    df = df.drop_duplicates()
    path = eh.generate_export_csv_path("Watched")
    eh.check_path_exists(path)
    df = eh.add_lb_watched_status_column(df, path)
    render_generic_table(df, name)

    film = user_choose_film_from_dataframe(df)

    # We want to print the link of the selected film. This has to be retrieved from the search page.
    while film is not None:
        search_film_query = f"{film['Title']} {film['Release Date'].year}"  # type: ignore
        title_url = user_search_for_lb_title(connector, search_film_query)
        lb_url = lbcon.create_lb_operation_url_with_title(title_url, "film_page")
        selected_details = tmdbcon.get_all_tmdb_movie_details(int(film.name), lb_url)  # type: ignore
        render_film_details(selected_details)
        
        film = user_choose_film_from_dataframe(df)

def user_search_film(connector: lbcon.LBConnector, search_query: str):
    letterboxd_title = user_search_for_lb_title(connector, search_query, True)
    selected_details = fetch_all_film_metadata(letterboxd_title, connector)
    render_film_details(selected_details)

    while True:
        answer = user_choose_option(["Exit"] + list(lbcon.FILM_OPERATIONS.keys()), "Select operation:")
        if answer == "Exit":
            break
        if answer == "Rate film":
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
            connector.perform_operation(answer, letterboxd_title, stars)
        else:
            connector.perform_operation(answer, letterboxd_title)

def user_search_for_lb_title(connector: lbcon.LBConnector, title: str, allow_selection=False) -> str:
    """Search a film and get its Letterboxd link.
    For reference: https://letterboxd.com/search/seven+samurai/?adult
    """
    search_results=connector.search_lb_by_title(title)
    # If we want to select films from the search page, get more data to print the selection prompt.
    if allow_selection:
        selected_film = user_choose_option(list(search_results.keys()), "Select your film")
        title_url = search_results[selected_film].split("/")[-2]
    else:
        selected_film = list(search_results.keys())[0]
        title_url = search_results[selected_film].split("/")[-2]
    return title_url

def user_create_dairy_entry_payload() -> dict[str, str]:
    print("Set all the infos for the film:\n")
    specify_date = inquirer.confirm(message="Specify date?").execute()  # type: ignore
    today = datetime.today().strftime("%Y-%m-%d")
    get_specified_date = inquirer.text(  # type: ignore
        message="Set viewing date:",
        default=today,
        validate=lambda d: _validate_date(d),
        invalid_message="Wrong date format",
    )
    specified_date = get_specified_date.execute() if specify_date else today
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
    liked = inquirer.confirm(message="Give this film a ♥?").execute()  # type: ignore
    leave_review = inquirer.confirm(message="Leave a review?").execute()  # type: ignore
    review = inquirer.text(  # type: ignore
        message="Write a review. "
        + "Use HTML tags for formatting (<b>, <i>, <a href='[URL]'>, <blockquote<>). "
        + "Press Enter for multiline.",
        multiline=True,
    ).execute() if leave_review else ""
    contains_spoilers = False
    if len(review) > 0:
        contains_spoilers = inquirer.confirm(message="The review contains spoilers?").execute()  # type: ignore
    rewatch = inquirer.confirm(message="Have you seen this film before?").execute()  # type: ignore
    payload = {
        "specifiedDate": specify_date,
        "viewingDateStr": specified_date,
        "rating": stars,
        "liked": liked,
        "review": review,
        "containsSpoilers": contains_spoilers,
        "rewatch": rewatch,
    }
    if len(review.strip().rstrip("\n")) > 0 or specify_date:
        tags = inquirer.text(message="Add some comma separated tags. Or leave this empty.").execute()  # type: ignore
        payload["tag"] = (tags.split(",") if "," in tags else tags) if len(tags) > 0 else ""
    return payload

def user_add_diary_entry(connector: lbcon.LBConnector, title: str):
    payload = user_create_dairy_entry_payload()
    connector.add_diary_entry(title, payload)
    