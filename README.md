# Privacy Builds

Research notes and source-level privacy hardening experiments for selected
Android applications and Stremio. The repository contains audits, small policy
layers, tests, rebuild tooling, and a patch against pinned upstream Stremio Web
source.

## Included work

| Project | Baseline | Public material |
| --- | --- | --- |
| Facebook for Android | 580.0.0.51.74 | Static audit and local privacy-control source |
| Messenger for Android | 582.0.0.61.92 | Static audit and local privacy-control source |
| Gmail for Android | 2026.10.05.993506826 | Static audit and local privacy-control source |
| Spotify for Android | 9.1.90.2270 | Static audit and local privacy-control source |
| Stremio | Desktop 5.1.27, Android 2.4.0, Web commit `9d1d526` | Local companion, desktop builder, Web UI patch, tests, and sanitized audits |

## Deliberate exclusions

This repository does **not** distribute APKs, application bundles, vendor
assets, decompiled application trees, signing keys, account profiles, personal
addon inventories, configured service URLs, access tokens, API keys, or local
build artifacts. Obtain upstream applications and open-source dependencies from
their official or otherwise authorized sources, then verify their signatures
and hashes before experimenting.

The Android Java sources here are policy-layer excerpts from local experiments,
not turnkey vendor-app source trees. The audits explain the injection points and
limitations. Re-signing vendor applications can break updates, authentication,
DRM, push delivery, or integrity checks.

## Stremio

The Stremio directory is the most reproducible project:

- `runtime/` is a dependency-free, loopback-only companion with credential
  isolation, caching, and narrow connector boundaries.
- `desktop/build_private_desktop.py` patches a locally installed macOS copy and
  bundles a locally built Web UI and companion runtime.
- `webui/stremio-private.patch` applies to upstream Stremio Web commit
  `9d1d526591b4c076c7307a1ba9ec056d483f169a`.
- `reports/` contains sanitized desktop, Android, player, and Web UI findings.

Personal Stremio credentials belong in the runtime's external mode-`0600`
configuration. Never commit `.env`, `addons.json`, profile databases, or a built
application. The migration helper requires explicit `--allow-id` values and
prints no private transport URLs.

## Scope and ethics

Use these materials only with applications, devices, and accounts you are
authorized to inspect. Findings are primarily static-analysis results: code
presence and wiring do not prove that a feature runs for every account, region,
or experiment cohort. Treat aggressive interpretations as threat-model inputs,
not statements of vendor intent.

See each project's audit for version-specific evidence and caveats.
