from rich.console import Console
from rich.table import Table
from rich import box
import pandas as pd
from InquirerPy import inquirer


def select_department(departments: list[str], name: str, known_for_department: str) -> str:
    department = inquirer.select(  # type: ignore
        message=f"Select a department for {name}",
        choices=departments,
        default=known_for_department,
    ).execute()
    return department


def select_movie_id(movies_id: list[int]) -> str:
    movie_id = inquirer.fuzzy(  # type: ignore
        message="Write movie id for more information",
        mandatory=False,
        max_height="25%",
        choices=movies_id,
        keybindings={"skip": [{"key": "escape"}]},
        validate=lambda result: int(result) in movies_id,
        invalid_message="Input must be in the resulting IDs",
    ).execute()
    return movie_id


def select_search_result(results: list[str]) -> int:
    result = inquirer.select(  # type: ignore
        message="Result of your search. Please select one",
        choices=results,
        default=results[0],
        transformer=lambda result: results.index(result),
    ).execute()
    return result


def select_sort(sort_options: list[str]) -> str:
    result = inquirer.select(  # type: ignore
        message="Select the order of your diary entry:", choices=sort_options, default=sort_options[0]
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
