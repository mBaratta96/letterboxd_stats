from rich.console import Console
from rich.table import Table
from rich import box
import pandas as pd
from InquirerPy import inquirer
from InquirerPy.base.control import Choice
from letterboxd_stats import config
from letterboxd_stats import web_scraper as ws
from letterboxd_stats.tmdb_connector import get_movie_duration
from letterboxd_stats import tmdb_connector as tmdbcon
from letterboxd_stats import export_handler
import os

from ascii_magic import AsciiArt
from datetime import datetime

POSTER_URL_PREFIX = "https://www.themoviedb.org/t/p/w600_and_h900_bestv2"

DATA_FILES = {"Watchlist": "watchlist.csv", "Diary": "diary.csv", "Ratings": "ratings.csv", "Lists": "lists"}


def get_list_name(path: str) -> str:
    df = pd.read_csv(path, header=1)
    return df["Name"].iloc[0]


def select_value(values: list[str], message: str, default: str | None = None) -> str:
    value = inquirer.select(  # type: ignore
        message=message,
        choices=values,
        default=default or values[0],
    ).execute()
    return value


def select_film(film_titles: pd.Series, film_ids: pd.Series) -> str:
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


def select_list(names: list[str]) -> str:
    name = inquirer.fuzzy(  # type: ignore
        message="Select your list:",
        mandatory=True,
        max_height="25%",
        choices=names,
        validate=lambda result: result in names,
    ).execute()
    return name


def select_search_result(results: list[str]) -> int:
    choices = [Choice(i, name=r) for i, r in enumerate(results)]
    result = inquirer.select(  # type: ignore
        message="Result of your search. Please select one",
        choices=choices,
        default=choices[0],
    ).execute()
    return result


def select_range(options: list[str]) -> list[str]:
    result = inquirer.rawlist(  # type: ignore
        message="Pick a desired value (or select 'all'). Use space to toggle your choices. CTRL+R to select all.",
        choices=options,
        default=options[0],
        multiselect=True,
        validate=lambda result: len(result) > 0,
    ).execute()
    return result


def print_dict(dict_: dict, expand=True):
    grid = Table.grid(expand=expand, padding=1)
    grid.add_column(style="bold yellow")
    grid.add_column()
    for k, v in dict_.items():
        grid.add_row(str(k), str(v))
    console = Console()
    console.print(grid)

def render_table(df: pd.DataFrame, name: str):
    df_str = df.astype(str)
    table = Table(title=name, box=box.SIMPLE)
    for col in df_str.columns:
        table.add_column(col)
    for _, row in df_str.iterrows():
        table.add_row(*row)
    console = Console()
    console.print(table)


def print_ascii_poster(poster_url: str):
    art = AsciiArt.from_url(poster_url)
    art.to_terminal(columns=int(config["CLI"]["poster_columns"]))

def print_film_details(film_details: dict):
    if film_details["Poster URL"] and config["CLI"]["poster_columns"] > 0:
        print_ascii_poster(film_details["Poster URL"])
        del film_details["Poster URL"]  # Remove the Poster key after displaying it
    if film_details["Title"] == film_details["Original Title"]:
        del film_details["Original Title"]  # Remove the Poster key after displaying it

    print_dict(film_details)



def _validate_date(s: str) -> bool:
    try:
        datetime.strptime(s, "%Y-%m-%d")
    except ValueError:
        return False
    return True


def get_input_add_diary_entry() -> dict[str, str]:
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





def user_add_diary_entry(connector: ws.Connector, title: str):
    payload = get_input_add_diary_entry()
    connector.add_diary_entry(title, payload)



def select_film_from_dataframe(df: pd.DataFrame) -> pd.Series | None:
    print(df["Title"])
    film_id = select_film(df["Title"], df.index.to_series())
    if film_id is None:
        return None
    film_row = df.loc[film_id]
    return film_row


def open_list(path: str, limit: int, ascending: bool) -> str:
    """Select a list from the saved ones."""

    list_names = {
        get_list_name(os.path.join(path, letterboxd_list)): letterboxd_list for letterboxd_list in os.listdir(path)
    }
    name = select_list(sorted(list(list_names.keys())))
    return open_file("Lists", os.path.join(path, list_names[name]), limit, ascending, header=3)



