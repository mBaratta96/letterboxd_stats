from rich.console import Console
from rich.table import Table
from rich import box
import pandas as pd
from InquirerPy import inquirer
from InquirerPy.base.control import Choice
from letterboxd_stats import config
from ascii_magic import AsciiArt

IMAGE_URL = "https://www.themoviedb.org/t/p/w600_and_h900_bestv2"


def select_value(values: list[str], message: str, default: str | None = None):
    value = inquirer.select(  # type: ignore
        message=message,
        choices=values,
        default=default or values[0],
    ).execute()
    return value


def select_movie_id(movies_info: pd.DataFrame) -> int:
    movie_id = inquirer.fuzzy(  # type: ignore
        message="Write movie id for more information",
        mandatory=False,
        max_height="25%",
        choices=[
            Choice(value=id, name=f"{id} - {title}") for id, title in zip(movies_info["id"], movies_info["title"])
        ],
        keybindings={"skip": [{"key": "escape"}]},
        validate=lambda result: result in movies_info["id"].values,
        filter=lambda result: None if result is None else int(result),
        invalid_message="Input must be in the resulting IDs",
    ).execute()
    return movie_id


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


def select_movie(movie_df: pd.DataFrame) -> str:
    result = inquirer.fuzzy(  # type: ingore
        message="Write movie id for more information",
        mandatory=False,
        max_height="25%",
        choices=[
            Choice(value=url, name=f"{title}") for url, title in zip(movie_df["url"], movie_df["title"])
        ],
        keybindings={"skip": [{"key": "escape"}]},
        invalid_message="Input must be in the resulting IDs",
    ).execute()
    return result


def print_film(film):
    grid = Table.grid(expand=True, padding=1)
    grid.add_column()
    grid.add_column()
    for k, v in film.items():
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


def download_poster(poster: str):
    if config['poster_columns'] > 0:
        art = AsciiArt.from_url(IMAGE_URL + poster)
        art.to_terminal(columns=180)
