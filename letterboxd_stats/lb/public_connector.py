"""
LBPublicConnector Module
========================

This module provides the `LBPublicConnector` class, which serves as an
interface for accessing public Letterboxd data without requiring user
authentication. It includes methods for searching films, retrieving
metadata, and interacting with related third-party services like TMDb.

Classes:
--------
- LBPublicConnector: A connector for accessing public Letterboxd data
    and performing operations such as film searches and metadata retrieval.

Notable Imports:
--------
- GeneralCache: For caching data to reduce redundant requests.

Features:
---------
1. **Film Search**:
   - Search for films by title and retrieve results with links.

2. **Metadata Retrieval**:
   - Fetch metadata for a specific film, including Letterboxd film IDs and TMDb IDs.
   - Handle redirects for diary links to resolve the correct film page.

3. **Caching**:
   - Leverages a `GeneralCache` instance to store and retrieve frequently accessed data,
     reducing redundant network requests.

4. **Error Handling**:
   - Provides detailed exceptions for scenarios such as failed requests, missing data,
     or unsupported TMDb categories.

"""

import logging

import requests
from lxml import html

from ..utils.general_cache import GeneralCache
from .utilities import (LB_BASE_URL, create_lb_operation_url_with_title,
                        create_lb_search_url)

logger = logging.getLogger(__name__)


