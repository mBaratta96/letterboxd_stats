# Expose key modules and functions from the package

from .core.config_loader import load_config, default_config_dir
from .core.letterboxd_connector import LBConnector

__all__ = [
    "load_config",
    "default_config_dir",
    "LBConnector",
    "user_search_person",
    "user_search_film",
]
