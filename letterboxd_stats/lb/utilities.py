from typing import Callable, Dict

import logging

# Create a library-specific logger
logger = logging.getLogger("letterboxd")
logger.setLevel(logging.INFO)

# Add a console handler (users can customize this)
console_handler = logging.StreamHandler()
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)


LB_BASE_URL = "https://letterboxd.com"
LOGIN_URL = LB_BASE_URL + "/user/login.do"
SEARCH_URL_TEMPLATE = LB_BASE_URL + "/s/search/{query}/"
ADD_DIARY_URL = LB_BASE_URL + "/s/save-diary-entry"
METADATA_URL = LB_BASE_URL +"/ajax/letterboxd-metadata/"


LB_OPERATION_TITLE_TEMPLATES: Dict[str, Callable[[str], str]] = {
    "diary": lambda s: f"/csi/film/{s}/sidebar-user-actions/?esiAllowUser=true",
    "add_watchlist": lambda s: f"/film/{s}/add-to-watchlist/",
    "remove_watchlist": lambda s: f"/film/{s}/remove-from-watchlist/",
    "film_page": lambda s: f"/film/{s}",
}

LB_OPERATION_ID_TEMPLATES: Dict[str, Callable[[str], str]] = {
    "watch": lambda s: f"/s/film:{s}/watch/",
    "like": lambda s: f"/s/film:{s}/like/",
    "rate": lambda s: f"/s/film:{s}/rate/",
}

LB_OPERATIONS: Dict[str, Dict[str, str | bool | None]] = {
    "Add to diary": {"method": "add_diary_entry", "status": None},
    "Update film rating": {"method": "set_film_rating", "status": None},
    "Add to Liked films": {"method": "set_film_liked_status", "status": True},
    "Remove from liked films": {"method": "set_film_liked_status", "status": False},
    "Mark film as watched": {"method": "set_film_watched_status", "status": True},
    "Un-mark film as watched": {"method": "set_film_watched_status", "status": False},
    "Add to watchlist": {"method": "set_film_watchlist_status", "status": True},
    "Remove from watchlist": {"method": "set_film_watchlist_status", "status": False},
}

def create_lb_operation_url_with_title(lb_title: str, operation: str) -> str:
    return LB_BASE_URL + LB_OPERATION_TITLE_TEMPLATES[operation](lb_title)

def create_lb_operation_url_with_id(id: str, operation: str) -> str:
    return LB_BASE_URL + LB_OPERATION_ID_TEMPLATES[operation](id)

def create_lb_search_url(search_query: str) -> str:
    return SEARCH_URL_TEMPLATE.format(query=search_query)