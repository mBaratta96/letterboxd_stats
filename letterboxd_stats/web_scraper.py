import os
from zipfile import ZipFile
from letterboxd_stats import config
from letterboxd_stats import cli
import requests
from lxml import html
import shelve

URL = "https://letterboxd.com"
LOGIN_PAGE = URL + "/user/login.do"
DATA_PAGE = URL + "/data/export"
ADD_DIARY_URL = URL + "/s/save-diary-entry"
FILM_OPERATIONS = {
    "Add to diary": "add_diary_entry",
    "Add to watchlist": "add_watchlist_entry",
    "Remove from watchlist": "remove_watchlist_entry",
}
OPERATIONS_URLS = {
    "search": lambda s: f"/s/search/{s}/",
    "diary": lambda s: f"/csi/film/{s}/sidebar-user-actions/?esiAllowUser=true",
    "add_watchlist": lambda s: f"/film/{s}/add-to-watchlist/",
    "remove_watchlist": lambda s: f"/film/{s}/remove-from-watchlist/",
    "film_page": lambda s: f"/film/{s}",
}

cache_path = os.path.expanduser(os.path.join(config["root_folder"], "static", "cache.db"))


class Connector:
    def __init__(self):
        self.session = requests.Session()
        # get home page to set cookies in the session.
        self.session.get(URL)

    def login(self):
        request_payload = {
            "username": config["Letterboxd"]["username"],
            "password": config["Letterboxd"]["password"],
            "__csrf": self.session.cookies.get("com.xk72.webparts.csrf"),
        }
        res = self.session.post(LOGIN_PAGE, data=request_payload)
        if res.json()["result"] != "success":
            raise ConnectionError("Failed to login")

    def download_stats(self):
        """Download and extract data of the import/export section.
        .CSV file will be extracted in the folder specified in the config file."""

        res = self.session.get(DATA_PAGE)
        if res.status_code != 200 or "application/zip" not in res.headers["Content-Type"]:
            raise ConnectionError(f"Failed to download data. Response headers:\n{res.headers}")
        print("Data download successful.")
        filename = res.headers["content-disposition"].split()[-1].split("=")[-1]
        path = os.path.expanduser(os.path.join(config["root_folder"], "static"))
        if not os.path.exists(path):
            os.makedirs(path)
        archive = os.path.join(path, filename)
        with open(archive, "wb") as f:
            f.write(res.content)
        with ZipFile(archive, "r") as zip:
            zip.extractall(path)
        os.remove(archive)

    def add_diary_entry(self, title: str):
        payload = cli.add_film_questions()
        url = create_lb_url(title, "diary")
        res = self.session.get(url)
        if res.status_code != 200:
            raise ConnectionError("Failed to retrieve the Letterboxd page")
        film_page = html.fromstring(res.text)
        # Not the TMDB id, but the Letterboxd ID to use to add the film to diary.
        # Reference: https://letterboxd.com/film/seven-samurai/
        letterboxd_film_id = film_page.get_element_by_id("frm-sidebar-rating").get("data-rateable-uid").split(":", 1)[1]
        payload["filmId"] = letterboxd_film_id
        payload["__csrf"] = self.session.cookies.get("com.xk72.webparts.csrf")
        res = self.session.post(ADD_DIARY_URL, data=payload)
        if not (res.status_code == 200 and res.json()["result"] is True):
            raise ConnectionError(f"Failed to add to diary.")
        print(f"{title} was added to your diary.")

    def add_watchlist_entry(self, title: str):
        url = create_lb_url(title, "add_watchlist")
        res = self.session.post(url, data={"__csrf": self.session.cookies.get("com.xk72.webparts.csrf")})
        if not (res.status_code == 200 and res.json()["result"] is True):
            raise ConnectionError("Failed to add to watchlist.")
        print(f"{title} was added to your watchlist.")

    def remove_watchlist_entry(self, title: str):
        url = create_lb_url(title, "remove_watchlist")
        res = self.session.post(url, data={"__csrf": self.session.cookies.get("com.xk72.webparts.csrf")})
        if not (res.status_code == 200 and res.json()["result"] is True):
            raise ConnectionError("Failed to remove from watchlist.")
        print(f"{title} was removed from your watchlist.")

    def perform_operation(self, operation: str, link: str):
        """Depending on what the user has chosen, add to diary, add/remove watchlist."""

        getattr(self, FILM_OPERATIONS[operation])(link)


