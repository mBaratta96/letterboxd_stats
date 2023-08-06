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
MOVIE_OPERATIONS = {
    "Add to diary": "add_film_diary",
    "Add to watchlist": "add_watchlist",
    "Remove from watchlist": "remove_watchlist",
}
OPERATIONS_URLS = {
    "search": lambda s: f"/search/films/{s}/?adult",
    "diary": lambda s: f"/csi/film/{s}/sidebar-user-actions/?esiAllowUser=true",
    "add_watchlist": lambda s: f"/film/{s}/add-to-watchlist/",
    "remove_watchlist": lambda s: f"/film/{s}/remove-from-watchlist/",
    "film_page": lambda s: f"/film/{s}",
}

cache_path = os.path.expanduser(os.path.join(config["root_folder"], "static", "cache.db"))


class Downloader:
    def __init__(self):
        self.session = requests.Session()
        self.session.get(URL)

    def login(self):
        request_payload = {
            "username": config["Letterboxd"]["username"],
            "password": config["Letterboxd"]["password"],
            "__csrf": self.session.cookies.get("com.xk72.webparts.csrf"),
        }
        res = self.session.post(LOGIN_PAGE, data=request_payload)
        if res.json()["result"] != "success":
            raise ConnectionError("Impossible to login")

    def download_stats(self):
        res = self.session.get(DATA_PAGE)
        if res.status_code != 200 or "application/zip" not in res.headers["Content-Type"]:
            raise ConnectionError(f"Impossible to download data. Response headers:\n{res.headers}")
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

    def add_film_diary(self, title: str):
        payload = cli.add_film_questions()
        url = create_movie_url(title, "diary")
        res = self.session.get(url)
        if res.status_code != 200:
            raise ConnectionError("It's been impossible to retireve the Letterboxd page")
        movie_page = html.fromstring(res.text)
        letterboxd_film_id = movie_page.get_element_by_id("frm-sidebar-rating").get("data-film-id")
        payload["filmId"] = letterboxd_film_id
        payload["__csrf"] = self.session.cookies.get("com.xk72.webparts.csrf")
        res = self.session.post(ADD_DIARY_URL, data=payload)
        if not (res.status_code == 200 and res.json()["result"] is True):
            raise ConnectionError("Add diary request failed.")
        print("The movie was added to your diary.")

    def add_watchlist(self, title: str):
        url = create_movie_url(title, "add_watchlist")
        res = self.session.post(url, data={"__csrf": self.session.cookies.get("com.xk72.webparts.csrf")})
        if not (res.status_code == 200 and res.json()["result"] is True):
            raise ConnectionError("Add diary request failed.")
        print("Added to your watchlist.")

    def remove_watchlist(self, title: str):
        url = create_movie_url(title, "remove_watchlist")
        res = self.session.post(url, data={"__csrf": self.session.cookies.get("com.xk72.webparts.csrf")})
        if not (res.status_code == 200 and res.json()["result"] is True):
            raise ConnectionError("Add diary request failed.")
        print("Removed to your watchlist.")

    def perform_operation(self, answer: str, link: str):
        getattr(self, MOVIE_OPERATIONS[answer])(link)


def create_movie_url(title: str, operation: str):
    return URL + OPERATIONS_URLS[operation](title)


def _get_tmdb_id_from_web(link: str, is_diary: bool):
    res = requests.get(link)
    movie_page = html.fromstring(res.text)
    if is_diary:
        title_link = movie_page.xpath("//span[@class='film-title-wrapper']/a")
        if len(title_link) == 0:
            raise ValueError("No movie link found.")
        movie_link = title_link[0]
        movie_url = URL + movie_link.get("href")
        movie_page = html.fromstring(requests.get(movie_url).text)
    tmdb_link = movie_page.xpath("//a[@data-track-action='TMDb']")
    if len(tmdb_link) == 0:
        raise ValueError("No Movie link found")
    id = tmdb_link[0].get("href").split("/")[-2]
    return int(id)


def get_tmdb_id(link: str, is_diary=False):
    tmdb_id_cache = shelve.open(cache_path, writeback=False, protocol=5)
    key = link.split("/")[-1]
    if key in tmdb_id_cache:
        id = tmdb_id_cache[key]
    else:
        try:
            id = _get_tmdb_id_from_web(link, is_diary)
            tmdb_id_cache[key] = id
        except ValueError as e:
            print(e)
            id = None
    tmdb_id_cache.close()
    return id


def select_optional_operation():
    return cli.select_value(["Exit"] + list(MOVIE_OPERATIONS.keys()), "Select operation:")


def search_film(title: str, allow_selection=False):
    search_url = create_movie_url(title, "search")
    res = requests.get(search_url)
    if res.status_code != 200:
        raise ConnectionError("It's been impossible to retireve the Letterboxd page")
    search_page = html.fromstring(res.text)
    if allow_selection:
        movie_list = search_page.xpath("//div[@class='film-detail-content']")
        if len(movie_list) == 0:
            raise ValueError(f"No film found with search query {title}")
        title_years_directors_links = {}
        for movie in movie_list:
            title = movie.xpath("./h2/span/a")[0].text.rstrip()
            director = director[0].text if len(director := movie.xpath("./p/a")) > 0 else ""
            year = f"({year[0].text}) " if len(year := movie.xpath("./h2/span//small/a")) > 0 else ""
            link = movie.xpath("./h2/span/a")[0].get("href")
            title_years_directors_links[f"{title} {year}- {director}"] = link

        selected_film = cli.select_value(list(title_years_directors_links.keys()), "Select your film")
        title_url = title_years_directors_links[selected_film].split("/")[-2]
    else:
        title_url = search_page.xpath("//span[@class='film-title-wrapper']/a")[0].get("href").split("/")[-2]
    return title_url
