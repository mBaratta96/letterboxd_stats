import os
import shelve
import requests
from lxml import html
from zipfile import ZipFile
from letterboxd_stats import config

LB_BASE_URL = "https://letterboxd.com"
LOGIN_URL = LB_BASE_URL + "/user/login.do"
DATA_EXPORT_URL = LB_BASE_URL + "/data/export"
METADATA_URL = LB_BASE_URL +"/ajax/letterboxd-metadata/"
ADD_DIARY_URL = LB_BASE_URL + "/s/save-diary-entry"

FILM_OPERATIONS = {
    "Rate film": "rate_film",
    "Add to diary": "set_film_liked_status",
    "Add to watchlist": "add_watchlist_entry",
    "Mark film as watched": "set_film_watched_status",
    "Add to Liked films": "set_film_liked_status",
    "Remove from watchlist": "remove_watchlist_entry",
    "Un-mark film as watched": "set_film_unwatched",
    "Remove from liked films": "set_film_not_liked",
}
LB_TITLE_URL_TEMPLATES = {
    "search": lambda s: f"/s/search/{s}/",
    "diary": lambda s: f"/csi/film/{s}/sidebar-user-actions/?esiAllowUser=true",
    "add_watchlist": lambda s: f"/film/{s}/add-to-watchlist/",
    "remove_watchlist": lambda s: f"/film/{s}/remove-from-watchlist/",
    "film_page": lambda s: f"/film/{s}",
}
LB_ID_URL_TEMPLATES = {
    "watch": lambda s: f"/s/film:{s}/watch/",
    "like": lambda s: f"/s/film:{s}/like/",
    "rate": lambda s: f"/s/film:{s}/rate/",
}

cache_path = os.path.expanduser(os.path.join(config["root_folder"], "static", "cache.db"))

