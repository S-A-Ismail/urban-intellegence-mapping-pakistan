#!/usr/bin/env python3
"""
rebuild_boundaries.py — regenerate pakistan_urban_geo.json from source

You will rarely need this. Boundaries change when districts or tehsils are
redrawn, which happens every few years. For a normal numbers update just run
refresh.py.

    pip install shapely requests
    python rebuild_boundaries.py

Downloads open datasets, rebuilds every geometry layer, and writes
pakistan_urban_geo.json next to this script. Then run refresh.py.

Sources, all open and attributable:
    HDX/OCHA admin boundaries (via mirror)  provinces, Karachi towns, Multan,
                                            Islamabad
    Internal-Lahore-Boundaries              Lahore district, localities, points
    OpenStreetMap via Overpass              Peshawar tehsils, and the
                                            neighbourhood layer that lets you
                                            zoom into Clifton and Defence

Everything is cached in _cache/, so the second run is offline.
"""
import json, os, zipfile, re, unicodedata, sys, math, time
from collections import Counter

try:
    import requests
    from shapely.geometry import shape, mapping, Polygon
    from shapely.ops import unary_union, transform
except ImportError:
    sys.exit("! needs: pip install shapely requests")

HERE = os.path.dirname(os.path.abspath(__file__))
p = lambda *a: os.path.join(HERE, *a)

SRC = {
 "admin": "https://codeload.github.com/muqeetahmaad9/live-weather-alert/zip/refs/heads/main",
 "lahore": "https://codeload.github.com/fatimaazfar/Internal-Lahore-Boundaries/zip/refs/heads/main",
}
CACHE = p("_cache")
os.makedirs(CACHE, exist_ok=True)

def grab(key):
    f = os.path.join(CACHE, key + ".zip")
    if not os.path.exists(f):
        print("· downloading", key)
        r = requests.get(SRC[key], timeout=180); r.raise_for_status()
        open(f, "wb").write(r.content)
    return zipfile.ZipFile(f)

# ------------------------------------------------------------------- overpass
OVERPASS = ["https://overpass-api.de/api/interpreter",
            "https://overpass.kumi.systems/api/interpreter",
            "https://overpass.private.coffee/api/interpreter",
            "https://overpass.osm.jp/api/interpreter"]
UA = {"User-Agent": "cenergy-region-map/1.0 (dealership territory mapping)"}

def overpass(name, query, required=True, rounds=3):
    """Cached Overpass query. Retries across mirrors with backoff.

    The public mirrors rate-limit and time out freely. When `required` is False a
    permanent failure returns None and the caller carries on with a thinner layer
    rather than losing the whole rebuild.
    """
    f = os.path.join(CACHE, "osm_%s.json" % name)
    if os.path.exists(f):
        return json.load(open(f))
    last = None
    for attempt in range(rounds):
        for ep in OVERPASS:
            try:
                print("· overpass: %s via %s%s"
                      % (name, ep.split("/")[2], "" if not attempt else " (retry %d)" % attempt))
                r = requests.post(ep, data={"data": query}, headers=UA, timeout=300)
                r.raise_for_status()
                d = r.json()
                json.dump(d, open(f, "w"))
                time.sleep(3)
                return d
            except Exception as ex:
                print("   %s failed (%s)" % (ep.split("/")[2], str(ex)[:70]))
                last = ex
                time.sleep(4 + 6 * attempt)
    if required:
        raise SystemExit("! every Overpass mirror failed for %s: %s" % (name, last))
    print("! giving up on %s — layer will be thinner (%s)" % (name, str(last)[:60]))
    return None

# ------------------------------------------------------- geometry from overpass
def _pts(g):
    """Overpass returns [{lat,lon}, ...] — not coordinate pairs."""
    return [(q["lon"], q["lat"]) for q in g]

