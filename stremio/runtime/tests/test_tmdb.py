import unittest

from stremio_private.connectors.tmdb import TMDBConnector
from stremio_private.protocol import ResourceRequest
from stremio_private.secrets import MemorySecretStore


class RecordingHttp:
    def __init__(self):
        self.calls = []

    def get_json(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return {
            "results": [
                {
                    "id": 42,
                    "title": "Example",
                    "release_date": "2025-01-01",
                    "poster_path": "/poster.jpg",
                }
            ]
        }


class TMDBTests(unittest.TestCase):
    def test_read_token_is_header_only(self):
        http = RecordingHttp()
        connector = TMDBConnector(
            MemorySecretStore({"tmdb.read_token": "private-token"}),
            http,
            region="US",
            providers=(("netflix", "Netflix", 8),),
        )
        result = connector.catalog(
            ResourceRequest("catalog", "movie", "tmdb-provider-netflix-movies", {})
        )
        url, options = http.calls[0]
        self.assertNotIn("private-token", url)
        self.assertNotIn("api_key", options["query"])
        self.assertEqual(options["headers"]["Authorization"], "Bearer private-token")
        self.assertEqual(result.payload["metas"][0]["id"], "tmdb:movie:42")


if __name__ == "__main__":
    unittest.main()
