from rich.console import Console
from rich.table import Table
from rich import box
import pandas as pd
from InquirerPy import inquirer


def select_department(departments: list[str], known_for_department: str):
    print(departments)
    print(known_for_department)
    department = inquirer.select(
        message="Select a department",
        choices=departments,
        default=known_for_department
    ).execute()
    return department


def render_table(df: pd.DataFrame, name: str):
    table = Table(title=name, box=box.SIMPLE)
    df_str = df.astype(str)
    for col in df_str.columns:
        table.add_column(col)
    for _, row in df_str.iterrows():
        table.add_row(*row)
    console = Console()
    console.print(table)
