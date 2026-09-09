-- 007 — the API surface
--
-- The only schema exposed to PostgREST. Every view is security_invoker so the
-- policies in 006 still apply; every function is `security invoker` for the
-- same reason. Nothing here uses SECURITY DEFINER — a definer function over
-- gold.fact would hand a viewer the commercial metrics that 006 exists to
-- withhold.

-- ------------------------------------------------------------- reference

create or replace view api.level with (security_invoker = true) as
  select level, depth, label, is_admin, note from geo.level;

create or replace view api.metric with (security_invoker = true) as
  select metric_id, label, unit, agg, numerator_id, denominator_id,
         min_geography, k_threshold, fmt, ramp, flat_guard, extrudable,
         sort_order, note, sensitivity
  from gold.metric;

comment on view api.metric is
  'The frontend layer registry, served as data. Adding a layer to the map is an INSERT here, not a code change — this is what LAYERS in map_template.html becomes.';

-- Units without geometry. Geometry reaches the client as PMTiles, not as JSON;
-- this is for pickers, breadcrumbs and the selection panel.
create or replace view api.unit with (security_invoker = true) as
  select u.geo_id, u.level, u.name, u.city, u.parent_id,
         u.valid_from, u.valid_to, u.vintage_label,
         u.accuracy, u.accuracy_note, u.area_km2, u.area_km2_ref,
         case when u.area_km2_ref is null or u.area_km2_ref = 0 then null
              else (u.area_km2 - u.area_km2_ref) / u.area_km2_ref
         end as area_gap,
         extensions.ST_X(u.label_point) as label_lon,
         extensions.ST_Y(u.label_point) as label_lat
  from geo.unit u;

-- Source registry minus the operator's private columns.
create or replace view api.source with (security_invoker = true) as
  select source_id, name, publisher, kind, legal_basis,
         permits_redistribution, pii_class, min_geography, refresh_cadence
  from src.source
  where enabled;

-- ------------------------------------------------------------ attributes
--
-- The read path behind every choropleth and every extrusion height. Returns a
-- compact (geo_id, value) set the client joins onto PMTiles features by feature
-- state. Attributes deliberately never enter a tile (invariant 7): changing the
-- metric or the year is then a small fetch rather than a tile rebuild, and a
-- commercial metric is never baked into a public file.

create or replace function api.attributes(
  p_level     text,
  p_metric_id text,
  p_period    date,
  p_city      text default null
)
returns table (
  geo_id   text,
  value    numeric,
  n        integer,
  accuracy text,
  basis    text
)
language sql stable security invoker
set search_path = public, extensions
as $fn$
  select f.geo_id, f.value, f.n, f.accuracy, f.basis
  from gold.fact f
  join geo.unit u on u.geo_id = f.geo_id
  where u.level = p_level
    and u.valid_to is null
    and (p_city is null or u.city = p_city)
    and f.metric_id = p_metric_id
    and f.period = p_period;
$fn$;

-- ----------------------------------------------------------------- drill
--
-- Drill reads geo.containment, not a hardcoded ladder. Karachi's Towns do not
-- nest inside the census talukas, so children come back with the fraction of
-- each that actually falls inside the parent. Partial containment is reported,
-- never hidden.

create or replace function api.children(
  p_geo_id       text,
  p_level        text,
  p_min_coverage numeric default 0.05
)
returns table (
  geo_id   text,
  name     text,
  level    text,
  coverage numeric,
  partial  boolean,
  accuracy text
)
language sql stable security invoker
set search_path = public, extensions
as $fn$
  select c.child_id, u.name, u.level, c.coverage,
         c.coverage < 0.999 as partial,
         u.accuracy
  from geo.containment c
  join geo.unit u on u.geo_id = c.child_id
  where c.ancestor_id = p_geo_id
    and u.level = p_level
    and u.valid_to is null
    and c.coverage >= p_min_coverage
  order by u.name;
$fn$;

