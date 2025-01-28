"""
CLIRenderer Module
==================

This module provides utilities for rendering data and visuals in the terminal
using the `rich` library and additional ASCII rendering tools. It is
tailored for Letterboxd-related content, offering functionality to render tables,
dictionaries, and images (posters) in ASCII  format.

Classes:
--------
- CLIRenderer:
    Handles rendering of various data structures and visuals in a terminal-based CLI.

"""

import logging
import sys

import pandas as pd
from ascii_magic import AsciiArt
from rich.box import SIMPLE
from rich.console import Console
from rich.table import Table

logger = logging.getLogger(__name__)

class CLIRenderer:
    """
    A utility class for rendering data and visuals in a terminal-based CLI application.

    Attributes:
    -----------
    - poster_columns (int): The width of the ASCII poster rendering in characters. Defaults to 80.
    - sort_ascending (bool): Whether or not data is sorted in ascending order. Defaults to False.
    - list_print_limit (int | None): Optional limit for the number of rows to display in tables.
    - console (Console): Instance of `rich.console.Console` for rendering output to the terminal.

    Methods:
    --------
    - __init__(limit: int = None, poster_columns: int = 80, sort_ascending: bool = False):
        Initializes the `CLIRenderer` instance with optional parameters for row limits,
        poster width, and sorting order.

    - render_table(df: pd.DataFrame, title: str):
        Renders a Pandas DataFrame as a table in the console with a given title.

    - render_dict(data: dict, expand: bool = True):
        Renders a dictionary as a grid with key-value pairs.

    - render_text(string: str):
        Prints a plain text string to the console, replacing backslashes with forward slashes.

    - render_film_details(film_details: dict):
        Renders film details in a formatted dictionary and optionally displays a poster
        in ASCII art if the `Poster` key is present.

    - render_ascii_image_from_url(img_url: str, poster_columns: int = 80):
        Fetches an image from a URL and renders it in colored ASCII art within the terminal.

    Notes:
    ------
    - This class assumes a working internet connection for fetching images via URLs.
    - The `rich` library provides flexible formatting and color options, while `ascii_magic`
      ensures visually appealing ASCII art rendering.
    """
    def __init__(
        self, limit: int = None, poster_columns: int = 80, sort_ascending: bool = False
    ):
        """
        Initialize the CLI Renderer.

        Parameters:
        - limit: Optional limit for rows to display in tables.
        - poster_columns: Width of ASCII poster rendering.
        - sort_ascending: Sorting order for rendered data.
        """

        self.poster_columns = poster_columns
        self.sort_ascending = sort_ascending or False
        self.list_print_limit = limit

        self.console = Console()

        logger.info(
            "CLIRenderer initialized with poster_columns=%d, sort_ascending=%s, limit=%s",
            poster_columns,
            sort_ascending,
            limit,
        )

    def render_table(self, df: pd.DataFrame, title: str):
        """Generic Render table to the Console"""
        logger.info(
            "Rendering table with title: '%s', rows: %d, columns: %d",
            title,
            len(df),
            len(df.columns),
        )
        table = Table(title=title, box=SIMPLE)
        for col in df.columns.astype(str):
            table.add_column(col)
        for row in df.astype(str).itertuples(index=False):
            table.add_row(*row)
        self.console.print(table)

    def render_dict(self, data: dict, expand: bool = True):
        """Generic Render dict to the Console"""
        logger.info("Rendering dictionary with %d key-value pairs", len(data))
        grid = Table.grid(expand=expand, padding=1)
        grid.add_column(style="bold yellow")
        grid.add_column()
        for key, value in data.items():
            grid.add_row(str(key), str(value))
        self.console.print(grid)

    def render_text(self, string: str):
        """Render text to the Console"""
        print_str = string.replace("\\", "/")
        logger.info("Rendering string: '%s'", print_str)
        self.console.print(print_str)

    def render_film_details(self, film_details: dict):
        """Render a film to the Console

        Args:
            film_details (dict): Formatted dict of film data
        """
        if "Poster" in film_details and self.poster_columns > 0:
            self.render_ascii_image_from_url(
                film_details.pop("Poster"), self.poster_columns
            )
        if film_details.get("Title") == film_details.get("Original Title"):
            film_details.pop("Original Title", None)
        self.render_dict(film_details, expand=False)

    def clear_last_rows(self, num_rows=5):
        # Use ANSI escape codes to move the cursor up and clear lines
        clear_lines = f"\033[{num_rows}F\033[J"  # Move up `num_rows` lines and clear
        sys.stdout.write(clear_lines)  # Write raw ANSI codes directly to stdout
        sys.stdout.flush()  # Ensure the output is flushed

    def render_last_dict_rows(self,metadata, num_rows=5):
        self.clear_last_rows(num_rows*2+1)
        trimmed_metadata = dict(list(metadata.items())[-num_rows:])

        self.render_dict(trimmed_metadata, expand=False)


    @staticmethod
    def render_ascii_image_from_url(img_url: str, poster_columns: int = 80):
        """Render an image to the Console in colored ASCII. Primarily used for posters.
        """
        art = AsciiArt.from_url(img_url)
        art.to_terminal(columns=poster_columns)