def _rings(members):
    """Stitch member ways into closed outer rings."""
    segs = [_pts(m["geometry"]) for m in members
            if m.get("role") in ("outer", "") and m.get("geometry")]
    out, used = [], [False] * len(segs)
    for i, s in enumerate(segs):
        if used[i]: continue
        used[i] = True; cur = list(s); moved = True
        while moved and cur[0] != cur[-1]:
            moved = False
            for j, t in enumerate(segs):
                if used[j]: continue
                if   t[0]  == cur[-1]: cur += t[1:];            used[j]=moved=True
                elif t[-1] == cur[-1]: cur += t[::-1][1:];      used[j]=moved=True
                elif t[-1] == cur[0]:  cur = t[:-1] + cur;      used[j]=moved=True
                elif t[0]  == cur[0]:  cur = t[::-1][:-1] + cur;used[j]=moved=True
        if len(cur) >= 4:
            if cur[0] != cur[-1]: cur.append(cur[0])
            try:
                g = Polygon(cur).buffer(0)
                if not g.is_empty: out.append(g)
            except Exception:
                pass
    return out

def osm_geom(e):
    """Polygon for an Overpass way or relation, or None."""
    if e["type"] == "way" and e.get("geometry"):
        c = _pts(e["geometry"])
        if len(c) < 4: return None
        if c[0] != c[-1]: c.append(c[0])
        try:
            g = Polygon(c).buffer(0)
            return None if g.is_empty else g
        except Exception:
            return None
    if e["type"] == "relation" and e.get("members"):
        r = _rings(e["members"])
        if not r: return None
        g = unary_union(r).buffer(0)
        return None if g.is_empty else g
    return None

def osm_name(e):
    t = e.get("tags", {})
    return t.get("name:en") or t.get("name") or ""

def km2(g):
    """Area in km2 via a local azimuthal-equidistant projection."""
    c = g.centroid
    lat0, lon0, R = math.radians(c.y), math.radians(c.x), 6371.0088
    def fwd(x, y, z=None):
        lam, phi = math.radians(x), math.radians(y); dl = lam - lon0
        cc = max(-1.0, min(1.0, math.sin(lat0)*math.sin(phi) +
                               math.cos(lat0)*math.cos(phi)*math.cos(dl)))
        a = math.acos(cc); k = 1.0 if abs(a) < 1e-12 else a/math.sin(a)
        return (R*k*math.cos(phi)*math.sin(dl),
                R*k*(math.cos(lat0)*math.sin(phi) -
                     math.sin(lat0)*math.cos(phi)*math.cos(dl)))
    try:
        return transform(fwd, g).area
    except Exception:
        return 0.0

# --------------------------------------------------------------------- helpers
simp = lambda g, t: mapping(shape(g).buffer(0).simplify(t, preserve_topology=True))
def rnd(o, d=4):
    if isinstance(o, float): return round(o, d)
    if isinstance(o, list):  return [rnd(x, d) for x in o]
    if isinstance(o, dict):  return {k: rnd(v, d) for k, v in o.items()}
    return o
FC = lambda fs: {"type": "FeatureCollection", "features": fs}

def feat(geom, props, tol=0.0012, d=4):
    """Feature with simplified geometry and a measured area_km2."""
    g = shape(geom).buffer(0) if not hasattr(geom, "geom_type") else geom
    props = dict(props); props["area_km2"] = round(km2(g), 1)
    return {"type": "Feature", "properties": props,
            "geometry": rnd(mapping(g.simplify(tol, preserve_topology=True)), d)}

A, B = grab("admin"), grab("lahore")
PA = "live-weather-alert-main/"
PB = "Internal-Lahore-Boundaries-main/lahore_near_real_shapefile/"
out = {}

# ---------------------------------------------------------------- provinces --
prov = json.loads(A.read(PA + "Provincial_Boundary.geojson"))
out["provinces"] = FC([{"type":"Feature",
    "properties":{"name":f["properties"].get("name")},
    "geometry": rnd(simp(f["geometry"], 0.02), 3)} for f in prov["features"]])

teh = json.loads(A.read(PA + "Tehsil_Boundary.geojson"))
def by_district(*names):
    return [f for f in teh["features"] if str(f["properties"].get("District")) in names]

# ------------------------------------------- karachi towns -> 7 districts ----
OLD = {"Central Karachi","East Karachi","South Karachi","West Karachi",
       "Korangi Karachi","Malir Karachi"}
