#!/usr/bin/env python3
"""Migrate selected configured addon descriptors without displaying secrets."""

from __future__ import annotations

import json
import os
import sqlite3
import tempfile
import argparse
from pathlib import Path
from urllib.parse import urlsplit


def decode_profile(value: bytes | str) -> dict:
    if isinstance(value, str):
        return json.loads(value)
    for encoding in ("utf-16-le", "utf-8"):
        try:
            return json.loads(value.decode(encoding).rstrip("\x00"))
        except (UnicodeError, json.JSONDecodeError):
            pass
    raise ValueError("unsupported profile encoding")


def descriptors_from_profile(profile: dict, allowed_ids: set[str]) -> list[dict]:
    addons = profile.get("addons", [])
    if isinstance(addons, dict):
        addons = addons.get("addons", addons.get("installed", []))
    result = []
    for addon in addons if isinstance(addons, list) else []:
        if not isinstance(addon, dict):
            continue
        manifest = addon.get("manifest")
        transport_url = addon.get("transportUrl") or addon.get("transportURL")
        if not isinstance(manifest, dict) or not isinstance(transport_url, str):
            continue
        addon_id = manifest.get("id")
        parsed = urlsplit(transport_url)
        if (
            addon_id not in allowed_ids
            or parsed.scheme != "https"
            or not parsed.hostname
            or parsed.username
            or parsed.password
        ):
            continue
        result.append({"transportUrl": transport_url, "manifest": manifest})
    return result


def candidates(allowed_ids: set[str]) -> list[tuple[list[dict], float]]:
    roots = [
        Path.home() / "Library" / "WebKit" / "com.westbridge.stremio5-mac",
        Path.home() / "Library" / "WebKit" / "com.stremio.stremio-shell-macos",
    ]
    found = []
    for root in roots:
        for database in root.glob("WebsiteData/**/LocalStorage/localstorage.sqlite3"):
            try:
                uri = f"file:{database}?mode=ro"
                with sqlite3.connect(uri, uri=True) as connection:
                    row = connection.execute(
                        "SELECT value FROM ItemTable WHERE key = ?", ("profile",)
                    ).fetchone()
                if row:
                    addons = descriptors_from_profile(decode_profile(row[0]), allowed_ids)
                    if addons:
                        found.append((addons, database.stat().st_mtime))
            except (OSError, sqlite3.Error, ValueError):
                continue
    return found


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Migrate explicitly allowlisted configured Stremio addons."
    )
    parser.add_argument(
        "--allow-id",
        action="append",
        default=[],
        help="Exact manifest ID to migrate; repeat for each approved addon.",
    )
    args = parser.parse_args()
    allowed_ids = {value.strip() for value in args.allow_id if value.strip()}
    if not allowed_ids:
        parser.error("at least one --allow-id is required")
    profiles = candidates(allowed_ids)
    if not profiles:
        print("No eligible configured Stremio addons were found.")
        return 1
    addons, _ = max(profiles, key=lambda item: (len(item[0]), item[1]))
    destination = (
        Path.home() / "Library" / "Application Support" / "Stremio Private" / "addons.json"
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary_name = tempfile.mkstemp(prefix=".addons-", dir=destination.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as stream:
            json.dump({"version": 1, "addons": addons}, stream, indent=2)
            stream.write("\n")
        os.chmod(temporary, 0o600)
        os.replace(temporary, destination)
    finally:
        if temporary.exists():
            temporary.unlink()

    print(f"Migrated {len(addons)} configured addons to the private local profile:")
    for addon in addons:
        manifest = addon["manifest"]
        host = urlsplit(addon["transportUrl"]).hostname
        print(f"- {manifest['id']} | {manifest['name']} | {host}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
