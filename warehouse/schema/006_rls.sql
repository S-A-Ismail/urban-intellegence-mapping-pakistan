-- 006 — row level security
--
-- Invariant 6: RLS on every table, no exceptions for "reference" data. The
-- anon key ships inside the browser bundle; it is safe only because of this
-- file. A table with RLS enabled and no policy denies everything, which is the
-- correct default for anything not listed here.

-- Two helpers, both SECURITY DEFINER, and the reason matters.
--
-- app.member carries its own policy, and that policy needs to know which orgs
-- the caller belongs to — which means reading app.member. A security-invoker
-- helper would re-enter the policy that called it and Postgres would raise
-- "infinite recursion detected in policy". Definer rights break the cycle.
--
-- This is safe because neither function takes an argument. Both derive
-- everything from auth.uid() and can only ever return the caller's own
-- membership; there is no parameter to pass someone else's id through. The
-- search_path is pinned so a definer function cannot be hijacked by a
-- shadowing object in a caller-controlled schema.

create or replace function app.my_orgs()
returns setof uuid
language sql stable security definer
set search_path = app, public, pg_temp
as $fn$
  select org_id from app.member where user_id = auth.uid()
$fn$;

create or replace function app.my_sensitivities()
returns setof text
language sql stable security definer
set search_path = app, public, pg_temp
as $fn$
  select distinct rs.sensitivity
  from app.member m
  join app.role_sensitivity rs on rs.role = m.role
  where m.user_id = auth.uid()
$fn$;

revoke all on function app.my_orgs()         from public, anon;
revoke all on function app.my_sensitivities() from public, anon;
grant execute on function app.my_orgs()         to authenticated;
grant execute on function app.my_sensitivities() to authenticated;

-- --------------------------------------------------- reference data

alter table geo.level       enable row level security;
alter table geo.unit        enable row level security;
alter table geo.crosswalk   enable row level security;
alter table geo.containment enable row level security;
alter table gold.metric     enable row level security;
alter table gold.fact       enable row level security;
alter table src.source      enable row level security;

-- Geometry and level definitions are readable by any signed-in user. They carry
-- no commercial content: a boundary is a boundary.
drop policy if exists geo_level_read on geo.level;
create policy geo_level_read on geo.level
  for select to authenticated using (true);

drop policy if exists geo_unit_read on geo.unit;
create policy geo_unit_read on geo.unit
  for select to authenticated using (true);

drop policy if exists geo_crosswalk_read on geo.crosswalk;
create policy geo_crosswalk_read on geo.crosswalk
  for select to authenticated using (true);

drop policy if exists geo_containment_read on geo.containment;
create policy geo_containment_read on geo.containment
  for select to authenticated using (true);

-- Metric definitions are visible only where the caller could read the values;
-- otherwise the layer list itself leaks what is being tracked.
drop policy if exists gold_metric_read on gold.metric;
create policy gold_metric_read on gold.metric
  for select to authenticated
  using (sensitivity in (select app.my_sensitivities()));

-- The one that matters. A fact is readable only if its metric's sensitivity is
-- within the caller's tier. This is what keeps entry fees out of the client.
drop policy if exists gold_fact_read on gold.fact;
create policy gold_fact_read on gold.fact
  for select to authenticated
  using (exists (
    select 1 from gold.metric m
    where m.metric_id = gold.fact.metric_id
      and m.sensitivity in (select app.my_sensitivities())
  ));

-- The registry is readable (provenance is meant to be inspectable) but the
-- licence reference and operator notes are not exposed through api (007).
drop policy if exists src_source_read on src.source;
create policy src_source_read on src.source
  for select to authenticated using (true);

-- Bronze, silver and ingest runs get NO policies. RLS is on, so PostgREST sees
-- nothing. Only the ETL, holding service_role, bypasses RLS to write them.
alter table bronze.record      enable row level security;
alter table silver.observation enable row level security;
alter table src.ingest_run     enable row level security;

-- --------------------------------------------------- user data

alter table app.org              enable row level security;
alter table app.member           enable row level security;
alter table app.role_sensitivity enable row level security;
alter table app.cluster          enable row level security;
alter table app.cluster_member   enable row level security;
alter table app.saved_view       enable row level security;

drop policy if exists org_read on app.org;
create policy org_read on app.org
  for select to authenticated using (org_id in (select app.my_orgs()));

drop policy if exists member_read on app.member;
create policy member_read on app.member
  for select to authenticated using (org_id in (select app.my_orgs()));

drop policy if exists role_sens_read on app.role_sensitivity;
create policy role_sens_read on app.role_sensitivity
  for select to authenticated using (true);

drop policy if exists cluster_read on app.cluster;
create policy cluster_read on app.cluster
  for select to authenticated using (org_id in (select app.my_orgs()));

-- Only analysts and admins create or change clusters.
drop policy if exists cluster_write on app.cluster;
create policy cluster_write on app.cluster
  for all to authenticated
  using (exists (
    select 1 from app.member m
    where m.org_id = app.cluster.org_id
      and m.user_id = auth.uid()
      and m.role in ('analyst','admin')
  ))
  with check (
    created_by = auth.uid()
    and exists (
      select 1 from app.member m
      where m.org_id = app.cluster.org_id
        and m.user_id = auth.uid()
        and m.role in ('analyst','admin')
    )
  );

drop policy if exists cluster_member_rw on app.cluster_member;
create policy cluster_member_rw on app.cluster_member
  for all to authenticated
  using (exists (
    select 1 from app.cluster c
    where c.cluster_id = app.cluster_member.cluster_id
      and c.org_id in (select app.my_orgs())
  ))
  with check (exists (
    select 1 from app.cluster c
    where c.cluster_id = app.cluster_member.cluster_id
      and c.org_id in (select app.my_orgs())
  ));

drop policy if exists saved_view_rw on app.saved_view;
create policy saved_view_rw on app.saved_view
  for all to authenticated
  using (org_id in (select app.my_orgs()))
  with check (org_id in (select app.my_orgs()) and created_by = auth.uid());

-- --------------------------------------------------- grants
--
-- PostgREST reaches the data only through api (007). Grant usage on the
-- underlying schemas so security_invoker views can resolve, but grant no table
-- privileges beyond select — writes go through api functions.

grant usage on schema geo, gold, src, app, api to authenticated;
grant select on geo.level, geo.unit, geo.crosswalk, geo.containment,
                gold.metric, gold.fact, src.source to authenticated;
grant select, insert, update, delete
  on app.cluster, app.cluster_member, app.saved_view to authenticated;
grant usage, select on all sequences in schema app to authenticated;

-- anon gets nothing. Sign-in is required to see a boundary, let alone a figure.
revoke all on schema geo, gold, src, app from anon;
