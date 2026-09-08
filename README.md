# Pakistan Urban Intelligence Map — how to refresh it

Five cities: **Karachi, Lahore, Islamabad, Peshawar, Multan** — 29 territories,
10 dealerships, drawn from `Dealership_Model.xlsx`.

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
  **2023 census** (official) and **2026 projected** (derived, the model's
  pricing base year). The provenance tag in the legend changes with it.
- **Data layer** — six census layers, seven dealership-model layers, and three
  deliberately disabled slots where no attributable dataset exists.

Select a territory and drop a level and the map **enlarges that territory** —
this is how you get from Karachi South down to Clifton and Defence. The
breadcrumb shows what you are zoomed into and lets you clear it.

---

## Refreshing the numbers — the usual case

You changed something in `Dealership_Model.xlsx` (an assumption, the anchor, a
house-share) and want the map to show it.

```
python refresh.py
```

**No dependencies.** It reads the values Excel caches inside the workbook, so
`openpyxl` is no longer required. Takes about a second. Then hard-refresh the
browser.

You should see:

```
· model data: Dealership_Model.xlsx (22 regions + 7 hyper markets, 5 cities)
· anchor: scenario A — Islamabad at Rs 1.00 Cr (rate PKR 1,058,239 / Fee Unit)
· geometry layers: provinces, karachi_towns, ...
✓ pakistan_urban_map.html rebuilt (1.00 MB)
```

**What it reads, all from this folder:**

| File | Required | What it does |
|---|---|---|
| `map_template.html` | yes | the UI — edit this to change look or behaviour |
| `pakistan_urban_geo.json` | yes | the boundaries |
| `Dealership_Model.xlsx` | no | the whole model — census, projections, fees, quotas, economics |
| `scenario_a.json` | no | fallback if the workbook is absent |
| `census.json` | no | overrides for any census figure |

Nothing is hardcoded in `refresh.py` any more. Every census figure, projection
and commercial number comes from the workbook, so changing an assumption there
is the only thing you need to do.

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
area, /km² for density, % for rates. Money is the one exception and uses PKR
Lakh and Crore, via the `money()` helper. Do not format money any other way.

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
2. `refresh.py` — add it to `CITY_PT`, `CITY_GEO` and `CITY_NOTE`.
3. `map_template.html` — add an entry to `LEVELS`.

The census, projection and commercial figures come from the workbook
automatically as soon as the city's regions appear in `CensusBase`. No logic
needs rewriting.

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
- **Housing price, price growth and project counts** have no attributable open
  dataset. Those layers are deliberately disabled rather than estimated.
