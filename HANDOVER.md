# Cenergy / Grundfos Pakistan — Dealership Workstream Handover

**Written:** 8 September 2026 · **Anchor decided:** Islamabad whole city = Rs 1.00 Cr
**Covers:** territory design, dealer entry-fee model, sales quotas, and the urban intelligence map
**Read this first if:** you are picking this work up cold, or handing it to someone else.
**Companion file:** `CLAUDE.md` — the same material compressed into agent context for Claude Code. This file is the human-readable version; that one is the operational reference.

---

## 0. What this document is

A complete record of the territory-and-pricing workstream: what was built, in what order, why each decision was made, what is real data versus assumption, what is still undecided, and which file is which in both folders.

It is written so that someone with no prior context — a colleague, a lawyer, or a fresh AI session — can pick the work up without re-deriving anything.

**One honesty note carried throughout:** this workstream produced a defensible *framework*. It did not produce final prices. Several load-bearing inputs are still judgement rather than measurement, and they are all flagged. Do not issue any figure to a dealer without reading section 7.

---

## 1. The commercial context

Cenergy (with NTS, Nexus Technical Solutions Pvt Ltd) is the authorised distributor for **Grundfos Gulf Distribution FZE** (JAFZA North, Dubai) in Pakistan — *not* Grundfos Holding A/S. That distinction matters and is applied across every legal document.

Products in scope: **SCALA2, SOLOLIFT2, UNILIFT**.

The task in this workstream: divide Pakistan's major cities into dealership territories, price each one so that no dealer feels treated differently from another, and set a sales quota each dealer must meet.

Cities covered: **Karachi, Lahore, Islamabad, Peshawar, Multan**.

---

## 2. What we did, step by step

The work ran through nine distinct stages. Each stage's output is preserved so the reasoning trail survives.

### Stage 1 — Lahore demographics
Started narrow: split Lahore into dealer sub-regions. Established the five official tehsils (Lahore City, Model Town, Shalimar, Lahore Cantt, Raiwind) with PBS Census 2023 population, area and household size.

### Stage 2 — Multi-metric comparison
Ranked the same five tehsils four ways: by area, population, households, and 2017–23 growth. First appearance of the idea that **different metrics produce different rankings**, so the choice of metric is the whole argument.

### Stage 3 — Four-city framework, Fee Units introduced
Extended to Karachi, Lahore, Islamabad, Peshawar. Introduced the core mechanism:

> Territories are priced in **Fee Units** — a relative index out of 100. One anchor price fixes what a unit is worth in rupees; every other fee follows arithmetically. Nobody negotiates a number.

This is the fairness principle. One formula, one public data source, applied identically. Any dealer can recompute their own fee and everyone else's from the same census table.

### Stage 4 — Premium clusters
Added a layer for DHA, Clifton, Cavalry Ground, the CDA E/F sectors and similar. Established that the census publishes nothing below sub-division level, so these are named and mapped but not measured.

### Stage 5 — Hyper markets split out
DHA Phase VIII, Malir Cantt and Bahria Town became standalone territories, with equivalents identified in the other cities. Introduced the **carve-out rule**: a cluster sold separately must be subtracted from its parent, or the same households get charged twice.

### Stage 6 — Multan added, prices attached, weights revised
Added Multan (4 tehsils). Attached actual rupee prices for the first time via the Islamabad = Rs 1 Cr anchor. Weighting revised twice at your direction, ending at 45% new households / 40% households / 10% population / 5% area.

### Stage 7 — The pump-point restructure (the biggest change)
You observed that pumps sell on new construction and end-of-life replacement, so Karachi South should be the most expensive market. The stated reason didn't hold — Karachi East has 54% more households *and* 54% more new construction. But the underlying instinct was right, for a different reason:

> **A household is not a pump.** A bungalow needs one to two pump sets. A 200-flat tower needs one or two booster sets for the whole building. Counting households treats those as equal. They differ by roughly 48:1.

The unit changed from households to **serviceable pump points (SPP)**, weighted by achievable selling price (**RPP**). Karachi South and Karachi East hold near-identical pump points — 321,088 vs 321,502 — but South is bungalow stock at premium prices. That flipped the ranking and vindicated your instinct on the correct grounds.

