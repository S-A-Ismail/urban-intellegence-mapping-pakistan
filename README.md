# Pakistan Urban Intelligence Map — how to refresh it

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
  with its **premium cluster areas highlighted** on top. The parent carries the
  dealership name and proposed fee; each highlight carries its area name. There
  is also a **Dealership** data layer colouring whole regions by club.

Select a territory and drop a level and the map **enlarges that territory** —
this is how you get from Karachi South down to Clifton and Defence. The
breadcrumb shows what you are zoomed into and lets you clear it.

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
· scope: geography and population only — no fee, quota or revenue figure is read
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
area, /km² for density, % for rates. There is no currency formatter, because the
map carries no monetary figure.

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
| Lahore | tehsils (10) → localities (801) → neighbourhoods (191) | 5 of 10 tehsils | see the vintage warning below |
| Peshawar | territories (4) → tehsils (7) → neighbourhoods (5) | territories | groups built by unioning OSM tehsils |
| Multan | tehsils (4) | tehsils | no OSM neighbourhood layer exists |
| Islamabad | ICT (whole) → neighbourhoods (32) | whole city | the urban/rural split is not a boundary |

---

## Known data limitations, all carried in the UI

- **Karachi district shapes** are crosswalked from a 2022 town layer. Total area
  is within 10% of census, but four districts vary individually (East +47%,
  West −47%, Malir +27%, South −20%). Statistics are exact; shapes approximate.
- **Lahore tehsil shapes are a different administrative vintage.** The ten 2024
  tehsils partition the same district as the five 2023 census tehsils, so a
  same-named outline is a *fraction* of its census unit — post-2024 Shalimar is
  23 km² against the census unit's 272 km². The figures shown are exact for the
  census tehsil; the outline is not that tehsil. The five 2024 tehsils with no
  census counterpart carry no statistics at all.
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
