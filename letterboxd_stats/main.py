import os
import sys
import argparse
from .core.config_loader import load_config, default_config_dir
from .cli.letterboxd_cli import LetterboxdCLI
from .cli.export_viewer import ExportViewer

def create_parser():
    parser = argparse.ArgumentParser(
        prog="Letterboxd Stats",
        description="CLI tool to view and interact with Letterboxd",
    )
    parser.add_argument("-s", "--search", help="Search for a person")
    parser.add_argument("-S", "--search-film", help="Search for a film")
    parser.add_argument("-d", "--download", help="Download letterboxd data", action="store_true")
    parser.add_argument("-W", "--watchlist", help="View downloaded Letterboxd watchlist", action="store_true")
    parser.add_argument("-D", "--diary", help="View downloaded Letterboxd diary entries", action="store_true")
    parser.add_argument("-R", "--ratings", help="View downloaded Letterboxd ratings", action="store_true")
    parser.add_argument("-L", "--lists", help="View downloaded Letterboxd lists", action="store_true")
    parser.add_argument("-l", "--limit", help="Limit the number of items of your wishlist/diary", type=int)
    parser.add_argument("-c", "--config_folder", help="Specify the folder of your config.toml file")
    return parser

def parse_args():
    parser = create_parser()
    args = parser.parse_args()

    # Check if no arguments were passed
    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(0)
        
    return args

def try_command(command, args):
    try:
        command(*args)
    except Exception as e:
        print(e)

def main():
    args = parse_args()

    # Load config
    folder = args.config_folder or default_config_dir
    
    config_path = os.path.abspath(os.path.join(folder, "config.toml"))
    if not os.path.exists(config_path):
        raise FileNotFoundError(
            f"Found no config file in {config_path}. "
            + "Please, add a config.toml in that folder or specify a custom one with the -c command."
        )

    config = load_config(config_path)    
    cli = LetterboxdCLI(config, args.limit)
    path = os.path.expanduser(os.path.join(config["root_folder"], "static"))

    try:
        if args.download:
            try_command(cli.lb_connector.download_stats, (path,))
        if args.search:
            try_command(cli.search_person, (args.search,))
        if args.search_film:
            try_command(cli.search_film, (args.search_film,))
        if args.watchlist:
            try_command(cli.view_exported_lb_data, ("Watchlist",))
        if args.diary:
            try_command(cli.view_exported_lb_data, ("Diary",))
        if args.ratings:
            try_command(cli.view_exported_lb_data, ("Ratings",))
        if args.lists:
            try_command(cli.view_exported_lb_data, ("Lists",))
        
    except KeyboardInterrupt:
        print('\nProgram interrupted. Exiting.')
        sys.exit(0)

if __name__ == "__main__":
    main()