class LBPublicConnector:
    """
    The `LBPublicConnector` class provides methods to interact with publicly accessible Letterboxd
    data without requiring user authentication.

    Attributes:
    -----------
    - session (requests.Session):
        A persistent HTTP session for making requests to Letterboxd.
    - cache (GeneralCache):
        An instance of the `GeneralCache` class for storing and retrieving cached data.

    Methods:
    --------
    - __init__(cache_path="cache.db"):
        Initializes the connector, setting up the HTTP session and cache system.

    - search_lb_by_title(search_query: str) -> dict:
        Searches Letterboxd for films by title and retrieves a dictionary of results,
        including titles and corresponding links.

    - get_lb_film_id(lb_title: str) -> str:
        Retrieves the Letterboxd film ID for a given title, using cached data if available.

    - get_tmdb_id(lb_title: str) -> int | None:
        Fetches the TMDb ID for a film using its Letterboxd title.

    - get_tmdb_id_from_lb(lb_url: str, is_diary=False) -> int | None:
        Scrapes a Letterboxd film page to retrieve the associated TMDb ID.

    - _get_tmdb_id_from_lb_page(lb_url: str, is_diary: bool) -> int:
        Internal method to scrape the TMDb link from a Letterboxd page,
        ensuring the film is categorized as a "movie" on TMDb.

    Notes:
    ------
    - TMDb links on Letterboxd pages are only supported for films categorized as "movies" in TMDb.
    - Diary links on Letterboxd are redirected to the main film page before processing.

    Example Usage:
    --------------
    ```python
    connector = LBPublicConnector(cache_path="letterboxd_cache.db")

    # Search for a film by title
    results = connector.search_lb_by_title("Inception")
    print(results)

    # Get Letterboxd film ID
    film_id = connector.get_lb_film_id("inception")
    print(film_id)

    # Get TMDb ID
    tmdb_id = connector.get_tmdb_id("inception")
    print(tmdb_id)
    ```
    """

    def __init__(self, cache_path="cache.db"):
        logger.info("Initializing LBPublicConnector with cache path: %s", cache_path)
        self.session = requests.Session()
        self.session.get(LB_BASE_URL)  # Initialize cookies, etc.
        self.cache = GeneralCache(cache_path)
        logger.info("LBPublicConnector initialized successfully.")

    def search_lb_by_title(self, search_query: str):
        """
        Search for films by title.

        Args:
            search_query (str): The search query string.

        Returns:
            dict: A dictionary of search results with film titles as keys and links as values.
        """
        logger.info("Searching for films with query: %s", search_query)
        search_url = create_lb_search_url(search_query)
        logger.debug("Generated search URL: %s", search_url)

        try:
            res = self.session.get(search_url)
            res.raise_for_status()  # Raise an HTTPError for bad responses
        except requests.RequestException as e:
            logger.error("Failed to retrieve search results: %s", e)
            raise

        # Parse the search page
        search_page = html.fromstring(res.text)
        film_list = search_page.xpath("//div[@class='film-detail-content']")
        if not film_list or len(film_list) == 0:
            logger.warning("No results found for query: %s", search_query)
            raise ValueError(f"No results found for query: {search_query}")

        logger.info("Found %d results for query: %s", len(film_list), search_query)

        results = {}
        for film in film_list:
            search_query = film.xpath("./h2/span/a")[0].text.rstrip()
            director = (
                director[0].text if len(director := film.xpath("./p/a")) > 0 else ""
            )
            year = (
                f"({year[0].text}) "
                if len(year := film.xpath("./h2/span//small/a")) > 0
                else ""
            )
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
        namespace = "lb_title_to_lb_id"
        logger.info("Retrieving Letterboxd film ID for title: %s", lb_title)

        cached_id = self.cache.get(namespace, lb_title)
        if cached_id:
            logger.debug("Cache hit for title: %s, ID: %s", lb_title, cached_id)
            return cached_id

        logger.debug("Cache miss for title: %s. Fetching from Letterboxd.", lb_title)
        # If not cached, retrieve the ID from the Letterboxd page
        lb_url = create_lb_operation_url_with_title(lb_title, "diary")
        try:
            res = self.session.get(lb_url)
            res.raise_for_status()
        except requests.RequestException as e:
            logger.error("Failed to fetch URL: %s", e)
            raise

        # Parse the HTML to find the film ID
        film_page = html.fromstring(res.text)
        letterboxd_film_id = (
            film_page.get_element_by_id("frm-sidebar-rating")
            .get("data-rateable-uid")
            .split(":", 1)[1]
        )

        # Save the retrieved ID to the cache
        self.cache.save(namespace, lb_title, letterboxd_film_id)
        logger.info(
            "Successfully retrieved and cached Letterboxd ID: %s for URL: %s",
            id,
            lb_url,
        )

        return letterboxd_film_id

    def get_tmdb_id(self, lb_title: str) -> int | None:
        """Fetch TMDB ID using the Letterboxd Title"""
        film_url = create_lb_operation_url_with_title(lb_title, "film_page")
        return self.get_tmdb_id_from_lb(film_url)

    def get_tmdb_id_from_lb(self, lb_url: str, is_diary=False) -> int | None:
        """Fetch TMDB ID using the Letterboxd film page URL. Uses cache is possible.
        """

        namespace = "lb_title_to_tmdb_id"
        # key = lb_url.rsplit("/", 1)[1]
        logger.info("Retrieving TMDb ID for URL: %s", lb_url)

        cached_id = self.cache.get(namespace, lb_url)

        if cached_id:
            logger.debug("Cache hit for URL: %s, TMDb ID: %s", lb_url, cached_id)
            return cached_id

        logger.debug(
            "Cache miss for URL: %s. Attempting to fetch from Letterboxd.", lb_url
        )

        try:
            tmdb_id = self._get_tmdb_id_from_lb_page(lb_url, is_diary)
            if tmdb_id:
                self.cache.save(namespace, lb_url, tmdb_id)
                logger.info(
                    "Successfully retrieved and cached TMDb ID: %s for URL: %s",
                    tmdb_id,
                    lb_url,
                )
            return tmdb_id
        except ValueError as e:
            logger.warning("Failed to retrieve TMDb ID for URL '%s': %s", lb_url, e)
            tmdb_id = None

    @staticmethod
    def _get_tmdb_id_from_lb_page(lb_url: str, is_diary: bool) -> int:
        """Scraping the TMDB link from a Letterboxd film page.
        Inspect this HTML for reference: https://letterboxd.com/film/seven-samurai/
        """
        logger.info("Fetching TMDb ID from URL: %s (is_diary=%s)", lb_url, is_diary)

        try:
            res = requests.get(lb_url, timeout=10)
            res.raise_for_status()
        except requests.RequestException as e:
            logger.error("Failed to fetch URL: %s", e)
            raise

        lb_page = html.fromstring(res.text)

        if is_diary:
            # Diary pages have no link to TMDB. Redirect to the main film page.
            logger.debug("Handling diary page redirect for URL: %s", lb_url)
            title_link = lb_page.xpath("//span[@class='film-title-wrapper']/a")
            if not title_link:
                raise ValueError("No link found for film on diary page.")
            film_url = LB_BASE_URL + title_link[0].get("href")

            logger.debug("Redirecting to film page URL: %s", film_url)

            try:
                res = requests.get(film_url, timeout=10)
                res.raise_for_status()
            except requests.RequestException as e:
                logger.error("Failed to fetch URL: %s", e)
                raise

            lb_page = html.fromstring(res.text)

        tmdb_link = lb_page.xpath("//a[@data-track-action='TMDb']")
        if not tmdb_link:
            raise ValueError("No TMDb link found on page.")

        tmdb_category = tmdb_link[0].get("href").split("/")[-3]

        if tmdb_category != "movie":
            raise ValueError(
                f"Found TMDb link with type '{tmdb_category}'."
                + "This tool only supports type 'movie'."
            )

        tmdb_id = tmdb_link[0].get("href").split("/")[-2]
        logger.info("Successfully fetched TMDb ID: %s from URL: %s", tmdb_id, lb_url)
        return int(tmdb_id)

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
