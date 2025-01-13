from .auth import LBAuth
from .data_exporter import LBUserDataExporter
from .public_connector import LBPublicConnector

from .utilities import (
    LB_OPERATIONS, 
    ADD_DIARY_URL, 
    METADATA_URL, 
    create_lb_operation_url_with_title, 
    create_lb_operation_url_with_id)

class LBAuthConnector(LBPublicConnector):
    def __init__(self, username: str = None, password: str = None, cache_path: str = "/tmp/cache.db"):
        super().__init__(cache_path) 
        self.auth = LBAuth(username, password)
        self.data_exporter = LBUserDataExporter(self.auth)
        self.session = self.auth.session

        try:
            self.auth.login()  # Automatically login during initialization
        except ConnectionError:
            print("Failed to login. Not all operations will be available.")

    def download_stats(self, download_dir: str = "/tmp"):
        return self.data_exporter.download_and_extract_data(download_dir)


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

            if not self.auth.logged_in:
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

        print(f"Performing operation: {operation}")
        return method(link, *args, **kwargs)
        
    def add_diary_entry(self, lb_title: str, payload: dict):        
        payload["filmId"] = self.get_lb_film_id(lb_title)
        payload["__csrf"] = self.auth.get_csrf_token()
        res = self.session.post(ADD_DIARY_URL, data=payload)
        if not (res.status_code == 200 and res.json()["result"] is True):
            raise ConnectionError(f"Failed to add to diary.")
        print(f"{lb_title} was added to your diary.")

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
        print(f"{lb_title} was successfully {action}.")
        
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
        print(f"{lb_title} was successfully marked as {action}.")
        
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
        print(f"{lb_title} was {"added to" if status else "removed from"} your watchlist.")
    
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

        print(f"{lb_title} was successfully rated {rating}/10.")