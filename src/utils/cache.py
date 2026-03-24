import time
import aiosqlite
import os

DEFAULT_CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "cache")
DEFAULT_TTL = 86400  # 24 hours


class HttpCache:
    """SQLite-based HTTP response cache with TTL."""

    def __init__(self, cache_dir: str = DEFAULT_CACHE_DIR, ttl: int = DEFAULT_TTL):
        self.db_path = os.path.join(cache_dir, "http_cache.db")
        self.ttl = ttl
        os.makedirs(cache_dir, exist_ok=True)
        self._db = None

    async def _get_db(self) -> aiosqlite.Connection:
        if self._db is None:
            self._db = await aiosqlite.connect(self.db_path)
            await self._db.execute("""
                CREATE TABLE IF NOT EXISTS cache (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    created_at REAL NOT NULL
                )
            """)
            await self._db.commit()
        return self._db

    async def get(self, key: str) -> str | None:
        db = await self._get_db()
        cursor = await db.execute(
            "SELECT value, created_at FROM cache WHERE key = ?", (key,)
        )
        row = await cursor.fetchone()
        if row is None:
            return None
        value, created_at = row
        if time.time() - created_at > self.ttl:
            await db.execute("DELETE FROM cache WHERE key = ?", (key,))
            await db.commit()
            return None
        return value

    async def set(self, key: str, value: str):
        db = await self._get_db()
        await db.execute(
            "INSERT OR REPLACE INTO cache (key, value, created_at) VALUES (?, ?, ?)",
            (key, value, time.time()),
        )
        await db.commit()

    async def clear(self):
        db = await self._get_db()
        await db.execute("DELETE FROM cache")
        await db.commit()

    async def close(self):
        if self._db:
            await self._db.close()
            self._db = None
