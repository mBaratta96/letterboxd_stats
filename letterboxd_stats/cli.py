from rich.console import Console
from rich.table import Table
import pandas as pd

def render_table(df: pd.DataFrame, name: str):
    table = Table(title=name)
    df_str = df.astype(str)
    for col in df_str.columns:
        table.add_column(col)
    for _, row in df_str.iterrows():
        table.add_row(*row)
    console = Console()
    console.print(table)
    
