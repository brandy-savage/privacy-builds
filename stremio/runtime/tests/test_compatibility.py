import unittest

from stremio_private.connectors.compatibility import (
    CompatibilityProxyConnector,
    CompatibilityTarget,
)
from stremio_private.protocol import ResourceRequest


class RecordingHttp:
    def __init__(self):
        self.calls = []

    def get_json(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return {"metas": []}


class CompatibilityTests(unittest.TestCase):
    def test_rejects_secret_bearing_target_url(self):
        with self.assertRaises(ValueError):
            CompatibilityTarget(
                id="bad",
                base_url="https://example.invalid/config?key=secret",
                allowed_host="example.invalid",
                resources=frozenset({"catalog"}),
            )

    def test_rejects_opaque_config_path(self):
        with self.assertRaises(ValueError):
            CompatibilityTarget(
                id="bad-path",
                base_url="https://example.invalid/opaque-config-uuid",
                allowed_host="example.invalid",
                resources=frozenset({"catalog"}),
            )

    def test_fixed_allowlisted_forward(self):
        http = RecordingHttp()
        target = CompatibilityTarget(
            id="public",
            base_url="https://example.invalid",
            allowed_host="example.invalid",
            resources=frozenset({"catalog"}),
            catalogs=({"type": "movie", "id": "top", "name": "Top"},),
        )
        connector = CompatibilityProxyConnector(target, http)
        connector.catalog(ResourceRequest("catalog", "movie", "top", {"skip": "20"}))
        url, options = http.calls[0]
        self.assertEqual(url, "https://example.invalid/catalog/movie/top/skip=20.json")
        self.assertEqual(options["allowed_host"], "example.invalid")


if __name__ == "__main__":
    unittest.main()
