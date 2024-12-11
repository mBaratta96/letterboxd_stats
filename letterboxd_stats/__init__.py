import tomli
import os
import platformdirs
import argparse
import getpass
import sys

default_folder = platformdirs.user_config_dir("letterboxd_stats", getpass.getuser())

CONFIG_DEFAULTS = {
    "CLI": {
        "poster_columns": 180,
        "ascending": False,
    },
    "TMDB": {
        "get_list_runtimes": False,
    },
}

def load_config(file_path, defaults):
    # Load the TOML file if it exists
    if os.path.exists(file_path):
        with open(file_path, "rb") as f:
            user_config = tomli.load(f)
    else:
        user_config = {}

    # Merge user_config with defaults (user_config takes precedence)
    return merge_dicts(defaults, user_config)

def merge_dicts(defaults, overrides):
    """Recursively merge two dictionaries."""
    merged = defaults.copy()
    for key, value in overrides.items():
        if isinstance(value, dict) and key in merged and isinstance(merged[key], dict):
            merged[key] = merge_dicts(merged[key], value)
        else:
            merged[key] = value
    return merged

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

if len(sys.argv)==1:
    parser.print_help(sys.stderr)
    sys.exit(1)

args = parser.parse_args()

folder = args.config_folder or default_folder
config_path = os.path.abspath(os.path.join(folder, "config.toml"))
if not os.path.exists(config_path):
    raise FileNotFoundError(
        f"Found no configuration file in {config_path}. "
        + "Please, add a config.toml in that folder or specify a custom one with the -c command."
    )
    
config = load_config(config_path, CONFIG_DEFAULTS)

