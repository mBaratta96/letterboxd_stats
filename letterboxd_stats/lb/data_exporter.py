"""
LBUserDataExporter Module
=========================

This module provides the `LBUserDataExporter` class, which is responsible for
downloading and extracting user-specific data exports from Letterboxd. It requires
an authenticated session to perform its operations.

Classes:
--------
- LBUserDataExporter: Handles downloading and extracting Letterboxd export data for
    authenticated users.

Constants:
----------
- `DATA_EXPORT_URL`: The URL endpoint for requesting Letterboxd export data.

Features:
---------
1. **Data Export Handling**:
   - Downloads the user's export data from Letterboxd as a ZIP archive.
   - Extracts the archive into the specified directory.
   - Cleans up temporary files after extraction.

"""

import logging
import os
from zipfile import ZipFile

from .utilities import LB_BASE_URL

logger = logging.getLogger(__name__)
DATA_EXPORT_URL = LB_BASE_URL + "/data/export"

class LBUserDataExporter:
    """
    Handles downloading and extracting user-specific data exports from Letterboxd.

    This class uses an authenticated session to fetch data as a ZIP archive,
    extracts its contents, and cleans up temporary files. It ensures proper
    error handling for login status, response validation, and file operations.

    Attributes:
    -----------
    - auth (LBAuth): Authenticated session handler.

    Example:
    --------
    ```python
    auth = LBAuth(username="user", password="pass")
    auth.login()
    exporter = LBUserDataExporter(auth)
    path = exporter.download_and_extract_data("/path/to/extract")
    print(f"Data extracted to: {path}")
    ```
    """
    def __init__(self, auth):
        """
        Initialize the LBDataExporter with an authentication handler.

        Args:
            auth (LBAuth): An instance of the LBAuth class for handling authentication.
        """
        self.auth = auth

    def download_and_extract_data(self, download_dir: str = "/tmp") -> str:
        """
        Download and extract the Letterboxd export data.

        Args:
            download_dir (str): The directory to download and extract the data.

        Returns:
            str: The path to the extracted files.

        Raises:
            RuntimeError: If the user is not logged in.
            ConnectionError: If the data download fails.
        """
        if not self.auth.logged_in:
            raise RuntimeError("The user must be logged in to perform this action.")

        try:
            response = self.auth.session.get(DATA_EXPORT_URL)
            response.raise_for_status()
        except Exception as e:
            logger.error("Failed to fetch export data: %s", e)
            raise ConnectionError(
                "Failed to download export data from Letterboxd."
            ) from e

        # Verify response content
        if "application/zip" not in response.headers.get("Content-Type", ""):
            logger.error(
                "Unexpected content type: %s", response.headers.get("Content-Type", "")
            )
            raise ConnectionError("Received invalid response. Expected a ZIP file.")

        # Extract filename from headers
        content_disposition = response.headers.get("content-disposition", "")
        if not content_disposition or "filename=" not in content_disposition:
            logger.error(
                "Missing or invalid 'content-disposition' header: %s",
                content_disposition,
            )
            raise ValueError(
                "Could not determine the filename from the response headers."
            )
        filename = content_disposition.split("filename=")[-1].strip('";')
        logger.info("Downloaded file identified as '%s'.", filename)

        # Ensure the download directory exists
        os.makedirs(download_dir, exist_ok=True)

        # Write the downloaded archive to disk
        archive_path = os.path.join(download_dir, filename)
        try:
            with open(archive_path, "wb") as archive_file:
                archive_file.write(response.content)
            logger.info("Export data saved to '%s'.", archive_path)
        except IOError as e:
            logger.error("Failed to save the export archive: %s", e)
            raise

        # Extract the archive
        extracted_dir = os.path.join(download_dir, os.path.splitext(filename)[0])
        try:
            with ZipFile(archive_path, "r") as zip_file:
                zip_file.extractall(extracted_dir)
            logger.info("Export data extracted to '%s'.", extracted_dir)
        except Exception as e:
            logger.error("Failed to extract the export archive: %s", e)
            raise

        # Clean up the archive file
        try:
            os.remove(archive_path)
            logger.info("Temporary archive file '%s' deleted.", archive_path)
        except OSError as e:
            logger.warning("Failed to delete temporary archive file: %s", e)

        return extracted_dir
