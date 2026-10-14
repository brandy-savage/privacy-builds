from __future__ import annotations

import json
import os
import platform
import subprocess
import tempfile
from abc import ABC, abstractmethod
from pathlib import Path


ALLOWED_SECRET_NAMES = frozenset(
    {
        "premiumize.api_key",
        "tmdb.read_token",
        "trakt.client_id",
        "trakt.client_secret",
        "trakt.access_token",
        "trakt.refresh_token",
        "runtime.lan_token",
    }
)

ENV_SECRET_NAMES = {
    "PREMIUMIZE_API_KEY": "premiumize.api_key",
    "TMDB_READ_TOKEN": "tmdb.read_token",
    "TRAKT_CLIENT_ID": "trakt.client_id",
    "TRAKT_CLIENT_SECRET": "trakt.client_secret",
    "TRAKT_ACCESS_TOKEN": "trakt.access_token",
    "TRAKT_REFRESH_TOKEN": "trakt.refresh_token",
    "STREMIO_PRIVATE_LAN_TOKEN": "runtime.lan_token",
}

DOTENV_TEMPLATE = """# Stremio Private credentials. Restart the app after editing.
# Keep this file private (mode 0600). Values are never shown in the GUI.
PREMIUMIZE_API_KEY=
TMDB_READ_TOKEN=
TRAKT_CLIENT_ID=
TRAKT_CLIENT_SECRET=
TRAKT_ACCESS_TOKEN=
TRAKT_REFRESH_TOKEN=
"""


class SecretStoreError(RuntimeError):
    pass


class SecretStore(ABC):
    @abstractmethod
    def get(self, name: str) -> str | None:
        raise NotImplementedError

    @abstractmethod
    def set(self, name: str, value: str) -> None:
        raise NotImplementedError

    def has(self, name: str) -> bool:
        return self.get(name) is not None

    @staticmethod
    def validate_name(name: str) -> None:
        if name not in ALLOWED_SECRET_NAMES:
            raise SecretStoreError(f"Unsupported secret name: {name}")


class MemorySecretStore(SecretStore):
    """Test-only store."""

    def __init__(self, values: dict[str, str] | None = None):
        self._values = dict(values or {})

    def get(self, name: str) -> str | None:
        self.validate_name(name)
        return self._values.get(name)

    def set(self, name: str, value: str) -> None:
        self.validate_name(name)
        self._values[name] = value


def ensure_dotenv_template(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    try:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        os.chmod(path, 0o600)
        return
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        handle.write(DOTENV_TEMPLATE)
        handle.flush()
        os.fsync(handle.fileno())
    os.chmod(path, 0o600)


def read_dotenv(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    mode = path.stat().st_mode & 0o777
    if mode != 0o600:
        raise SecretStoreError(f"Credential .env must have mode 0600, found {mode:04o}")
    values: dict[str, str] = {}
    for line_number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            raise SecretStoreError(f"Malformed credential .env line {line_number}")
        key, value = line.split("=", 1)
        key = key.strip()
        if key not in ENV_SECRET_NAMES:
            continue
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        if value:
            values[ENV_SECRET_NAMES[key]] = value
    return values


class DotEnvSecretStore(SecretStore):
    """Read-only environment/.env overlay in front of the configured backend."""

    def __init__(self, path: Path, fallback: SecretStore):
        self.path = path
        self.fallback = fallback
        self._env_by_secret = {secret: env for env, secret in ENV_SECRET_NAMES.items()}

    def get(self, name: str) -> str | None:
        self.validate_name(name)
        env_name = self._env_by_secret.get(name)
        if env_name:
            process_value = os.environ.get(env_name, "").strip()
            if process_value:
                return process_value
        dotenv_value = read_dotenv(self.path).get(name)
        return dotenv_value if dotenv_value is not None else self.fallback.get(name)

    def set(self, name: str, value: str) -> None:
        self.validate_name(name)
        self.fallback.set(name, value)


class FileSecretStore(SecretStore):
    """Portable fallback using a local file that must remain mode 0600.

    This is intentionally explicit: it does not pretend filesystem permissions
    are encryption. Prefer Keychain on macOS.
    """

    def __init__(self, path: Path):
        self.path = path

    def _read(self) -> dict[str, str]:
        if not self.path.exists():
            return {}
        mode = self.path.stat().st_mode & 0o777
        if mode != 0o600:
            raise SecretStoreError(f"Secret file must have mode 0600, found {mode:04o}")
        data = json.loads(self.path.read_text(encoding="utf-8"))
        if not isinstance(data, dict) or not all(
            isinstance(k, str) and isinstance(v, str) for k, v in data.items()
        ):
            raise SecretStoreError("Secret file is malformed")
        return data

    def get(self, name: str) -> str | None:
        self.validate_name(name)
        return self._read().get(name)

    def set(self, name: str, value: str) -> None:
        self.validate_name(name)
        if not value:
            raise SecretStoreError("Refusing to store an empty secret")
        values = self._read()
        values[name] = value
        self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        fd, temp_name = tempfile.mkstemp(prefix=".secrets-", dir=self.path.parent)
        try:
            os.fchmod(fd, 0o600)
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(values, handle, separators=(",", ":"))
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp_name, self.path)
            os.chmod(self.path, 0o600)
        finally:
            if os.path.exists(temp_name):
                os.unlink(temp_name)


class MacOSKeychainSecretStore(SecretStore):
    """Generic-password records through macOS security(1).

    The password is supplied to security's interactive stdin prompt, never as
    an argument. Secret values are captured on reads and never printed.
    """

    def __init__(self, service: str = "com.local.stremio-private"):
        if platform.system() != "Darwin":
            raise SecretStoreError("macOS Keychain backend is only available on macOS")
        self.service = service

    def get(self, name: str) -> str | None:
        self.validate_name(name)
        result = subprocess.run(
            ["/usr/bin/security", "find-generic-password", "-s", self.service, "-a", name, "-w"],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            check=False,
        )
        if result.returncode == 44:
            return None
        if result.returncode != 0:
            raise SecretStoreError("Keychain lookup failed")
        return result.stdout.rstrip("\n")

    def set(self, name: str, value: str) -> None:
        self.validate_name(name)
        if not value:
            raise SecretStoreError("Refusing to store an empty secret")
        result = subprocess.run(
            [
                "/usr/bin/security",
                "add-generic-password",
                "-U",
                "-s",
                self.service,
                "-a",
                name,
                "-w",
            ],
            input=value + "\n",
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            raise SecretStoreError("Keychain insert failed")


def create_secret_store(backend: str, file_path: Path) -> SecretStore:
    if backend == "keychain":
        return MacOSKeychainSecretStore()
    if backend == "file":
        return FileSecretStore(file_path)
    raise SecretStoreError("Secret backend must be 'keychain' or 'file'")
