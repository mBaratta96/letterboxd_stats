import os
import shelve
import requests
from lxml import html
from zipfile import ZipFile

from .tmdb_cache import TMDBCache

LB_BASE_URL = "https://letterboxd.com"
LOGIN_URL = LB_BASE_URL + "/user/login.do"
DATA_EXPORT_URL = LB_BASE_URL + "/data/export"
METADATA_URL = LB_BASE_URL +"/ajax/letterboxd-metadata/"
ADD_DIARY_URL = LB_BASE_URL + "/s/save-diary-entry"

FILM_OPERATIONS = {
    "Add to diary": "add_diary_entry",    
    "Update film rating": "set_film_rating",
    "Add to Liked films": "set_film_liked_status",
    "Remove from liked films": "set_film_not_liked",
    "Mark film as watched": "set_film_watched_status",
    "Un-mark film as watched": "set_film_unwatched",
    "Add to watchlist": "set_film_watchlist_status",
    "Remove from watchlist": "remove_film_from_watchlist",
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


class LBConnector:
    
    # Constructor
    ##########################
    
    def __init__(self, username: str=None, password: str=None, cache_path: str = "tmdb_cache.db"):
                
        self.logged_in = False

        self.session = requests.Session()
        self.session.get(LB_BASE_URL)
        self.cache = TMDBCache(cache_path)

        if username and password:
            print("Logging in...")
            self.__username = username  # Private attribute
            self.__password = password  # Private attribute
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

    def download_stats(self, download_dir: str = "/tmp"):
        """Download and extract data of the import/export section.
        """
        if not self.logged_in:
            raise RuntimeError("The user must be logged in to perform this action.")
        
        res = self.session.get(DATA_EXPORT_URL)
        if res.status_code != 200 or "application/zip" not in res.headers["Content-Type"]:
            raise ConnectionError(f"Failed to download data. Response headers:\n{res.headers}")
        print("Data download successful.")
        filename = res.headers["content-disposition"].split()[-1].split("=")[-1]
        if not os.path.exists(download_dir):
            os.makedirs(download_dir)
        archive = os.path.join(download_dir, filename)
        with open(archive, "wb") as f:
            f.write(res.content)
        with ZipFile(archive, "r") as zip:
            zip.extractall(download_dir)
        os.remove(archive)
        
        return res.status_code

        
    # Scrape Letterboxd Web Data
    ############################
    
    def search_lb_by_title(self, search_query: str):
        """Search a film and return the results.
        For reference: https://letterboxd.com/search/seven+samurai/?adult
        """
        search_url = self.create_lb_operation_url_with_title(search_query, "search")
        print(f"Searching for '{search_query}'")
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
            search_query = film.xpath("./h2/span/a")[0].text.rstrip()
            director = director[0].text if len(director := film.xpath("./p/a")) > 0 else ""
            year = f"({year[0].text}) " if len(year := film.xpath("./h2/span//small/a")) > 0 else ""
            link = film.xpath("./h2/span/a")[0].get("href")
            title_years_directors_links[f"{search_query} {year}- {director}"] = link
            
        return title_years_directors_links

    
    def get_lb_film_id(self, lb_title: str):
        """
        Retrieve the Letterboxd film ID for a given film title.

        Args:
            lb_title (str): The unique Letterboxd title of the film.

        Returns:
            str: The Letterboxd film ID.

        Raises:
            ConnectionError: If the page cannot be retrieved.
        """
        url = self.create_lb_operation_url_with_title(lb_title, "diary")
        res = self.session.get(url)
        if res.status_code != 200:
            raise ConnectionError("Failed to retrieve the Letterboxd page")
        film_page = html.fromstring(res.text)
        # Not the TMDB id, but the Letterboxd ID to use to add the film to diary.
        # Reference: https://letterboxd.com/film/seven-samurai/
        letterboxd_film_id = film_page.get_element_by_id("frm-sidebar-rating").get("data-rateable-uid").split(":", 1)[1]
        return letterboxd_film_id

    def get_tmdb_id_from_lb_page(self, lb_page_url: str, is_diary=False) -> int | None:
        """Find the TMDB id from a letterboxd page.

        A link to a Letterboxd film usually starts with either https://letterboxd.com/
        or https://boxd.it/ (usually all .csv files have this prefix). We structure the cache dict accordingly.
        The cache is meant to avoid bottleneck of constantly retrieving the Id from an HTML page.
        """      
        prefix, key = lb_page_url.rsplit("/", 1)
        cached_id = self.cache.get_tmdb_id_from_cache(prefix, key)
        
        if cached_id:
            return cached_id
        else:
            try:
                id = self._get_tmdb_id_from_lb_html(lb_page_url, is_diary)
                self.cache.save_tmdb_id_to_cache(prefix, key, id)
                return id

            except ValueError as e:
                print(e)
                id = None
    
        
    def fetch_lb_film_user_metadata(self, lb_title: str) -> bool:
        """
        Fetch metadata about a film from Letterboxd for the current user.

        Args:
            lb_title (str): The unique Letterboxd title of the film.

        Returns:
            dict: Metadata containing 'Watched', 'Liked', 'Watchlisted', and 'Rating' statuses.

        Raises:
            ValueError: If the required user cookie is missing.
            ConnectionError: If the metadata API call fails.
        """

        if not self.logged_in:
            raise RuntimeError("The user must be logged in to perform this action.")

        # Construct headers
        user_cookie = self.session.cookies.get("letterboxd.user.CURRENT")
        if not user_cookie:
            raise ValueError("Missing `letterboxd.user.CURRENT` cookie in session.")
        
        headers = {"Cookie": f"letterboxd.user.CURRENT={user_cookie}"}

        payload= {}
        film_id = self.get_lb_film_id(lb_title)
        details = [ "posters", "likeables", "watchables", "ratables"]
        for detail in details:
            payload[detail] = f"film:{film_id}"

        res = self.session.post(METADATA_URL, headers=headers, data=payload)

        try:
            metadata_json = res.json()
        except ValueError:
            print("Response JSON: Unable to parse as JSON.")

        # Validate the response
        if not (res.status_code == 200 and res.json().get("result") is True):
            raise ConnectionError("Failed to update watched status.")

        # Return the simplified dictionary
        metadata = {
            "Watched": any(item.get("watched", False) for item in metadata_json.get("watchables", [])),
            "Liked": any(item.get("liked", False) for item in metadata_json.get("likeables", [])),
            "Watchlisted": bool(metadata_json.get("filmsInWatchlist")),
            "Rating": next((item.get("rating") for item in metadata_json.get("rateables", []) if "rating" in item), None),
        }
        
        return metadata
    
    # Letterboxd Pseudo-API
    ########################
    def set_film_liked_status(self, lb_title: str, liked: bool = True):
        """
        Set the like status of a film on Letterboxd.

        Args:
            lb_title (str): The unique Letterboxd title of the film.
            liked (bool): True to like the film, False to unlike it.

        Raises:
            ConnectionError: If the request to update the like status fails.
        """
       
        lb_id = self.get_lb_film_id(lb_title)
        url = self.create_lb_operation_url_with_id(lb_id, "like")
        payload = {
            "liked": "true" if liked else "false",  # Mark as liked or unliked
            "__csrf": self.session.cookies.get("com.xk72.webparts.csrf"),
        }
        res = self.session.post(url, data=payload)
        if not (res.status_code == 200 and res.json().get("result") is True):
            raise ConnectionError("Failed to update like status.")
        action = "liked" if liked else "unliked"
        print(f"{lb_title} was successfully {action}.")
        
        
    def set_film_not_liked(self, lb_title: str):
        self.set_film_liked_status(lb_title, False)   

    def set_film_watched_status(self, lb_title: str, watched: bool = True):
        """
        Set the watched status of a film on Letterboxd.

        Args:
            lb_title (str): The unique Letterboxd title of the film.
            watched (bool, optional): True to mark as watched, False to mark as unwatched. Defaults to True.

        Raises:
            ConnectionError: If the request to update the watched status fails.
        """
                
        lb_id = self.get_lb_film_id(lb_title)
        url = self.create_lb_operation_url_with_id(lb_id, "watch")
        # Create the payload for the request
        payload = {
            "watched": "true" if watched else "false",  # Mark as watched or unwatched
            "__csrf": self.session.cookies.get("com.xk72.webparts.csrf"),
        }

        res = self.session.post(url, data=payload)
        if not (res.status_code == 200 and res.json().get("result") is True):
            raise ConnectionError("Failed to update watched status.")

        action = "watched" if watched else "unwatched"
        print(f"{lb_title} was successfully marked as {action}.")
        
    def set_film_unwatched(self, lb_title: str):
        self.set_film_watched_status(lb_title, False)
        
    def set_film_watchlist_status(self, lb_title: str, watchlisted: bool = True):
        """
        Add or remove a film from the user's watchlist on Letterboxd.

        Args:
            lb_title (str): The unique Letterboxd title of the film to add or remove from the watchlist.
            watchlisted (bool): True to add to the watchlist, False to remove.

        Raises:
            ConnectionError: If the request to update the watchlist fails.
        """        
        
        operation = "add" if watchlisted else "remove"

        url = self.create_lb_operation_url_with_title(lb_title, operation+"_watchlist")
        res = self.session.post(url, data={"__csrf": self.session.cookies.get("com.xk72.webparts.csrf")})
        if not (res.status_code == 200 and res.json()["result"] is True):
            raise ConnectionError(f"Failed to {operation} watchlist entry.")
        print(f"{lb_title} was {"added to" if watchlisted else "removed from"} your watchlist.")
                
    def remove_film_from_watchlist(self, lb_title: str):
        self.set_film_watchlist_status(lb_title, False)
    
    def set_film_rating(self, lb_title: str, rating: int):
        """
        Rate a film on Letterboxd.

        Args:
            lb_title (str): The unique Letterboxd title of the film to rate.
            rating (int): The rating to assign to the film (e.g., 1-10).

        Raises:
            ValueError: If the rating is outside the allowed range (1-10).
            ConnectionError: If the request to update the rating fails.
        """
                
        if not (0 <= rating <= 10):
            raise ValueError(f"Invalid rating: {rating}. Rating must be between (inclusive) 0 and 10.")

        lb_id = self.get_lb_film_id(lb_title)
        url = self.create_lb_operation_url_with_id(lb_id, "rate")
        
        # Create the payload for the request
        payload = {
            "rating": int(rating),  # Letterboxd expects the rating as a string
            "__csrf": self.session.cookies.get("com.xk72.webparts.csrf"),
        }

        res = self.session.post(url, data=payload)
        if not (res.status_code == 200 and res.json().get("result") is True):
            raise ConnectionError("Failed to update rating.")

        print(f"{lb_title} was successfully rated {rating}/10.")
        
    def add_diary_entry(self, lb_title: str, payload: dict):        
        payload["filmId"] = self.get_lb_film_id(lb_title)
        payload["__csrf"] = self.session.cookies.get("com.xk72.webparts.csrf")
        res = self.session.post(ADD_DIARY_URL, data=payload)
        if not (res.status_code == 200 and res.json()["result"] is True):
            raise ConnectionError(f"Failed to add to diary.")
        print(f"{lb_title} was added to your diary.")

    # Helper Function
    ##########################
    
    def perform_operation(self, operation: str, link: str, *args, **kwargs):
        """Perform an operation on a Letterboxd link.
        """

        if not self.logged_in:
            raise RuntimeError("The user must be logged in to perform this action.")
        
        print(operation)
        getattr(self, FILM_OPERATIONS[operation])(link, *args, **kwargs)
        


    # Non-Object Functions
    ##########################
    @staticmethod
    def create_lb_operation_url_with_title(lb_title: str, operation: str) -> str:
        return LB_BASE_URL + LB_TITLE_URL_TEMPLATES[operation](lb_title)
    
    @staticmethod
    def create_lb_operation_url_with_id(id: str, operation: str) -> str:
        return LB_BASE_URL + LB_ID_URL_TEMPLATES[operation](id)

    @staticmethod
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
                raise ValueError("No link found for film on dairy page.")
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