### Stage 8 — Quotas, hyper-market tier, anchor conflict
Set quotas from the market rather than from the fee. Solved the hyper-market ASP tier. Discovered that **your two anchors are mutually inconsistent by about 11×** (section 6).

### Stage 9 — Excel model and the map
Turned everything into a live formula workbook, then built an interactive Pakistan map wired to the same numbers.

---

## 3. Where the model stands now

### The formula

```
Fee Units = 45% × new-construction share
          + 35% × replacement-due share
          + 15% × installed-base share
          +  5% × area share
```

All three revenue terms are in **revenue-weighted pump points**.

```
Serviceable pump points = (houses × 1.2) + (flats ÷ 40)
Revenue-weighted points = pump points × ASP tier multiplier
```

**ASP tiers:** S Hyper ×8 · A Premium ×3 · B Upper-mid ×1.6 · C Mass ×1.0

**Two revenue channels, both yours:**
- New construction — pump points added 2026–30
- Replacement — the 2018 base × (4-year term ÷ 9-year pump life)

Replacement exceeds new construction in **every** territory. That is the argument for pricing a four-year term on the standing base rather than on a 2030 projection.

### Territory structure — 29 territories, 10 dealerships

| City | Territories | Structure |
|---|---|---|
| Karachi | 7 districts | Division → District → **Town** → Union Council |
| Lahore | 5 tehsils (census) | Division → District → **Tehsil** → Union Council |
| Multan | 4 tehsils | |
| Peshawar | 7 tehsils → 4 groups | Hassan Khel too small to stand alone |
| Islamabad | 2 (urban/rural) | ICT is a single district |
| Hyper markets | 7 | Carved out of parents |

**Karachi and Lahore do not share an administrative structure.** Karachi's municipal tier is the Town; Lahore's is the Tehsil. Using "tehsil" for both is wrong.

**Lahore has had ten tehsils since 27 Aug 2024** (Punjab BoR notification 1058-2024/4496): the original five plus Allama Iqbal, Nishter, Saddar, Wahga, Ravi. The 2023 census reports only the original five, so the model prices those five.

---

## 4. Key numbers — quick reference

**Chosen anchor: Islamabad whole city = Rs 1.00 Cr** — rate PKR 1,058,239 per Fee Unit

| | |
|---|---|
| Network entry fees | **Rs 10.58 Cr** |
| Network top line / yr | Rs 119.1 Cr |
| Network bottom line / yr | Rs 24.9 Cr |
| Median dealer payback | 2.7 months |
| Payback range | 1.2 to 7.8 months |

*Alternative kept in the workbook for comparison only:* DHA Phase VIII at Rs 1.5 Cr → network Rs 123.5 Cr. Not in use.

**The ten dealerships:**

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

**Quota rule:** annual addressable pump points × tier market share ÷ 4, with a Year-1 ramp of 50 / 75 / 100 / 100%.

**Market shares assumed:** 6% hyper · 4% premium · 1.5% upper-mid · 0.3% mass — share of *all* pump installations, not of the premium segment.

**Commercials:** PKR 125,000 average pump price · 22% dealer margin · 50% of fee returned as inventory credit · 4-year term.

---

## 5. Findings worth carrying forward

- **Karachi South is the most valuable market**, but not because it has the most households. It has the most *revenue-weighted pump points*. Karachi East has 54% more households and converts to the same number of pump points.
- **Islamabad's growth is outside the CDA sectors.** The Zone IV/V society belt holds 248,346 households against the sectors' 204,861, and three times the forward growth. Sold on prestige, the wrong half gets bought.
- **Peshawar City is a maintenance market.** 306,318 households — third-largest base in the schedule — but its 2023 population *declined* against 2017, so new construction is zero. Sell it on service and replacement revenue.
- **Bahria Town Karachi is mostly empty.** 186 km² at roughly 91 people/km². Malir Cantonment holds more than twice its population on 42 km². Bahria's "100,000+ residents" is a developer figure; the census counted 100,351 in the *entire* Gadap sub-division.
- **Multan outranks Peshawar** and nearly doubles Islamabad on units.
- **Replacement beats new construction everywhere**, which is why a four-year term should be priced on the standing base.

---

## 6. The anchor — decided

