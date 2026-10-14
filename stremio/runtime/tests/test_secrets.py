import os
import tempfile
import unittest
from pathlib import Path

from stremio_private.secrets import (
    DotEnvSecretStore,
    FileSecretStore,
    MemorySecretStore,
    SecretStoreError,
    ensure_dotenv_template,
    read_dotenv,
)


class SecretStoreTests(unittest.TestCase):
    def test_file_store_is_mode_0600(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "secrets.json"
            store = FileSecretStore(path)
            store.set("trakt.client_id", "not-a-real-key")
            self.assertEqual(store.get("trakt.client_id"), "not-a-real-key")
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)

    def test_rejects_permissive_secret_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "secrets.json"
            path.write_text("{}", encoding="utf-8")
            os.chmod(path, 0o644)
            with self.assertRaises(SecretStoreError):
                FileSecretStore(path).get("trakt.client_id")

    def test_dotenv_template_is_mode_0600_and_blank(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / ".env"
            ensure_dotenv_template(path)
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            self.assertEqual(read_dotenv(path), {})

    def test_dotenv_overrides_fallback_without_shell_evaluation(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / ".env"
            path.write_text(
                "TRAKT_CLIENT_ID=from-file\nUNKNOWN=$(not-executed)\nTMDB_READ_TOKEN='quoted'\n",
                encoding="utf-8",
            )
            os.chmod(path, 0o600)
            store = DotEnvSecretStore(
                path,
                MemorySecretStore({"trakt.client_id": "fallback"}),
            )
            self.assertEqual(store.get("trakt.client_id"), "from-file")
            self.assertEqual(store.get("tmdb.read_token"), "quoted")


if __name__ == "__main__":
    unittest.main()