def open_file(filetype: str, path: str, limit, ascending, header=0) -> str:
    """There are some operations that are the same for all the .csv files. So isolate those similar operations,
    and then we proceed to perform the particular operation for a certain file (watchlist, list, diary...).
    FILE_OPERATIONS selects those particular operations according to the file we opened. Mainly they do
    ordering and column filtering operations.
    """

    df = pd.read_csv(path, header=header)
    df.rename(columns={"Name": "Title", "Letterboxd URI": "Url"}, inplace=True)
    df["Year"] = df["Year"].fillna(0).astype(int)
    df = FILE_OPERATIONS[filetype](df, ascending)
    if limit is not None:
        df = df.iloc[:limit, :]
    render_table(df, filetype)
    return select_film(df["Title"], df["Url"])


def _show_lists(df: pd.DataFrame, ascending: bool) -> pd.DataFrame:
    ratings_path = os.path.expanduser(os.path.join(config["root_folder"], "static", "ratings.csv"))
    df_ratings = pd.read_csv(ratings_path)
    df_ratings.rename(columns={"Letterboxd URI": "URL"}, inplace=True)
    df = df.merge(df_ratings[["URL", "Rating"]], on="URL", how="inner")
    df.rename(columns={"URL": "Url"}, inplace=True)
    df = df.drop("Description", axis=1)
    df["Rating"] = df["Rating"].astype(float)
    sort_column = select_value(df.columns.values.tolist(), "Select the order of your diary entries:")
    df.sort_values(by=sort_column, ascending=ascending, inplace=True)
    avg = {"Rating Mean": "{:.2f}".format(df["Rating"].mean())}
    if config["TMDB"]["get_list_runtimes"] is True:
        ids = df["Url"].parallel_map(ws.get_tmdb_id_from_lb)
        df["Duration"] = ids.parallel_map(lambda id: get_movie_duration(id))  # type: ignore
        avg["Time-weighted Rating Mean"] = "{:.2f}".format(
            ((df["Duration"] / df["Duration"].sum()) * df["Rating"]).sum()
        )
    print_dict(avg, expand=False)
    return df


def _show_watchlist(df: pd.DataFrame, ascending: bool) -> pd.DataFrame:
    sort_column = select_value(
        df.columns.values.tolist() + ["Shuffle"],
        "Select the order of your watchlist entries:",
    )
    if sort_column == "Shuffle":
        df = df.sample(frac=1)
    else:
        df.sort_values(by=sort_column, ascending=ascending, inplace=True)
    return df


def _show_diary(df: pd.DataFrame, ascending: bool) -> pd.DataFrame:
    df["Watched Date"] = pd.to_datetime(df["Watched Date"])
    sort_column = select_value(df.columns.values.tolist(), "Select the order of your diary entries:")
    df.sort_values(by=sort_column, ascending=ascending, inplace=True)
    df = df.drop(["Rewatch", "Tags"], axis=1)
    return df


def _show_ratings(df: pd.DataFrame, ascending: bool) -> pd.DataFrame:
    df["Date"] = pd.to_datetime(df["Date"])
    sort_column = select_value(df.columns.values.tolist(), "Select the order of your ratings:")
    df.sort_values(by=sort_column, ascending=ascending, inplace=True)
    if sort_column == "Rating":
        options = df["Rating"].unique().tolist()
        rating_range = select_range(options=options)
        df = df[df["Rating"].isin(rating_range)]
    return df


FILE_OPERATIONS = {
    "Diary": _show_diary,
    "Watchlist": _show_watchlist,
    "Ratings": _show_ratings,
    "Lists": _show_lists,
}



