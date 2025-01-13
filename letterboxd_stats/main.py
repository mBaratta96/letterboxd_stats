import os
import sys
import argparse
from .utils.config_loader import load_config, default_config_dir
from .cli.letterboxd_cli import LetterboxdCLI

def _create_parser():
    parser = argparse.ArgumentParser(
        prog="Letterboxd Stats",
        description="CLI tool to view and interact with Letterboxd",
    )
    parser.add_argument("-s", "--search-person", help="Search for a person")
    parser.add_argument("-S", "--search-film", help="Search for a film")
    parser.add_argument("-d", "--download", help="Download letterboxd data", action="store_true")
    parser.add_argument("-W", "--watchlist", help="View downloaded Letterboxd watchlist", action="store_true")
    parser.add_argument("-D", "--diary", help="View downloaded Letterboxd diary entries", action="store_true")
    parser.add_argument("-R", "--ratings", help="View downloaded Letterboxd ratings", action="store_true")
    parser.add_argument("-L", "--lists", help="View downloaded Letterboxd lists", action="store_true")
    parser.add_argument("-l", "--limit", help="Limit the number of items of your wishlist/diary", type=int)
    parser.add_argument("-c", "--config_folder", help="Specify the folder of your config.toml file")
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
        print(e)

def main():
    args = _parse_args()

    # Load config
    folder = args.config_folder or default_config_dir
    
    config_path = os.path.abspath(os.path.join(folder, "config.toml"))


    config = load_config(config_path)
    
    try:
        tmdb_api_key = config["TMDB"]["api_key"]
    except KeyError:
        raise KeyError("The 'TMDB API key' is required but was not provided in the configuration or environment.")
    
    cli = LetterboxdCLI(
        tmdb_api_key,
        config["Letterboxd"]["username"], 
        config["Letterboxd"]["password"], 
        config["root_folder"], 
        config["CLI"]["poster_columns"], 
        config["CLI"]["ascending"], 
        config["TMDB"]["get_list_runtimes"], 
        args.limit
        )

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
        print('\nProgram interrupted. Exiting.')
        sys.exit(0)

if __name__ == "__main__":
    main()