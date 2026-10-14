#!/usr/bin/env python3
"""Build a hardened personal copy of the installed macOS Stremio app.

The builder never edits /Applications/Stremio.app in place.  It applies
asserted, version-specific source patches to the bundled server.js, changes the
bundle identity/name, and ad-hoc signs the resulting private copy.
"""

from __future__ import annotations

import argparse
import plistlib
import re
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path


SOURCE_DEFAULT = Path("/Applications/Stremio.app")
RUNTIME_DEFAULT = Path(__file__).resolve().parent.parent / "runtime"


UI_SERVER = r'''"use strict";
const http = require("http");
const fs = require("fs");
const path = require("path");

const root = path.resolve(process.argv[2]);
const port = Number(process.env.STREMIO_PRIVATE_UI_PORT || "18080");
const types = {
  ".css": "text/css; charset=utf-8", ".html": "text/html; charset=utf-8",
  ".ico": "image/x-icon", ".js": "text/javascript; charset=utf-8",
  ".json": "application/json; charset=utf-8", ".png": "image/png",
  ".svg": "image/svg+xml", ".wasm": "application/wasm", ".webp": "image/webp"
};

http.createServer((req, res) => {
  const host = String(req.headers.host || "").split(":")[0];
  if (!['127.0.0.1', 'localhost'].includes(host) || !['GET', 'HEAD'].includes(req.method)) {
    res.writeHead(403).end(); return;
  }
  let pathname;
  try { pathname = decodeURIComponent(new URL(req.url, "http://127.0.0.1").pathname); }
  catch (_) { res.writeHead(400).end(); return; }
  let target = path.resolve(root, "." + pathname);
  if (target !== root && !target.startsWith(root + path.sep)) {
    res.writeHead(404).end(); return;
  }
  if (!fs.existsSync(target) || fs.statSync(target).isDirectory()) target = path.join(root, "index.html");
  fs.readFile(target, (error, body) => {
    if (error) { res.writeHead(404).end(); return; }
    res.writeHead(200, {
      "Content-Type": types[path.extname(target)] || "application/octet-stream",
      "Cache-Control": "no-store", "Referrer-Policy": "no-referrer",
      "X-Content-Type-Options": "nosniff", "X-Frame-Options": "DENY"
    });
    res.end(req.method === "HEAD" ? undefined : body);
  });
}).listen(port, "127.0.0.1");
'''


LAUNCHER = r'''#!/bin/sh
set -eu
HERE=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
UI_PORT=${STREMIO_PRIVATE_UI_PORT:-18080}
RUNTIME_PID=""
for PYTHON in /usr/bin/python3 /opt/homebrew/bin/python3 /usr/local/bin/python3; do
    if [ -x "$PYTHON" ]; then
        PYTHONPATH="$HERE/private-runtime" "$PYTHON" -m stremio_private \
            --config "$HERE/private-runtime/config.toml" serve >/dev/null 2>&1 &
        RUNTIME_PID=$!
        break
    fi
done
"$HERE/node" "$HERE/private-ui-server.js" "$HERE/private-webui" &
UI_PID=$!
cleanup() {
    kill "$UI_PID" 2>/dev/null || true
    [ -z "$RUNTIME_PID" ] || kill "$RUNTIME_PID" 2>/dev/null || true
    wait "$UI_PID" 2>/dev/null || true
    [ -z "$RUNTIME_PID" ] || wait "$RUNTIME_PID" 2>/dev/null || true
}
trap cleanup EXIT HUP INT TERM
"$HERE/StremioPrivate-bin" "--webui-url=http://127.0.0.1:${UI_PORT}/" "$@" &
APP_PID=$!
wait "$APP_PID"
'''


LAUNCHER_SHIM = r'''#include <errno.h>
#include <limits.h>
#include <mach-o/dyld.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

int main(int argc, char **argv) {
    char executable[PATH_MAX];
    uint32_t size = sizeof(executable);
    if (_NSGetExecutablePath(executable, &size) != 0) return 126;
    char *slash = strrchr(executable, '/');
    if (slash == NULL) return 126;
    *slash = '\0';
    char script[PATH_MAX];
    if (snprintf(script, sizeof(script), "%s/StremioPrivate-launcher.sh", executable) >= (int)sizeof(script)) return 126;
    char **args = calloc((size_t)argc + 2, sizeof(char *));
    if (args == NULL) return 126;
    args[0] = "/bin/sh";
    args[1] = script;
    for (int index = 1; index < argc; index++) args[index + 1] = argv[index];
    execv(args[0], args);
    fprintf(stderr, "Stremio Private launcher failed: %s\n", strerror(errno));
    return 126;
}
'''


