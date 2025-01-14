"""
GeneralCache Module
===================

This module provides a lightweight SQLite-based caching system for storing and retrieving
key-value pairs within a specified namespace (prefix). It is useful for reducing redundant
operations, such as repeated API calls or computation.

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

SQLite Schema:
--------------
The cache is stored in a single table with the following structure:
- `prefix` (TEXT): The namespace for the cached value.
- `key` (TEXT): The unique key within the namespace.
- `id` (INTEGER): The cached value (e.g., an ID or similar data).
- Primary Key: Combination of `prefix` and `key`.

"""
import logging
import sqlite3

logger = logging.getLogger(__name__)

class GeneralCache:
    def __init__(self, db_path="cache.db"):
        self.db_path = db_path
        self._initialize_db()

    def _initialize_db(self):
        """Ensure the cache table exists."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS cache (
                    prefix TEXT,
                    key TEXT,
                    id INTEGER,
                    PRIMARY KEY (prefix, key)
                )
            """)
            conn.commit()

    def get(self, prefix, key):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM cache WHERE prefix = ? AND key = ?", (prefix, key))
            result = cursor.fetchone()
            return result[0] if result else None

    def save(self, prefix, key, tmdb_id):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT OR REPLACE INTO cache (prefix, key, id) VALUES (?, ?, ?)", (prefix, key, tmdb_id))
            conn.commit()

    def clear(self, namespace=None):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            if namespace:
                cursor.execute("DELETE FROM cache WHERE namespace = ?", (namespace,))
            else:
                cursor.execute("DELETE FROM cache")
            conn.commit()
