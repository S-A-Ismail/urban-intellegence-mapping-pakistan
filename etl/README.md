# ETL

Runs **off cPanel** — GitHub Actions on a schedule, a VPS, or a workstation.
See [DEPLOYMENT_CPANEL.md](../docs/DEPLOYMENT_CPANEL.md) for why that is a
constraint rather than a preference.

Python, as the rest of this repo already is. Holds `service_role`, so it is the
only component that bypasses RLS.

Status: **contract written, nothing implemented.**

---

## Connector contract

One module per source under `connectors/`, named in
`warehouse/sources/registry.yml`. Each exposes:

```python
def fetch(run: Run, since: date | None) -> Iterator[Raw]:
    """Yield raw records exactly as the source gave them.

    No parsing beyond what is needed to split records apart. No cleaning, no
    renaming, no dropping. Whatever this yields is what lands in bronze, and
    silver must be reproducible from it.
    """

def conform(raw: Raw, run: Run) -> Iterator[Observation]:
    """Map one raw record onto silver.observation.

    Geocode, snap to the geo_id valid AS OF observed_at, compute H3 r8/r9,
    score geocode quality, and drop every attribute the registry says must not
    be persisted — seller names and phone numbers included, licence or no
    licence.
    """
```

The runner supplies the `Run`, writes bronze, calls `conform`, upserts silver,
and closes `src.ingest_run`. A connector never writes to the database itself and
never touches gold.

### Rules the runner enforces

1. **Refuse a disabled source.** `src.source.enabled = false` is a hard stop,
   not a warning.
2. **Record the digest.** sha256 of the raw payload into
   `ingest_run.input_digest`, and the git sha into `code_version`. A gold fact
   that cannot be traced to both is a bug.
3. **Set `expires_at`** from `src.source.retention_days` on every bronze row.
4. **Never delete bronze** except through `bronze.purge_expired()`.
5. **`--dry-run` writes bronze and stops**, so a new connector can be inspected
   before it reaches silver.

---

## Jobs

| Job | Cadence | Does |
|---|---|---|
| `sync_registry` | on change | upserts `registry.yml` into `src.source` |
| `ingest <source>` | per source | fetch → bronze → silver |
| `build_gold` | after ingest | silver → `gold.fact`, applies crosswalks |
| `rebuild_containment` | after any geo load | `select geo.rebuild_containment()` |
| `build_tiles` | after any geo load | tippecanoe → `*.pmtiles` |
| `purge` | daily | `bronze.purge_expired()` |
| `check` | after every run | the guards below |

### Guards

Run after every load; a failure fails the job.

```sql
-- Invariant 3: crosswalk weights sum to 1 per source unit.
select * from geo.v_crosswalk_check where not ok;

-- Invariant 2: no unlabelled derived geometry.
select geo_id from geo.unit where accuracy <> 'official' and accuracy_note is null;

-- Invariant 1: every fact traces to a run.
select f.* from gold.fact f
  left join src.ingest_run r on r.run_id = f.run_id where r.run_id is null;

-- Orphaned facts: a metric whose source is no longer enabled.
select distinct m.metric_id from gold.metric m
  join src.source s on s.source_id = m.source_id where not s.enabled;
```

---

## Tiles

`build_tiles` writes one PMTiles archive per city plus the basemap.

**Features carry `geo_id` and `level`. Nothing else.** No population, no price,
no name that is not needed for label placement. Attributes arrive separately
from `api.attributes` and are joined client-side (invariant 7), which is what
keeps a commercial metric out of a public file and lets a year change without a
tile rebuild.

```bash
tippecanoe -o karachi.pmtiles \
  --no-tile-compression \
  -Z6 -z16 --drop-densest-as-needed \
  -L districts:districts.geojson \
  -L towns:towns.geojson \
  -L neighbourhoods:neighbourhoods.geojson
```

`--no-tile-compression` matters: the server must not be compressing these
either, and mismatched expectations here produce the same blank map as a
misconfigured `.htaccess`.

Output filenames are content-hashed so they can be cached immutably.

---

## Seed

`seed/` reloads the existing artefacts as the first warehouse content —
`pakistan_urban_geo.json` into `geo.unit`, `scenario_a.json` into `gold.fact`,
`dealership_clusters.json` into `app.cluster`.

**The acceptance test is a diff against `scenario_a.json`.** The warehouse must
reproduce the current map's figures exactly. If it does not, the load is wrong,
and finding that out at seed time is very much cheaper than finding it out after
three more layers are built on top.

Per-unit `accuracy` is not guesswork — the existing gotchas already record it:
Karachi districts crosswalked from a 2022 town layer (`approximate`, with the
per-district area gaps), Lahore's ten tehsils derived from revenue estates
(`derived`), the locality cells Voronoi (`derived`), Peshawar's groups unioned
from OSM tehsils (`derived`), Islamabad's urban/rural split unmappable and
therefore both territories against the whole-city shape.