class PatchError(RuntimeError):
    pass


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise PatchError(f"{label}: expected one match, found {count}")
    return text.replace(old, new, 1)


def patch_server(text: str) -> tuple[str, list[str]]:
    applied: list[str] = []

    replacements = [
        (
            "enginefs.loggingEnabled = !0;",
            "enginefs.loggingEnabled = !1;",
            "disable full request logging",
        ),
        (
            'console.log("Using app path -> " + appPath), enginefs.router.use((function(req, res, next) {',
            '''console.log("Using app path -> " + appPath);
        var privateFs = __webpack_require__(1), privateChild = __webpack_require__(32), privateBundleRoot = path.dirname(path.resolve(process.argv[1])), privateWebRoot = path.join(privateBundleRoot, "private-webui"), privateMime = {
            ".css": "text/css; charset=utf-8", ".html": "text/html; charset=utf-8", ".ico": "image/x-icon",
            ".js": "text/javascript; charset=utf-8", ".json": "application/json; charset=utf-8",
            ".png": "image/png", ".svg": "image/svg+xml", ".ttf": "font/ttf",
            ".wasm": "application/wasm", ".webp": "image/webp", ".woff2": "font/woff2"
        }, privateRuntime = null, privatePython = [ "/usr/bin/python3", "/opt/homebrew/bin/python3", "/usr/local/bin/python3" ].find((candidate => privateFs.existsSync(candidate)));
        privatePython && privateFs.existsSync(path.join(privateBundleRoot, "private-runtime", "stremio_private")) && (privateRuntime = privateChild.spawn(privatePython, [ "-m", "stremio_private", "--config", path.join(privateBundleRoot, "private-runtime", "config.toml"), "serve" ], {
            env: Object.assign({}, process.env, { PYTHONPATH: path.join(privateBundleRoot, "private-runtime"), STREMIO_PRIVATE_PARENT_PID: String(process.pid) }), stdio: "ignore"
        }), privateRuntime.on("error", (() => {})), process.once("exit", (() => {
            try { privateRuntime.kill(); } catch (e) {}
        })));
        enginefs.router.use((function(req, res, next) {
            var host = String(req.headers.host || "");
            if (!/^(?:127\\.0\\.0\\.1|localhost):(?:1147[0-4]|12470)$/.test(host)) return res.writeHead(403), void res.end();
            if (![ "GET", "HEAD" ].includes(req.method)) return next();
            var pathname;
            try { pathname = decodeURIComponent(url.parse(req.url).pathname); } catch (e) { return res.writeHead(400), void res.end(); }
            var relative = /^\\/+$/g.test(pathname) ? "index.html" : pathname.replace(/^\\/+/, ""), target = path.resolve(privateWebRoot, relative);
            if (target !== privateWebRoot && !target.startsWith(privateWebRoot + path.sep) || !privateFs.existsSync(target) || !privateFs.statSync(target).isFile()) return next();
            privateFs.readFile(target, ((error, body) => {
                if (error) return res.writeHead(404), void res.end();
                res.writeHead(200, { "Content-Type": privateMime[path.extname(target)] || "application/octet-stream", "Cache-Control": "no-store", "Referrer-Policy": "no-referrer", "X-Content-Type-Options": "nosniff", "X-Frame-Options": "DENY" }), res.end("HEAD" === req.method ? void 0 : body);
            }));
        })), enginefs.router.use((function(req, res, next) {''',
            "serve the pinned UI and launch the private runtime from the engine",
        ),
        (
            'req.headers.origin.match("(127.0.0.1|localhost):11470$")',
            'req.headers.origin.match("(127.0.0.1|localhost):11470$") || req.headers.origin === "http://127.0.0.1:18080"',
            "allow the pinned loopback UI to reach the engine",
        ),
        (
            "discovery = new Discovery([ SSDPDiscovery, MDNSDiscovery, ExternalDiscovery ])",
            "discovery = new Discovery([ ExternalDiscovery ])",
            "disable SSDP and mDNS discovery",
        ),
        (
            'server.listen(port), server.on("error", (function(err) {\n'
            '            port++ < 11474 ? (console.warn(err), server.listen(port))',
            'server.listen(port, "127.0.0.1"), server.on("error", (function(err) {\n'
            '            port++ < 11474 ? (console.warn(err), server.listen(port, "127.0.0.1"))',
            "bind HTTP server to loopback",
        ),
        (
            "((sserver = https.createServer(app)).listen(12470),",
            '((sserver = https.createServer(app)).listen(12470, "127.0.0.1"),',
            "bind HTTPS server to loopback",
        ),
        (
            ': server.listen(port, (() => {\n'
            "                        listening = !0, cb();",
            ': server.listen(port, "127.0.0.1", (() => {\n'
            "                        listening = !0, cb();",
            "keep restart listener on loopback",
        ),
        (
            'enginefs.baseUrl = "http://" + ip.address() + ":" + server.address().port,',
            "enginefs.baseUrl = enginefs.baseUrlLocal,",
            "advertise loopback instead of LAN address",
        ),
        (
            'url.parse(req.url).path + " " + (req.headers.range || "")',
            'url.parse(req.url).pathname + " " + (req.headers.range || "")',
            "redact query strings if diagnostics are re-enabled",
        ),
        (
            "agent: httpsAgent,",
            'agent: "https:" === dest.protocol ? httpsAgent : void 0,',
            "support loopback HTTP URLs in the media/UI proxy",
        ),
        (
            'path: [ "/usr/local/bin/mpv", "/opt/local/bin/mpv", "/sw/bin/mpv" ]',
            'path: [ "/opt/homebrew/bin/mpv", "/usr/local/bin/mpv", "/opt/local/bin/mpv", "/sw/bin/mpv" ]',
            "recognize Homebrew mpv",
        ),
    ]

    for old, new, label in replacements:
        text = replace_once(text, old, new, label)
        applied.append(label)

    vlc_end = '''            },
            mplayerx: {'''
    system_player = '''            },
            systemDefault: {
                title: "System Default",
                args: [],
                subArg: "",
                timeArg: "",
                playArg: "",
                darwin: {
                    path: [ "/usr/bin/open" ]
                },
                linux: {
                    path: [ "/usr/bin/xdg-open" ]
                },
                win32: {
                    path: [ "cmd.exe" ]
                }
            },
            mplayerx: {'''
    text = replace_once(text, vlc_end, system_player, "add system-default player")
    applied.append("add system-default player")

    declaration = re.compile(
        r'''var wrappedSrc = '"' \+ src \+ '"', subsCmd = subsFile && players\[player\]\.subArg && players\[player\]\.subArg\.length > 0 \? players\[player\]\.subArg \+ subsFile : "", argsCmd = players\[player\]\.args && players\[player\]\.args\.length > 0 \? players\[player\]\.args\.join\(" "\) : "", timeCmd = players\[player\]\.timeArg && players\[player\]\.timeArg\.length > 0 \? players\[player\]\.timeArg \+ parseInt\(time / 1e3\) : "", playCmd = players\[player\]\.playArg && players\[player\]\.playArg\.length > 0 \? players\[player\]\.playArg \+ wrappedSrc : wrappedSrc, fullCmd = playerPaths\[0\] \+ " " \+ timeCmd \+ " " \+ argsCmd \+ " " \+ subsCmd \+ " " \+ playCmd;'''
    )
    safe_declaration = '''var launchArgs = [], timeCmd = players[player].timeArg && players[player].timeArg.length > 0 ? players[player].timeArg + parseInt(time / 1e3) : "", subsCmd = subsFile && players[player].subArg && players[player].subArg.length > 0 ? players[player].subArg + subsFile : "";
                                        timeCmd && launchArgs.push(timeCmd), (players[player].args || []).filter(Boolean).forEach((function(arg) {
                                            launchArgs.push(arg);
                                        })), subsCmd && launchArgs.push(subsCmd), players[player].playArg && players[player].playArg.trim() && launchArgs.push(players[player].playArg.trim()), launchArgs.push(src);'''
    text, count = declaration.subn(safe_declaration, text, count=1)
    if count != 1:
        raise PatchError(f"safe external-player argv: expected one match, found {count}")
    applied.append("build external-player argv without a shell")

    text = replace_once(
        text,
        "child.exec(fullCmd, (function(error) {",
        'child.execFile(playerPaths[0].replace(/"/gi, ""), launchArgs, (function(error) {',
        "launch external players with execFile",
    )
    applied.append("launch external players with execFile")
    return text, applied