-- ------------------------------------------------------- polygon rollup
--
-- Draw a shape, get the numbers. This is where an analytics tool usually starts
-- lying, so three things come back beside every value:
--
--   coverage          fraction of the drawn polygon covered by units that carry
--                     this metric. A cluster over ground with no data reads as
--                     partial coverage, not as a small total.
--   apportioned_share fraction of the value contributed by units only partly
--                     inside the polygon. Zero means the answer is exact.
--   basis_used        how the split was made, and at which level.
--
-- Splitting a unit by AREA assumes uniform density inside it. That is false
-- everywhere and badly false here: Bahria Town Karachi is 186 km2 at roughly 91
-- people per km2, and area-weighting it against a dense neighbour would invent
-- tens of thousands of households. The mitigation is to descend — with
-- p_basis = 'finest' the rollup runs at the finest level that carries the
-- metric, so most units are wholly in or wholly out and only the fringe is
-- apportioned.

create or replace function api.rollup_polygon(
  p_geojson jsonb,
  p_level   text,
  p_metrics text[],
  p_period  date,
  p_basis   text default 'finest'
)
returns table (
  metric_id         text,
  label             text,
  unit              text,
  agg               text,
  value             numeric,
  level_used        text,
  basis_used        text,
  coverage          numeric,
  apportioned_share numeric,
  units_touched     integer,
  units_with_data   integer,
  suppressed        boolean,
  note              text
)
language plpgsql stable security invoker
set search_path = public, extensions
as $fn$
declare
  v_draw      extensions.geometry;
  v_draw_area numeric;
  v_level     text := p_level;
  v_depth     smallint;
begin
  v_draw := extensions.ST_MakeValid(
              extensions.ST_SetSRID(extensions.ST_GeomFromGeoJSON(p_geojson::text), 4326));

  if v_draw is null or extensions.ST_IsEmpty(v_draw) then
    raise exception 'rollup_polygon: empty or unparseable geometry';
  end if;
  if extensions.ST_Dimension(v_draw) <> 2 then
    raise exception 'rollup_polygon: need a polygon, got %', extensions.ST_GeometryType(v_draw);
  end if;

  v_draw_area := extensions.ST_Area(v_draw::extensions.geography);
  if v_draw_area <= 0 then
    raise exception 'rollup_polygon: zero-area polygon';
  end if;

  select depth into v_depth from geo.level where level = p_level;

  -- Descend to the finest level that actually carries these metrics for this
  -- period. Fewer straddled units means less apportionment and less error.
  if p_basis = 'finest' then
    select l.level into v_level
    from geo.level l
    where l.depth >= v_depth
      and exists (
        select 1 from gold.fact f
        join geo.unit u on u.geo_id = f.geo_id
        where u.level = l.level
          and u.valid_to is null
          and f.metric_id = any(p_metrics)
          and f.period = p_period
      )
    order by l.depth desc
    limit 1;
    v_level := coalesce(v_level, p_level);
  end if;

  return query
  with w as (
    select u.geo_id,
           extensions.ST_Area(u.geom::extensions.geography) as unit_area,
           extensions.ST_Area(
             extensions.ST_Intersection(u.geom, v_draw)::extensions.geography) as inter_area
    from geo.unit u
    where u.level = v_level
      and u.valid_to is null
      and extensions.ST_Intersects(u.geom, v_draw)
  ),
  wf as (
    select geo_id, unit_area, inter_area,
           case when unit_area > 0 then least(inter_area / unit_area, 1.0) else 0 end as frac
    from w
    where inter_area > 0
  ),
  touched as (select count(*)::int as c from wf),
  contrib as (
    select m.metric_id, m.label, m.unit, m.agg, m.k_threshold, m.min_geography,
           wf.geo_id, wf.frac, wf.inter_area, wf.unit_area,
           f.value, f.n,
           -- weight for non-additive metrics: the metric's own denominator
           -- where one is declared, otherwise unit area
           coalesce(d.value, wf.unit_area / 1e6) as wt
    from gold.metric m
    cross join wf
    join gold.fact f
      on f.geo_id = wf.geo_id and f.metric_id = m.metric_id and f.period = p_period
    left join gold.fact d
      on d.geo_id = wf.geo_id and d.metric_id = m.denominator_id and d.period = p_period
    where m.metric_id = any(p_metrics)
  )
  select
    c.metric_id,
    c.label,
    c.unit,
    c.agg,
    case
      when bool_or(c.n is not null and c.n < c.k_threshold) then null
      when ml.depth > coalesce(mg.depth, 99)                then null
      when c.agg = 'sum' then sum(c.value * c.frac)
      else sum(c.value * c.wt * c.frac) / nullif(sum(c.wt * c.frac), 0)
    end,
    v_level,
    case when sum(case when c.frac < 0.999 then 1 else 0 end) = 0
         then 'exact' else 'area@' || v_level end,
    least(sum(c.inter_area) / v_draw_area, 1.0),
    case when c.agg = 'sum'
         then coalesce(sum(c.value * c.frac) filter (where c.frac < 0.999)
                       / nullif(sum(c.value * c.frac), 0), 0)
         else coalesce(sum(c.wt * c.frac) filter (where c.frac < 0.999)
                       / nullif(sum(c.wt * c.frac), 0), 0)
    end,
    (select t.c from touched t),
    count(*)::int,
    bool_or(c.n is not null and c.n < c.k_threshold)
      or ml.depth > coalesce(mg.depth, 99),
    case
      when bool_or(c.n is not null and c.n < c.k_threshold)
        then 'suppressed: a contributing unit has fewer than ' || max(c.k_threshold) || ' records'
      when ml.depth > coalesce(mg.depth, 99)
        then 'suppressed: this metric may not be published below ' || max(c.min_geography)
      when sum(case when c.frac < 0.999 then 1 else 0 end) = 0
        then 'exact — the polygon covers whole units only'
      else 'estimated — partly covered units apportioned by area at ' || v_level
    end
  from contrib c
  join geo.level ml on ml.level = v_level
  left join geo.level mg on mg.level = c.min_geography
  group by c.metric_id, c.label, c.unit, c.agg, ml.depth, mg.depth;
