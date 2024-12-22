import sys
from letterboxd_stats import args, config
from letterboxd_stats.web_scraper import Connector
from letterboxd_stats.cli import search_person, search_film, display_data

connector = Connector(config["Letterboxd"]["username"], config["Letterboxd"]["password"])

def try_command(command, args):
    try:
        command(*args)
    except Exception as e:
        print(e)

def main():
    try:
        if args.download:
            try_command(connector.download_stats, ())
        if args.search:
            try_command(search_person, (args.search,))
        if args.search_film:
            try_command(search_film, (connector, args.search_film,))
        if args.watchlist:
            try_command(display_data, (args.limit, config["CLI"]["ascending"], "Watchlist"))
        if args.diary:
            try_command(display_data, (args.limit, config["CLI"]["ascending"], "Diary"))
        if args.ratings:
            try_command(display_data, (args.limit, config["CLI"]["ascending"], "Ratings"))
        if args.lists:
            try_command(display_data, (args.limit, config["CLI"]["ascending"], "Lists"))
        
    except KeyboardInterrupt:
        print('\nProgram interrupted. Exiting.')
        sys.exit(0)

if __name__ == "__main__":
    main()