def update_plist(path: Path) -> None:
    with path.open("rb") as handle:
        info = plistlib.load(handle)
    info["CFBundleName"] = "Stremio Private"
    info["CFBundleDisplayName"] = "Stremio Private"
    info["CFBundleIdentifier"] = "local.stremio.private"
    info["NSAppTransportSecurity"] = {
        "NSAllowsLocalNetworking": True,
        "NSAllowsArbitraryLoads": False,
        "NSAllowsArbitraryLoadsInWebContent": False,
    }
    with path.open("wb") as handle:
        plistlib.dump(info, handle, sort_keys=False)


def install_local_webui(output: Path, webui: Path, runtime: Path | None) -> None:
    index = webui / "index.html"
    if not index.is_file():
        raise PatchError(f"Web UI does not contain index.html: {webui}")
    macos = output / "Contents/MacOS"
    original_binary = macos / "Stremio"
    # A top-level .well-known directory is only for web deployment and causes
    # codesign --deep to treat it as a malformed nested bundle.
    shutil.copytree(
        webui,
        macos / "private-webui",
        symlinks=True,
        ignore=shutil.ignore_patterns(".well-known"),
    )
    if runtime is not None:
        package = runtime / "src" / "stremio_private"
        config = runtime / "config.example.toml"
        if not package.is_dir() or not config.is_file():
            raise PatchError(f"Private runtime is incomplete: {runtime}")
        runtime_output = macos / "private-runtime"
        shutil.copytree(
            package,
            runtime_output / "stremio_private",
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
        )
        runtime_config = config.read_text(encoding="utf-8").replace(
            "port = 7000", "port = 17100", 1
        )
        (runtime_output / "config.toml").write_text(runtime_config, encoding="utf-8")
    original_url = b"https://web.stremio.com/"
    private_url = b"http://127.0.0.1:11470//"
    binary = original_binary.read_bytes()
    if binary.count(original_url) != 1 or len(private_url) != len(original_url):
        raise PatchError("native Web UI URL: unsupported binary layout")
    original_binary.write_bytes(binary.replace(original_url, private_url, 1))


