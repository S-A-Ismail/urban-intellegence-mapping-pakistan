# Deployment — cPanel + Supabase

Companion to [ARCHITECTURE.md](ARCHITECTURE.md) §2 and §10.

The split, restated: **cPanel serves bytes. Supabase is the database and the
API. The ETL runs somewhere else entirely.**

---

## What goes where

| Artefact | Lives on | Why |
|---|---|---|
| SPA bundle (`index.html`, hashed JS/CSS) | cPanel `public_html` | static, cacheable, no runtime needed |
| `*.pmtiles` — basemap and per-city geometry | cPanel, or Supabase Storage | single files read by HTTP Range |
| Postgres + PostGIS, Auth, RLS, RPCs | Supabase | the only stateful component |
| Connectors, tile builds, seed loads | GitHub Actions / VPS / workstation | needs a real CPU and GDAL |

---

## Why the ETL cannot run on cPanel

This is not a preference and it is worth being blunt about, because it is the
constraint most likely to be argued with:

- `tippecanoe` needs a C++ toolchain. GDAL and `shapely` need system libraries.
  Neither installs on shared hosting without root.
- CloudLinux LVE caps CPU and memory per account and kills long-running
  processes. A tile build is minutes to tens of minutes of sustained CPU — it
  will be killed, and usually partway through, leaving a truncated `.pmtiles`.
- cPanel cron is coarse and gives no run history, no retries and no secret
  storage. `src.ingest_run` would be recording failures that nobody sees.

GitHub Actions is free at this cadence, gives secrets, logs, retries and a git
sha for `code_version` — which the provenance model needs anyway. Use it.

Node.js app support via Passenger exists on many cPanel installs. Do not rely on
it. The SPA is static precisely so hosting stays boring.

---

## `.htaccess`

Template: [`deploy/htaccess.template`](../deploy/htaccess.template) — copy to
`public_html/.htaccess`.

Four things it must get right:

**1. Never compress `.pmtiles`.** This is the one that will cost an afternoon if
missed. PMTiles works by asking for byte ranges of a large file. `mod_deflate`
compresses the response and the byte offsets no longer mean anything — the map
loads blank or garbled, with no error in the console beyond a failed tile
decode. Exclude the extension explicitly and confirm `Accept-Ranges: bytes` is
coming back.

**2. Serve `.pmtiles` with a known MIME type** and long cache lifetime. The
files are content-addressed by the build, so they can be immutable.

**3. SPA fallback.** Any path that is not a real file rewrites to `index.html`,
or a deep link into a city view 404s.

**4. Do not compress or cache `index.html`.** It carries the hashed asset names;
a cached copy pins the app to an old build.

### Verifying ranges actually work

```bash
curl -sI -H "Range: bytes=0-99" https://example.com/tiles/karachi.pmtiles
```

A working setup returns `206 Partial Content`, `Content-Length: 100` and
`Accept-Ranges: bytes`. A `200` with the whole file, or any `Content-Encoding:
gzip`, means rule 1 is not in effect.

Most cPanel hosts now run **LiteSpeed** rather than Apache. It honours
`.htaccess`, but its own cache module can re-add compression above the rewrite
layer. If ranges fail with a correct `.htaccess`, disable LiteSpeed cache for
the tiles directory before looking anywhere else.

---

## Deploying the app

Two routes; pick one and stay on it.

### cPanel Git Version Control (simplest)

Push to a repo cPanel can pull, and let [`deploy/.cpanel.yml`](../deploy/.cpanel.yml)
copy the built files into `public_html`. Note that cPanel does **not** run the
build — it only copies. So `app/dist/` must be committed on the deploy branch,
or a CI job must build and push it there. A deploy branch carrying built assets
is the pragmatic answer; keep it out of `main`.

### GitHub Actions over SSH (better)

Build in CI, `rsync` the result. Nothing built is committed, the deploy is
atomic if you rsync to a staging directory and swap, and secrets stay in CI.
Requires SSH access, which not every shared plan includes — check before
promising it.

---

## Configuration and secrets

The bundle is static, so anything it needs is baked in at build time:

```
VITE_SUPABASE_URL=https://<project>.supabase.co
VITE_SUPABASE_ANON_KEY=<anon key>
VITE_TILES_BASE=/tiles
```

The **anon key is meant to be public**. It is safe only because RLS is enabled
on every table (`006_rls.sql`) and `anon` is granted nothing — sign-in is
required to read a boundary, let alone a figure. If RLS is ever disabled on a
table "temporarily", the anon key becomes a full read credential for it.

The `service_role` key must never appear in the app, in the repo, or in
`public_html`. It belongs in the ETL runner's secret store and nowhere else.

Keep `.env` files out of `public_html` entirely; the template denies dotfiles as
a backstop, not as the primary control.

---

## Capacity

Rough, and worth checking against the actual plan before committing:

| | Size | Note |
|---|---|---|
| SPA bundle | 1–2 MB gzipped | MapLibre + deck.gl are the bulk |
| Protomaps basemap, 5 cities | 200–600 MB | the largest single item on disk |
| Per-city data geometry | 5–50 MB each | `geo_id` only, no attributes |
| Supabase — census only | well under 500 MB | free tier fits |
| Supabase — with listings/POI | multiple GB | Pro tier, 8 GB |

Two levers if cPanel disk or bandwidth becomes the binding constraint:

- Move `.pmtiles` to **Supabase Storage**, which supports range requests, and
  point `VITE_TILES_BASE` at it. Adds a CORS header requirement.
- Cut the basemap to the five city bounding boxes rather than national coverage.
  This is usually the bigger saving and costs nothing that matters.

---

## Order of operations, first deploy

1. Create the Supabase project. Run `warehouse/schema/001`–`007` in order.
2. Expose **only** the `api` schema (Settings → API → Exposed schemas). Leave
   `geo`, `gold`, `src`, `app` unexposed.
3. Seed geography and census (§9 of ARCHITECTURE.md), then
   `select geo.rebuild_containment();`.
4. Check the guards: `select * from geo.v_crosswalk_check where not ok;` must
   return zero rows.
5. Build the tiles, upload to `public_html/tiles/`.
6. Verify a byte-range request returns `206` before touching the app at all.
7. Build the SPA, deploy, create the first org and member row.

Step 6 before step 7 saves debugging a blank map against two possible causes at
once.
