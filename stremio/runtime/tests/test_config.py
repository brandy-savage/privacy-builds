from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from stremio_private import _tomllib_compat
from stremio_private.config import load_config


class ConfigTests(unittest.TestCase):
    def test_compat_parser_handles_shipped_config_shapes(self):
        parsed = _tomllib_compat.loads(
            '''
            [server]
            host = "127.0.0.1"
            port = 17100
            [connectors]
            trakt = true
            [tmdb]
            providers = [
              { id = "netflix", name = "Netflix", provider_id = 8 },
              { id = "max", name = "Max", provider_id = 189 },
            ]
            [playlist]
            files = []
            '''
        )
        self.assertEqual(parsed["server"]["port"], 17100)
        self.assertTrue(parsed["connectors"]["trakt"])
        self.assertEqual(parsed["tmdb"]["providers"][1]["provider_id"], 189)

    def test_load_config(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "config.toml"
            path.write_text('[server]\nhost = "127.0.0.1"\nport = 17100\n')
            config = load_config(path)
            self.assertEqual(config.host, "127.0.0.1")
            self.assertEqual(config.port, 17100)

    def test_load_personal_addons_path(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "config.toml"
            addons_path = Path(directory) / "private-addons.json"
            path.write_text(f'[addons]\nfile = "{addons_path}"\n')
            config = load_config(path)
            self.assertEqual(config.personal_addons_path, addons_path)


if __name__ == "__main__":
    unittest.main()
