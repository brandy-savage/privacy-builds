import tempfile
import unittest
from pathlib import Path

from stremio_private.cache import CacheStore


class CacheTests(unittest.TestCase):
    def test_fresh_stale_expired_lifecycle(self):
        with tempfile.TemporaryDirectory() as directory:
            cache = CacheStore(Path(directory) / "cache.sqlite3")
            cache.put("key", {"metas": [{"id": "one"}]}, ttl=10, stale_seconds=20, now=100)
            self.assertEqual(cache.get("key", now=105).state, "fresh")
            self.assertEqual(cache.get("key", now=115).state, "stale")
            self.assertIsNone(cache.get("key", now=131))
            self.assertEqual((Path(directory) / "cache.sqlite3").stat().st_mode & 0o777, 0o600)


if __name__ == "__main__":
    unittest.main()