class LBConnector:
    
    # Constructors
    ##########################
    
    def __init__(self):     
        self.__username = config["Letterboxd"]["username"]  # Private attribute
        self.__password = config["Letterboxd"]["password"]  # Private attribute
        self.session = requests.Session()
        self.logged_in = False
        self.session.get(LB_BASE_URL)
        self.login()  # Automatically login during initialization
        
    def __init__(self, username: str, password: str):     
        self.__username = username  # Private attribute
        self.__password = password  # Private attribute
        self.session = requests.Session()
        self.logged_in = False
        self.session.get(LB_BASE_URL)
        self.login()  # Automatically login during initialization

    # Initialization
    ##########################
    
    def login(self):
        request_payload = {
            "username": self.__username,
            "password": self.__password,
            "__csrf": self.session.cookies.get("com.xk72.webparts.csrf"),
        }
        res = self.session.post(LOGIN_URL, data=request_payload)
        if res.json()["result"] != "success":
            raise ConnectionError("Failed to login")
        self.logged_in = True
        
    # Download
    ##########################

    def download_stats(self):
        """Download and extract data of the import/export section.
        .CSV file will be extracted in the folder specified in the config file."""

        res = self.session.get(DATA_EXPORT_URL)
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
        
        return res.status_code

        
    # Web Scraping + API Calls
    ###########################
    
    def search_lb_by_title(self, title: str):
        """Search a film and return the results.
        For reference: https://letterboxd.com/search/seven+samurai/?adult
        """
        search_url = create_lb_operation_url_with_title(title, "search")
        print(f"Searching for '{title}'")
        res = requests.get(search_url)
        if res.status_code != 200:
            raise ConnectionError("Failed to retrieve the Letterboxd page.")
        search_page = html.fromstring(res.text)
        # If we want to select films from the search page, get more data to print the selection prompt.
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
            
        return title_years_directors_links

    
    def get_lb_film_id(self, lb_title: str):
        """
        Retrieve the Letterboxd film ID for a given film title.

        Args:
            title (str): The internal, unique Letterboxd title of the film.

        Returns:
            str: The Letterboxd film ID.

        Raises:
            ConnectionError: If the page cannot be retrieved.
        """
        url = create_lb_operation_url_with_title(lb_title, "diary")
        res = self.session.get(url)
        if res.status_code != 200:
            raise ConnectionError("Failed to retrieve the Letterboxd page")
        film_page = html.fromstring(res.text)
        # Not the TMDB id, but the Letterboxd ID to use to add the film to diary.
        # Reference: https://letterboxd.com/film/seven-samurai/
        letterboxd_film_id = film_page.get_element_by_id("frm-sidebar-rating").get("data-rateable-uid").split(":", 1)[1]
        return letterboxd_film_id

    
    def fetch_lb_film_user_metadata(self, lb_title: str) -> bool:
        """
        Fetch metadata about a film from Letterboxd for the current user.

        Args:
            lb_title (str): The title of the film.

        Returns:
            dict: Metadata containing 'Watched', 'Liked', 'Watchlisted', and 'Rating' statuses.

        Raises:
            ValueError: If the required user cookie is missing.
            ConnectionError: If the metadata API call fails.
        """
        film_id = self.get_lb_film_id(lb_title)

        film_str = f"film:{film_id}"
        payload= { 
            "posters": film_str,  # posters retrieves "watchlist" status
            "likeables": film_str,
            "watchables": film_str,
            "ratables": film_str,
            }
        
            # Construct headers
        user_cookie = self.session.cookies.get("letterboxd.user.CURRENT")
        if not user_cookie:
            raise ValueError("Missing `letterboxd.user.CURRENT` cookie in session.")
        headers = {
            "Cookie": f"letterboxd.user.CURRENT={user_cookie}",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:133.0) Gecko/20100101 Firefox/133.0",
            "X-Requested-With": "XMLHttpRequest",
            "Content-Type": "application/x-www-form-urlencoded",
        }

        res = self.session.post(METADATA_URL, headers=headers, data=payload)

        try:
            metadata = res.json()
        except ValueError:
            print("Response JSON: Unable to parse as JSON.")

        # Validate the response
        if not (res.status_code == 200 and res.json().get("result") is True):
            raise ConnectionError("Failed to update watched status.")
  
        # Extract data
        watched = any(item.get("watched", False) for item in metadata.get("watchables", []))
        liked = any(item.get("liked", False) for item in metadata.get("likeables", []))
        watchlisted = bool(metadata.get("filmsInWatchlist"))
        rating = next((item.get("rating") for item in metadata.get("rateables", []) if "rating" in item), None)

        # Return the simplified dictionary
        return {
            "Watched": watched,
            "Liked": liked,
            "Watchlisted": watchlisted,
            "Rating": rating,
        }
    
    def set_film_liked_status(self, title: str, liked: bool = True):
        """
        Set the like status of a film on Letterboxd.

        Args:
            title (str): The title of the film.
            liked (bool): True to like the film, False to unlike it.

        Raises:
            ConnectionError: If the request to update the like status fails.
        """
        lb_id = self.get_lb_film_id(title)
        url = create_lb_operation_url_with_id(lb_id, "like")
        payload = {
            "liked": "true" if liked else "false",  # Mark as liked or unliked
            "__csrf": self.session.cookies.get("com.xk72.webparts.csrf"),
        }
        res = self.session.post(url, data=payload)
        if not (res.status_code == 200 and res.json().get("result") is True):
            raise ConnectionError("Failed to update like status.")
        action = "liked" if liked else "unliked"
        print(f"{title} was successfully {action}.")
        
        
    def set_film_not_liked(self, title: str):
        self.set_film_liked_status(title, False)   

    def set_film_watched_status(self, title: str, watched: bool = True):
        """
        Set the watched status of a film on Letterboxd.

        Args:
            title (str): The title of the film.
            watched (bool, optional): True to mark as watched, False to mark as unwatched. Defaults to True.

        Raises:
            ConnectionError: If the request to update the watched status fails.
        """
        lb_id = self.get_lb_film_id(title)
        url = create_lb_operation_url_with_id(lb_id, "watch")
        # Create the payload for the request
        payload = {
            "watched": "true" if watched else "false",  # Mark as watched or unwatched
            "__csrf": self.session.cookies.get("com.xk72.webparts.csrf"),
        }

        res = self.session.post(url, data=payload)
        if not (res.status_code == 200 and res.json().get("result") is True):
            raise ConnectionError("Failed to update watched status.")

        action = "watched" if watched else "unwatched"
        print(f"{title} was successfully marked as {action}.")
        
    def set_film_unwatched(self, title: str):
        self.set_film_watched_status(title, False)
        
    def add_watchlist_entry(self, title: str):
        """
        Add a film to the user's watchlist on Letterboxd.

        Args:
            title (str): The title of the film to add to the watchlist.

        Raises:
            ConnectionError: If the request to add the film to the watchlist fails.
        """
        url = create_lb_operation_url_with_title(title, "add_watchlist")
        res = self.session.post(url, data={"__csrf": self.session.cookies.get("com.xk72.webparts.csrf")})
        if not (res.status_code == 200 and res.json()["result"] is True):
            raise ConnectionError("Failed to add to watchlist.")
        print(f"{title} was added to your watchlist.")
                
    def remove_watchlist_entry(self, title: str):
        """
        Remove a film from the user's watchlist on Letterboxd.

        Args:
            title (str): The title of the film to remove from the watchlist.

        Raises:
            ConnectionError: If the request to remove the film from the watchlist fails.
        """
        url = create_lb_operation_url_with_title(title, "remove_watchlist")
        res = self.session.post(url, data={"__csrf": self.session.cookies.get("com.xk72.webparts.csrf")})
        if not (res.status_code == 200 and res.json()["result"] is True):
            raise ConnectionError("Failed to remove from watchlist.")
        print(f"{title} was removed from your watchlist.")
    
    def rate_film(self, title: str, rating: int):
        """
        Rate a film on Letterboxd.

        Args:
            title (str): The title of the film to rate.
            rating (int): The rating to assign to the film (e.g., 1-10).

        Raises:
            ValueError: If the rating is outside the allowed range (1-10).
            ConnectionError: If the request to update the rating fails.
        """
        if not (1 <= rating <= 10):
            raise ValueError(f"Invalid rating: {rating}. Rating must be between 1 and 10.")

        lb_id = self.get_lb_film_id(title)
        url = create_lb_operation_url_with_id(lb_id, "rate")
        
        # Create the payload for the request
        payload = {
            "rating": int(rating),  # Letterboxd expects the rating as a string
            "__csrf": self.session.cookies.get("com.xk72.webparts.csrf"),
        }

        res = self.session.post(url, data=payload)
        if not (res.status_code == 200 and res.json().get("result") is True):
            raise ConnectionError("Failed to update rating.")

        print(f"{title} was successfully rated {rating}/10.")
        
    def add_diary_entry(self, title: str, payload: dict):
        payload["filmId"] = self.get_lb_film_id(title)
        payload["__csrf"] = self.session.cookies.get("com.xk72.webparts.csrf")
        res = self.session.post(ADD_DIARY_URL, data=payload)
        if not (res.status_code == 200 and res.json()["result"] is True):
            raise ConnectionError(f"Failed to add to diary.")
        print(f"{title} was added to your diary.")

    # Helper Function
    ##########################
    
    def perform_operation(self, operation: str, link: str, *args, **kwargs):
        """Perform an operation on a Letterboxd link.
        """
        getattr(self, FILM_OPERATIONS[operation])(link, *args, **kwargs)
        


