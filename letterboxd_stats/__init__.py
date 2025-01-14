"""
Letterboxd Stats Package Exports
===============

This module exposes the key modules and functions from the package, making them available for import
when the package is accessed as a whole. It simplifies the import process for users of the package
by providing a central location for core functionality.

Metadata:
---------
__version__: The current version of the package.
__author__: The package author.
__description__: A brief description of the package.
__all__: Specifies the modules and functions to be exported when using `from package import *`.
"""
from .cli.letterboxd_cli import LetterboxdCLI
from .lb.auth_connector import LBAuthConnector
from .lb.data_exporter import LBUserDataExporter
from .lb.public_connector import LBPublicConnector
from .utils.tmdb_connector import TMDbAPI

__version__ = "0.3.0"
__author__ = "mBaratta96"
__description__ = "A CLI tool for interacting with Letterboxd."
__all__ = [
    "TMDbAPI",
    "LetterboxdCLI",
    "LBAuthConnector",
    "LBPublicConnector",
    "LBUserDataExporter",
]
