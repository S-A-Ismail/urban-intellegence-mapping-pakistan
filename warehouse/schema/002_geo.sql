-- 002 — geographic identity
--
-- The centre of the design. See docs/ARCHITECTURE.md §3.
--
-- Three ideas, each of which exists because this project has already been
-- burned by its absence:
--
--   1. A unit has a VINTAGE. Lahore had 5 tehsils until 27 Aug 2024 and 10
--      after. A same-named 2024 outline can be a small fraction of its census
--      parent. Joining across vintages by name left 59% of Lahore undrawn.
--   2. Containment is COMPUTED from geometry. Karachi's municipal Towns and the
--      census talukas are different partitions of the same ground; neither
--      nests inside the other, and no name-based tree can express that.
--   3. Every unit declares its ACCURACY. Derived geometry is welcome; silent
--      derived geometry is not.

-- ---------------------------------------------------------------- levels

create table if not exists geo.level (
  level       text primary key,
  depth       smallint not null,          -- 0 country … larger = finer
  label       text     not null,
  is_admin    boolean  not null default true,   -- false for H3, Voronoi, commercial groupings
  note        text
);

comment on column geo.level.is_admin is
  'False for constructs that are not administrative units — H3 cells, Voronoi tessellations, dealership groupings. The UI must not present these as official boundaries.';

insert into geo.level (level, depth, label, is_admin, note) values
  ('country',       0, 'Country',        true,  null),
  ('province',      1, 'Province',       true,  null),
  ('division',      2, 'Division',       true,  null),
  ('district',      3, 'District',       true,  null),
  ('tehsil',        4, 'Tehsil',         true,  'Lahore, Multan, Peshawar municipal tier'),
  ('taluka',        4, 'Taluka',         true,  'Census sub-division layer in Sindh; parallel to town, does not align'),
  ('town',          4, 'Town',           true,  'Karachi municipal tier, Sindh LG Act 2021'),
  ('uc',            5, 'Union Council',  true,  null),
  ('locality',      6, 'Locality',       false, 'Lahore locality cells are Voronoi tessellations, not boundaries'),
  ('neighbourhood', 6, 'Neighbourhood',  true,  null),
  ('block',         7, 'Census block',   true,  'Smallest published census unit; join key for ECP electoral counts'),
  ('h3_r8',         8, 'H3 cell (r8)',   false, 'Vintage-free grid, ~0.74 km2'),
  ('h3_r9',         9, 'H3 cell (r9)',   false, 'Vintage-free grid, ~0.11 km2')
on conflict (level) do nothing;

-- ---------------------------------------------------------------- units

create table if not exists geo.unit (
  geo_id        text primary key,
  level         text        not null references geo.level(level),
  name          text        not null,
  name_norm     text        not null,     -- casefolded, punctuation-stripped; ETL match key
  city          text,                     -- denormalised for the common filter
  parent_id     text        references geo.unit(geo_id),

  valid_from    date        not null,
  valid_to      date,                     -- null = current
  vintage_label text,                     -- '2023 census', '2024 notification'

  source_id     text        not null,     -- FK added in 003 (load order)
  accuracy      text        not null check (accuracy in ('official','derived','approximate')),
  accuracy_note text,
  area_km2      numeric,                  -- from geometry
  area_km2_ref  numeric,                  -- as published by the source, where it differs
  attrs         jsonb       not null default '{}'::jsonb,

  geom          extensions.geometry(MultiPolygon, 4326) not null,
  created_at    timestamptz not null default now(),

  constraint unit_validity check (valid_to is null or valid_to > valid_from),
  -- Invariant 2: derived and approximate geometry must say why.
  constraint unit_accuracy_explained
    check (accuracy = 'official' or accuracy_note is not null)
);

comment on table geo.unit is
  'One row per (place, level, vintage). geo_id is a deterministic string so ETL reruns are idempotent and seed diffs are readable: PK.PB.LHE.TEHC.SHALIMAR@2023';

comment on column geo.unit.area_km2_ref is
  'The area the source publishes, where it differs from the geometry. The gap is the boundary-accuracy caveat the UI and CSV export must carry — e.g. Karachi East +47%, West -47%.';

