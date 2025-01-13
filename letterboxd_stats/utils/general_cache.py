import sqlite3

class GeneralCache:
    def __init__(self, db_path="general_cache.db"):
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
        """
        Retrieve a cached value.

        Args:
            namespace (str): The namespace (e.g., 'tmdb', 'letterboxd').
            key (str): The key within the namespace.

        Returns:
            str | None: The cached value, or None if not found.
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM cache WHERE prefix = ? AND key = ?", (prefix, key))
            result = cursor.fetchone()
            return result[0] if result else None

    def save(self, prefix, key, tmdb_id):        
        """
        Save a value to the cache.

        Args:
            namespace (str): The namespace (e.g., 'tmdb', 'letterboxd').
            key (str): The key within the namespace.
            value (str): The value to cache.
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT OR REPLACE INTO cache (prefix, key, id) VALUES (?, ?, ?)", (prefix, key, tmdb_id))
            conn.commit()

    def clear(self, namespace=None):
        """
        Clear cache entries.

        Args:
            namespace (str, optional): The namespace to clear. Clears all entries if None.
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            if namespace:
                cursor.execute("DELETE FROM cache WHERE namespace = ?", (namespace,))
            else:
                cursor.execute("DELETE FROM cache")
            conn.commit()