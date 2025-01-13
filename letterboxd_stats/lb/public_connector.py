import requests
from lxml import html
from ..utils.general_cache import GeneralCache
from .utilities import LB_BASE_URL, create_lb_search_url, create_lb_operation_url_with_title


class LBPublicConnector:
    def __init__(self, cache_path="/tmp/general_cache.db"):
        self.session = requests.Session()
        self.session.get(LB_BASE_URL)  # Initialize cookies, etc.
        self.cache = GeneralCache(cache_path)

    def search_lb_by_title(self, search_query: str):
        """
        Search for films by title.

        Args:
            search_query (str): The search query string.

        Returns:
            dict: A dictionary of search results with film titles as keys and links as values.
        """
        search_url = create_lb_search_url(search_query)
        res = self.session.get(search_url)
        if res.status_code != 200:
            raise ConnectionError("Failed to retrieve search results.")

        # Parse the search page
        search_page = html.fromstring(res.text)
        film_list = search_page.xpath("//div[@class='film-detail-content']")
        if not film_list or len(film_list) == 0:
            raise ValueError(f"No results found for query: {search_query}")

        results = {}
        for film in film_list:
            search_query = film.xpath("./h2/span/a")[0].text.rstrip()
            director = director[0].text if len(director := film.xpath("./p/a")) > 0 else ""
            year = f"({year[0].text}) " if len(year := film.xpath("./h2/span//small/a")) > 0 else ""
            link = film.xpath("./h2/span/a")[0].get("href")
            display_string = f"{search_query} {year}- {director}"
            
            results[display_string] = link
            
        return results

    def get_lb_film_id(self, lb_title: str) -> str:
        """
        Retrieve the Letterboxd film ID for a given film title, with caching.

        Args:
            lb_title (str): The unique Letterboxd title of the film.

        Returns:
            str: The Letterboxd film ID.

        Raises:
            ConnectionError: If the page cannot be retrieved.
        """
        # Check if the film ID is already cached
        cached_id = self.cache.get("letterboxd", lb_title)
        if cached_id:
            return cached_id

        # If not cached, retrieve the ID from the Letterboxd page
        url = create_lb_operation_url_with_title(lb_title, "diary")
        res = self.session.get(url)
        if res.status_code != 200:
            raise ConnectionError("Failed to retrieve the Letterboxd page")
        
        # Parse the HTML to find the film ID
        film_page = html.fromstring(res.text)
        letterboxd_film_id = film_page.get_element_by_id("frm-sidebar-rating").get("data-rateable-uid").split(":", 1)[1]

        # Save the retrieved ID to the cache
        self.cache.save("letterboxd", lb_title, letterboxd_film_id)

        return letterboxd_film_id

    def get_tmdb_id_from_lb_page(self, lb_url: str, is_diary=False) -> int | None:
        """Find the TMDB id from a letterboxd page.

        A link to a Letterboxd film usually starts with either https://letterboxd.com/
        or https://boxd.it/ (usually all .csv files have this prefix). We structure the cache dict accordingly.
        The cache is meant to avoid bottleneck of constantly retrieving the Id from an HTML page.
        """      
        namespace, key = lb_url.rsplit("/", 1)
        cached_id = self.cache.get(namespace, key)
        
        if cached_id:
            return cached_id
        else:
            try:
                id = self._get_tmdb_id_from_lb(lb_url, is_diary)
                self.cache.save(namespace, key, id)
                return id

            except ValueError as e:
                print(e)
                id = None
                
    @staticmethod
    def _get_tmdb_id_from_lb(lb_url: str, is_diary: bool) -> int:
        """Scraping the TMDB link from a Letterboxd film page.
        Inspect this HTML for reference: https://letterboxd.com/film/seven-samurai/
        """

        res = requests.get(lb_url)
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
    
    # def get_public_film_metadata(self, lb_title: str):
    #     """
    #     Fetch public metadata for a film.

    #     Args:
    #         lb_title (str): The title of the film.

    #     Returns:
    #         dict: Metadata for the film.
    #     """
    #     # Example URL: https://letterboxd.com/film/seven-samurai/
    #     film_url = f"{LB_BASE_URL}/film/{lb_title.replace(' ', '-').lower()}/"
    #     res = self.session.get(film_url)
    #     if res.status_code != 200:
    #         raise ConnectionError("Failed to retrieve film metadata.")

    #     # Parse metadata
    #     film_page = html.fromstring(res.text)
    #     title = film_page.xpath("//h1[@class='headline-1 js-widont']")[0].text.strip()
    #     synopsis = film_page.xpath("//div[@class='synopsis']//p")[0].text.strip()

    #     return {"title": title, "synopsis": synopsis}