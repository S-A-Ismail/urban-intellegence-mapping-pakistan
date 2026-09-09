# Data sources — what goes in the warehouse, and on what basis

Companion to [ARCHITECTURE.md](ARCHITECTURE.md) §5. The machine-readable form is
[`warehouse/sources/registry.yml`](../warehouse/sources/registry.yml); the
enforcement point is `src.source` in
[`003_sources.sql`](../warehouse/schema/003_sources.sql).

---

## The gate

`src.source.enabled` defaults to **false**, and a CHECK constraint refuses to
let it become true without a `license_ref` and a named `enabled_by`. Connectors
refuse to run against a disabled source.

This is a small amount of deliberate friction in exactly the place where a data
platform normally acquires its worst liabilities: someone writes a scraper on a
Friday, it works, and two years later nobody remembers that the terms of use
said no. Making the licence a foreign key means the answer to "on what basis do
we hold this?" is a `SELECT`, not an archaeology project.

It also keeps the build moving. Census, boundaries and the internal model are
enabled today and are enough to stand the whole platform up. The gated sources
slot in behind an interface that already exists.

---

## The five named in the brief

### Census — enabled

Already the backbone. Nothing changes except that it lands in a warehouse with
provenance instead of a workbook.

One correction worth keeping visible, because it has been got wrong here before:
**PBS Table 20 does not give the house-versus-flat split.** It reports Pakka /
Semi-Pakka / Kacha — construction material. No PBS table publishes house versus
apartment by district. That split remains an assumption with the largest blast
radius in the model, and the fix is building approvals or utility connection
counts, not another census table.

### Google — enabled with a retention clock

Maps Platform terms restrict caching of Places content. Rather than remember
that, the schema enforces it: `retention_days: 30` drives
`bronze.record.expires_at`, and `bronze.purge_expired()` deletes the raw content
on schedule. Derived aggregates already written to gold survive the purge, so
the warehouse keeps *"cafés per km²"* without keeping Google's content.

Confirm the current terms before enabling. They change, and the number in the
registry is a starting assumption, not a citation.

### NADRA — not a bulk source, and the design does not pretend otherwise

NADRA does not provide bulk citizen or household data. There is no public feed,
and a platform built on the assumption that one will appear is a platform built
on sand. Household-level registry data would also be **direct PII**, which the
`source_pii_gate` constraint refuses to store at all.

What is genuinely obtainable and genuinely useful:

- **NADRA's published aggregate statistics**, under a written arrangement.
- **ECP electoral-roll counts by block code** — public, aggregate, and joinable
  straight onto census block geography. Registered voters per block is a decent
  independent check on census household counts and a good proxy for adult
  occupancy, which is exactly the signal a registry source was wanted for.

Both are modelled as `kind='registry'`, `pii_class='none'`,
`min_geography='block'`, `k_threshold=25`. The individual electoral roll is out
of scope and is not to be ingested in any form.

This is not a refusal to build the feature. It is the same feature, sourced from
the aggregate series that actually exist.

### OLX and Zameen — the interface is ready, the licence is not

Neither publishes a bulk API, and both prohibit scraping in their terms. Two
things follow.

**What works today:** Zameen publishes aggregate area-level price indices. That
is a real, usable, licensable signal, and at neighbourhood level it is close to
what a price layer needs anyway.

**What needs a conversation:** listing-level data, via a licensed feed or a data
partnership. Worth having — asking price per square foot at listing resolution
would be the single best proxy for the ASP tier multipliers the model currently
assumes at ×8 / ×3 / ×1.6 / ×1.

The connector interface is identical for both routes, so a source moves from
index to feed with a registry edit and a new connector module. Nothing in
silver, gold, the API or the frontend changes.

**If listing data does arrive:** OLX listings carry seller names and phone
numbers. That is indirect PII and it is dropped at silver — `pii_class:
indirect` in the registry, and the connector keeps only price, area, type,
bedrooms and location. Contact details are never persisted, licence or no
licence.

---

## The two that are worth more than any of them

Both are already documented in the model as the highest-blast-radius unknowns,
and neither needs a scraper — they need a letter.

**Building approvals** (SBCA / LDA / CDA / PDA / MDA) would replace the
house-versus-flat share assumption outright. That assumption currently ranges
35–95% by region and drives the pump-point arithmetic that the whole fee
schedule rests on.

**Utility connection counts** by block — house meters versus bulk meters — get
to the same answer faster. A bulk meter implies a building; a domestic meter
implies a house. Request aggregate counts by block, never the connection
register, which identifies premises.

---

## Privacy model

Three mechanisms, all enforced in the schema rather than in a policy document:

| Mechanism | Column | Effect |
|---|---|---|
| Classification | `src.source.pii_class` | `direct` cannot be stored at all (`source_pii_gate`) |
| Minimum geography | `gold.metric.min_geography` | a metric is not returned below its coarsest permitted level |
| k-anonymity | `gold.metric.k_threshold`, `gold.fact.n` | a cell with fewer than k records returns `null` and a reason |

`api.rollup_polygon` applies the last two on the read path and returns
`suppressed = true` with a note, rather than a plausible-looking number. A user
drawing a small polygon over a sparse area gets told the answer is suppressed —
which is the honest outcome, and the one that stops a listings-derived layer
from becoming a re-identification tool by accident.

H3 cells (`silver.observation.h3_r8` / `h3_r9`) are the aggregation unit of
choice for anything point-derived: a fixed grid that does not move when a tehsil
is redrawn, and a natural place to apply suppression.

---

## Attribution obligations

OSM boundaries are **ODbL**. Two consequences that are easy to miss:

1. Attribution must appear in the map UI, not only in a repo file.
2. Share-alike applies to a derived database that is *redistributed*. Internal
   use is unaffected; handing a client a boundary set as proprietary data is
   not.

The existing derived layers — the crosswalked Karachi districts, the Lahore
tehsils built from revenue estates, the Voronoi localities — are derived from
OSM and inherit this. Worth settling before any boundary file leaves the
building.

---

## Adding a source

1. Add a block to `registry.yml` with `enabled: false`.
2. Get the licence question answered. Record the answer in `license_ref`.
3. Write `etl/connectors/<name>.py` against the connector interface
   ([`etl/README.md`](../etl/README.md)).
4. Set `enabled: true` and `enabled_by: <person>`. Sync the registry.
5. Run once with `--dry-run`, inspect bronze, then let the schedule take it.

Steps 2 and 4 are the whole point. Everything else is typing.
