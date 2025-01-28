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

import logging.config
import os
import sys

from .cli.argument_parser import parse_args
from .cli.commands import execute_commands
from .cli.config_loader import default_config_dir, load_config
from .cli.letterboxd_cli import LetterboxdCLI

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
            "filename": "letterboxd_stats.log",
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

def main():
    logger.info("Starting Letterboxd Stats CLI.")

    args = parse_args()

    # Load configuration
    folder = args.config_folder or default_config_dir
    config_path = os.path.abspath(os.path.join(folder, "config.toml"))
    config = load_config(config_path)

    # Initialize CLI
    cli = LetterboxdCLI(
        tmdb_api_key=config["TMDB"]["api_key"],
        lb_username=config["Letterboxd"].get("username"),
        lb_password=config["Letterboxd"].get("password"),
        root_folder=config.get("root_folder"),
        cli_poster_columns=config["CLI"].get("poster_columns"),
        cli_ascending=config["CLI"].get("ascending"),
        tmdb_get_list_runtimes=config["TMDB"].get("get_list_runtimes"),
        limit=args.limit,
    )

    try:
        execute_commands(cli, args)
    except KeyboardInterrupt:
        logger.info("\nProgram interrupted. Exiting.")
        sys.exit(0)

if __name__ == "__main__":
    main()