# crosswalk from the 2022 town layer to the post-2020 seven-district structure
T2D = {"Gulberg Town":"Karachi Central","Liaqatabad Town":"Karachi Central",
 "New Karachi Town":"Karachi Central","North Nazimabad Town":"Karachi Central",
 "Gulshan Iqbal Town":"Karachi East","Jamshaid Town":"Karachi East",
 "Korangi Town":"Korangi","Landhi Town":"Korangi","Shah Faisal Town":"Korangi",
 "Bin Qasim Town":"Malir","Gadap Town":"Malir","Malir Town":"Malir",
 "Liyari Town":"Karachi South","Saddar Town":"Karachi South",
 "Orangi Town":"Karachi West",
 "Kemari Town":"Keamari","Baldia Town":"Keamari","Site Town":"Keamari"}
khi = [f for f in teh["features"] if f["properties"].get("District") in OLD]
out["karachi_towns"] = FC([feat(shape(f["geometry"]), {
    "name": f["properties"]["Tehsil"],
    "district": T2D.get(f["properties"]["Tehsil"], "?"),
    "level":"town", "city":"Karachi"}, 0.0012) for f in khi])
ds = []
for d in ["Karachi Central","Karachi East","Karachi South","Karachi West",
          "Korangi","Malir","Keamari"]:
    u = unary_union([shape(f["geometry"]).buffer(0) for f in khi
                     if T2D.get(f["properties"]["Tehsil"]) == d])
    u = u.buffer(0.0008).buffer(-0.0008)
    ds.append(feat(u, {"name":d, "level":"district", "city":"Karachi"}, 0.0015))
out["karachi_districts"] = FC(ds)

# ------------------------------------------------------------------ lahore ---
ld = json.loads(B.read(PB + "lahore_district_boundary.geojson"))
out["lahore_district"] = FC([feat(shape(ld["features"][0]["geometry"]),
    {"name":"Lahore", "level":"district", "city":"Lahore"}, 0.002)])
vor = json.loads(B.read(PB + "lahore_locality_voronoi.geojson"))
out["lahore_localities"] = FC([{"type":"Feature","properties":{
    "name": f["properties"].get("name"),
    "area_km2": round(f["properties"].get("area_sqkm") or 0, 2),
    "level":"locality","city":"Lahore","method":"voronoi"},
    "geometry": rnd(simp(f["geometry"], 0.0009))} for f in vor["features"]])
pts_ = json.loads(B.read(PB + "lahore_locality_points.geojson"))
out["lahore_points"] = FC([{"type":"Feature",
    "properties":{"name": f["properties"].get("name")},
    "geometry": rnd(f["geometry"])} for f in pts_["features"]])

# --------------------- lahore tehsils, derived from the 27-08-2024 notification
EST = json.load(open(p("lahore_revenue_estates.json")))
HINTS = {"Bahria Town":"Raiwind","Jubilee Town":"Raiwind","Tricon Village":"Raiwind",
 "LDA Avenue":"Allama Iqbal","Samanabad":"Lahore City","Gulshan-e-Ravi":"Lahore City",
 "Gulshan Ravi":"Lahore City","Johar Town":"Model Town","Garden Town":"Model Town",
 "Wapda Town":"Model Town","Raj Garh":"Lahore City"}
STOP = r"\b(rakh|chak|theh|arazi|asal|kalan|khurd|wala|kay|pur|pura|abad|town|colony|scheme|phase|block)\b"
def norm(s):
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii","ignore").decode().lower()
    return re.sub(r"\s+", " ", re.sub(r"[^a-z ]", " ", re.sub(STOP, " ", s))).strip()
EMAP = {}
for t, lst in EST.items():
    for e in lst:
        EMAP.setdefault(norm(e), t); EMAP.setdefault(norm(e).replace(" ",""), t)
items = []
for f in vor["features"]:
    nm = f["properties"].get("name") or ""; t = None
    for k, v in HINTS.items():
        if k.lower() in nm.lower(): t = v; break
    if not t:
        n = norm(nm); t = EMAP.get(n) or EMAP.get(n.replace(" ",""))
    if not t and len(norm(nm)) > 3:
        key = norm(nm)
        for ek, ev in EMAP.items():
            if len(ek) > 4 and (ek in key or key in ek): t = ev; break
    c = shape(f["geometry"]).centroid
    items.append(dict(f=f, x=c.x, y=c.y, t=t, seed=t is not None))