**Chosen: Islamabad whole city = Rs 1.00 Cr.** This fixes the rate at PKR 1,058,239 per Fee Unit and every other price in the schedule follows arithmetically. The workbook is set to it (Assumptions, Scenario A, active). The alternative sits in Scenario B for comparison and is not in use.

The decision was made against a real tension, recorded here so nobody reopens it without the context.

Two anchors had been floated — Islamabad at Rs 1 Cr and DHA Phase VIII at Rs 1.5 Cr — and they differ by about 11×. Islamabad at Rs 1 Cr prices DHA Phase VIII at Rs 12.9 L; to reach Rs 1.5 Cr it would have to be worth eleven times that.

| Anchor basis | Network | DHA Phase VIII |
|---|---|---|
| **Islamabad Rs 1 Cr — chosen** | **Rs 10.58 Cr** | **Rs 12.9 L** |
| 1-year payback | Rs 52.4 Cr | Rs 57.6 L |
| 2-year payback | Rs 104.9 Cr | Rs 1.15 Cr |
| 2.6-year (DHA Rs 1.5 Cr) | Rs 123.5 Cr | Rs 1.50 Cr |

**Known consequence, accepted:** at this anchor a dealer recovers their net cash outlay in 1.2 to 7.8 months, median 2.7. That is fast for a licence fee — closer to a deposit than a licence — and it means the network leaves money on the table if dealers are queueing. It was chosen deliberately, presumably because a low entry barrier matters more right now than fee revenue. The diagnostic block on the Assumptions sheet shows this live for any anchor, so it can be revisited with one cell change.

**What has not changed:** the *relative* pricing between territories. The anchor only scales the whole schedule. Every ranking, every ratio, and every quota is anchor-independent.

**Still true regardless of anchor:** the payback spread is 6.6×, and mass-tier territories earn least relative to their fee. That is a property of the weighting, not the anchor.

---

## 7. What is assumed, not measured

Ranked by how much damage a wrong value does.

| Assumption | Current | Why it matters | How to fix |
|---|---|---|---|
| **House vs flat share** | 35–95% by region | The whole reordering rests on it | SBCA / LDA / CDA / PDA / MDA building approvals, **or** utility connection counts (house meters vs bulk building meters) — faster |
| **ASP tier multipliers** | ×8 / ×3 / ×1.6 / ×1 | 39% swing on Karachi South across a plausible range | Grundfos Gulf margin data by city and area type, last 8 quarters; or your own quotation history |
| **Market share by tier** | 6 / 4 / 1.5 / 0.3% | Drives every quota directly | Your own sales history |
| **Pumps per house / flats per set** | 1.2 and 40 | Sets the 48:1 house-to-flat ratio | Your installation records |
| **Hyper-market house counts** | 4,000–14,000 est. | DHA Ph VIII at 12,000 is the anchor | DHA / Bahria / CDA plot and occupancy registers |
| **Pump life** | 9 years | Shorter life raises every mature market | Your warranty and service records |
| **Dealer margin** | 22% | Every payback figure | Known internally |

**Important correction to an earlier claim:** PBS Census **Table 20 does not give the house/flat split.** It classifies housing units as Pakka / Semi-Pakka / Kacha — construction material, not building form. No PBS table publishes house-versus-apartment counts by district. I said otherwise earlier; that was wrong.

**Sensitivity result worth knowing:** Karachi South outranks Karachi East at *every* premium multiplier tested, including ×2.0. **The ranking is robust; the magnitude is not.** You can design the network on this. You cannot yet defend a specific rupee figure across a table.

---

## 8. Corrections made along the way

Kept for audit, and because a framework that hides its errors cannot be trusted.

1. **Table 20 misidentified** — claimed it gave house/flat split; it gives construction material.
2. **Replacement formula wrong on first pass** — tied to construction vintage, which valued Peshawar City at Rs 5.5 L despite 259,605 standing pump points. A mature base replaces on its own cycle whether or not it grows. Corrected to base ÷ life.
3. **Duplicate labels in the workbook** — "A — Premium" appeared under both ASP multipliers and market shares, so tiers silently picked up share values. Fixed; tiers now read 8 / 3 / 1.6 / 1.
4. **Hyper tier initially solved to ×91** — a red flag, not a result. Fixed at ×8 with the anchor conflict surfaced separately.
5. **Non-portable scripts shipped** — the first map scripts had sandbox paths and would not have run on your machine. Replaced with `refresh.py`.
6. **Karachi district boundaries** — crosswalked from a 2022 town layer. Total area within 10% of census, but four districts vary individually. Disclosed per district in the map.
7. **Lahore tehsil shapes are derived, not official.** Merging them back to the five census tehsils reproduces areas poorly (Shalimar −92%, Cantt +92%), so **no statistics are joined to them**.

