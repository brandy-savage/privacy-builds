# Stremio Web privacy patch

Apply `stremio-private.patch` to upstream Stremio Web commit
`9d1d526591b4c076c7307a1ba9ec056d483f169a`:

```sh
git clone https://github.com/Stremio/stremio-web.git
cd stremio-web
git checkout 9d1d526591b4c076c7307a1ba9ec056d483f169a
git apply /path/to/stremio-private.patch
corepack pnpm install --frozen-lockfile
pnpm test -- --runInBand
pnpm build
```

The patch removes the inspected analytics/Sentry path, disables mutable service
worker behavior in local mode, adds local companion/addon integration, removes
WatchHub offers, and exposes connector readiness without secret values.