seeds = [(i["x"], i["y"], i["t"]) for i in items if i["seed"]]
print("· tehsil seeds matched: %d / %d" % (len(seeds), len(items)))
for it in items:
    if not it["seed"]:
        it["t"] = min(seeds, key=lambda s: (s[0]-it["x"])**2 + (s[1]-it["y"])**2)[2]
for _ in range(6):                                   # k-NN majority smoothing
    new = [i["t"] for i in items]
    for i, it in enumerate(items):
        if it["seed"]: continue
        d = sorted(((it["x"]-o["x"])**2 + (it["y"]-o["y"])**2, o["t"])
                   for j, o in enumerate(items) if j != i)[:9]
        new[i] = Counter(t for _, t in d).most_common(1)[0][0]
    for it, t in zip(items, new): it["t"] = t
grp = {}
for it in items: grp.setdefault(it["t"], []).append(it)
tf = []
for t, lst in grp.items():
    u = unary_union([shape(i["f"]["geometry"]).buffer(0) for i in lst])
    u = u.buffer(0.0035).buffer(-0.0035)
    tf.append(feat(u, {"name":t, "level":"tehsil", "city":"Lahore",
        "localities":len(lst), "seeds":sum(1 for i in lst if i["seed"]),
        "method":"derived"}, 0.0013))
out["lahore_tehsils"] = FC(tf)

# ------------------------------------- lahore, the five census tehsils -------
# The model prices the five 2023 census tehsils. The derived layer above is the
# ten 2024-notification tehsils — a different administrative vintage, and only
# five of its names collide with the census ones, which left 59% of Lahore
# undrawn whenever the map grouped by census unit. OSM carries the five census
# tehsils as real boundaries, so those are used for anything joined to census or
# dealership data; the derived ten stay available as their own level.
LHE_CENSUS = {"Lahore City Tehsil": "Lahore City",
              "Model Town Tehsil": "Model Town",
              "Shalimar Tehsil": "Shalimar",
              "Lahore Cantonment Tehsil": "Lahore Cantt",
              "Raiwind Tehsil": "Raiwind"}
lhe = overpass("lahore_census_tehsils", """
[out:json][timeout:300];
(relation["boundary"="administrative"]["admin_level"="7"](31.20,74.00,31.80,74.75););
out geom;""")
lf = []
for e in lhe["elements"]:
    n = osm_name(e)
    if n not in LHE_CENSUS:
        continue
    g = osm_geom(e)
    if g is None:
        continue
    lf.append(feat(g, {"name": LHE_CENSUS[n], "level": "tehsil", "city": "Lahore",
                       "source": "osm", "vintage": "2023 census"}, 0.0012))
out["lahore_census_tehsils"] = FC(lf)
print("   lahore census tehsils: %d of 5" % len(lf))

# ------------------------------------------------------------------ multan ---
# The four tehsils carry exactly the names the model prices.
mux = by_district("Multan")
out["multan_tehsils"] = FC([feat(shape(f["geometry"]), {
    "name": f["properties"]["Tehsil"], "level":"tehsil", "city":"Multan"},
    0.0012) for f in mux])
out["multan_district"] = FC([feat(
    unary_union([shape(f["geometry"]).buffer(0) for f in mux]),
    {"name":"Multan", "level":"district", "city":"Multan"}, 0.0015)])

# --------------------------------------------------------------- islamabad ---
# ICT is one district. The model's urban/rural split follows the census's own
# urban/rural classification, which is not a published boundary — so it is not
# drawn. Both territories are still listed against the whole-city polygon.
isb = by_district("Islamabad")
out["islamabad_district"] = FC([feat(
    unary_union([shape(f["geometry"]).buffer(0) for f in isb]),
    {"name":"Islamabad", "level":"district", "city":"Islamabad",
     "note":"ICT is a single district; the model's urban/rural split is a "
            "census classification, not a boundary"}, 0.0015)])