def search_person(args_search: str):
    """Search for a director, list his/her films and check if you have watched them."""
    
    search_results = tmdbcon.search_tmdb_people(args_search)
    search_result = search_results[select_search_result([result.name for result in search_results])]  # Get User Input
    df, name, known_for_department = tmdbcon.get_tmdb_person_and_movies(search_result['id'])
    department = select_value(
        df["Department"].unique(), f"Select a department for {name}", known_for_department
    )
    df = df[df["Department"] == department]
    df = df.drop("Department", axis=1)
    # person.details provides movies without time duration. If the user wants<S-D-A>
    # (since this slows down the process) get with the movie.details API.
    if config["TMDB"]["get_list_runtimes"] is True:
        df["Duration"] = df.index.to_series().parallel_map(get_movie_duration)  # type: ignore
    
    
    path = os.path.expanduser(os.path.join(config["root_folder"], "static", "watched.csv"))
    check_path(path)
    df = export_handler.add_lb_watched_status_column(df, path)
    render_table(df, name)

    film = select_film_from_dataframe(df)

    # We want to print the link of the selected film. This has to be retrieved from the search page.
    while film is not None:
        search_film_query = f"{film['Title']} {film['Release Date'].year}"  # type: ignore
        title_url = search_for_lb_title(search_film_query)
        lb_url = ws.create_lb_operation_url_with_title(title_url, "film_page")
        selected_details = tmdbcon.get_all_tmdb_movie_details(int(film.name), lb_url)  # type: ignore
        print_film_details(selected_details)
        
        film = select_film_from_dataframe(df)


def check_path(path: str):
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"No Letterboxd data was found in {path}. Make sure the path is correct or run -d to download your data"
        )


def search_film(connector: ws.Connector, search_query: str):
    letterboxd_title = search_for_lb_title(search_query, True)
    selected_details = get_all_film_details(letterboxd_title, connector)
    print_film_details(selected_details)

    while True:
        answer = select_value(["Exit"] + list(ws.FILM_OPERATIONS.keys()), "Select operation:")
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

    
        
def get_all_film_details(letterboxd_title: str, connector: ws.Connector = None):
    film_url = ws.create_lb_operation_url_with_title(letterboxd_title, "film_page")
    tmdb_id = ws.get_tmdb_id_from_lb(film_url)
    
    selected_details = {}
    if tmdb_id:
        tmdb_details = tmdbcon.get_all_tmdb_movie_details(tmdb_id, film_url)  # type: ignore
        selected_details.update(tmdb_details)
    if connector and connector.logged_in:
        lb_data = connector.fetch_lb_film_user_metadata(letterboxd_title)
        selected_details.update(lb_data)
        
    return selected_details


def search_for_lb_title(title: str, allow_selection=False) -> str:
    """Search a film and get its Letterboxd link.
    For reference: https://letterboxd.com/search/seven+samurai/?adult
    """
    search_page = ws.get_search_results_from_lb(title)
    # If we want to select films from the search page, get more data to print the selection prompt.
    if allow_selection:
        film_list = search_page.xpath("//div[@class='film-detail-content']")
        if len(film_list) == 0:
            raise ValueError(f"No results found for your Letterboxd film search.")
        title_years_directors_links = {}
        for film in film_list:
            title = film.xpath("./h2/span/a")[0].text.rstrip()
            director = director[0].text if len(director := film.xpath("./p/a")) > 0 else ""
            year = f"({year[0].text}) " if len(year := film.xpath("./h2/span//small/a")) > 0 else ""
            link = film.xpath("./h2/span/a")[0].get("href")
            title_years_directors_links[f"{title} {year}- {director}"] = link
        selected_film = select_value(list(title_years_directors_links.keys()), "Select your film")
        title_url = title_years_directors_links[selected_film].split("/")[-2]
    else:
        title_url = search_page.xpath("//span[@class='film-title-wrapper']/a")[0].get("href").split("/")[-2]
    return title_url

 
def display_data(args_limit: int, args_ascending: bool, data_type: str):
    """Load and show on the CLI different .csv files that you have downloaded with the -d flag."""

    path = os.path.expanduser(os.path.join(config["root_folder"], "static", DATA_FILES[data_type]))
    check_path(path)
    letterboxd_url = (
        open_file(data_type, path, args_limit, args_ascending)
        if data_type != "Lists"
        else open_list(path, args_limit, args_ascending)
    )
    # If you select a film, show its details.
    if letterboxd_url is not None:
        id = ws.get_tmdb_id_from_lb(letterboxd_url, data_type == "diary")
        if id is not None:
            selected_details = tmdbcon.get_all_tmdb_movie_details(id, letterboxd_url)
            print_film_details(selected_details)

