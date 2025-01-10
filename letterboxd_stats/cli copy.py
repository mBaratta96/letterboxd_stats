# Render to CLI
################

from rich.console import Console
from rich.table import Table
from rich.box import SIMPLE
from ascii_magic import AsciiArt  # Assuming AsciiArt is imported

class CLIRenderer:
    def __init__(self, config):
        self.config = config
        self.console = Console()

    def render_table(self, df: pd.DataFrame, title: str):
        table = Table(title=title, box=SIMPLE)
        for col in df.columns.astype(str):
            table.add_column(col)
        for row in df.astype(str).itertuples(index=False):
            table.add_row(*row)
        self.console.print(table)

    def render_dict(self, data: dict, expand: bool = True):
        grid = Table.grid(expand=expand, padding=1)
        grid.add_column(style="bold yellow")
        grid.add_column()
        for key, value in data.items():
            grid.add_row(str(key), str(value))
        self.console.print(grid)

    def render_film_details(self, film_details: dict):
        poster_columns = self.config["CLI"].get("poster_columns", 0)
        if "Poster URL" in film_details and poster_columns > 0:
            self.render_ascii_poster(film_details.pop("Poster URL"))
        if film_details.get("Title") == film_details.get("Original Title"):
            film_details.pop("Original Title", None)
        self.render_dict(film_details, expand=False)

    def render_ascii_poster(self, poster_url: str):
        columns = int(self.config["CLI"].get("poster_columns", 80))
        art = AsciiArt.from_url(poster_url)
        art.to_terminal(columns=columns)

    def render_exported_lb_data(self, export_type: str, limit: int = None, sort_ascending: bool = False):
        """Load and display CLI data from exported .csv files."""
        path = eh.generate_export_csv_path(export_type)
        eh.check_path_exists(path)

        if export_type == "Lists":
            letterboxd_url = user_view_lb_export_lists_directory(path, limit, sort_ascending)
        else:
            letterboxd_url = user_view_lb_export_csv(export_type, path, limit, sort_ascending)

        if letterboxd_url:
            tmdb_id = lbcon.get_tmdb_id_from_lb(letterboxd_url, export_type == "diary")
            if tmdb_id:
                film_details = tmdbcon.get_all_tmdb_movie_details(tmdb_id, letterboxd_url)
                self.render_film_details(film_details)