# ---------------------------------------------------------------- peshawar ---
# The source admin layer still uses the old Town-I..IV structure, which does not
# crosswalk to the model's territories. OSM carries the current seven tehsils
# under the model's own names, so those are used and unioned into the four
# commercial groups documented in Dealer_Fee_Schedule_PumpPoints.docx.
PEW_GROUP = {"Peshawar City Tehsil":"Peshawar City",
             "Chamkani Tehsil":"East Ring",      "Shah Alam Tehsil":"East Ring",
             "Mathra Tehsil":"North-West Ring",  "Peshtakhara Tehsil":"North-West Ring",
             "Badabher Tehsil":"South Belt",     "Hassan Khel Tehsil":"South Belt"}
pew = overpass("peshawar_tehsils", """
[out:json][timeout:300];
(relation["boundary"="administrative"]["admin_level"="7"](33.72,71.29,34.20,71.86););
out geom;""")
pf, pg = [], {}
for e in pew["elements"]:
    n = osm_name(e)
    if n not in PEW_GROUP: continue
    g = osm_geom(e)
    if g is None: continue
    pf.append(feat(g, {"name": n.replace(" Tehsil",""), "group": PEW_GROUP[n],
                       "level":"tehsil", "city":"Peshawar", "source":"osm"}, 0.0012))
    pg.setdefault(PEW_GROUP[n], []).append(g)
out["peshawar_tehsils"] = FC(pf)
out["peshawar_groups"] = FC([feat(unary_union(v).buffer(0),
    {"name":k, "level":"territory", "city":"Peshawar", "source":"osm",
     "tehsils":len(v)}, 0.0013) for k, v in pg.items()])
out["peshawar_district"] = FC([feat(
    unary_union([g for v in pg.values() for g in v]).buffer(0),
    {"name":"Peshawar", "level":"district", "city":"Peshawar"}, 0.0015)])

# ---------------------------------------- one polygon per city, for the map ---
CITY_OF = {"Karachi": out["karachi_districts"], "Lahore": out["lahore_district"],
           "Multan": out["multan_district"], "Islamabad": out["islamabad_district"],
           "Peshawar": out["peshawar_district"]}
out["cities"] = FC([feat(
    unary_union([shape(f["geometry"]).buffer(0) for f in fc["features"]]).buffer(0),
    {"name": city, "level": "city", "city": city}, 0.002)
    for city, fc in CITY_OF.items()])

# ------------------------------------------ neighbourhoods, all five cities ---
# This is the layer that lets you zoom past a district into Clifton or Defence.
# OSM coverage is uneven by city and nothing here carries a census statistic.
BBOX = {"Karachi":   "24.70,66.55,25.65,67.60",
        "Lahore":    "31.25,74.10,31.75,74.70",
        "Islamabad": "33.40,72.75,33.85,73.35",
        "Peshawar":  "33.72,71.29,34.20,71.86",
        "Multan":    "29.95,71.20,30.45,71.75"}
AREA_Q = """
[out:json][timeout:300];
(
  relation["boundary"="administrative"]["admin_level"~"^(9|10|11)$"](%(b)s);
  way["boundary"="administrative"]["admin_level"~"^(9|10|11)$"](%(b)s);
  relation["place"~"^(suburb|neighbourhood|quarter)$"](%(b)s);
  way["place"~"^(suburb|neighbourhood|quarter)$"](%(b)s);
);
out geom;"""
areas = []
for city, bb in BBOX.items():
    d = overpass(city.lower() + "_areas_geom", AREA_Q % {"b": bb}, required=False)
    if d is None:
        continue
    kept = 0
    for e in d["elements"]:
        n = osm_name(e)
        if not n: continue
        g = osm_geom(e)
        if g is None or g.is_empty: continue
        a = km2(g)
        if a < 0.05 or a > 900: continue          # drop slivers and stray regions
        t = e.get("tags", {})
        areas.append(feat(g, {
            "name": n, "city": city, "level": "area", "source": "osm",
            "kind": t.get("place") or ("admin%s" % t.get("admin_level"))}, 0.0004, 5))
        kept += 1
    print("   %-10s %4d areas" % (city, kept))
out["city_areas"] = FC(areas)

json.dump(out, open(p("pakistan_urban_geo.json"), "w"), separators=(',', ':'))
print("✓ pakistan_urban_geo.json rebuilt (%.2f MB)"
      % (os.path.getsize(p("pakistan_urban_geo.json")) / 1e6))
for k, v in out.items(): print("   %-20s %d features" % (k, len(v["features"])))
print("  now run:  python refresh.py")
