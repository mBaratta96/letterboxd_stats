from rich.console import Console
from rich.table import Table
from rich import box
import pandas as pd
from InquirerPy import inquirer
from InquirerPy.base.control import Choice
from letterboxd_stats import config
from ascii_magic import AsciiArt
from datetime import datetime

IMAGE_URL = "https://www.themoviedb.org/t/p/w600_and_h900_bestv2"


def select_value(values: list[str], message: str, default: str | None = None) -> str:
    value = inquirer.select(  # type: ignore
        message=message,
        choices=values,
        default=default or values[0],
    ).execute()
    return value


def select_film(films: pd.Series, results: pd.Series) -> str:
    result = inquirer.fuzzy(  # type: ignore
        message="Select film for more information:",
        mandatory=False,
        max_height="25%",
        choices=[Choice(value=result, name=title) for result, title in zip(results, films)],
        keybindings={"skip": [{"key": "escape"}]},
        invalid_message="Input not in list of films.",
        validate=lambda result: result in results.values,
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


def print_film(film: dict, expand=True):
    grid = Table.grid(expand=expand, padding=1)
    grid.add_column(style="bold yellow")
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
    if config["CLI"]["poster_columns"] > 0:
        art = AsciiArt.from_url(IMAGE_URL + poster)
        art.to_terminal(columns=int(config["CLI"]["poster_columns"]))


def _validate_date(s: str) -> bool:
    try:
        datetime.strptime(s, "%Y-%m-%d")
    except ValueError:
        return False
    return True


def add_film_questions() -> dict[str, str]:
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
    liked = inquirer.confirm(message="Add to your ""Liked"" films?").execute()  # type: ignore
    review = inquirer.text(  # type: ignore
        message="Write a review. "
        + "Use HTML tags for formatting (<b>, <i>, <a href='[URL]'>, <blockquote<>). "
        + "Press Enter for multiline.",
        multiline=True,
    ).execute()
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
