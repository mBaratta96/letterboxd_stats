import sys
from letterboxd_stats import args, config
from letterboxd_stats.letterboxd_connector import LBConnector
from letterboxd_stats.cli import user_search_person, user_search_film, render_exported_lb_data

connector = LBConnector(config["Letterboxd"]["username"], config["Letterboxd"]["password"])

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
            try_command(user_search_person, (connector, args.search,))
        if args.search_film:
            try_command(user_search_film, (connector, args.search_film,))
        if args.watchlist:
            try_command(render_exported_lb_data, ("Watchlist", args.limit, config["CLI"]["ascending"]))
        if args.diary:
            try_command(render_exported_lb_data, ("Diary", args.limit, config["CLI"]["ascending"]))
        if args.ratings:
            try_command(render_exported_lb_data, ("Ratings", args.limit, config["CLI"]["ascending"]))
        if args.lists:
            try_command(render_exported_lb_data, ("Lists", args.limit, config["CLI"]["ascending"]))
        
    except KeyboardInterrupt:
        print('\nProgram interrupted. Exiting.')
        sys.exit(0)

if __name__ == "__main__":
    main()