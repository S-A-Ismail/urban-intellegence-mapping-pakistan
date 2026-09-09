# Cenergy / Grundfos Pakistan — Dealership Territory & Fee Model

Agent context. Read before touching anything in this folder.

---

## What this is

Cenergy (with NTS) is the authorised distributor for **Grundfos Gulf Distribution FZE** (JAFZA North, Dubai — *not* Grundfos Holding A/S) in Pakistan. Products: **SCALA2, SOLOLIFT2, UNILIFT**.

This folder holds the model that divides Pakistan's five major cities into dealership territories, prices each one, and sets a per-quarter sales quota. Its outputs feed a dealership agreement drafted elsewhere (`Grundfos Pumps/Docs/Dealership Agreement/`) — the entry fee lands in Part A, the quota in Sales Targets and Reporting, and the territory definition in Appointment and Territory. That agreement is not edited from here.

Cities: **Karachi, Lahore, Islamabad, Peshawar, Multan**. 29 territories, 10 dealerships.

---

## Decided parameters — do not change without being asked

| Parameter | Value |
|---|---|
| **Anchor** | **Islamabad whole city = Rs 1.00 Cr** (Scenario A, active) |
| Rate | PKR 1,058,239 per Fee Unit |
| Alternative anchor (comparison only) | DHA Phase VIII = Rs 1.5 Cr → Scenario B |
| Term | 4 years |
| Pump price | PKR 125,000 |
| Dealer margin | 22% |
| Inventory credit | 50% of fee |
| Whole-city premium | ×1.10 |
| Growth cap | 3.5% (census CAGR capped, floored at 0) |
| Pump life | 9 years |

Scenario B exists only for comparison. Do not present its numbers as live prices.

---

## The formula

```
Fee Units = 45% × new-construction share
          + 35% × replacement-due share
          + 15% × installed-base share
          +  5% × area share          → sums to 100 across all 29 territories

Serviceable pump points (SPP) = houses × 1.2 + flats ÷ 40
Revenue-weighted points (RPP) = SPP × ASP tier

ASP tiers: S Hyper ×8 · A Premium ×3 · B Upper-mid ×1.6 · C Mass ×1.0
Replacement = SPP(2018) × (4-yr term ÷ 9-yr life)
Quota/qtr   = addressable pump points × tier share ÷ 4
Tier shares: S 6% · A 4% · B 1.5% · C 0.3%   (of ALL pump installs, not premium only)
```

**Why pump points, not households:** a bungalow needs 1–2 pump sets; a 200-flat tower needs one booster set for the whole building. Roughly 48:1. Karachi South and Karachi East hold near-identical pump points (321,088 vs 321,502) despite East having 54% more households.

---

## Current output at the chosen anchor

Network **Rs 10.58 Cr** entry fees · top line **Rs 119.1 Cr/yr** · bottom line **Rs 24.9 Cr/yr**

| Code | Dealership | Fee | Quota/qtr |
|---|---|---|---|
| LHE-1 | South Lahore | Rs 1.49 Cr | 508 |
| MUX-1 | Multan | Rs 1.27 Cr | 232 |
| KHI-3 | Central, West & Keamari | Rs 1.24 Cr | 102 |
| KHI-1 | South & Coastal | Rs 1.14 Cr | 398 |
| KHI-2 | East & Korangi | Rs 1.00 Cr | 182 |
| LHE-2 | Central Lahore | Rs 0.97 Cr | 90 |
| KHI-4 | Malir & Outer | Rs 0.93 Cr | 210 |
| ISB-1 | Islamabad | Rs 0.91 Cr | 296 |
| PEW-1 | Peshawar | Rs 0.85 Cr | 158 |
| LHE-3 | West Lahore | Rs 0.78 Cr | 207 |

Notable territories: Karachi South Rs 101.6 L · Lahore Cantt Rs 95.0 L · DHA Phase VIII Rs 12.9 L.

**Known consequence of this anchor:** payback runs 1.2–7.8 months (median 2.7). That is fast for a licence fee. It was chosen deliberately; flag it once if asked to review pricing, then leave it alone.

