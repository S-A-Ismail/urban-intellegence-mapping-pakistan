-- 004 — gold: metric definitions and facts
--
-- Long format, one row per (geo_id, metric_id, period).
--
-- Why long and not wide: a wide table needs a migration for every new
-- indicator. Long needs an INSERT. Adding "median asking price per sq ft,
-- monthly" is one metric row and a load. The nine census layers in the current
-- map, the 2023-2030 household projections, listing prices, POI density and any
-- internal sales figure all live in these two tables — and the frontend's layer
-- registry stops being code and becomes data.

create table if not exists gold.metric (
  metric_id    text primary key,            -- 'pop', 'hh', 'hh_new', 'price_sqft_med'
  label        text not null,
  unit         text,                        -- 'people', 'households', 'PKR/sqft', '%', 'km2'
  agg          text not null check (agg in ('sum','mean','median','rate','ratio','count')),

  -- Derived metrics name their parts rather than being precomputed blind, so a
  -- ratio can be re-derived correctly at any level instead of being averaged.
  numerator_id   text references gold.metric(metric_id),
  denominator_id text references gold.metric(metric_id),

  source_id    text not null references src.source(source_id),
  sensitivity  text not null default 'public'
                 check (sensitivity in ('public','internal','commercial')),
  min_geography text references geo.level(level),
  k_threshold  int  not null default 1,

  -- Presentation defaults, so a new layer needs no frontend change.
  fmt          text,                        -- 'int','pct1','money_lakh','dec1'
  ramp         text,                        -- named palette in the client registry
  flat_guard   numeric default 0.05,        -- shade flat below this relative spread
  extrudable   boolean not null default true,
  sort_order   int,
  note         text
);

comment on column gold.metric.sensitivity is
  'The access-control seam. Replaces the FORBIDDEN key check in refresh.py: a static file cannot keep a secret, so commercial figures are kept out of the bundle by RLS instead of by a build-time assertion.';
comment on column gold.metric.agg is
  'How this metric combines upward. sum aggregates; mean/median/rate/ratio must be recomputed from numerator and denominator, never averaged across units of unequal size.';
comment on column gold.metric.flat_guard is
  'Carried over from the current map: where every value in view sits within this relative spread, shade flat and state the spread rather than stretching a rounding difference across the whole palette.';

create table if not exists gold.fact (
  geo_id     text    not null references geo.unit(geo_id) on delete cascade,
  metric_id  text    not null references gold.metric(metric_id) on delete cascade,
  period     date    not null,                 -- year as YYYY-01-01, or month
  value      numeric,
  n          integer,                          -- underlying record count, for suppression
  accuracy   text    not null default 'official'
               check (accuracy in ('official','derived','approximate','apportioned')),
  basis      text,                             -- set when accuracy = 'apportioned'
  run_id     bigint  not null references src.ingest_run(run_id),
  primary key (geo_id, metric_id, period)
);

comment on column gold.fact.accuracy is
  'apportioned means the value was reallocated across a vintage change via geo.crosswalk. basis records how. Invariant 4: this travels with the number all the way to the CSV.';

create index if not exists fact_metric_idx on gold.fact (metric_id, period);
create index if not exists fact_geo_idx    on gold.fact (geo_id, period);

-- Convenience: the current value of every metric for a unit, with its caveats
-- already attached. Used by the selection panel.
create or replace view gold.v_fact_annotated as
  select f.geo_id, f.metric_id, f.period, f.value, f.n,
         f.accuracy      as value_accuracy,
         f.basis,
         u.accuracy      as geometry_accuracy,
         u.accuracy_note as geometry_note,
         u.area_km2, u.area_km2_ref,
         case when u.area_km2_ref is null or u.area_km2_ref = 0 then null
              else (u.area_km2 - u.area_km2_ref) / u.area_km2_ref
         end             as area_gap,
         m.label, m.unit, m.agg, m.sensitivity, m.fmt,
         f.run_id
  from gold.fact f
  join gold.metric m on m.metric_id = f.metric_id
  join geo.unit    u on u.geo_id    = f.geo_id;

comment on view gold.v_fact_annotated is
  'A figure and its caveats in one row: value accuracy, geometry accuracy, and the gap between computed and published area. The current CSV export already refuses to separate these; here it is the default shape.';
