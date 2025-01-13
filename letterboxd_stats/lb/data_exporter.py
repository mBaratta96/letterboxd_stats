import os
from zipfile import ZipFile
from .utilities import LB_BASE_URL

DATA_EXPORT_URL = LB_BASE_URL + "/data/export"

class LBUserDataExporter:
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

        # Request the export data
        response = self.auth.session.get(DATA_EXPORT_URL)
        if response.status_code != 200 or "application/zip" not in response.headers.get("Content-Type", ""):
            raise ConnectionError(f"Failed to download data. Response headers:\n{response.headers}")

        # Extract filename from headers
        content_disposition = response.headers.get("content-disposition", "")
        if not content_disposition or "filename=" not in content_disposition:
            raise ValueError("Could not determine the filename from the response headers.")
        filename = content_disposition.split("filename=")[-1].strip('";')

        # Ensure the download directory exists
        os.makedirs(download_dir, exist_ok=True)

        # Write the downloaded archive to disk
        archive_path = os.path.join(download_dir, filename)
        with open(archive_path, "wb") as archive_file:
            archive_file.write(response.content)

        # Extract the archive
        extracted_dir = os.path.join(download_dir)
        with ZipFile(archive_path, "r") as zip_file:
            zip_file.extractall(extracted_dir)

        # Clean up the archive file
        os.remove(archive_path)

        return extracted_dir