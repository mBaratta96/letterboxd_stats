"""
LBAuthConnector Module
======================

This module defines the `LBAuthConnector` class, which serves as an interface for authenticated interactions with
Letterboxd's user-specific features. It builds on the `LBPublicConnector` to provide additional functionality
that requires user authentication, such as managing ratings, watchlist statuses, and diary entries.

Classes:
--------
- LBAuthConnector: A connector that handles user authentication, data export, and various operations on Letterboxd.

Notable Imports:
--------
- From `.auth`: `LBAuth` for managing user authentication.
- From `.data_exporter`: `LBUserDataExporter` for handling the download of user account export data.
- From `.public_connector`: `LBPublicConnector` as the base class for public API interactions.
- From `.utilities`: Various constants and helper functions for constructing URLs and managing operations.

Features:
---------
1. **User Authentication**:
   - Login during initialization via the `LBAuth` class.
   - Handles session management and secure token retrieval for authenticated operations.

2. **Data Export**:
   - Download and extract user-specific data using `LBUserDataExporter`.

3. **Film Operations**:
   - Perform operations on Letterboxd films, such as:
     - Fetching user-specific metadata (e.g., Watched, Liked, Watchlisted, Ratings).
     - Managing watchlist, diary entries, and ratings.
     - Setting watched and liked statuses.
"""

import logging

from .auth import LBAuth
from .data_exporter import LBUserDataExporter
from .public_connector import LBPublicConnector
from .utilities import (ADD_DIARY_URL, LB_OPERATIONS, METADATA_URL,
                        create_lb_operation_url_with_id,
                        create_lb_operation_url_with_title)

logger = logging.getLogger(__name__)