# Non-Object Functions
##########################

def create_lb_operation_url_with_title(title: str, operation: str) -> str:
    return LB_BASE_URL + LB_TITLE_URL_TEMPLATES[operation](title)

def create_lb_operation_url_with_id(id: str, operation: str) -> str:
    return LB_BASE_URL + LB_ID_URL_TEMPLATES[operation](id)

def _get_tmdb_id_from_lb_html(link: str, is_diary: bool) -> int:
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
        film_url = LB_BASE_URL + film_link.get("href")
        film_page = html.fromstring(requests.get(film_url).text)
    tmdb_link = film_page.xpath("//a[@data-track-action='TMDb']")
    if len(tmdb_link) == 0:
        raise ValueError("No link found for film")
    
    tmdb_category = tmdb_link[0].get("href").split("/")[-3]
    
    if tmdb_category != "movie":
        raise ValueError(f"Unable to display detailed information for items with TMDB category \"{tmdb_category}\": {tmdb_link[0].get("href")}")

    id = tmdb_link[0].get("href").split("/")[-2]
    return int(id)


def get_tmdb_id_from_lb(link: str, is_diary=False) -> int | None:
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
            id = _get_tmdb_id_from_lb_html(link, is_diary)
            prefix_dict = tmdb_id_cache.get(prefix) or {}
            prefix_dict[key] = id
            tmdb_id_cache[prefix] = prefix_dict
        except ValueError as e:
            print(e)
            id = None
    tmdb_id_cache.close()
    return id