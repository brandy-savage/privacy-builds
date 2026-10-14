# Downloads and Obtainium

Compiled files are published as assets on a manual GitHub prerelease. They are
not stored in Git and are not produced by CI/CD.

## Before installing

- These builds are experimental and may simply not work.
- The Android packages retain the upstream package IDs but use local signing
  certificates. They normally cannot replace official installs in place.
- Removing an official app can remove its local data.
- Facebook and Stremio are split APK sets packaged as ZIP files. Installation
  support depends on the installer and device.
- Stremio desktop is an ad-hoc-signed macOS archive, not a notarized product
  release made for other machines.

## Obtainium import

Obtainium can follow APK assets published on GitHub Releases. Import
`obtainium.json` from Obtainium's Import/Export screen. Each entry filters the
shared release down to one app's asset.

This is a best-effort convenience. Multiple apps in one GitHub repository and
ZIP-packaged split APKs have changed across Obtainium versions. If an entry
doesn't import or selects the wrong asset, add the repository manually and use
the same release-title and asset-name filters shown in the JSON.

The import does not grant access to any account and contains no credentials.

Obtainium documentation:

- https://wiki.obtainium.imranr.dev/deep_links/
- https://wiki.obtainium.imranr.dev/sources/

## Manual release process

For now, releases are intentionally manual:

1. Build and test locally.
2. Scan expanded archives for credentials and identifying paths.
3. Record SHA-256 hashes in `SHA256SUMS`.
4. Create a GitHub prerelease and attach the binaries plus `SHA256SUMS`.
5. Update the versions and filters here if filenames change.

Do not add signing keys, `.env` files, personal addon manifests, account
profiles, or vendor APKs that have not been modified for this experiment.
