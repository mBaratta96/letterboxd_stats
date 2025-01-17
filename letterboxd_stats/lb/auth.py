"""
LBAuth Module
=============

This module provides the `LBAuth` class, which handles user authentication and
tokens for Letterboxd.

Classes:
--------
- LBAuth: Manages user authentication and session handling for authenticated operations.


Features:
---------
1. **Session Management**:
   - Initializes an HTTP session upon instantiation.
   - Automatically fetches cookies and prepares the session for interaction with Letterboxd.

2. **User Authentication**:
   - Handles login using a username, password, and CSRF token.
   - Tracks the login state through the `logged_in` attribute.

3. **CSRF Token Management**:
   - Retrieves the CSRF token from session cookies for secure API calls.

"""

import logging

import requests

from .utilities import LB_BASE_URL, LOGIN_URL

logger = logging.getLogger(__name__)
class LBAuth:
    """
    Manages user authentication and session handling for Letterboxd.

    Example:
    --------
    ```python
    auth = LBAuth(username="user", password="pass")
    auth.login()
    print(auth.logged_in)  # Output: True
    ```
    """
    def __init__(self, username=None, password=None, session=None):
        self.session = session or requests.Session()

        self.username = username
        self.password = password

        self.logged_in = False

        # Initialize session by fetching cookies
        try:
            response = self.session.get(LB_BASE_URL)
            response.raise_for_status()
            logger.info("Session initialized with Letterboxd.")
        except requests.RequestException as e:
            logger.error("Failed to initialize session with Letterboxd: %s", e)
            raise


    def login(self):
        """Logs the LBAuth Session into Letterboxd using the class credentials.
        """
        if not self.username or not self.password:
            logger.error("Login attempted without username or password.")
            raise ValueError("Username and password must be provided to log in.")

        # Prepare login payload
        payload = {
            "username": self.username,
            "password": self.password,
            "__csrf": self.get_csrf_token(),
        }

        try:
            response = self.session.post(LOGIN_URL, data=payload)
            response.raise_for_status()
        except requests.RequestException as e:
            logger.error("Login request failed: %s", e)
            raise

        # Check the login result
        login_result = response.json().get("result")
        if login_result != "success":
            logger.error("Login failed with response: %s", response.json())
            raise ConnectionError("Login failed. Please check your credentials.")

        self.logged_in = True
        logger.info("Successfully logged in as '%s'.", self.username)

    def get_csrf_token(self):
        """Fetch token essential for most authenticated calls to LB"""
        return self.session.cookies.get("com.xk72.webparts.csrf")
