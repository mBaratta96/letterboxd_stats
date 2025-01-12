import sqlite3

class TMDBCache:
    def __init__(self, db_path="tmdb_cache.db"):
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

    def get_tmdb_id_from_cache(self, prefix, key):
        """Retrieve a cached TMDB ID."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM cache WHERE prefix = ? AND key = ?", (prefix, key))
            result = cursor.fetchone()
            return result[0] if result else None

    def save_tmdb_id_to_cache(self, prefix, key, tmdb_id):
        """Save a TMDB ID to the cache."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT OR REPLACE INTO cache (prefix, key, id) VALUES (?, ?, ?)", (prefix, key, tmdb_id))
            conn.commit()
