"""
Letterboxd Stats CLI Entry Point
================================

This script serves as the entry point for the Letterboxd Stats CLI application.
It allows users to interact with their Letterboxd data, perform searches, update
metadata, and explore export files, all from the command line. The script uses
an `argparse` interface to provide a variety of commands and options.

Features:
---------
1. **Configuration Support**:
   - Loads settings from a `config.toml` file or environment variables.
   - Supports specifying a custom configuration folder via command-line arguments.

2. **Letterboxd Data Management**:
   - Download Letterboxd export data for offline analysis.
   - View and interact with Watchlist, Diary, Ratings, and Lists export files.

3. **Search Functionality**:
   - Search for films and people using Letterboxd and TMDb integrations.

4. **Metadata Interaction**:
   - Update metadata such as watched status, ratings, and diary entries directly from the CLI.

"""

import argparse
import logging
import logging.config
import os
import sys

from .cli.letterboxd_cli import LetterboxdCLI
from .utils.config_loader import default_config_dir, load_config

DEBUG_LOGGING = True
LOGGING_LEVEL = "DEBUG" if DEBUG_LOGGING else "INFO"
LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "detailed": {
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        },
        "simple": {
            "format": "%(levelname)s - %(message)s",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "level": "WARNING",
            "formatter": "simple",
        },
        "file": {
            "class": "logging.FileHandler",
            "filename": "app.log",
            "level": LOGGING_LEVEL,
            "formatter": "detailed",
        },
    },
    "loggers": {
        "": {  # Root logger
            "level": LOGGING_LEVEL,
            "handlers": ["console", "file"],
        },
    },
}

logging.config.dictConfig(LOGGING_CONFIG)

logger = logging.getLogger(__name__)


def _create_parser():
    parser = argparse.ArgumentParser(
        prog="Letterboxd Stats",
        description="CLI tool to view and interact with Letterboxd",
    )
    parser.add_argument("-s", "--search-person", help="Search for a person")
    parser.add_argument("-S", "--search-film", help="Search for a film")
    parser.add_argument(
        "-d", "--download", help="Download letterboxd data", action="store_true"
    )
    parser.add_argument(
        "-W",
        "--watchlist",
        help="View downloaded Letterboxd watchlist",
        action="store_true",
    )
    parser.add_argument(
        "-D",
        "--diary",
        help="View downloaded Letterboxd diary entries",
        action="store_true",
    )
    parser.add_argument(
        "-R",
        "--ratings",
        help="View downloaded Letterboxd ratings",
        action="store_true",
    )
    parser.add_argument(
        "-L", "--lists", help="View downloaded Letterboxd lists", action="store_true"
    )
    parser.add_argument(
        "-l",
        "--limit",
        help="Limit the number of items of your wishlist/diary",
        type=int,
    )
    parser.add_argument(
        "-c", "--config_folder", help="Specify the folder of your config.toml file"
    )
    return parser


def _parse_args():
    parser = _create_parser()
    args = parser.parse_args()

    # Check if no arguments were passed
    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(0)

    return args


def _try_command(command, args):
    try:
        command(*args)
    except Exception as e:
        logger.error(e)
        raise


def main():
    """
    Main entry point for the Letterboxd Stats CLI application.

    This function initializes the logging system, parses command-line arguments,
    loads the configuration, and executes the requested commands. The commands
    allow users to interact with Letterboxd data such as downloading export
    files, searching for films or people, and viewing Watchlist, Diary, Ratings,
    or Lists.

    Key Responsibilities:
    ----------------------
    1. **Argument Parsing**:
       - Handles user input via command-line arguments using argparse.
       - Prints help information if no arguments are provided.

    2. **Configuration Loading**:
       - Loads settings from a `config.toml` file or an environment variable.
       - Validates the presence of critical keys like the TMDB API key.

    3. **Command Execution**:
       - Downloads Letterboxd data, performs searches, or views exports.
       - Gracefully handles errors during command execution with proper logging.

    4. **Graceful Exit**:
       - Handles `KeyboardInterrupt` (Ctrl+C) to ensure a clean exit.

    Raises:
    -------
    - SystemExit:
        If required arguments are missing or if the program is interrupted.
    """

    logger.info("Letterboxd Stats started.")

    # Get CLI arguments
    args = _parse_args()

    # Load configuration file
    folder = args.config_folder or default_config_dir
    config_path = os.path.abspath(os.path.join(folder, "config.toml"))
    config = load_config(config_path)

    tmdb_api_key = config.get("TMDB", {}).get("api_key")

    if tmdb_api_key is None:
        logger.error(
            "TMDB API key is required, but was not found in configuration or environment."
        )
        return

    lb_cli_kwargs = {
        "tmdb_api_key": tmdb_api_key,
        "lb_username": config.get("Letterboxd", {}).get("username"),
        "lb_password": config.get("Letterboxd", {}).get("password"),
        "root_folder": config.get("root_folder"),
        "cli_poster_columns": config.get("CLI", {}).get("poster_columns"),
        "cli_ascending": config.get("CLI", {}).get("ascending"),
        "tmdb_get_list_runtimes": config.get("TMDB", {}).get("get_list_runtimes"),
        "limit": args.limit,
    }

    filtered_kwargs = {k: v for k, v in lb_cli_kwargs.items() if v is not None}

    cli = LetterboxdCLI(**filtered_kwargs)

    try:
        if args.download:
            _try_command(cli.download_stats, ())
        if args.search_person:
            _try_command(cli.search_person, (args.search_person,))
        if args.search_film:
            _try_command(cli.search_film, (args.search_film,))
        if args.watchlist:
            _try_command(cli.view_exported_lb_data, ("Watchlist",))
        if args.diary:
            _try_command(cli.view_exported_lb_data, ("Diary",))
        if args.ratings:
            _try_command(cli.view_exported_lb_data, ("Ratings",))
        if args.lists:
            _try_command(cli.view_exported_lb_data, ("Lists",))

    except KeyboardInterrupt:
        logger.info("\nProgram interrupted. Exiting.")
        sys.exit(0)


if __name__ == "__main__":
    main()
