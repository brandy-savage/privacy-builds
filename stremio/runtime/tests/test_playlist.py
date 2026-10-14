import tempfile
import unittest
from pathlib import Path

from stremio_private.connectors.playlist import LocalPlaylistConnector
from stremio_private.protocol import ResourceRequest


class PlaylistTests(unittest.TestCase):
    def test_accepts_only_allowlisted_credential_free_https(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "channels.m3u"
            path.write_text(
                """#EXTM3U
#EXTINF:-1 tvg-name="Allowed",Allowed
https://media.example/live.m3u8
#EXTINF:-1 tvg-name="Wrong host",Wrong host
https://tracker.example/live.m3u8
#EXTINF:-1 tvg-name="Token query",Token query
https://media.example/live.m3u8?token=secret
#EXTINF:-1 tvg-name="Clear text",Clear text
http://media.example/live.m3u8
""",
                encoding="utf-8",
            )
            connector = LocalPlaylistConnector((path,), ("media.example",))
            result = connector.catalog(
                ResourceRequest("catalog", "tv", "local-authorized-tv", {})
            )
            self.assertEqual([item["name"] for item in result.payload["metas"]], ["Allowed"])


if __name__ == "__main__":
    unittest.main()
