#!/usr/bin/env python3
"""
refresh.py — rebuild pakistan_urban_map.html

Run it from this folder:

    python refresh.py

No dependencies. It reads the cached values Excel stores in the workbook, so
openpyxl is no longer needed.

It reads whatever is sitting next to it:
    map_template.html         the UI (edit this to change look or behaviour)
    pakistan_urban_geo.json   the boundaries (rarely changes)
    Dealership_Model.xlsx     the model — all 29 territories, five cities
    census.json               optional — override any census figure

and writes:
    pakistan_urban_map.html

Everything the map shows comes from the workbook. There are no census figures
hardcoded here any more: change an assumption in Dealership_Model.xlsx, run this,
and the map follows.

If the workbook is missing it falls back to scenario_a.json.
"""
import json, sys, os, re, zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
p = lambda *a: os.path.join(HERE, *a)

# ------------------------------------------------------- minimal xlsx reader --
# Excel caches the computed value of every formula inside the sheet XML. That is
# exactly what we want, and reading it directly keeps this script dependency-free.
class Book:
    def __init__(self, path):
        self.z = z = zipfile.ZipFile(path)
        rels = z.read("xl/_rels/workbook.xml.rels").decode("utf8", "ignore")
        rmap = dict(re.findall(r'Id="(rId\d+)"[^>]*Target="([^"]+)"', rels))
        wbx = z.read("xl/workbook.xml").decode("utf8", "ignore")
        self.sheets = {n: "xl/" + rmap[r].lstrip("/") for n, r in
                       re.findall(r'<sheet name="([^"]+)"[^>]*r:id="(rId\d+)"', wbx)}
        self.ss = []
        if "xl/sharedStrings.xml" in z.namelist():
            sx = z.read("xl/sharedStrings.xml").decode("utf8", "ignore")
            self.ss = [self._unescape(re.sub(r"<[^>]+>", "", m))
                       for m in re.findall(r"<si>(.*?)</si>", sx, re.S)]
        self._cache = {}

    @staticmethod
    def _unescape(s):
        return (s.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
                 .replace("&quot;", '"').replace("&apos;", "'"))

    def sheet(self, name):
        if name not in self._cache:
            x = self.z.read(self.sheets[name]).decode("utf8", "ignore")
            d = {}
            for m in re.finditer(r'<c r="([A-Z]+\d+)"([^>]*)>(.*?)</c>', x, re.S):
                ref, attrs, body = m.groups()
                v = re.search(r"<v>(.*?)</v>", body, re.S)
                if not v:
                    continue
                val = v.group(1)
                if 't="s"' in attrs:
                    val = self.ss[int(val)]
                elif 't="str"' in attrs or 't="b"' in attrs:
                    val = self._unescape(val)
                else:
                    try:
                        val = float(val)
                    except ValueError:
                        pass
                d[ref] = val
            self._cache[name] = d
        return self._cache[name]

    def cell(self, sheet, col, row):
        return self.sheet(sheet).get("%s%d" % (COL(col), row))


def COL(n):
    s = ""
    while n:
        n, r = divmod(n - 1, 26)
        s = chr(65 + r) + s
    return s


num = lambda v: float(v) if isinstance(v, (int, float)) else 0.0
r0 = lambda v: round(num(v))
r2 = lambda v, d=2: round(num(v), d)

# --------------------------------------------------------------- read the model
XL = p("Dealership_Model.xlsx")
REGIONS, HYPER, CITIES, META = {}, {}, {}, {}
src = "none"


