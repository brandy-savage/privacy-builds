# Player fallback design

## macOS

The bundled server already detects VLC at
`/Applications/VLC.app/Contents/MacOS/VLC`. The private desktop builder keeps
VLC first, adds a **System Default** target (`/usr/bin/open`), recognizes
Apple-Silicon Homebrew MPV, and leaves Stremio's internal mpv player available.

Order:

1. VLC
2. System Default
3. Internal Stremio/mpv player

The upstream implementation builds a shell command from the stream URL. The
private builder changes this to `execFile` with an argument array so a hostile
URL cannot inject shell syntax.

## Android

The APK already uses `ExternalPlayerContract` with a generic `ACTION_VIEW`
intent and supplies the interoperable extras `return_result`, `startfrom`, and
`position`. It already understands result actions from VLC, MX Player, MPV, and
Vimu.

The private build resolves packages in this order:

1. VLC: `org.videolan.vlc`
2. MX Player Pro: `com.mxtech.videoplayer.pro`
3. MX Player free/ad: `com.mxtech.videoplayer.ad`
4. Android's generic video-player chooser
5. Stremio's internal player remains the in-app fallback

No player APK is bundled or installed. Missing packages are skipped. The
generic chooser is retained so future players continue to work.

## Authentication placeholders

Player selection requires no custom authentication. Premiumize, Trakt, TMDB,
and subtitle credentials are blank by default and are stored only after an
explicit local setup step. No credential is embedded in the desktop app, the
Android APK, a manifest URL, logs, or source files.
