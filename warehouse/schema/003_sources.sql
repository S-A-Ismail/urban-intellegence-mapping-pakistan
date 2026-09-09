-- 003 — source registry, ingest runs, bronze and silver
--
-- src.source is the legal gate. See docs/DATA_SOURCES.md.
-- Nothing ingests until a source row exists with a legal basis AND someone
-- sets enabled = true. That is deliberate friction, aimed squarely at the
-- sources in the brief that are not straightforwardly public.

-- ------------------------------------------------------------ the registry

create table if not exists src.source (
  source_id   text primary key,                 -- 'pbs_census_2023', 'zameen_index'
  name        text not null,
  publisher   text not null,
  kind        text not null check (kind in
                ('census','registry','listings','poi','imagery','utility','authority','internal')),

  -- legal --------------------------------------------------------------
  legal_basis text not null check (legal_basis in
                ('public_domain','open_data','licensed','contract','internal','restricted')),
  license_ref text,                              -- URL, contract id, or licence file path
  permits_storage         boolean not null default false,  -- may raw records persist?
  permits_redistribution  boolean not null default false,  -- may derived output be shared?
  retention_days          int,                   -- null = indefinite; set where terms cap caching

  -- privacy ------------------------------------------------------------
  pii_class     text not null default 'none'
                check (pii_class in ('none','indirect','direct')),
  min_geography text references geo.level(level),  -- coarsest level this may be published at
  k_threshold   int  not null default 1,           -- suppress cells with fewer records

  -- operations ---------------------------------------------------------
  refresh_cadence interval,
  connector       text,                            -- python module under etl/connectors/
  enabled         boolean not null default false,
  enabled_by      text,
  enabled_at      timestamptz,
  notes           text,

  -- Invariant 5: no enabling without a recorded licence reference.
  constraint source_gate check (
    not enabled or (license_ref is not null and enabled_by is not null)
  ),
  -- A source holding direct identifiers may not be stored raw.
  constraint source_pii_gate check (
    pii_class <> 'direct' or permits_storage = false
  )
);

comment on table src.source is
  'The legal gate. enabled defaults to false; flipping it requires a license_ref and a named person. Connectors refuse to run against a disabled source.';
comment on column src.source.retention_days is
  'Where terms cap how long raw content may be cached, this drives bronze.record.expires_at and bronze.purge_expired(). Enforcement, not a reminder.';
comment on column src.source.min_geography is
  'Coarsest level at which anything derived from this source may be published. Read-path enforced in api (007), not by convention.';

-- Deferred FK from geo.unit — geo loads before sources on a cold start.
do $$
begin
  if not exists (select 1 from pg_constraint where conname = 'unit_source_fk') then
    alter table geo.unit
      add constraint unit_source_fk foreign key (source_id) references src.source(source_id);
  end if;
end
$$;

-- --------------------------------------------------------------- runs

create table if not exists src.ingest_run (
  run_id        bigserial primary key,
  source_id     text not null references src.source(source_id),
  started_at    timestamptz not null default now(),
  finished_at   timestamptz,
  status        text not null default 'running'
                  check (status in ('running','ok','failed','skipped')),
  rows_in       bigint,
  rows_out      bigint,
  input_digest  text,        -- sha256 of the raw payload
  code_version  text,        -- git sha of the ETL that produced it
  params        jsonb not null default '{}'::jsonb,
  error         text
);

comment on table src.ingest_run is
  'Invariant 1: every published figure resolves to a run, a digest and a code version. A gold fact with no reachable run is a bug, not a shortcut.';

create index if not exists run_source_idx on src.ingest_run (source_id, started_at desc);

-- ------------------------------------------------------------- bronze

create table if not exists bronze.record (
  record_id   bigserial primary key,
  run_id      bigint not null references src.ingest_run(run_id),
  source_id   text   not null references src.source(source_id),
  fetched_at  timestamptz not null default now(),
  natural_key text,                                     -- the source's own id, for dedupe
  payload     jsonb  not null,
  geom        extensions.geometry(Point, 4326),         -- when the source is point-located
  expires_at  date                                      -- from src.source.retention_days
);

comment on table bronze.record is
  'Raw payload exactly as fetched. Never edited. Silver must be reproducible from here plus a code version, or provenance is a fiction.';

create index if not exists bronze_src_idx     on bronze.record (source_id, fetched_at desc);
create index if not exists bronze_natkey_idx  on bronze.record (source_id, natural_key);
create index if not exists bronze_expiry_idx  on bronze.record (expires_at) where expires_at is not null;
create index if not exists bronze_geom_gix    on bronze.record using gist (geom) where geom is not null;

create or replace function bronze.purge_expired()
returns bigint
language plpgsql
as $fn$
declare n bigint;
begin
  delete from bronze.record where expires_at is not null and expires_at < current_date;
  get diagnostics n = row_count;
  return n;
end
$fn$;

comment on function bronze.purge_expired is
  'Run daily. Derived aggregates already in gold survive; the raw content does not. This is how a limited-caching licence is honoured rather than merely acknowledged.';

-- ------------------------------------------------------------- silver

create table if not exists silver.observation (
  obs_id      bigserial primary key,
  source_id   text not null references src.source(source_id),
  run_id      bigint not null references src.ingest_run(run_id),
  entity_type text not null,                  -- 'listing','poi','connection_agg','household_agg'
  natural_key text not null,
  observed_at date not null,                  -- when the fact was true, not when fetched

  geom        extensions.geometry(Point, 4326),
  h3_r8       text,                           -- computed in Python; no h3-pg on hosted Supabase
  h3_r9       text,
  geo_id      text references geo.unit(geo_id),   -- containing unit AS OF observed_at
  quality     smallint check (quality between 0 and 100),  -- geocode confidence

  attrs       jsonb not null default '{}'::jsonb,

  unique (source_id, natural_key, observed_at)
);

comment on column silver.observation.geo_id is
  'Resolved against the unit vintage valid on observed_at. A 2023 listing snaps to a 2023 tehsil, not to the 2024 redraw.';
comment on column silver.observation.attrs is
  'Source attributes stay in jsonb. Listing sites change their schema without notice and will not be filing a migration ticket.';

create index if not exists obs_geo_idx   on silver.observation (geo_id, observed_at);
create index if not exists obs_h3_idx    on silver.observation (h3_r8, observed_at);
create index if not exists obs_geom_gix  on silver.observation using gist (geom) where geom is not null;
create index if not exists obs_attrs_gin on silver.observation using gin (attrs);
