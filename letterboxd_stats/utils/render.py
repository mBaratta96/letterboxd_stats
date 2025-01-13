import pandas as pd
import tempfile
import img2unicode
import requests
from io import BytesIO

from rich.console import Console
from rich.table import Table
from rich.box import SIMPLE
from ascii_magic import AsciiArt


class CLIRenderer:    
    def __init__(self, limit:int = None, poster_columns: int = 80, sort_ascending:bool = False):
        """
        Initialize the CLI Renderer.
        
        Parameters:
        - limit: Optional limit for rows to display in tables.
        - poster_columns: Width of ASCII poster rendering.
        - sort_ascending: Sorting order for rendered data.
        """
        if sort_ascending is None:
            sort_ascending = False
        self.poster_columns = poster_columns
        self.sort_ascending = sort_ascending
        self.list_print_limit = limit

        self.console = Console()

    def render_table(self, df: pd.DataFrame, title: str):
        """
        Render a DataFrame as a styled table in the console.
        
        Parameters:
        - df: DataFrame to render.
        - title: Title for the table.
        """
        table = Table(title=title, box=SIMPLE)
        for col in df.columns.astype(str):
            table.add_column(col)
        for row in df.astype(str).itertuples(index=False):
            table.add_row(*row)
        self.console.print(table)

    def render_dict(self, data: dict, expand: bool = True):
        """
        Render a dictionary as a styled grid in the console.
        
        Parameters:
        - data: Dictionary to render.
        - expand: Whether the grid should expand to fit content.
        """
        grid = Table.grid(expand=expand, padding=1)
        grid.add_column(style="bold yellow")
        grid.add_column()
        for key, value in data.items():
            grid.add_row(str(key), str(value))
        self.console.print(grid)

    def render_film_details(self, film_details: dict):
        """
        Render detailed information about a film.
        
        Parameters:
        - film_details: Dictionary containing film details, including optional "Poster".
        """
        poster_columns = self.poster_columns
        if "Poster" in film_details and self.poster_columns > 0:
            self.render_ascii_poster(film_details.pop("Poster"), self.poster_columns)
        if film_details.get("Title") == film_details.get("Original Title"):
            film_details.pop("Original Title", None)
        self.render_dict(film_details, expand=False)

    @staticmethod
    def render_ascii_poster(poster_url: str, poster_columns: int = 80):
        """
        Render a poster as ASCII art in the console.
        
        Parameters:
        - poster_url: URL of the poster image.
        - poster_columns: Width of the ASCII art in characters.
        """
        art = AsciiArt.from_url(poster_url)
        art.to_terminal(columns=poster_columns)
        
    @staticmethod
    def render_unicode_poster(poster_url: str, poster_columns: int = 80, max_height: int = 60, block_mode: bool = True):
        """
        Render a poster as Unicode art in the console.

        Parameters:
        - poster_url: URL of the poster image.
        - poster_columns: Width of the Unicode art in characters.
        - max_height: Maximum height of the Unicode art in characters.
        - block_mode: Whether to use Unicode block elements for rendering.
        """
        # Fetch the poster image from the URL
        response = requests.get(poster_url)
        if response.status_code != 200:
            raise ValueError(f"Failed to fetch image from URL: {poster_url}")
        
        # Save the image to a temporary file
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as temp_file:
            temp_file.write(response.content)
            temp_file_path = temp_file.name
        
        # Load the image into img2unicode
        image_data = BytesIO(response.content)
        optimizer = img2unicode.FastGenericDualOptimizer("block") if block_mode else img2unicode.FastGammaOptimizer("no_block")
        renderer = img2unicode.Renderer(default_optimizer=optimizer, max_h=max_height, max_w=poster_columns)
        
        # Render the poster directly to the terminal
        renderer.render_terminal(temp_file_path, "test.txt")