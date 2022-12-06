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
        height="50%",
        choices=movies_id,
        keybindings={"skip": [{"key": "escape"}]},
        validate=lambda result: int(result) in movies_id,
        invalid_message="Input must be in the resulting IDs",
    ).execute()
    return movie_id


def select_search_result(results: list[str]) -> int:
    result = inquirer.select(  # type: ignore
        message="Result of your search. Please select one", choices=results, default=results[0]
    ).execute()
    return results.index(result)


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
