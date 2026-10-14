# Stremio Private desktop builder

This builds a separate, ad-hoc-signed personal copy of the installed macOS app.
It never edits `/Applications/Stremio.app` in place.

The current patch set:

- binds HTTP and HTTPS streaming listeners to `127.0.0.1`;
- advertises only the loopback streaming URL;
- disables SSDP and mDNS casting discovery by default;
- disables request logging and removes query strings from diagnostic logs;
- keeps VLC as the first external-player option;
- adds System Default as a fallback player and recognizes Apple Silicon
  Homebrew's `mpv` path;
- replaces shell-command player launching with `execFile` argument arrays;
- removes arbitrary network loads from the native app's ATS exceptions; and
- changes the bundle identity so the private copy is visibly distinct.

Pass `--webui` with a production build of the official open-source Stremio Web
client to bundle and serve that exact UI from loopback.  The builder replaces
the app entry point with a small launcher for the bundled Node runtime, so the
shell no longer fetches mutable UI code from `web.stremio.com`.

Check compatibility without writing anything:

```sh
python3 desktop/build_private_desktop.py --check
```

Build a private copy:

```sh
python3 desktop/build_private_desktop.py \
  --webui /path/to/stremio-web/build \
  --output "$HOME/Applications/Stremio Private.app"
```

The resulting app is ad-hoc signed. macOS may require an explicit first-open
approval because it is not notarized by Stremio's developer. Re-run `--check`
after every upstream Stremio update; the builder aborts if any expected source
pattern changed.

MX Player is Android-only. The Android build uses VLC, MX Player Pro/free,
the system chooser, and the internal player in that order.