---

## Files

### Model
| Path | Role |
|---|---|
| `Dealership_Model.xlsx` | **Source of truth.** 11 sheets, 2,494 formulas, 0 errors. |
| `model/build_xlsx2.py` | Rebuilds the workbook from scratch. |
| `model/model_spp.py`, `model_hyper.py`, `model_final.py` | Python implementations used to derive and cross-check the workbook. |

Workbook sheets, in dependency order:
`README → Assumptions → CensusBase → Projection → HyperMarkets → PumpPoints → FeeSchedule → Quotas → Economics → DealerStructure → Visuals`

Only **Assumptions** holds inputs (blue on yellow). Everything else is formulas. Row 41 selects the active scenario.

### Map
Covers all five cities, census 2023 and projected 2026.

**Scope: geography, population, and one price.** Nothing commercial is read from
the workbook — no quota, pump point, revenue, profit or payback figure, and not
the model's derived fee schedule. They are not suppressed in the UI, they are
never extracted, because hiding them in the interface while leaving them in the
page source would be false secrecy. `refresh.py` ends with a `FORBIDDEN` key
check that fails the build if one reaches the output.

Two things come from the commercial side:
- the *structure* — which club covers each region, and the ten clubs on
  DealerStructure (code, name, city, region count). That sheet's fee, quota and
  revenue columns are not read.
- the *proposed entry fee* per dealership, hand-entered in
  `dealership_clusters.json` as `proposed_fee_pkr` — the client's two-tier
  Rs 1.5 Cr / Rs 1 Cr proposal, network Rs 12.00 Cr. It is **not** the model's
  derived schedule (network Rs 10.58 Cr) and the two differ per dealership, so
  the UI always labels it "proposed". It is the sole entry in `ALLOWED`.

**Because a price is in the page, the built HTML is commercially sensitive.**

| Path | Role |
|---|---|
| `pakistan_urban_map.html` | Built artifact. Do not edit directly — it is regenerated. |
| `refresh.py` | **Rebuild command.** Reads the workbook + geo JSON, rewrites the HTML. No dependencies — parses the values Excel caches in the workbook, so openpyxl is not needed. |
| `map_template.html` | The UI. All CSS, layer defs, tooltips, panels. Edit this. |
| `pakistan_urban_geo.json` | 15 geometry layers, all five cities. |
| `scenario_a.json` | Fallback if the workbook is absent. Now holds regions + hyper + cities + meta. |
| `lahore_revenue_estates.json` | 363 revenue estates, Punjab BoR notification 1058-2024/4496 (27 Aug 2024). |
| `rebuild_boundaries.py` | Only when districts/tehsils are redrawn. Downloads sources, caches in `_cache/`. |
| `.claude/launch.json` | Serves the folder on :8765 for previewing. |

**Nothing is hardcoded in `refresh.py`.** Every census figure, projection and
commercial number is read from the workbook, so changing an assumption there is
the only edit needed. `census.json` still overrides per region for what-ifs.

**Drill depth by city** — as far as real geometry allows, no further:

| City | Levels | Stats join |
|---|---|---|
| Karachi | districts (7) → towns (18) → neighbourhoods (454) | districts |
| Lahore | tehsils (5 census) → tehsils (10, 2024) → localities (801) → neighbourhoods (191) | the 5 census |
| Peshawar | territories (4) → tehsils (7) → neighbourhoods (5) | territories |
| Multan | tehsils (4) | tehsils |
| Islamabad | ICT whole → neighbourhoods (32) | whole city |

Selecting a territory and dropping a level enlarges it — that is how you get
from Karachi South to Clifton and Defence.

**Units in the UI:** standard units everywhere — grouped integers for counts,
km² for area, /km² for density, % for rates. The single monetary figure, the
proposed entry fee, uses PKR Lakh and Crore via `money()` — in the side panel and
CSV only, never on the map itself. Do not format money any other way.