end
$fn$;

comment on function api.rollup_polygon is
  'Invariant 4 in function form: no value is returned without its coverage, its apportioned share and the basis used. A drawn-cluster figure is an estimate and says so.';

-- Selections need no apportionment at all — whole units, exact arithmetic. This
-- is the right way to define anything contractual.
create or replace function api.rollup_selection(
  p_cluster_id uuid,
  p_metrics    text[],
  p_period     date
)
returns table (
  metric_id text, label text, unit text, agg text,
  value numeric, units integer, accuracy text
)
language sql stable security invoker
set search_path = public, extensions
as $fn$
  select m.metric_id, m.label, m.unit, m.agg,
         case when m.agg = 'sum' then sum(f.value)
              else sum(f.value * coalesce(d.value, 1)) / nullif(sum(coalesce(d.value, 1)), 0)
         end,
         count(*)::int,
         case when bool_or(f.accuracy <> 'official') then 'mixed' else 'official' end
  from app.cluster_member cm
  join gold.fact f on f.geo_id = cm.geo_id and f.period = p_period
  join gold.metric m on m.metric_id = f.metric_id
  left join gold.fact d
    on d.geo_id = cm.geo_id and d.metric_id = m.denominator_id and d.period = p_period
  where cm.cluster_id = p_cluster_id
    and m.metric_id = any(p_metrics)
  group by m.metric_id, m.label, m.unit, m.agg;
$fn$;

-- ------------------------------------------------------------- live tiles
--
-- Base geometry is served as PMTiles from cPanel: one static file, HTTP Range,
-- no tile server. Only geometry that is small, per-org and constantly changing
-- comes from the database — which means drawn clusters, and nothing else.

create or replace function api.cluster_tile(z integer, x integer, y integer)
returns bytea
language plpgsql stable security invoker
set search_path = public, extensions
as $fn$
declare
  env3857 extensions.geometry := extensions.ST_TileEnvelope(z, x, y);
  env4326 extensions.geometry := extensions.ST_Transform(env3857, 4326);
  mvt     bytea;
begin
  select extensions.ST_AsMVT(t, 'clusters', 4096, 'geom')
  into mvt
  from (
    select c.cluster_id::text as id,
           c.name,
           c.kind,
           c.colour,
           extensions.ST_AsMVTGeom(
             extensions.ST_Transform(c.geom, 3857), env3857, 4096, 64, true) as geom
    from app.cluster c
    where c.geom is not null
      and c.geom && env4326
  ) t;

  return coalesce(mvt, ''::bytea);
end
$fn$;

comment on function api.cluster_tile is
  'RLS on app.cluster still applies because this is security invoker: a drawn cluster is visible only to its own org, tiles included.';

grant execute on function
  api.attributes(text, text, date, text),
  api.children(text, text, numeric),
  api.rollup_polygon(jsonb, text, text[], date, text),
  api.rollup_selection(uuid, text[], date),
  api.cluster_tile(integer, integer, integer)
to authenticated;
