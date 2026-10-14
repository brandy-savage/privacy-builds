# Experimental app-stripping builds

This is a small collection of personal experiments that remove or disable
selected permissions, telemetry paths, background components, and integrations
from locally rebuilt applications.

That is the whole claim. These are unofficial binary modifications, not secure
or anonymous replacements for the original apps. Some may fail to install,
launch, authenticate, stream, receive notifications, pass integrity checks, or
update. The changes have mostly been checked with static analysis and limited
local testing; they have not received a security audit.

## What is here

| Project | Baseline | Repository material | Initial binary status |
| --- | --- | --- | --- |
| Facebook for Android | 580.0.0.51.74 | Audit and patch/policy source | Split APK set; not device-tested |
| Messenger for Android | 582.0.0.61.92 | Audit and patch/policy source | arm64 APK; not device-tested |
| Gmail for Android | 2026.10.05.993506826 | Audit and patch/policy source | APK; not device-tested |
| Spotify for Android | 9.1.90.2270 | Audit and patch/policy source | APK; not device-tested |
| Stremio | Desktop 5.1.27, Android 2.4.0, Web commit `9d1d526` | Companion source, desktop builder, Web patch, tests, and sanitized Android/desktop notes | macOS archive and arm64 split APK set; experimental |

The source tree contains only the work added for these experiments and the
notes needed to reproduce or inspect it. It is not a complete source release of
the proprietary upstream applications.

## Downloads

Compiled files are attached to the repository's GitHub Releases instead of
being committed to Git history. Each release includes SHA-256 checksums.

The files are locally signed or ad-hoc signed. Their signatures do not match the
official applications, so Android generally cannot install them over an
official copy. Uninstalling an official app may erase its local data. Do not do
that without a backup.

There is no CI/CD or automated release process yet. The current files were
built and uploaded manually.

## Obtainium

`distribution/obtainium.json` is an experimental Obtainium import for the
Android release assets. See `distribution/README.md` before using it. Split APK
archives and several apps sharing one GitHub repository are edge cases, so the
import is provided as a convenience rather than a promise that updates work.

## Stremio data handling

The committed Stremio files and release archives contain no account profile,
personal addon list, configured addon URL, Premiumize credential, Trakt
credential, TMDB credential, or local signing key. Runtime configuration is
blank and must be supplied by the user outside the application.

## Boundaries

- No guarantee of functionality, privacy, anonymity, completeness, or fitness
  for any purpose.
- No claim about a vendor's intent. Static code presence does not prove a path
  runs for every account, region, device, or experiment cohort.
- No signing keys, account data, or service credentials are published.
- Upstream names and trademarks belong to their owners. This repository is not
  affiliated with or endorsed by them.
- Use only on software, devices, and accounts you are authorized to inspect.

See the per-project notes for the exact edits and known limitations.
