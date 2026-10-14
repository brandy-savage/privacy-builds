import unittest

from stremio_private.connectors.premiumize import PremiumizeConnector
from stremio_private.protocol import ResourceRequest
from stremio_private.secrets import MemorySecretStore


class RecordingHttp:
    def __init__(self):
        self.calls = []

    def get_json(self, url, **kwargs):
        self.calls.append((url, kwargs))
        if url.endswith("folder/list"):
            return {
                "status": "success",
                "content": [
                    {
                        "id": "file-1",
                        "name": "personal.mp4",
                        "type": "file",
                        "mime_type": "video/mp4",
                        "link": "https://private.invalid/capability",
                    }
                ],
            }
        return {
            "status": "success",
            "id": "file-1",
            "name": "personal.mp4",
            "link": "https://private.invalid/capability",
        }


class PremiumizeTests(unittest.TestCase):
    def test_key_is_header_only_and_catalog_discards_link(self):
        http = RecordingHttp()
        connector = PremiumizeConnector(
            MemorySecretStore({"premiumize.api_key": "test-secret"}), http
        )
        result = connector.catalog(ResourceRequest("catalog", "movie", "premiumize-cloud", {}))
        url, options = http.calls[0]
        self.assertNotIn("test-secret", url)
        self.assertEqual(options["headers"]["Authorization"], "Bearer test-secret")
        self.assertNotIn("private.invalid", str(result.payload))


if __name__ == "__main__":
    unittest.main()
