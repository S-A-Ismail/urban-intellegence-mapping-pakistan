#!/usr/bin/env python3
"""
refresh.py — rebuild pakistan_urban_map.html

Run it from this folder:

    python refresh.py

No dependencies. It reads the cached values Excel stores in the workbook, so
openpyxl is not needed.

    map_template.html         the UI (edit this to change look or behaviour)
    pakistan_urban_geo.json   the boundaries (rarely changes)
    Dealership_Model.xlsx     the model
    census.json               optional — override any census figure

and writes:
    pakistan_urban_map.html

SCOPE — geography, population, and one price.

Nothing commercial is read from the workbook. No quota, pump point, revenue,
profit or payback figure is extracted, and neither is the model's derived fee
schedule. Suppressing those in the UI alone would be false secrecy: they would
still sit in the page source for anyone who opened it, so they are never
extracted at all. The FORBIDDEN check at the bottom fails the build if one ever
reaches the output.

Two things do come from the commercial side:

  * the *structure* — which dealership covers each region, and the ten clubs on
    the DealerStructure sheet. That sheet's fee and revenue columns are skipped.

  * the *proposed entry fee* per dealership, hand-entered in
    dealership_clusters.json. This is the client's own two-tier proposal
    (Rs 1.5 Cr / Rs 1 Cr), not the model's derived figure, and is labelled
    "proposed" wherever it is shown.

Because a price is now in the page, treat the built HTML as commercially
sensitive when hosting it.
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

XL = p("Dealership_Model.xlsx")
REGIONS, HYPER, CITIES, DEALERS, META = {}, {}, {}, {}, {}
src = "none"


def read_workbook(path):
    b = Book(path)

    # --- Assumptions: only the growth cap, which the projection note needs.
    #     Read by label; the first input under each section header carries no
    #     column-A label of its own, so anchoring off a fixed row would break.
    A = b.sheet("Assumptions")
    lab = {}
    for ref, v in A.items():
        if ref.startswith("A") and isinstance(v, str):
            lab[v.strip()] = A.get("B%d" % int(ref[1:]))
    meta = dict(growth_cap=num(lab.get("Growth rate cap")),
                base_year="2026", census_year="2023", prev_census="2017")

    # --- CensusBase: the 22 official regions. Geography and population only —
    #     the ASP tier and house share are pricing inputs and are not read.
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
            hh_size=r2(c(6)), growth_raw=r2(c(9), 5), growth=r2(c(10), 5))
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

    # --- PumpPoints, columns B and E only: the territory list and which
    #     dealership club each belongs to. Nothing else on this sheet is read.
    hyper = {}
    r = 6
    while True:
        name = b.cell("PumpPoints", 2, r)
        if not isinstance(name, str) or not name.strip() or name.upper().startswith("TOTAL"):
            break
        club = b.cell("PumpPoints", 5, r)
        if name in regions:
            regions[name]["club"] = club
            regions[name]["area_net"] = r2(b.cell("PumpPoints", 6, r), 1)
        else:
            hyper[name] = dict(kind="hyper", club=club,
                               area=r2(b.cell("PumpPoints", 6, r), 1))
        r += 1

    # --- HyperMarkets: the enclave's city, parent and estimated house count.
    #     Columns E-I (pump points, fees) are not read.
    r = 6
    while True:
        name = b.cell("HyperMarkets", 1, r)
        if not isinstance(name, str) or not name.strip() or name.upper().startswith("TOTAL"):
            break
        if name in hyper:
            hyper[name].update(city=b.cell("HyperMarkets", 2, r),
                               parent=b.cell("HyperMarkets", 3, r),
                               houses=r0(b.cell("HyperMarkets", 6, r)))
        r += 1

    # --- DealerStructure, columns A-D only: the ten clubs and how many
    #     territories each covers. Columns E-K hold pump points, fees, quota and
    #     revenue and are deliberately skipped.
    dealers = {}
    r = 6
    while True:
        code = b.cell("DealerStructure", 1, r)
        if not isinstance(code, str) or not code.strip():
            break
        dealers[code] = dict(name=b.cell("DealerStructure", 2, r),
                             city=b.cell("DealerStructure", 3, r),
                             territories=r0(b.cell("DealerStructure", 4, r)))
        r += 1

    return regions, hyper, cities, dealers, meta


if os.path.exists(XL):
    try:
        REGIONS, HYPER, CITIES, DEALERS, META = read_workbook(XL)
        src = "Dealership_Model.xlsx"
    except Exception as ex:
        print("! could not read workbook (%s)" % ex)

if not REGIONS and os.path.exists(p("scenario_a.json")):
    cached = json.load(open(p("scenario_a.json")))
    REGIONS = cached.get("regions", {}); HYPER = cached.get("hyper", {})
    CITIES = cached.get("cities", {});   DEALERS = cached.get("dealers", {})
    META = cached.get("meta", {})
    src = "scenario_a.json"

if REGIONS:
    json.dump(dict(regions=REGIONS, hyper=HYPER, cities=CITIES,
                   dealers=DEALERS, meta=META),
              open(p("scenario_a.json"), "w"), indent=0)

print("· model data: %s (%d regions + %d enclaves, %d cities, %d dealerships)"
      % (src, len(REGIONS), len(HYPER), len(CITIES), len(DEALERS)))
print("· scope: geography and population — no fee, quota or revenue figure is "
      "read from the workbook")

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

# Where a polygon is drawn for a census region, measure it against the census
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
             "Lahore":  ("lahore_census_tehsils", "match")}
VAR, VKIND = {}, {}
for city, (layer, kind) in GEO_LAYER.items():
    for ft in GEO.get(layer, {}).get("features", []):
        nm = ft["properties"].get("name")
        drawn = ft["properties"].get("area_km2")
        reg = REGIONS.get(nm)
        if reg and drawn and reg.get("area"):
            VAR[nm] = round((drawn - reg["area"]) / reg["area"] * 100)
            VKIND[nm] = kind

# --------------------------------------------- named enclaves -> OSM outlines
# The model carves out seven enclaves. OSM draws some of them and not others,
# and where it draws only part of one the shortfall is measured and carried so
# the UI can say so instead of implying the outline is the whole enclave.
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
ENCLAVE = {}
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

# ----------------------------------------------- dealership clustering scheme
# A commercial grouping, not a census unit, so it is hand-edited in
# dealership_clusters.json rather than read from the workbook. Each named area is
# resolved to whatever outlines exist for it; an area with none is still listed,
# labelled as having no outline rather than quietly dropped.
CLUSTERS = []
CLUSTER_OF = {}                       # outline "city|layer|name" -> cluster code
def _norm(s):
    return re.sub(r"[^a-z0-9]", "", str(s).lower())

if os.path.exists(p("dealership_clusters.json")):
    scheme = json.load(open(p("dealership_clusters.json"), encoding="utf8"))
    # Layers a cluster area may be drawn from, best first.
    #
    # Tehsil and district layers are deliberately absent. "Lahore Cantt" and
    # "Model Town" name both a premium neighbourhood and a 100-plus km2
    # administrative tehsil; matching the tehsil would draw a whole
    # administrative unit as though it were the cluster area.
    #
    # First layer that yields a hit wins, so one place is never drawn twice from
    # two different layers. Real OSM outlines outrank Lahore's Voronoi locality
    # cells, which are approximations and are labelled as such in the UI.
    PRIORITY = ["city_areas", "lahore_localities", "karachi_towns"]
    POOL = {}
    for layer in PRIORITY:
        for ft in GEO.get(layer, {}).get("features", []):
            q = ft["properties"]
            nm = q.get("name")
            if not nm:
                continue
            POOL.setdefault((q.get("city") or "", layer), []).append(nm)

    def match(city, prefixes):
        """Prefix-anchored, so 'E-7' cannot swallow 'Bahria Town Phase 7'."""
        norms = [_norm(x) for x in prefixes]
        for layer in PRIORITY:
            hit = []
            for nm in POOL.get((city, layer), []):
                n = _norm(nm)
                if any(n == q or n.startswith(q) for q in norms):
                    hit.append({"layer": layer, "name": nm})
            if hit:
                return hit
        return []

    total_areas = total_drawn = 0
    for c in scheme.get("clusters", []):
        areas = []
        for a in c.get("areas", []):
            found = match(c["city"], a.get("prefixes", []))
            for f in found:
                CLUSTER_OF["%s|%s|%s" % (c["city"], f["layer"], f["name"])] = c["code"]
            areas.append({"label": a["label"], "found": found})
            total_areas += 1
            total_drawn += 1 if found else 0
        CLUSTERS.append(dict(code=c["code"], name=c["name"], city=c["city"],
                             premium=c.get("premium", True), note=c.get("note"),
                             proposed_fee_pkr=c.get("proposed_fee_pkr"),
                             areas=areas))
    net = sum(c.get("proposed_fee_pkr") or 0 for c in CLUSTERS)
    print("· clusters: %d dealerships, %d named areas, %d with an outline"
          % (len(CLUSTERS), total_areas, total_drawn))
    if net:
        print("· proposed entry fees carried: Rs %.2f Cr across the network "
              "(client's two-tier proposal, not the model's derived schedule)"
              % (net / 1e7))
    for c in CLUSTERS:
        miss = [a["label"] for a in c["areas"] if not a["found"]]
        if miss:
            print("    %-6s no outline for: %s" % (c["code"], ", ".join(miss)))

CITY_PT = {"Karachi": [67.01, 24.86], "Lahore": [74.34, 31.55],
           "Islamabad": [73.06, 33.68], "Peshawar": [71.55, 34.01],
           "Multan": [71.48, 30.18]}
CITY_NOTE = {
 "Islamabad": "ICT is a single district. The census urban/rural split the model "
              "uses is a classification, not a published boundary, so the whole "
              "city is drawn as one shape.",
 "Peshawar":  "Seven OSM tehsils unioned into four groups. The OSM line between "
              "Peshawar City and the East Ring differs from the census one — "
              "statistics are exact, shapes vary.",
 "Multan":    "Four tehsils, names matching the census exactly. No OSM "
              "neighbourhood layer exists for Multan, so the drill-down stops "
              "at tehsil.",
 "Lahore":    "Five census tehsils, drawn from OpenStreetMap and matching the "
              "census areas within 2% overall. The ten 2024-notification "
              "tehsils are a different administrative vintage and are kept as "
              "their own level; they carry no statistics.",
 "Karachi":   "Seven districts crosswalked from a 2022 town layer. Total area "
              "within 10% of census; four districts vary individually.",
}

# dealership_clusters.json is the naming authority for what a dealership is
# called. DealerStructure carries its own labels, and letting both through would
# show one name on the cluster card and a different one on the structure card.
for _c in CLUSTERS:
    if _c["code"] in DEALERS and _c.get("name"):
        DEALERS[_c["code"]]["name"] = _c["name"]

DATA = dict(regions=REGIONS, hyper=HYPER, cities=CITIES, dealers=DEALERS,
            meta=META, var=VAR, vkind=VKIND, city_pt=CITY_PT,
            city_note=CITY_NOTE, enclave=ENCLAVE,
            clusters=CLUSTERS, cluster_of=CLUSTER_OF)

# ------------------------------------------------------------- forbidden keys
# A guard, not a formality. If a future edit reintroduces a commercial field the
# build fails loudly rather than quietly publishing the model's fee schedule,
# quotas or margins inside the page source.
#
# ALLOWED is the one deliberate exception: the client's proposed per-dealership
# entry fee, typed by hand into dealership_clusters.json. It is not derived from
# the workbook and does not open the door to the rest of the model.
ALLOWED = {"proposed_fee_pkr"}
FORBIDDEN = {"fee", "feea", "feeb", "units", "quota", "quota_yr", "topline",
             "bottom", "gross", "payback", "spp", "spp18", "spp30", "rpp",
             "outlay", "fee_yr", "cum4", "roi", "inv", "addressable", "asp",
             "tier", "tier_share", "rate", "anchor_fee", "pump_price", "margin",
             "newbuild", "repl", "share", "gshare", "y1", "house_share",
             "spp_factor", "anchor_on", "alt_fee"}
def check(node, trail="DATA"):
    if isinstance(node, dict):
        for k, v in node.items():
            if str(k).lower() in FORBIDDEN and str(k) not in ALLOWED:
                sys.exit("! %s.%s is a commercial field — this map is geography "
                         "and population only. Remove it from read_workbook()."
                         % (trail, k))
            check(v, trail + "." + str(k))
    elif isinstance(node, list):
        for v in node[:50]:
            check(v, trail + "[]")
check(DATA)

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
