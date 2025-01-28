# cli/commands.py
import logging

from .letterboxd_cli import LetterboxdCLI

logger = logging.getLogger(__name__)

def execute_commands(cli: LetterboxdCLI, args):
    try:
        if args.download:
            cli.download_stats()
        if args.search_person:
            cli.search_person(args.search_person)
        if args.search_film:
            cli.search_film(args.search_film)
        if args.watchlist:
            cli.view_exported_lb_data("Watchlist")
        if args.diary:
            cli.view_exported_lb_data("Diary")
        if args.ratings:
            cli.view_exported_lb_data("Ratings")
        if args.lists:
            cli.view_exported_lb_data("Lists")
    except Exception as e:
        logger.error("An error occurred: %s", e)
        raise