def build(
    source: Path,
    output: Path,
    *,
    verify_only: bool,
    webui: Path | None = None,
    runtime: Path | None = None,
) -> list[str]:
    server = source / "Contents/MacOS/server.js"
    info = source / "Contents/Info.plist"
    if not server.is_file() or not info.is_file():
        raise PatchError(f"Not a supported Stremio app bundle: {source}")
    original = server.read_text(encoding="utf-8")
    patched, applied = patch_server(original)
    if verify_only:
        return applied
    if output.exists():
        raise PatchError(f"Output already exists; refusing to overwrite: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, output, symlinks=True)
    (output / "Contents/MacOS/server.js").write_text(patched, encoding="utf-8")
    update_plist(output / "Contents/Info.plist")
    if webui is not None:
        install_local_webui(output, webui, runtime)
        applied.append("pin and serve the Web UI from loopback")
        if runtime is not None:
            applied.append("bundle and launch the private companion runtime")
    subprocess.run(
        ["/usr/bin/codesign", "--force", "--deep", "--sign", "-", str(output)],
        check=True,
    )
    subprocess.run(
        ["/usr/bin/codesign", "--verify", "--deep", "--strict", str(output)],
        check=True,
    )
    return applied


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=SOURCE_DEFAULT)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--webui", type=Path, help="Built Stremio Web directory to pin locally")
    parser.add_argument("--runtime", type=Path, default=RUNTIME_DEFAULT, help="Private companion runtime directory")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    if not args.check and args.output is None:
        parser.error("--output is required unless --check is used")
    try:
        applied = build(
            args.source,
            args.output or Path("unused"),
            verify_only=args.check,
            webui=args.webui,
            runtime=args.runtime,
        )
    except (OSError, PatchError, subprocess.CalledProcessError) as exc:
        print(f"build_private_desktop: {exc}", file=sys.stderr)
        return 1
    print(f"Verified {len(applied)} privacy patches." if args.check else f"Built {args.output} with {len(applied)} privacy patches.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