create index if not exists unit_geom_gix   on geo.unit using gist (geom);
create index if not exists unit_level_idx  on geo.unit (level, city);
create index if not exists unit_current_idx on geo.unit (level) where valid_to is null;
create index if not exists unit_name_trgm  on geo.unit using gin (name_norm extensions.gin_trgm_ops);

-- Centroid for labelling. ST_PointOnSurface is guaranteed inside the polygon,
-- unlike a centroid, which matters for crescent-shaped territories.
alter table geo.unit
  add column if not exists label_point extensions.geometry(Point, 4326)
  generated always as (extensions.ST_PointOnSurface(geom)) stored;

-- ------------------------------------------------------- vintage crosswalk

create table if not exists geo.crosswalk (
  from_geo_id text    not null references geo.unit(geo_id) on delete cascade,
  to_geo_id   text    not null references geo.unit(geo_id) on delete cascade,
  weight      numeric not null check (weight > 0 and weight <= 1),
  basis       text    not null check (basis in ('exact','area','households','population')),
  note        text,
  primary key (from_geo_id, to_geo_id)
);

comment on table geo.crosswalk is
  'Weighted mapping between vintages. Lets a 2023 census figure be apportioned onto the 2024 Lahore tehsils, labelled as apportioned, with the basis stated.';

-- Invariant 3: weights sum to 1 per source unit. Same shape of guard as the
-- model workbook''s "Fee Units sum to 100" check row. Run after every load.
create or replace view geo.v_crosswalk_check as
  select from_geo_id,
         sum(weight)                as total_weight,
         count(*)                   as targets,
         abs(sum(weight) - 1) < 1e-6 as ok
  from geo.crosswalk
  group by from_geo_id;

-- ------------------------------------------------------------- containment

create table if not exists geo.containment (
  child_id    text     not null references geo.unit(geo_id) on delete cascade,
  ancestor_id text     not null references geo.unit(geo_id) on delete cascade,
  depth_gap   smallint not null,
  coverage    numeric  not null check (coverage > 0 and coverage <= 1),
  primary key (child_id, ancestor_id)
);

comment on column geo.containment.coverage is
  'Fraction of the child area inside the ancestor. 1.0 = clean nesting. Partials are the truth for Karachi towns against census talukas, and the UI reports them rather than hiding them.';

create index if not exists containment_anc_idx on geo.containment (ancestor_id, depth_gap);

-- Rebuild containment from geometry. Called by the ETL after any geo.unit load.
-- Deliberately not a trigger: it is an O(n*m) spatial join and belongs in a
-- controlled batch, not in the middle of a row insert.
create or replace function geo.rebuild_containment(p_min_coverage numeric default 0.02)
returns bigint
language plpgsql
as $fn$
declare n bigint;
begin
  truncate geo.containment;

  insert into geo.containment (child_id, ancestor_id, depth_gap, coverage)
  select child_id, ancestor_id, depth_gap, coverage
  from (
    select c.geo_id                       as child_id,
           a.geo_id                       as ancestor_id,
           (lc.depth - la.depth)::smallint as depth_gap,
           extensions.ST_Area(extensions.ST_Intersection(c.geom, a.geom)::extensions.geography)
             / nullif(extensions.ST_Area(c.geom::extensions.geography), 0) as coverage
    from geo.unit c
    join geo.level lc on lc.level = c.level
    join geo.unit  a  on a.geo_id <> c.geo_id
                     and extensions.ST_Intersects(c.geom, a.geom)
    join geo.level la on la.level = a.level and la.depth < lc.depth
    -- Only relate units whose validity windows overlap. A 2024 tehsil is not an
    -- ancestor of a unit that ceased to exist in 2023.
    where (c.valid_to is null or a.valid_from < c.valid_to)
      and (a.valid_to is null or c.valid_from < a.valid_to)
  ) s
  where coverage >= p_min_coverage;

  get diagnostics n = row_count;
  return n;
end
$fn$;

comment on function geo.rebuild_containment is
  'Materialises containment from geometry. p_min_coverage drops slivers caused by digitisation noise along shared borders — raise it if neighbouring units start appearing as each other''s children.';
