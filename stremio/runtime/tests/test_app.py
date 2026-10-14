import tempfile
import unittest
import json
import os
from pathlib import Path

from stremio_private.app import CompanionApp
from stremio_private.cache import CacheStore
from stremio_private.config import Config
from stremio_private.connectors.base import Connector, ConnectorRegistry, ConnectorResult
from stremio_private.protocol import ResourceRequest
from stremio_private.secrets import MemorySecretStore


class FakeConnector(Connector):
    id = "trakt"

    def __init__(self):
        self.stream_calls = 0

    def catalogs(self):
        return [{"type": "movie", "id": "fake", "name": "Fake"}]

    def catalog(self, request: ResourceRequest):
        if request.id == "fake":
            return ConnectorResult({"metas": [{"id": "tt1", "type": "movie", "name": "One"}]})
        return None

    def stream(self, request: ResourceRequest):
        if request.id.startswith("pm:"):
            self.stream_calls += 1
            return ConnectorResult(
                {"streams": [{"url": "https://example.invalid/private"}]},
                ttl=0,
                stale_seconds=0,
                persist=False,
            )
        return None


class AppTests(unittest.TestCase):
    def build(self, directory: str, *, host: str = "127.0.0.1"):
        config = Config(
            host=host,
            state_dir=Path(directory),
            personal_addons_path=Path(directory) / "addons.json",
        )
        secret_values = {"runtime.lan_token": "local-capability"} if host != "127.0.0.1" else {}
        secret_store = MemorySecretStore(secret_values)
        connector = FakeConnector()
        app = CompanionApp(
            config,
            secret_store,
            CacheStore(Path(directory) / "cache.sqlite3"),
            ConnectorRegistry([connector]),
        )
        return app, connector

    def test_manifest_contains_no_secrets(self):
        with tempfile.TemporaryDirectory() as directory:
            app, _ = self.build(directory)
            response = app.handle("/manifest.json")
            self.assertEqual(response.status, 200)
            self.assertNotIn("local-capability", str(response.body))
            app.close()

    def test_private_addon_index_and_virtual_manifest(self):
        with tempfile.TemporaryDirectory() as directory:
            app, _ = self.build(directory)
            index = app.handle("/addons/index.json")
            self.assertEqual(index.status, 200)
            ids = [addon["manifest"]["id"] for addon in index.body["addons"]]
            self.assertIn("local.privacy.stremio.companion", ids)
            self.assertIn("local.privacy.trakt", ids)
            self.assertNotIn("auth", str(index.body).lower())

            manifest = app.handle("/addons/trakt/manifest.json")
            self.assertEqual(manifest.status, 200)
            self.assertEqual(manifest.body["name"], "Private Trakt")
            self.assertEqual(manifest.body["catalogs"][0]["id"], "fake")

            catalog = app.handle("/addons/trakt/catalog/movie/fake.json")
            self.assertEqual(catalog.status, 200)
            self.assertEqual(catalog.body["metas"][0]["name"], "One")
            app.close()

    def test_personal_addons_are_loaded_but_watchhub_is_blocked(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "addons.json"
            path.write_text(json.dumps({"addons": [
                {
                    "transportUrl": "https://example.invalid/config/manifest.json",
                    "manifest": {"id": "example.streams", "name": "Example Streams"},
                },
                {
                    "transportUrl": "https://watchhub.strem.io/manifest.json",
                    "manifest": {"id": "org.stremio.watchhub", "name": "WatchHub"},
                },
            ]}), encoding="utf-8")
            os.chmod(path, 0o600)
            app, _ = self.build(directory)
            index = app.handle("/addons/index.json")
            ids = [addon["manifest"]["id"] for addon in index.body["addons"]]
            self.assertIn("example.streams", ids)
            self.assertNotIn("org.stremio.watchhub", ids)
            app.close()

    def test_addon_status_exposes_flags_but_no_values(self):
        with tempfile.TemporaryDirectory() as directory:
            app, _ = self.build(directory)
            response = app.handle("/addons/status.json")
            self.assertEqual(response.status, 200)
            self.assertEqual(response.body["build"], CompanionApp.BUILD_ID)
            self.assertTrue(response.body["connectors"]["trakt"])
            self.assertIn(".env", response.body["credentials"]["path"])
            self.assertNotIn("local-capability", str(response.body))
            app.close()

    def test_stream_responses_are_not_cached(self):
        with tempfile.TemporaryDirectory() as directory:
            app, connector = self.build(directory)
            first = app.handle("/stream/movie/pm%3Aabc.json")
            second = app.handle("/stream/movie/pm%3Aabc.json")
            self.assertEqual(first.status, 200)
            self.assertEqual(second.status, 200)
            self.assertEqual(connector.stream_calls, 2)
            app.close()

    def test_lan_requires_capability_path(self):
        with tempfile.TemporaryDirectory() as directory:
            app, _ = self.build(directory, host="0.0.0.0")
            self.assertEqual(app.handle("/manifest.json").status, 404)
            self.assertEqual(
                app.handle("/a/local-capability/manifest.json").status,
                200,
            )
            app.close()

    def test_playback_policy_order(self):
        with tempfile.TemporaryDirectory() as directory:
            app, _ = self.build(directory)
            response = app.handle("/policy/playback.json")
            self.assertEqual(response.status, 200)
            self.assertEqual(response.body["macos"], ["vlc", "system", "internal"])
            self.assertEqual(
                response.body["android"],
                ["vlc", "mx_player", "system", "internal"],
            )
            app.close()


if __name__ == "__main__":
    unittest.main()