def read_workbook(path):
    b = Book(path)

    # --- Assumptions: read by label, never by hardcoded row (rows shift)
    A = b.sheet("Assumptions")
    lab, lrow = {}, {}
    for ref, v in A.items():
        if ref.startswith("A") and isinstance(v, str):
            row = int(ref[1:])
            lab[v.strip()] = A.get("B%d" % row)
            lrow[v.strip()] = row
    g = lambda k, d=None: lab.get(k, d)

    def above(label):
        """Value one row above a labelled row.

        The first input under each section header carries no label of its own —
        the anchor territory, the pump price, the S-tier multiplier and so on all
        sit in a bare B cell. Anchoring off the next label down keeps this
        row-shift safe, which reading a fixed row number would not be.
        """
        r = lrow.get(label)
        return A.get("B%d" % (r - 1)) if r else None
    meta = dict(
        anchor_on=above("Scenario A: anchor fee (PKR)"),
        anchor_fee=num(g("Scenario A: anchor fee (PKR)")),
        alt_on=g("Scenario B: anchor on"),
        alt_fee=num(g("Scenario B: anchor fee (PKR)")),
        active=g("Active scenario for Economics & Visuals"),
        rate=num(g("Active rate (PKR per Fee Unit)")),
        rate_a=num(g("Scenario A rate (PKR per Fee Unit)")),
        rate_b=num(g("Scenario B rate (PKR per Fee Unit)")),
        pump_price=num(above("Dealer gross margin")),
        margin=num(g("Dealer gross margin")),
        term=num(g("Dealership term (years)")),
        pump_life=num(g("Average pump life (years)")),
        inv_credit=num(g("Inventory credit (fraction of fee)")),
        growth_cap=num(g("Growth rate cap")),
        pumps_per_house=num(above("Flats per booster set")),
        flats_per_set=num(g("Flats per booster set")),
        whole_city=num(g("Whole-city exclusivity premium")),
        asp=dict(S=num(above("ASP A — Premium")), A=num(g("ASP A — Premium")),
                 B=num(g("ASP B — Upper-mid")), C=num(g("ASP C — Mass"))),
        tier_share=dict(S=num(above("Share A — Premium")), A=num(g("Share A — Premium")),
                        B=num(g("Share B — Upper-mid")), C=num(g("Share C — Mass"))),
    )

    # --- CensusBase: the 22 official regions
    regions = {}
    r = 6
    while True:
        name = b.cell("CensusBase", 2, r)
        if not isinstance(name, str) or not name.strip():
            break
        c = lambda col: b.cell("CensusBase", col, r)
        regions[name] = dict(
            city=b.cell("CensusBase", 1, r), kind="region",
            area=r2(c(3), 1), pop17=r0(c(4)), pop23=r0(c(5)),
            hh_size=r2(c(6)), house_share=r2(c(7), 3), tier=c(8),
            growth_raw=r2(c(9), 5), growth=r2(c(10), 5), spp_factor=r2(c(11), 4),
        )
        r += 1

    # --- Projection: population and households, 2023 to 2030
    r = 6
    while True:
        name = b.cell("Projection", 2, r)
        if not isinstance(name, str) or not name.strip():
            break
        if name in regions:
            regions[name]["pop"] = {str(2023 + i): r0(b.cell("Projection", 3 + i, r))
                                    for i in range(8)}
            regions[name]["hh"] = {str(2023 + i): r0(b.cell("Projection", 11 + i, r))
                                   for i in range(8)}
        r += 1

    # --- Projection, BY CITY block (header at row 31)
    cities = {}
    r = 32
    while True:
        name = b.cell("Projection", 1, r)
        if not isinstance(name, str) or not name.strip():
            break
        cities[name] = dict(
            pop={str(2023 + i): r0(b.cell("Projection", 2 + i, r)) for i in range(8)},
            hh={str(2023 + i): r0(b.cell("Projection", 10 + i, r)) for i in range(8)})
        r += 1

    # --- PumpPoints / FeeSchedule / Quotas / Economics: all 29 territories
    hyper = {}
    r = 6
    while True:
        name = b.cell("FeeSchedule", 2, r)
        if not isinstance(name, str) or not name.strip() or name.upper().startswith("TOTAL"):
            break
        f = lambda col: b.cell("FeeSchedule", col, r)
        pp = lambda col: b.cell("PumpPoints", col, r)
        q = lambda col: b.cell("Quotas", col, r)
        e = lambda col: b.cell("Economics", col, r)
        rec = dict(
            city=f(1), typ=f(3), tier=f(4), club=f(5),
            units=r2(f(6), 3), share=r2(f(7), 5),
            feeA=r0(f(8)), feeB=r0(f(10)), fee=r0(f(12)), inv=r0(f(13)),
            spp18=r0(pp(8)), spp=r0(pp(9)), spp30=r0(pp(10)),
            newbuild=r0(pp(11)), repl=r0(pp(12)), asp=r2(pp(13)),
            rpp=r0(pp(14)),
            addressable=r0(q(5)), gshare=r2(q(6), 4),
            quota_yr=r0(q(7)), quota=r0(q(8)), y1=r0(q(13)),
            outlay=r0(e(6)), fee_yr=r0(e(7)),
            topline=r0(e(9)), gross=r0(e(10)), bottom=r0(e(11)),
            payback=r2(e(12), 1), cum4=r0(e(13)), roi=r2(e(14), 2),
        )
        if name in regions:
            regions[name].update(rec)
        else:                                    # a carved-out hyper market
            rec["kind"] = "hyper"
            rec["area"] = r2(pp(6), 1)
            rec["hh26"] = r0(pp(7))
            hyper[name] = rec
        r += 1

    # --- HyperMarkets: parent and estimated house count
    r = 6
    while True:
        name = b.cell("HyperMarkets", 1, r)
        if not isinstance(name, str) or not name.strip() or name.upper().startswith("TOTAL"):
            break
        if name in hyper:
            hyper[name].update(parent=b.cell("HyperMarkets", 3, r),
                               houses=r0(b.cell("HyperMarkets", 6, r)),
                               growth=r2(b.cell("HyperMarkets", 7, r), 4))
        r += 1

    # PumpPoints carries the carve-out-net area and households for regions too
    r = 6
    while True:
        name = b.cell("PumpPoints", 2, r)
        if not isinstance(name, str) or not name.strip() or name.upper().startswith("TOTAL"):
            break
        if name in regions:
            regions[name]["area_net"] = r2(b.cell("PumpPoints", 6, r), 1)
            regions[name]["hh26"] = r0(b.cell("PumpPoints", 7, r))
        r += 1

    return regions, hyper, cities, meta