class LBAuthConnector(LBPublicConnector):
    def __init__(self, username: str = None, password: str = None, cache_path: str = "cache.db"):
        super().__init__(cache_path)
        self.auth = LBAuth(username, password, self.session)
        self.data_exporter = LBUserDataExporter(self.auth)

        try:
            self.auth.login()  # Automatically login during initialization
        except ConnectionError:
            logger.error("Failed to login. Not all operations will be available.")

    def download_stats(self, download_dir: str = "/tmp"):
        return self.data_exporter.download_and_extract_data(download_dir)


    def fetch_lb_film_user_metadata(self, lb_title: str) -> dict:
        """
        Fetch metadata about a film from Letterboxd for the current user.

        Args:
            lb_title (str): The unique Letterboxd title of the film.

        Returns:
            dict: Metadata containing 'Watched', 'Liked', 'Watchlisted', and 'Rating' statuses.

        Raises:
            RuntimeError: If the user is not logged in.
            ValueError: If the required user cookie is missing.
            ConnectionError: If the metadata API call fails or response is invalid.
        """

        USER_COOKIE_NAME = "letterboxd.user.CURRENT"

        if not self.auth.logged_in:
            raise RuntimeError("User is not logged in. Cannot fetch personalized metadata.")

        # Construct headers
        user_cookie = self.session.cookies.get(USER_COOKIE_NAME)
        if not user_cookie:
            raise ValueError(f"Missing `{USER_COOKIE_NAME}` cookie in session.")

        headers = {"Cookie": f"{USER_COOKIE_NAME}={user_cookie}"}

        if not self.auth.logged_in:
            raise ConnectionError("Not logged in.")

        film_id = self.get_lb_film_id(lb_title)

        payload = {detail: f"film:{film_id}" for detail in ["posters", "likeables", "watchables", "ratables"]}

        try:
            response = self.session.post(METADATA_URL, headers=headers, data=payload)
            response.raise_for_status()
            metadata_json = response.json()
            logger.debug("Metadata API response received for '%s'.", lb_title)
        except ValueError as e:
            logger.error("Failed to parse response as JSON: %s", e)
            raise ConnectionError("Response from the metadata API is invalid.")
        except Exception as e:
            logger.error("Error fetching metadata for '%s': %s", lb_title, e)
            raise ConnectionError(f"Failed to fetch metadata for '{lb_title}'.")

        # Validate response content
        if not metadata_json.get("result"):
            logger.error("Metadata API call failed: %s", metadata_json)
            raise ConnectionError("Failed to fetch metadata. Response indicates failure.")

        # Return the simplified dictionary
        metadata = {
            "Watched": any(item.get("watched", False) for item in metadata_json.get("watchables", [])),
            "Liked": any(item.get("liked", False) for item in metadata_json.get("likeables", [])),
            "Watchlisted": bool(metadata_json.get("filmsInWatchlist")),
            "Rating": next((item.get("rating") for item in metadata_json.get("rateables", []) if "rating" in item), None),
        }

        logger.info("Fetched metadata for '%s': %s", lb_title, metadata)
        return metadata


    def perform_operation(self, operation: str, link: str, *args, **kwargs):
        """Perform an operation on a Letterboxd link.
        """
        if not self.auth.logged_in:
            raise RuntimeError("User must be logged in to perform this operation.")

        operation_data = LB_OPERATIONS.get(operation)
        if not operation_data:
            raise ValueError(f"Operation '{operation}' is not registered in FILM_OPERATIONS.")

        method_name = operation_data["method"]
        method = getattr(self, method_name, None)
        if not method:
            raise ValueError(f"Method '{method_name}' not found for operation '{operation}'.")

        # Inject `enabled` into kwargs if applicable
        if "status" in operation_data and operation_data["status"] is not None:
            kwargs["status"] = operation_data["status"]

        logger.info(f"Performing operation: {operation}")
        return method(link, *args, **kwargs)

    def add_diary_entry(self, lb_title: str, payload: dict):
        payload["filmId"] = self.get_lb_film_id(lb_title)
        payload["__csrf"] = self.auth.get_csrf_token()
        res = self.session.post(ADD_DIARY_URL, data=payload)
        if not (res.status_code == 200 and res.json()["result"] is True):
            raise ConnectionError(f"Failed to add to diary.")
        logger.info(f"{lb_title} was added to your diary.")

    def set_film_liked_status(self, lb_title: str, status: bool = True):
        """
        Set the like status of a film on Letterboxd.

        Args:
            lb_title (str): The unique Letterboxd title of the film.
            liked (bool): True to like the film, False to unlike it.

        Raises:
            ConnectionError: If the request to update the like status fails.
        """

        lb_id = self.get_lb_film_id(lb_title)
        url = create_lb_operation_url_with_id(lb_id, "like")
        payload = {
            "liked": "true" if status else "false",  # Mark as liked or unliked
            "__csrf": self.auth.get_csrf_token(),
        }
        res = self.session.post(url, data=payload)
        if not (res.status_code == 200 and res.json().get("result") is True):
            raise ConnectionError("Failed to update like status.")
        action = "liked" if status else "unliked"
        logger.info(f"{lb_title} was successfully {action}.")

    def set_film_watched_status(self, lb_title: str, status: bool = True):
        """
        Set the watched status of a film on Letterboxd.

        Args:
            lb_title (str): The unique Letterboxd title of the film.
            watched (bool, optional): True to mark as watched, False to mark as unwatched. Defaults to True.

        Raises:
            ConnectionError: If the request to update the watched status fails.
        """

        lb_id = self.get_lb_film_id(lb_title)
        url = create_lb_operation_url_with_id(lb_id, "watch")
        # Create the payload for the request
        payload = {
            "watched": "true" if status else "false",  # Mark as watched or unwatched
            "__csrf": self.auth.get_csrf_token(),
        }

        res = self.session.post(url, data=payload)
        if not (res.status_code == 200 and res.json().get("result") is True):
            raise ConnectionError("Failed to update watched status.")

        action = "watched" if status else "unwatched"
        logger.info(f"{lb_title} was successfully marked as {action}.")

    def set_film_watchlist_status(self, lb_title: str, status: bool = True):
        """
        Add or remove a film from the user's watchlist on Letterboxd.

        Args:
            lb_title (str): The unique Letterboxd title of the film to add or remove from the watchlist.
            watchlisted (bool): True to add to the watchlist, False to remove.

        Raises:
            ConnectionError: If the request to update the watchlist fails.
        """

        operation = "add" if status else "remove"

        url = create_lb_operation_url_with_title(lb_title, operation+"_watchlist")
        res = self.session.post(url, data={"__csrf": self.auth.get_csrf_token()})
        if not (res.status_code == 200 and res.json()["result"] is True):
            raise ConnectionError(f"Failed to {operation} watchlist entry.")

        logger.info(f"{lb_title} was {'added to' if status else 'removed from'} your watchlist.")

    def set_film_rating(self, lb_title: str, rating: int):
        """
        Rate a film on Letterboxd.

        Args:
            lb_title (str): The unique Letterboxd title of the film to rate.
            rating (int): The rating to assign to the film (e.g., 0-10).

        Raises:
            ValueError: If the rating is outside the allowed range (0-10).
            ConnectionError: If the request to update the rating fails.
        """

        if not (0 <= rating <= 10):
            raise ValueError(f"Invalid rating: {rating}. Rating must be between (inclusive) 0 and 10.")

        lb_id = self.get_lb_film_id(lb_title)
        url = create_lb_operation_url_with_id(lb_id, "rate")

        # Create the payload for the request
        payload = {
            "rating": int(rating),  # Letterboxd expects the rating as a string
            "__csrf": self.auth.get_csrf_token(),
        }

        res = self.session.post(url, data=payload)
        if not (res.status_code == 200 and res.json().get("result") is True):
            raise ConnectionError("Failed to update rating.")

        logger.info(f"{lb_title} was successfully rated {rating}/10.")