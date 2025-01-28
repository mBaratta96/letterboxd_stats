import argparse
import sys


def create_parser():
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


def parse_args():
    parser = create_parser()
    args = parser.parse_args()

    # Check if no arguments were passed
    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(0)

    return args

