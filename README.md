# Letterboxd Stats

Get information about your Letterboxd activity.

Search for actors/directors, analyze your diary/watchlist/rating, check which film you have seen for a particular person. All in your terminal.

## Requirements

- Python >= 3.8
- A [TMDb API key](https://www.themoviedb.org/documentation/api): to retrieve all the general information for movies/people
- A Letterboxd account: to export your Letterboxd activity through webscraping.

## Installation
Just run:
```shell
pip3 install letterboxd_stats
```

## Configuration
It is required to create a `config.toml`. You can create it in the default config folder (for example, `.config/letterboxd_stats` in Linux) or specify your custom folder with the `-c` command. For each platform, default config folder follows the structure of the [platformdirs](https://github.com/platformdirs/platformdirs) package.

```toml
# Where you want the .csv file of your Letterboxd activity to be saved.
root_folder = "~/Documents/letterboxd_stats/"

# The size of the ASCII art poster printed in your terminal when you check the details of a movie. Set to 0 to disable 
poster_columns = 180

[TMDB]
api_key = "your-TMDb-API-KEY"

[Letterboxd]
username = "your-username"
password = "your-password"
```

## Options
```shell
options:
  -h, --help            show this help message and exit
  -s SEARCH, --search SEARCH
                        Search for a actor/director
  -d, --download        Download letterboxd data from your account
  -w, --wishlist        show wishlist
  -l LIMIT, --limit LIMIT
                        limit the number of items of your wishlist/diary
  -r, --random          shuffle wishlist
  -D, --diary           show diary
  -R, --ratings         show ratings
  -c CONFIG_FOLDER, --config_folder CONFIG_FOLDER
                        Specifiy the folder of your config.toml file
```

## To do
_Note: this is something I do during my free time. Therefore, I can't promise consistent support for this project._

- [ ] Use web-scraping to add film to diary/wishlist

- [ ] Check followers' activity. 