---

## 9. File index — this workstream's outputs

### `PakistanUrbanMap.zip`

| File | What it is |
|---|---|
| `pakistan_urban_map.html` | **The app.** Open in a browser. Everything embedded except D3 (CDN). |
| `refresh.py` | **Run this to update numbers.** Reads the workbook, rewrites the HTML. `pip install openpyxl` first. |
| `CLAUDE.md` | Agent context, also shipped here. |
| `map_template.html` | The entire UI — CSS, layers, tooltips, panels. Edit to change look or behaviour. |
| `pakistan_urban_geo.json` | All seven geometry layers. |
| `Dealership_Model.xlsx` | The live model (same file as below). |
| `scenario_a.json` | Fallback if the workbook is absent. |
| `lahore_revenue_estates.json` | 363 revenue estates from the Aug 2024 notification. |
| `rebuild_boundaries.py` | Rare — only when districts/tehsils are redrawn. |
| `README.md` | How to refresh, add a city, change layers. |

**Map layers:** population, density, growth, households, new housing, new housing intensity (census-backed) · entry fee, Fee Units, pump points, quota, top line, bottom line (chosen anchor) · price, price growth, project counts (**disabled — no attributable open dataset**).

### `Dealership.zip`

| File | What it is |
|---|---|
| `CLAUDE.md` | Agent context for Claude Code — same material, compressed, with invariants and gotchas. |
| `Dealership_Model.xlsx` | **The live model.** 11 sheets, ~2,500 formulas. Start at README, then Assumptions. |
| `Dealer_Quotas_HyperMarkets.docx` | Quotas, hyper markets, the anchor conflict, data-request specs. |
| `Dealer_Fee_Schedule_PumpPoints.docx` | The pump-point method explained in full. |
| `map_dealership.png` | Pakistan map with treemaps by city. |
| `_superseded/01–08` | The eight earlier drafts in build order. Keep — the delta between v3 and PumpPoints is the answer to "why does Karachi South outprice Karachi East?" |
| `charts/` | 12 chart PNGs at 170 dpi. |
| `model/` | Python and JS source for every deliverable. |

**Workbook sheets:** README · Assumptions · CensusBase · Projection (2023–2030) · HyperMarkets · PumpPoints · FeeSchedule (chosen + alternative) · Quotas · Economics (top/bottom line, amortisation, payback) · DealerStructure · Visuals (7 live charts).

---

## 10. File index — `D:\Cenergy\Official Work\Grundfos Pumps\Docs\Dealership Agreement`

> **I cannot read your D: drive.** This section is reconstructed from our earlier working sessions (Aug 2026). Filenames are indicative — confirm and correct them. The *content* descriptions are accurate.

| Document | Length | Purpose | Confirmed? |
|---|---|---|---|
| Master dealership agreement template | ~35 pp | All-Pakistan master. Full legal form. | ☐ |
| Category B agreement — Peshawar | ~35 pp | City-specific instance of the master. | ☐ |
| Plain-English version | ~10 pp | No tables, large serif type. Written so a 70-year-old CEO reads it without a lawyer. | ☐ |
| Short-form version | ~6 pp | Full credit machinery, compressed. | ☐ |
| Dealer terms summary + Annex A | 2 pp + 1 | Terms table, city-generic. Annex A = eligibility criteria. | ☐ |

### What is settled in those documents

