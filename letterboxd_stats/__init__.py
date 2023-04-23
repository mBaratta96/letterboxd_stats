import tomli
import os
import platformdirs
import argparse

default_folder = platformdirs.user_config_dir("letterboxd_stats", "mBaratta96")

parser = argparse.ArgumentParser(
    prog="Letterboxd Stats",
    description="CLI tool to display Letterboxd statistics",
)
parser.add_argument("-s", "--search", help="Search for a director")
parser.add_argument("-S", "--search-film", help="Search for a film.")
parser.add_argument(
    "-d",
    "--download",
    help="Download letterboxd data from your account",
    action="store_true",
)
parser.add_argument("-W", "--watchlist", help="show watchlist", action="store_true")
parser.add_argument("-D", "--diary", help="show diary", action="store_true")
parser.add_argument("-R", "--ratings", help="show ratings", action="store_true")
parser.add_argument("-L", "--lists", help="show lists", action="store_true")
parser.add_argument("-l", "--limit", help="limit the number of items of your wishlist/diary", type=int)
parser.add_argument("-c", "--config_folder", help="Specifiy the folder of your config.toml file")


args = parser.parse_args()

folder = args.config_folder or default_folder
path = os.path.abspath(os.path.join(folder, "config.toml"))
if not os.path.exists(path):
    raise FileNotFoundError(
        f"Found no configuration file in {path}. "
        + "Please, add a config.toml in that folder or specify a custom one with the -c command."
    )
with open(path, "rb") as f:
    config = tomli.load(f)