def create_lb_url(title: str, operation: str) -> str:
    return URL + OPERATIONS_URLS[operation](title)


def _get_tmdb_id_from_web(link: str, is_diary: bool) -> int:
    """Scraping the TMDB link from a Letterboxd film page.
    Inspect this HTML for reference: https://letterboxd.com/film/seven-samurai/
    """

    res = requests.get(link)
    film_page = html.fromstring(res.text)
    # Diary links sends you to a different page with no link to TMDB. Redirect to the actual page.
    if is_diary:
        title_link = film_page.xpath("//span[@class='film-title-wrapper']/a")
        if len(title_link) == 0:
            raise ValueError("No link found for film.")
        film_link = title_link[0]
        film_url = URL + film_link.get("href")
        film_page = html.fromstring(requests.get(film_url).text)
    tmdb_link = film_page.xpath("//a[@data-track-action='TMDb']")
    if len(tmdb_link) == 0:
        raise ValueError("No link found for film")
    id = tmdb_link[0].get("href").split("/")[-2]
    return int(id)


def get_tmdb_id(link: str, is_diary=False) -> int | None:
    """Find the TMDB id from a letterboxd page.

    A link to a Letterboxd film usually starts with either https://letterboxd.com/
    or https://boxd.it/ (usually all .csv files have this prefix). We structure the cache dict accordingly.
    The cache is meant to avoid bottleneck of constantly retrieving the Id from an HTML page.
    """

    tmdb_id_cache = shelve.open(cache_path, writeback=False, protocol=5)
    prefix, key = link.rsplit("/", 1)
    if prefix in tmdb_id_cache and key in tmdb_id_cache[prefix]:
        id = tmdb_id_cache[prefix][key]
    else:
        try:
            id = _get_tmdb_id_from_web(link, is_diary)
            prefix_dict = tmdb_id_cache.get(prefix) or {}
            prefix_dict[key] = id
            tmdb_id_cache[prefix] = prefix_dict
        except ValueError as e:
            print(e)
            id = None
    tmdb_id_cache.close()
    return id


def select_optional_operation() -> str:
    return cli.select_value(["Exit"] + list(FILM_OPERATIONS.keys()), "Select operation:")


def get_lb_title(title: str, allow_selection=False) -> str:
    """Search a film and get its Letterboxd link.
    For reference: https://letterboxd.com/search/seven+samurai/?adult
    """

    search_url = create_lb_url(title, "search")
    print(f"Searching for '{title}'")
    res = requests.get(search_url)
    if res.status_code != 200:
        raise ConnectionError("Failed to retrieve the Letterboxd page.")
    search_page = html.fromstring(res.text)
    # If we want to select films from the search page, get more data to print the selection prompt.
    if allow_selection:
        film_list = search_page.xpath("//div[@class='film-detail-content']")
        if len(film_list) == 0:
            raise ValueError(f"No results found for your Letterboxd film search.")
        title_years_directors_links = {}
        for film in film_list:
            title = film.xpath("./h2/span/a")[0].text.rstrip()
            director = director[0].text if len(director := film.xpath("./p/a")) > 0 else ""
            year = f"({year[0].text}) " if len(year := film.xpath("./h2/span//small/a")) > 0 else ""
            link = film.xpath("./h2/span/a")[0].get("href")
            title_years_directors_links[f"{title} {year}- {director}"] = link
        selected_film = cli.select_value(list(title_years_directors_links.keys()), "Select your film")
        title_url = title_years_directors_links[selected_film].split("/")[-2]
    else:
        title_url = search_page.xpath("//span[@class='film-title-wrapper']/a")[0].get("href").split("/")[-2]
    return title_url
