# Pakistan Urban Intelligence Map

**[Viewing](#just-viewing-it) · [Deploying](#deploying-it) ·
[Refreshing the numbers](#refreshing-the-numbers--the-usual-case) ·
[Editing the clustering](#changing-the-dealership-clustering) ·
[Editing the map](#changing-the-look-the-layers-or-the-wording) ·
[Rebuilding boundaries](#rebuilding-the-boundaries--rarely) ·
[Data limitations](#known-data-limitations-all-carried-in-the-ui) ·
[How this was built](#how-this-was-built-step-by-step)**


Five cities: **Karachi, Lahore, Islamabad, Peshawar, Multan**, drawn from
`Dealership_Model.xlsx`.

**Scope: geography, population, and one price.** Nothing commercial is read from
the workbook — no quota, pump point, revenue, profit or payback figure, and not
the model's derived fee schedule either. The map does carry the **proposed entry
fee** per dealership (the two-tier Rs 1.5 Cr / Rs 1 Cr proposal), hand-entered in
`dealership_clusters.json` and labelled *proposed* everywhere it appears.

Because a price is in the page, **treat the built HTML as commercially
sensitive** when hosting it — see the password-protection step if you put it on a
public server.

## Just viewing it

Open `pakistan_urban_map.html` in any browser. Everything is embedded except
the D3 library, which loads from a CDN, so you need internet the first time.

If the page is already open and looks stale, hard-refresh it:
**Ctrl + Shift + R** (Windows) or **Cmd + Shift + R** (Mac). A normal F5 will
often serve the cached copy.

### What you can do in it

- **City** — all of Pakistan, or drill into any of the five.
- **Geographic level** — how far down each city goes. Karachi reaches
  neighbourhoods (Clifton, Defence, the DHA phases); Lahore reaches its 801
  localities; Multan stops at tehsil because no finer open boundary exists.
- **Year** — every population, household and density layer switches between
  **2023 census** (official) and **2026 projected** (derived). The provenance
  tag in the legend changes with it, and the panels no longer shift when you
  toggle.
- **Data layer** — nine census layers: population, density, growth, households,
  new households, new-housing intensity, population added, household size, area.
- **Download CSV** — bottom of the right panel. Exports exactly what is on
  screen: current city, level and year, one row per shape, with every population
  column plus the boundary-accuracy gap and its reason.
- **Collapsible panels** — drawer handles at the map edges, or `[` and `]`, or
  `f` to hide both for presenting. The map re-fits into the space.
- **Dealership clusters** — a geographic level in every city. Each dealership's
  **parent territory** (the census regions it covers) is shaded in its colour,
  with its **premium cluster areas highlighted** on top. By default the map
  labels only the dealership; a **Region names** toggle adds the area names,
  which the side panel lists in full either way. A **Premium areas** toggle
  switches between *Highlighted*, where the premium areas are picked out on top
  of the territory, and *Merged*, where they take the dealership's own colour so
  each territory reads as one shape. Merged areas stay named and hoverable. No
  price appears on the map — the proposed fee is in the panel and the CSV. There is also a **Dealership** data layer colouring
  whole regions by club.

The map labels each territory with its **dealership code only** — `KHI-1`,
`LHE-2` — since the panel already names everything. A dealership that holds
separated territories is labelled on each of them: LHE-1 appears twice, on
Lahore Cantt and on Raiwind, while territories that touch are labelled once
between them.

Lahore's dealerships are **LHE-1 Cantt & Shalimar**, **LHE-2 City & Raiwind**
(Rs 1.25 Cr each) and **LHE-3 Model Town** (Rs 1.00 Cr). That pairing differs
from the workbook's, and comes from the `regions` list in
`dealership_clusters.json`, which overrides the sheet. Enclaves follow their
parent region and the territory counts are recomputed to match, so nothing is
left pointing at the old grouping. Edit `name`, `regions` or
`proposed_fee_pkr` there to change any of it.

Select a territory and drop a level and the map **enlarges that territory** —
this is how you get from Karachi South down to Clifton and Defence. The
breadcrumb shows what you are zoomed into and lets you clear it.

---

## Deploying it

The map is **one self-contained file**. No server-side code, no database, no
Node — any static host serves it. These steps are for cPanel; adapt freely.

### 1. Upload

cPanel → **File Manager** → `public_html`. Create a folder `map` and upload
`pakistan_urban_map.html` into it.

### 2. Give it a clean URL and turn on compression

Create `.htaccess` inside `public_html/map/`:

```apache
DirectoryIndex pakistan_urban_map.html

# 1.00 MB -> 0.22 MB on the wire
<IfModule mod_deflate.c>
  AddOutputFilterByType DEFLATE text/html application/javascript text/css
</IfModule>

# always serve a fresh copy after you re-upload
<IfModule mod_headers.c>
  <FilesMatch "\.html$">
    Header set Cache-Control "no-cache, must-revalidate"
  </FilesMatch>
</IfModule>
```

The URL becomes `https://yoursite.com/map/`. Both blocks earn their place: gzip
cuts the transfer **79%** because the payload is mostly JSON text, and the
no-cache header means viewers stop needing Ctrl+Shift+R after you push an update.

Using `DirectoryIndex` rather than renaming the file means you never have to
rename anything again after a rebuild.

### 3. Put it behind a password

**Do this.** The page carries the proposed entry fee for all ten dealerships. On
an open URL any prospective dealer can see what every other territory is being
asked to pay.

cPanel → **Directory Privacy** → select `public_html/map` → tick *Password
protect this directory*, name it, then **Create User**. That is HTTP Basic auth,
so pair it with HTTPS or the password crosses the wire in clear text.

### 4. Force HTTPS

cPanel → **SSL/TLS Status** → *Run AutoSSL* (most hosts have this on already),
then add to the top of the same `.htaccess`:

```apache
RewriteEngine On
RewriteCond %{HTTPS} off
RewriteRule ^(.*)$ https://%{HTTP_HOST}%{REQUEST_URI} [L,R=301]
```

### 5. If the host or the viewers block the CDN

The page pulls D3 from `cdnjs.cloudflare.com`. Behind a strict firewall it will
render blank. To vendor it:

1. Download `https://cdnjs.cloudflare.com/ajax/libs/d3/7.8.5/d3.min.js` and
   upload it next to the map.
2. Edit **`map_template.html`** — not the built file — changing line 5's `src`
   to `d3.min.js`.
3. `python refresh.py`, re-upload both files.

Editing the built HTML directly works until the next refresh silently overwrites
it.

### 6. Updating a deployed map

```
python refresh.py
```

Re-upload the single file. With the no-cache header above, viewers get the new
numbers on their next load. cPanel's **FTP Accounts** or SSH make this a
drag-and-drop or a one-line `scp` if you would rather not use File Manager.

---

## Refreshing the numbers — the usual case

You changed a census figure or a growth assumption in `Dealership_Model.xlsx`
and want the map to show it.

```
python refresh.py
```

**No dependencies.** It reads the values Excel caches inside the workbook, so
`openpyxl` is no longer required. Takes about a second. Then hard-refresh the
browser.

You should see:

```
· model data: Dealership_Model.xlsx (22 regions + 7 enclaves, 5 cities, 10 dealerships)
· scope: geography and population — no fee, quota or revenue figure is read from the workbook
· clusters: 10 dealerships, 61 named areas, 43 with an outline
· proposed entry fees carried: Rs 12.00 Cr across the network
· geometry layers: provinces, karachi_towns, ...
✓ pakistan_urban_map.html rebuilt (1.00 MB)
```

**What it reads, all from this folder:**

| File | Required | What it does |
|---|---|---|
| `map_template.html` | yes | the UI — edit this to change look or behaviour |
| `pakistan_urban_geo.json` | yes | the boundaries |
| `Dealership_Model.xlsx` | no | census, projections, and the dealership grouping — nothing commercial |
| `scenario_a.json` | no | fallback if the workbook is absent |
| `census.json` | no | overrides for any census figure |
| `dealership_clusters.json` | no | the clustering scheme — cluster and area names |

Nothing is hardcoded in `refresh.py`. Every census figure and projection comes
from the workbook, so changing an assumption there is the only thing you need to
do.

`refresh.py` ends with a `FORBIDDEN` key check. If an edit ever reintroduces a
quota, revenue or model-derived fee field, the build fails with a message naming
it rather than quietly publishing the model's schedule inside the page. The one
deliberate exception is `proposed_fee_pkr`, listed in `ALLOWED`.

---

## Changing the dealership clustering

The scheme lives in `dealership_clusters.json` — a commercial grouping, not a
census unit, so it is hand-edited rather than read from the workbook.

```json
{ "code": "KHI-1", "proposed_fee_pkr": 15000000,
  "name": "South & Coastal", "city": "Karachi", "premium": true,
  "areas": [ { "label": "Clifton", "prefixes": ["Clifton", "Old Clifton"] } ] }
```

`proposed_fee_pkr` is in PKR and renders as Lakh or Crore. It is the client's own
proposal, **not** the model's derived figure — the two differ (LHE-3 is Rs 1 Cr
proposed against Rs 0.78 Cr derived, KHI-4 Rs 1.5 Cr against Rs 0.93 Cr), so the
UI always says "proposed".

`prefixes` are the outline names that identify the area in the geometry. Matching
is **prefix-anchored, not substring**, so `E-7` cannot pick up "Bahria Town
Phase 7". Outlines are searched in priority order — `city_areas`, then
`lahore_localities`, then `karachi_towns` — and the first layer with a hit wins,
so one place is never drawn twice.

Tehsil and district layers are excluded on purpose. "Lahore Cantt" and "Model
Town" name both a premium neighbourhood and a 100-plus km² administrative
tehsil; matching the tehsil would draw a whole administrative unit as if it were
the cluster area.

An area with no outline anywhere is still listed in the panel, greyed, and
labelled as having none. It is never approximated. `refresh.py` prints the
coverage on every run:

```
· clusters: 10 dealerships, 61 named areas, 43 with an outline
    KHI-1  no outline for: Karachi Cantt
```

Set `"premium": false` and add a `note` for a dealership with no designated
premium cluster — LHE-2 Central Lahore lists representative localities instead.

---

## Changing a census figure

Drop a `census.json` next to the script. It overrides the workbook per region:

```json
{
  "regions": {
    "Malir":       { "pop23": 2500000, "area": 2160 },
    "Multan City": { "hh_size": 6.2 }
  }
}
```

Then `python refresh.py`. Prefer editing the workbook — this is for
what-if testing without touching the model.

---

## Changing the look, the layers, or the wording

Everything visual lives in `map_template.html` — the CSS, the layer definitions,
the tooltips, the side panels. Edit it, run `refresh.py`, done. The two
placeholders `__GEO__` and `__DATA__` are where the data gets injected; leave
those alone.

To add or change a data layer, find the `LAYERS` object. Each entry needs a
label, an accessor, a formatter, a note and a provenance tag (`official`,
`open`, `derived`, `none`). Notes and provenance are functions of the selected
year, so a layer can be official in 2023 and derived in 2026.

To change how far a city drills, edit `LEVELS`.

**Units.** Standard units everywhere — grouped integers for counts, km² for
area, /km² for density, % for rates. The single monetary figure, the proposed
entry fee, goes through `money()` and renders in PKR Lakh and Crore. It appears
in the side panel and the CSV only, never on the map itself.

To add a CSV column, add a `[header, fn]` pair to `CSV_COLS`.

---

## Rebuilding the boundaries — rarely

Only needed when districts or tehsils are actually redrawn.

```
pip install shapely requests
python rebuild_boundaries.py
python refresh.py
```

It downloads the source datasets (cached in `_cache/`, so the second run is
offline), rebuilds every geometry layer, and regenerates
`pakistan_urban_geo.json`.

Sources, all open and attributable:

| Source | Gives |
|---|---|
| HDX/OCHA admin boundaries | provinces, Karachi towns, Multan tehsils, ICT |
| Internal-Lahore-Boundaries | Lahore district, 801 localities, locality points |
| OpenStreetMap via Overpass | Peshawar's 7 tehsils, and the neighbourhood layer |

The Overpass mirrors rate-limit and time out freely. The script retries across
four of them; if one city's neighbourhood query still fails it warns and carries
on with a thinner layer rather than losing the whole rebuild.

`lahore_revenue_estates.json` holds the 363 revenue estates from Punjab Board of
Revenue notification 1058-2024/4496 (27 Aug 2024). If tehsil composition changes
again, edit that file and re-run.

---

## Adding a city

1. `rebuild_boundaries.py` — add the city's polygons as new keys in `out`.
2. `refresh.py` — add it to `CITY_PT` and `CITY_NOTE`.
3. `map_template.html` — add an entry to `LEVELS`.

The census and projection figures come from the workbook automatically as soon
as the city's regions appear in `CensusBase`. No logic needs rewriting.

---

## How far each city drills, and why

| City | Levels | Statistics join | Note |
|---|---|---|---|
| Karachi | districts (7) → towns (18) → neighbourhoods (454) | districts | towns and neighbourhoods are shapes only |
| Lahore | tehsils (5 census) → tehsils (10, 2024) → localities (801) → neighbourhoods (191) | the 5 census tehsils | the 2024 ten are shapes only |
| Peshawar | territories (4) → tehsils (7) → neighbourhoods (5) | territories | groups built by unioning OSM tehsils |
| Multan | tehsils (4) | tehsils | no OSM neighbourhood layer exists |
| Islamabad | ICT (whole) → neighbourhoods (32) | whole city | the urban/rural split is not a boundary |

---

## Known data limitations, all carried in the UI

- **Karachi district shapes** are crosswalked from a 2022 town layer. Total area
  is within 10% of census, but four districts vary individually (East +47%,
  West −47%, Malir +27%, South −20%). Statistics are exact; shapes approximate.
- **Lahore has two tehsil layers, and only one carries statistics.** The five
  2023 census tehsils come from OpenStreetMap and match the census areas within
  2% overall (−6% to +9% each); everything joined to census or dealership data
  uses them. The ten 2024-notification tehsils are a different administrative
  vintage — a same-named outline is a *fraction* of its census unit, post-2024
  Shalimar being 23 km² against 272 km² — so they are kept as their own level
  and carry no statistics.
- **Peshawar territories** are unioned from OSM's seven tehsils. The OSM line
  between Peshawar City and the East Ring differs from the census one
  (+51% and −38%), though the four-territory total is within 6%.
- **Islamabad is not split.** ICT is a single district and the model's
  urban/rural split follows a census classification, not a published boundary.
  Both territories are listed against the whole-city shape.
- **Lahore locality cells** are Voronoi tessellations around points, not
  boundaries.
- **Neighbourhood outlines carry no statistics.** The census publishes nothing
  at that level, so nothing is shaded by value. Enclaves the model prices are
  picked out in gold, and the panel says what share of the priced area the
  outline actually covers — DHA Phase VIII's outline is 42% of the 38 km² it is
  priced on, because Sahil has no open boundary.
- **Enclave house counts are estimates**, not census figures — they come from the
  model's own assumptions and are labelled as such.
- **Near-uniform layers are shaded flat.** Where every value sits within 5% of
  the others — Lahore's household sizes run 6.3 to 6.5, Multan's are all 6.05 —
  a linear ramp would stretch a rounding difference across the whole palette and
  make it look dramatic. Those layers render in one shade with the spread stated
  in the legend. Anything with a real spread is unaffected.

---

## How this was built, step by step

Each step is one commit. `git log --oneline` gives the same list.

### 1. Five cities, on the right anchor — `c18a01a`

The map covered Karachi and Lahore only, and its fee figures were still on the
superseded DHA Phase VIII anchor while the workbook had moved to Islamabad at
Rs 1 Cr — a factor of about 11.7 out.

- **Boundaries sourced** for the three missing cities. Multan's four tehsils came
  from the HDX admin layer and matched the model's names exactly. Peshawar's
  source layer still used the old Town-I–IV structure that does not crosswalk, so
  its seven current tehsils came from OpenStreetMap under the model's own names
  and were unioned into the four commercial territories. Islamabad has no
  published boundary for its urban/rural split, so it stayed whole.
- **`refresh.py` rewritten** to read all 22 census regions, 7 enclaves, 5 city
  rollups and the 2023–2030 projection straight from the workbook, replacing the
  hardcoded dictionaries. It also dropped the `openpyxl` dependency by reading
  the values Excel caches in the sheet XML.
- **Verified against the documented invariants**: Fee Units 100.000, network
  entry fees Rs 10.58 Cr, top line Rs 119.1 Cr, bottom line Rs 24.9 Cr.
- **Drill-down and focus zoom** added, so selecting Karachi South and dropping a
  level enlarges it down to Clifton and Defence.
- **Year toggle** between 2023 census and 2026 projected, with the provenance tag
  changing to match.

### 2. Collapsible panels — `e8e2eb4`

Drawer handles at the map edges, `[` and `]` individually, `f` for both.

The first attempt hid panes with `display:none`, which *unplaces* a grid item —
`#stage` slid into the collapsed column and the map shrank to zero width instead
of expanding. Panes now stay in the grid with the column at `0` and
`overflow:hidden`. Below the 1180px breakpoint they are absolute overlays rather
than grid items, so `display:none` is correct there and is kept.

### 3. Narrowed to geography and population, CSV export — `ed951aa`

Commercial figures were removed from the workbook read, not just from the UI.
Suppressing them in the interface while leaving them in the embedded JSON would
have been false secrecy — the fee schedule would still sit in the page source.
A `FORBIDDEN` key check now fails the build if one reappears.

Also fixed the "map shifts when toggling year" report. The map never moved: the
projection is bit-identical across a toggle. The 2026 year hint wrapped to a
second line where the 2023 one did not, growing 15px and pushing every layer
button down by exactly that. Both panels now hold their height, measured at 0px.

CSV export added — current city, level and year, one row per shape, carrying the
boundary-accuracy gap and its reason so a figure never travels without its
caveat.

### 4. The dealership clustering scheme — `a48dbec`

Ten dealerships, their premium cluster areas, and the parent regions they cover,
in `dealership_clusters.json`.

Area names resolve to outlines by **prefix-anchored** match, after an early
version had `E-7` matching "Bahria Town Phase 7". Tehsil layers are excluded
deliberately: "Lahore Cantt" and "Model Town" each name both a premium
neighbourhood and a 100-plus km² tehsil, and an early pass matched the tehsil.
43 of 61 named areas have an outline; the other 18 are listed greyed rather than
approximated.

### 5. The proposed two-tier fee — `22fed0b`

Rs 1.5 Cr for KHI-1, KHI-4, LHE-1, MUX-1; Rs 1 Cr for the rest. Rs 12.00 Cr
across the network, against the model's derived Rs 10.58 Cr — so it is labelled
*proposed* everywhere, and `proposed_fee_pkr` is the single `ALLOWED` exception
to the build guard.

### 6. Cluster labelling and parent territories — `380ae3d`

The map was labelling outlines with their OSM names — "Clifton Block 5" nine
times over, never saying "Clifton". Outlines are now grouped by cluster area and
labelled once, with the dealership beneath. Each dealership's parent territory is
shaded underneath and the premium areas highlighted on top.

Labels are collision-filtered in screen space under the live zoom, so zooming
reveals more rather than the set being fixed at draw time.

### 7. Region-name toggle, price off the map — `a791f1b`

The panel lists every area, so the map labels only the dealership by default; a
**Region names** toggle brings the area names back. The proposed fee came off the
map entirely — label and tooltip — and stays in the panel and the CSV.

This commit also repaired two edits from step 6 that had silently missed their
target and left a NUL byte in the grouping key, which had been making git and
grep treat `map_template.html` as binary.

### 8. Lahore corrected — `d2f37ad`

Karachi was already right; this is Lahore only.

Lahore's territories were drawn from the ten derived 2024 tehsils, but only five
of those names collide with the five census tehsils the model prices — so the
rest were dropped and **59% of the city rendered blank**, in shapes running −91%
to −15% against census area. OpenStreetMap carries the five census tehsils as
real `admin_level 7` boundaries; those now carry the data, giving full coverage
and **+2% against census area overall**.

Lahore's three club colours had been three adjacent stops off the sequential
ramp — near-identical teals, the darkest invisible at 26% opacity — and were
separated across the hue wheel.

A guard was added for the opposite problem: where every value sits within 5% of
the others, a linear ramp stretches a rounding difference across the whole
palette. Lahore's household sizes run 6.3 to 6.5 and Multan's are all 6.05, so
those shade flat with the spread stated. Karachi's tightest layer spreads 17%, so
nothing there was affected.
