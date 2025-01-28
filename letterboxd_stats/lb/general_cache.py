"""
GeneralCache Module
===================

This module provides a lightweight SQLite-based caching system for storing and
retrieving key-value pairs within a specified namespace (prefix). It is useful
for reducing redundant operations, such as repeated API calls or computation.

Classes:
--------
- GeneralCache: Manages a persistent cache using an SQLite database.

Features:
---------
1. **Persistent Caching**:
   - Stores cached values in an SQLite database to persist data across application runs.

2. **Namespace Support**:
   - Organizes cached values into namespaces (prefixes) for better separation and management.

3. **Basic CRUD Operations**:
   - `get`: Retrieve a cached value.
   - `save`: Store or update a value in the cache.
   - `clear`: Remove entries from the cache, either globally or within a specific namespace.

"""
import logging
import sqlite3
import time

logger = logging.getLogger(__name__)


class GeneralCache:
    """
    A lightweight SQLite-based caching system for managing key-value pairs across namespaces.

    Attributes:
    -----------
    - db_path (str): The path to the SQLite database file. Defaults to "cache.db".

    Notes:
    ------
    - Cached data is stored in a table named `cache` with the following schema:
      - `prefix` (TEXT): Namespace for the cache entry.
      - `key` (TEXT): Unique key within the namespace.
      - `id` (INTEGER): Cached value associated with the key.
      - Primary Key: Combination of `prefix` and `key`.
    - The `clear` method supports partial or full cache clearing.

    Example Usage:
    --------------
    ```python
    cache = GeneralCache("my_cache.db")

    # Save a value
    cache.save("movies", "inception", 12345)

    # Retrieve the value
    movie_id = cache.get("movies", "inception")
    print(movie_id)  # Output: 12345

    # Clear the cache for a specific namespace
    cache.clear("movies")

    # Clear the entire cache
    cache.clear()
    ```
    """
    def __init__(self, db_path="cache.db"):
        self.db_path = db_path
        self._initialize_db()

    def _initialize_db(self):
        """Ensure the cache table exists."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS cache (
                    prefix TEXT,
                    key TEXT,
                    id INTEGER,
                    timestamp REAL,
                    PRIMARY KEY (prefix, key)
                )
                """
            )
            conn.commit()

    def get(self, prefix, key, timeout=None):
        """Basic CRUD Operation: READ"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, timestamp FROM cache WHERE prefix = ? AND key = ?",
                (prefix, key),
            )
            result = cursor.fetchone()
            if result:
                cached_id, timestamp = result
                if timeout is not None:
                    current_time = time.time()
                    if current_time - timestamp > timeout:
                        # Cache expired, remove the entry
                        self.clear(prefix, key)
                        return None
                return cached_id
            return None

    def save(self, prefix, key, tmdb_id):
        """Basic CRUD Operation: CREATE/UPDATE"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            current_time = time.time()
            cursor.execute(
                "INSERT OR REPLACE INTO cache (prefix, key, id, timestamp) VALUES (?, ?, ?, ?)",
                (prefix, key, tmdb_id, current_time),
            )
            conn.commit()

    def clear(self, prefix=None, key=None):
        """
        Remove entries from the cache.

        Parameters:
        - prefix (str, optional): Namespace for the cache entry.
        - key (str, optional): Specific key to clear within the namespace.
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            if prefix and key:
                cursor.execute(
                    "DELETE FROM cache WHERE prefix = ? AND key = ?", (prefix, key)
                )
            elif prefix:
                cursor.execute("DELETE FROM cache WHERE prefix = ?", (prefix,))
            else:
                cursor.execute("DELETE FROM cache")
            conn.commit()