- **Principal is Grundfos Gulf Distribution FZE**, JAFZA North Dubai — not Grundfos Holding A/S. Applied throughout.
- **Fee structure:** one-time fee; 50% returned as stock credit at Dealer Price invoiced normally; remaining 50% earned pro-rata over 4 years; refundable only on Cenergy-side termination.
- **No retail price caps.** Excluded deliberately — CCP enforcement risk under Section 4, Competition Act 2010. Any price-support mechanism needs careful framing.
- **Arbitration and signing in Karachi**, Sindh e-stamping.
- **After-sales timelines:** customer acknowledgement 4 working hours; site attendance 24/48 hours; escalation 24 hours from diagnosis.
- **Grundfos Standards clause** — Grundfos general terms, code of conduct and warranty policy are binding on dealers and paramount over the agreement.
- **Warranty:** 24 months from installation, capped at 30 months from production. Shipment-vs-installation clock depends on ASP status.
- **Term:** 4 years, clause 10.1. No automatic renewal (10.2); month-to-month on 30 days' notice if trading continues unsigned.
- **Structure:** Part A = Schedule of Commercial Terms · Part B = Terms and Conditions · Annexure 1 and 2.
- **Display centre:** 10 × 12 feet (not "display counter", not 8 running feet).
- **Products:** SCALA2 / SOLOLIFT2 / UNILIFT.

### Legal references in play

Competition Act 2010 (s.4) · Arbitration Act 1940 · Contract Act 1872 (incl. s.133 guarantor discharge) · PPC s.489-F · Trade Marks Ordinance 2001 · KP Consumers Protection Act 1997 · KPRA services tax · Sindh e-stamping · Income Tax s.236G/236H.

### Four deletions previously flagged as weakening the document

Confirm whether these were reinstated: the **price revision mechanism**; the **arbitrator appointment fallback** and direct court recovery carve-out; the **self-help repossession remedy**; and **inconsistent NTS/Cenergy naming**.

---

## 11. How the two workstreams connect

The agreement folder defines **what a dealer signs**. This workstream defines **what they pay, where, and what they must sell**.

Three joins to make when the fee schedule is finalised:

1. **Part A, Schedule of Commercial Terms** — the entry fee line takes its number from `FeeSchedule` in the workbook.
2. **Sales Targets and Reporting** — the quarterly quota and Year-1 ramp come from the `Quotas` sheet.
3. **Appointment and Territory** — the territory definition should name the census units (districts for Karachi, tehsils for Lahore), not informal city names, so the boundary is unambiguous if disputed.

**Watch:** if a hyper market is sold separately, the parent territory's fee *and* quota must both drop. The carve-out arithmetic is in `Dealer_Quotas_HyperMarkets.docx`.

**Watch:** Bahria Town Rawalpindi sits mostly in Rawalpindi District, **not ICT**. A dealer buying "Islamabad" does not automatically get it, and Rawalpindi is not costed anywhere. Settle this in the contract text or two dealers will claim the same 40,000 acres.

---

## 12. What I would do next, in order

1. ~~Decide the anchor~~ — **done.** Islamabad Rs 1 Cr, section 6.
2. **Send the four data requests** — PBS for cantonment census figures; DHA chapters for plot counts by phase; CDA/PDA/MDA for scheme plot counts; utilities for domestic connection counts by block. Specs are in `Dealer_Quotas_HyperMarkets.docx`.
3. **Back-test market shares** against whatever Lahore and Karachi sales history exists. This single input moves every quota.
4. **Re-run** — change the assumption cells, then `python refresh.py` for the map.
5. **Then** issue prices. Not before.

**One gap neither model covers:** commercial and industrial demand. SITE in Keamari, Korangi Industrial Area, the Multan MDA belt — SOLOLIFT2 and UNILIFT sell into those and the model gives them zero weight. If commercial is a real share of your volume, Keamari and Korangi are both understated.

---

## 13. Working principles established

- **One formula, one public source, applied identically.** The fairness argument depends entirely on this. No ad-hoc adjustments.
- **Serviceable pump points, not households.** A bungalow and a flat are not the same customer.
- **Additive bundling, no discount.** Two territories cost what two dealers would have paid. Incentivise multi-territory dealers through margin or volume targets, never through the entry fee.
- **Re-base every three years**, not at the next census. At these growth rates a seven-year lock hands a fast-territory dealer a double-digit unearned gain.
- **Carve-outs must be subtracted.** Selling a cluster without deducting it charges twice for the same households.
- **Never fabricate a boundary or a statistic.** Where data does not exist, the layer is disabled and labelled, not estimated.
- **Documents must explain themselves** to non-finance, non-legal readers, with assumptions visibly flagged.