if os.path.exists(XL):
    try:
        REGIONS, HYPER, CITIES, META = read_workbook(XL)
        src = "Dealership_Model.xlsx"
    except Exception as ex:
        print("! could not read workbook (%s)" % ex)

if not REGIONS and os.path.exists(p("scenario_a.json")):
    cached = json.load(open(p("scenario_a.json")))
    REGIONS = cached.get("regions", {}); HYPER = cached.get("hyper", {})
    CITIES = cached.get("cities", {});   META = cached.get("meta", {})
    src = "scenario_a.json"

if REGIONS:
    json.dump(dict(regions=REGIONS, hyper=HYPER, cities=CITIES, meta=META),
              open(p("scenario_a.json"), "w"), indent=0)

print("· model data: %s (%d regions + %d hyper markets, %d cities)"
      % (src, len(REGIONS), len(HYPER), len(CITIES)))
if META.get("anchor_on"):
    print("· anchor: scenario %s — %s at Rs %s (rate PKR %s / Fee Unit)"
          % (META.get("active"), META["anchor_on"],
             "{:,.2f} Cr".format(META["anchor_fee"] / 1e7),
             "{:,.0f}".format(META.get("rate", 0))))

# ------------------------------------------------------------ census overrides
if os.path.exists(p("census.json")):
    o = json.load(open(p("census.json")))
    for name, patch in o.get("regions", o).items():
        if name in REGIONS and isinstance(patch, dict):
            REGIONS[name].update(patch)
    print("· census.json applied to %d regions" % len(o.get("regions", o)))

# ------------------------------------------------------------------- geometry
for f in ("map_template.html", "pakistan_urban_geo.json"):
    if not os.path.exists(p(f)):
        sys.exit("! missing %s — it must sit next to refresh.py" % f)
GEO = json.load(open(p("pakistan_urban_geo.json")))

# Where a polygon is drawn for a priced territory, measure it against the census
# area and carry the gap so the UI can disclose it. Statistics stay exact; only
# the shapes are approximate.
#
# The *reason* a shape differs is not the same in every city, and the UI says
# which it is rather than lumping them together:
#   crosswalk — built by mapping an older layer onto the current units
#   source    — a different open source drew the line in a different place
#   match     — names and geometry correspond directly
#   vintage   — the polygon is a *different administrative unit* that happens to
#               share a name. Lahore's ten 2024 tehsils partition the same
#               district as the five 2023 census tehsils, so post-2024
#               "Shalimar" (23 km2) is a fraction of census "Shalimar"
#               (272 km2). The statistics are exact for the census unit; the
#               shape is not that unit.
GEO_LAYER = {"Karachi": ("karachi_districts", "crosswalk"),
             "Multan":  ("multan_tehsils",   "match"),
             "Peshawar": ("peshawar_groups", "source"),
             "Lahore":  ("lahore_tehsils",   "vintage")}
VAR, VKIND = {}, {}
for city, (layer, kind) in GEO_LAYER.items():
    for ft in GEO.get(layer, {}).get("features", []):
        nm = ft["properties"].get("name")
        drawn = ft["properties"].get("area_km2")
        reg = REGIONS.get(nm)
        if reg and drawn and reg.get("area"):
            VAR[nm] = round((drawn - reg["area"]) / reg["area"] * 100)
            VKIND[nm] = kind