**Layers:** population, density, growth, households, new households, new-housing
intensity, population added, household size, area — nine census-derived — plus
**Dealership**, a categorical layer colouring regions by the club covering them.

**Dealership clusters** is a geographic level in every city. It draws two things:
the dealership's **parent territory** (its census regions, shaded at 26% opacity,
labelled with the dealership) and its **premium cluster areas** highlighted on
top at full opacity with a light outline.

Map labels default to the dealership only — the panel already lists every area —
and a **Region names** toggle (`S.regionNames`, persisted) adds the area labels.
A dealership is labelled **once per touching group of its territories**, not once
overall. South Lahore is Lahore Cantt in the east and Raiwind in the south-west
with no shared boundary, so the name belongs on both; Multan's four tehsils do
touch, so it appears once. Centroid distance cannot tell those apart — Multan's
tehsils are large enough that their centres are far apart — so the grouping is a
union-find over **shared boundary vertices**: every adjacent pair in this data
shares 2 to 89, every separated pair shares none.

A **Premium areas** toggle (`S.mergePremium`, persisted) switches between
*Highlighted* and *Merged*. Merged means **same colour**: the premium area takes
the dealership's own shade so the territory reads as one block.

Two details make that work. Painting the premium at the parent's 0.26 opacity is
not enough — two translucent layers stack to about 0.45 and the pocket still
shows through as a brighter patch — so a merged premium is drawn at opacity 0
with `pointer-events:all`, which keeps it hoverable and still able to say which
place it is. Its constituent outlines are also combined into one MultiPolygon
(Karachi's 90 become 14) so `d3.geoPath` draws a single path with no seams, and
it carries no stroke.
The dealership label is exempt from collision suppression: at most five per city,
and a territory going unnamed is worse than a small overlap.

**No price is drawn on the map.** The proposed fee lives in the side panel and
the CSV column only. Defined in
`dealership_clusters.json` (hand-edited; a commercial grouping, not a census
unit, and carrying no fee). Area names resolve to outlines by **prefix-anchored**
match — `E-7` must not swallow "Bahria Town Phase 7" — searching `city_areas`,
then `lahore_localities`, then `karachi_towns`, first hit wins so nothing is
drawn twice. **Tehsil layers are excluded deliberately:** "Lahore Cantt" and
"Model Town" name both a premium neighbourhood and a 100-plus km² tehsil, and
matching the tehsil would draw an administrative unit as the cluster area.
43 of 61 named areas have an outline; the other 18 are listed greyed and never
approximated.

Map labels are collision-filtered in screen space under the live zoom, so
zooming reveals more. The pass re-runs 140ms after the zoom settles.

**Choropleth guard:** where every value in view sits within 5% of the others the
layer is shaded flat, with the spread stated in the legend, rather than letting a
linear ramp stretch a rounding difference across the whole palette. It fires on
household size in Lahore (3.2%), Multan (0%) and Islamabad (0%); Karachi's
tightest layer is 17% so nothing there is affected.

**Club colours:** Karachi's four are deliberately left alone. Lahore's three were
three adjacent stops off the sequential ramp — near-identical teals, the darkest
invisible once shaded back to 26% for a parent territory — and are now separated
across the hue wheel (`#2fb8f0`, `#8b5cf6`, `#34d399`).

**Export:** the panel has a Download CSV button. It exports exactly what is on
screen — current city, level and year, one row per drawn shape — with every
population column plus the boundary-accuracy gap and its reason, so a figure is
never separated from its caveat.

**Panels:** both side panels collapse. Drawer handles at the map edges, `[` and
`]` individually, `f` for both. State persists in localStorage. They collapse by
letting their grid column go to 0 and clipping — `display:none` would unplace the
grid item and slide `#stage` into the collapsed column.

### Documents
| Path | Role |
|---|---|
| `Dealer_Quotas_HyperMarkets.docx` | Quotas, hyper markets, carve-out arithmetic, data-request specs. |
| `Dealer_Fee_Schedule_PumpPoints.docx` | The pump-point method in full. |
| `map_dealership.png` | Pakistan map with per-city treemaps. |
| `_superseded/01–08` | Earlier drafts in build order. Keep. |
| `charts/` | 12 chart PNGs, 170 dpi. |

---

## Commands

```bash
# after changing any assumption in the workbook
python refresh.py                    # rebuilds pakistan_urban_map.html (~1s), no deps

# rebuild the workbook itself from source
python model/build_xlsx2.py
python /path/to/recalc.py Dealership_Model.xlsx 120   # must report 0 errors

# rebuild boundaries (rare — only when admin units are redrawn)
pip install shapely requests
python rebuild_boundaries.py && python refresh.py
```

Browser cache is sticky: hard-refresh with **Ctrl/Cmd + Shift + R**.

---

## Invariants — breaking these breaks the model

1. **One formula, one public source, applied identically.** The entire fairness argument rests on this. No per-territory adjustments, ever.
2. **Fee Units sum to 100** across all 29 territories. If they don't, the normalisation is broken.
3. **Weights sum to 100%.** Assumptions has a check row.
4. **Carve-outs must be subtracted.** A hyper market sold separately reduces its parent's fee *and* quota. Selling without deducting charges twice for the same households. Handled by `SUMIFS` on `HyperMarkets!C` in `PumpPoints`.
5. **Never fabricate a boundary or statistic.** Where data does not exist, the layer is disabled and labelled. Three map layers (price, price growth, project counts) are deliberately dead for this reason.
6. **Quota comes from the market, not the fee.** Deriving quota from fee produced required market shares from 0.14% to 16%.
7. **Additive bundling, no discount.** Two territories cost what two dealers would have paid.
8. Statistics are exact census; several *geometries* are approximate. Never present a derived shape as authoritative.

---

## Administrative structure — verified, and the two cities differ

- **Karachi** — Division → District (7) → **Town** (25–26, Sindh LG Act 2021) → Union Council. The census publishes a parallel *taluka / sub-division* layer that does not align with towns.
- **Lahore** — Division → District → **Tehsil** → Union Council (274). **Ten tehsils since 27 Aug 2024** (original five plus Allama Iqbal, Nishter, Saddar, Wahga, Ravi). The 2023 census covers only the original five, so the model prices those five.

Karachi's municipal tier is the Town; Lahore's is the Tehsil. Using "tehsil" for both is wrong.

Territory composition: Karachi 7 districts · Lahore 5 census tehsils · Multan 4 tehsils · Peshawar 7 tehsils grouped to 4 · Islamabad 2 (census urban/rural split) · plus 7 hyper markets carved from parents.

---

## Assumed, not measured — ranked by blast radius

| Assumption | Current | Fix with |
|---|---|---|
| House vs flat share | 35–95% by region | SBCA/LDA/CDA/PDA/MDA building approvals, or utility connection counts (house vs bulk meters — faster) |
| ASP tier multipliers | ×8 / ×3 / ×1.6 / ×1 | Grundfos Gulf margin data by city and area type |
| Market share by tier | 6 / 4 / 1.5 / 0.3% | Internal sales history |
| Pumps per house, flats per set | 1.2, 40 | Installation records |
| Hyper-market house counts | 4,000–14,000 est. | DHA / Bahria / CDA plot and occupancy registers |
| Pump life | 9 years | Warranty and service records |
| Dealer margin | 22% | Known internally |

**PBS Table 20 does not give the house/flat split.** It is Pakka / Semi-Pakka / Kacha — construction material. No PBS table publishes house-versus-apartment by district. An earlier draft claimed otherwise; that was wrong.

**Sensitivity:** Karachi South outranks Karachi East at every premium multiplier tested, including ×2.0. The *ranking* is robust; the *magnitude* is not.

---

## Gotchas — all previously hit

- **Duplicate labels in `build_xlsx2.py`.** The Assumptions dict is keyed by label. `"A — Premium"` once appeared under both ASP multipliers and market shares, so tiers silently picked up share values. All share rows are now prefixed `Share `. Keep every label unique.
- **`head -N` on a Python script kills it via SIGPIPE** before `json.dump` runs, leaving stale JSON. Redirect to a file instead.
- **Excel serialises float dict keys as `"1.0"`, not `"1"`.** JS lookups must match.
- **Assumptions row numbers shift** when rows are added. Read by label, not by hardcoded row.
- **Chrome will not install in this sandbox** — no headless render check. Verify JS by parsing it in Node and testing the data layer directly.
- **Karachi district polygons** are crosswalked from a 2022 town layer. Total area within 10% of census; four districts vary individually (East +47%, West −47%, Malir +27%, South −20%). Disclosed per district in the map UI.
- **Lahore tehsil polygons are derived**, not official. Built by matching the 2024 notification's revenue estates to locality points (167 of 801 matched), filling by nearest neighbour, then 9-NN majority smoothing.
- **Lahore has two tehsil layers.** `lahore_census_tehsils` (5, OSM, admin_level 7) are the 2023 census units the model prices and match census area within 2% overall; everything joined to census or dealership data uses them. `lahore_tehsils` (10, derived) are the 2024 notification units — a different vintage, where a same-named outline is a *fraction* of its census unit (post-2024 Shalimar 23 km² against 272 km², −91%). They are a shapes-only level. Joining the census figures to the derived ten was the earlier behaviour and left **59% of Lahore undrawn**, because only five of the ten names collide.
- **Peshawar's source admin layer uses the old Town-I..IV structure**, which does not crosswalk to the model's territories. The map uses OSM's current seven tehsils, which carry the model's own names, unioned into the four groups. Peshawar City +51% and East Ring −38% against census area; the four-territory total is within 6%.
- **Islamabad cannot be split geographically.** ICT is one district and the urban/rural split is a census classification, not a published boundary. No open source has it, OSM included. Both territories are listed against the whole-city shape.
- **Assumptions rows carry no column-A label directly under each section header** — the anchor territory, pump price, S-tier multiplier, first weight and Ramp Q1 all sit in a bare B cell. `refresh.py` reads these with an `above(label)` helper anchored to the next label down, never a fixed row number.
- **Lahore locality cells are Voronoi tessellations**, not boundaries.
- **Replacement is base ÷ life, not construction vintage.** An earlier version tied it to vintage and valued Peshawar City at Rs 5.5 L despite 259,605 standing pump points. A mature base replaces on its own cycle.

---

## Findings that shape the model

- **Karachi South is the most valuable Karachi territory** — on revenue-weighted pump points, not household count.
- **Islamabad's growth is outside the CDA sectors.** Zone IV/V societies hold 248,346 households vs the sectors' 204,861, with three times the forward growth.
- **Peshawar City is a maintenance market.** 306,318 households but 2023 population *declined* against 2017, so new construction is zero. Sell on service and replacement.
- **Bahria Town Karachi is largely empty** — 186 km² at ~91 people/km². Malir Cantonment holds more than twice the population on 42 km². Bahria's "100,000+ residents" is a developer figure; the census counted 100,351 across the entire Gadap sub-division.
- **Replacement exceeds new construction in every territory.** Price a 4-year term on the standing base, not a 2030 projection.
- **Bahria Town Rawalpindi is mostly in Rawalpindi District, not ICT.** Not costed anywhere. Must be settled in contract text or two dealers claim the same 40,000 acres.
- **Neither model covers commercial/industrial demand.** SITE, Korangi Industrial Area, the Multan MDA belt. If commercial is material, Keamari and Korangi are understated.

---

## Open work

1. Send the four data requests — PBS (cantonment census figures), DHA chapters (plot counts by phase), CDA/PDA/MDA (scheme plot counts), utilities (domestic connections by block). Specs in `Dealer_Quotas_HyperMarkets.docx`.
2. Back-test tier market shares against Lahore and Karachi sales history. Single biggest quota driver.
3. Decide whether commercial/industrial demand gets its own term.
4. Re-base every 3 years, not at the next census.
