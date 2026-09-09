# App

Vite + React + TypeScript. Builds to static files served from cPanel.

Status: **not scaffolded.** Node 20+ is a prerequisite and is not installed on
the current workstation.

---

## Stack

| Concern | Package |
|---|---|
| Map | `maplibre-gl` |
| Tiles from static files | `pmtiles` (protocol registered on MapLibre) |
| Data layers, 3D | `deck.gl` via `MapboxOverlay`, interleaved |
| Drawing | `terra-draw` + its MapLibre adapter |
| Data access | `@supabase/supabase-js` + `@tanstack/react-query` |
| Client state | `zustand` |
| Tables, charts | `@tanstack/react-table`, `@observablehq/plot` |

Observable Plot rather than a new charting library because it is d3-native, so
the existing chart logic ports rather than being rewritten.

---

## Layout

```
src/
  map/
    MapView.tsx          maplibre instance, kept out of React state
    layers/              choropleth · extrusion · h3 · clusters · labels
    pmtiles.ts           protocol registration, source config
    draw.ts              terra-draw wiring, geometry to api.rollup_polygon
  data/
    client.ts            supabase client, anon key only
    queries.ts           attributes · children · metrics · rollup
    types.ts             generated from the api schema
  state/
    url.ts               the view state <-> query string codec
    store.ts             zustand: transient UI only
  panels/
    LayerPanel.tsx       driven by api.metric — no hardcoded layer list
    SelectionPanel.tsx   values with coverage, basis, accuracy attached
    ClusterPanel.tsx     draw, name, save, compare
  export/csv.ts          every value ships with its caveat columns
```

---

## Three rules the current map earned

**1. The layer list is data.** `LAYERS` in `map_template.html` becomes rows in
`gold.metric`, fetched at startup. Adding a layer is an INSERT. `LEVELS` becomes
`geo.level` plus `geo.containment`, so a new city is a data load rather than a
code change.

**2. State lives in the URL.** City, level, metric, period, 3D, selection and
active cluster serialise into the query string, so a link reproduces a view.
`localStorage` keeps only per-user conveniences — panel collapse, label density,
the region-names toggle. The current app persists toggles but cannot share a
view, and sharing a view is most of what a dashboard is for.

**3. A number never appears without its caveat.** `api.attributes` returns
accuracy and basis; `api.rollup_polygon` returns coverage, apportioned share and
the basis used. The panel and the CSV render them beside the value. This is
already the CSV export's behaviour for the boundary-accuracy gap; here it is
uniform.

Carried over unchanged: the **flat-shading guard** (where every value in view
sits within `gold.metric.flat_guard` of the others, shade flat and state the
spread rather than stretching a rounding difference across the palette), the
collision-filtered labels that re-run after the zoom settles, and the
cluster-label rule of one label per *touching group* of a cluster's territories
rather than one overall.

---

## 3D

Extrusion binds to any metric where `gold.metric.extrudable` is true:
`fill-extrusion-height` for the MapLibre path, deck.gl `PolygonLayer` when the
feature count makes SVG-era assumptions untenable, `H3HexagonLayer` for
point-derived aggregates.

Defaults matter here. **2D is the default and 3D is a toggle**, because an
extruded choropleth is a worse chart than a flat one — tall polygons occlude
short ones, perspective foreshortens the back of the scene, and height is read
less accurately than colour. 3D earns its place where the third dimension
carries real meaning (households per km², a price surface) and for giving an
audience a skyline to navigate. The legend states the height metric and its
scale whenever it is on, and the flat-shading guard applies to height as well as
to colour.

---

## Drawing clusters

1. `terra-draw` polygon or freehand, or lasso-select existing units.
2. Geometry to `api.rollup_polygon(geojson, level, metrics, period, 'finest')`.
3. Render the value **with** its coverage and apportioned share.

A drawn cluster spanning ground with no data must read as partial coverage, not
as a small total. When `apportioned_share` is 0 the panel says *exact*; when it
is not, it says *estimated* and names the level the split was made at.

For anything contractual, use a **selection** — whole units, `api.rollup_selection`,
no apportionment. The existing dealership scheme is exactly that: named regions,
not drawn shapes.

---

## Environment

```
VITE_SUPABASE_URL=
VITE_SUPABASE_ANON_KEY=
VITE_TILES_BASE=/tiles
```

The anon key is public by design and safe only because RLS is on for every
table. `service_role` never appears here.