# --------------------------------------------- priced enclaves -> OSM outlines
# The model prices seven carved-out enclaves. OSM draws some of them and not
# others, and where it draws only part of one the shortfall is measured and
# carried so the UI can say so instead of implying the outline is the territory.
ENCLAVE_GEO = {
 "DHA Phase VIII + Sahil":         ("Karachi",  ["DHA Phase 8", "DHA Phase 8 Extension"]),
 "Bahria Town Karachi":            ("Karachi",  ["Bahria Town Karachi",
                                                 "Bahria Town Sports City Karachi"]),
 "DHA Lahore VII-IX + EME":        ("Lahore",   ["DHA Phase 8"]),
 "Bahria Town Lahore + Lake City": ("Lahore",   ["Bahria Town"]),
 "DHA Islamabad + Bahria Enclave": ("Islamabad", ["Bahria Enclave"]),
 "Hayatabad Ph 6-7 + DHA Peshawar": ("Peshawar", ["Hayatabad"]),
 "DHA Multan":                     ("Multan",   []),
}
AREA_IX = {}
for ft in GEO.get("city_areas", {}).get("features", []):
    q = ft["properties"]
    AREA_IX[(q["city"], q["name"])] = q.get("area_km2") or 0
ENCLAVE = {}                      # osm feature -> priced territory it belongs to
for terr, (city, names) in ENCLAVE_GEO.items():
    drawn = sum(AREA_IX.get((city, n), 0) for n in names)
    model_area = (HYPER.get(terr) or {}).get("area")
    for n in names:
        if (city, n) in AREA_IX:
            ENCLAVE["%s|%s" % (city, n)] = terr
    if terr in HYPER:
        HYPER[terr]["geo_drawn"] = round(drawn, 1)
        HYPER[terr]["geo_cover"] = (round(drawn / model_area * 100)
                                    if model_area and drawn else 0)

# which cities have a real sub-region split, and which are sold whole
CITY_PT = {"Karachi": [67.01, 24.86], "Lahore": [74.34, 31.55],
           "Islamabad": [73.06, 33.68], "Peshawar": [71.55, 34.01],
           "Multan": [71.48, 30.18]}
CITY_GEO = {"Karachi": "karachi_districts", "Lahore": "lahore_tehsils",
            "Multan": "multan_tehsils", "Peshawar": "peshawar_groups",
            "Islamabad": "islamabad_district"}
CITY_SUB = {"Karachi": "karachi_towns", "Lahore": "lahore_localities"}
CITY_NOTE = {
 "Islamabad": "ICT is a single district. The model's urban/rural split follows "
              "the census classification, which is not a published boundary, so "
              "both territories are listed against the whole-city shape.",
 "Peshawar":  "Seven OSM tehsils unioned into the model's four commercial "
              "territories. The OSM line between Peshawar City and the East Ring "
              "differs from the census one — statistics are exact, shapes vary.",
 "Multan":    "Four tehsils, names matching the model exactly. No OSM "
              "neighbourhood layer exists for Multan, so the drill-down stops "
              "at tehsil.",
 "Lahore":    "The model prices the five 2023 census tehsils. The shapes drawn "
              "are the ten 2024-notification tehsils, which partition the same "
              "district — so a same-named polygon is a fraction of its census "
              "unit. Figures are exact for the census tehsil; the outline is "
              "not that tehsil.",
 "Karachi":   "Seven districts crosswalked from a 2022 town layer. Total area "
              "within 10% of census; four districts vary individually.",
}

DATA = dict(regions=REGIONS, hyper=HYPER, cities=CITIES, meta=META,
            var=VAR, vkind=VKIND, city_pt=CITY_PT, city_geo=CITY_GEO,
            city_sub=CITY_SUB, city_note=CITY_NOTE, enclave=ENCLAVE)

html = open(p("map_template.html"), encoding="utf8").read()
html = html.replace("__GEO__",  json.dumps(GEO,  separators=(",", ":")))
html = html.replace("__DATA__", json.dumps(DATA, separators=(",", ":")))
open(p("pakistan_urban_map.html"), "w", encoding="utf8").write(html)

print("· geometry layers: %s" % ", ".join(GEO.keys()))
if VAR:
    worst = sorted(VAR.items(), key=lambda kv: -abs(kv[1]))[:4]
    print("· shape vs census area, largest gaps: %s"
          % ", ".join("%s %+d%%" % (k, v) for k, v in worst))
print("✓ pakistan_urban_map.html rebuilt (%.2f MB)"
      % (os.path.getsize(p("pakistan_urban_map.html")) / 1e6))
print("  open it in a browser, or hard-refresh if it is already open (Ctrl/Cmd + Shift + R)")
