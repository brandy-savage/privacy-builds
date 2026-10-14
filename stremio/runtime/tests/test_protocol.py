import unittest

from stremio_private.protocol import cache_control, parse_resource_path


class ProtocolTests(unittest.TestCase):
    def test_parses_catalog_extras(self):
        request = parse_resource_path(
            "/catalog/movie/private/genre%3DDrama%26skip%3D100.json"
        )
        self.assertIsNotNone(request)
        self.assertEqual(request.resource, "catalog")
        self.assertEqual(request.id, "private")
        self.assertEqual(request.extra, {"genre": "Drama", "skip": "100"})

    def test_parses_colon_id(self):
        request = parse_resource_path("/stream/movie/pm%3Aabc.json")
        self.assertEqual(request.id, "pm:abc")

    def test_rejects_unknown_resource(self):
        self.assertIsNone(parse_resource_path("/evil/movie/id.json"))

    def test_cache_control(self):
        self.assertEqual(
            cache_control(30, 60, 90),
            "max-age=30, stale-while-revalidate=60, stale-if-error=90",
        )


if __name__ == "__main__":
    unittest.main()
