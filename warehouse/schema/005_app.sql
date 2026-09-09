-- 005 — orgs, user-drawn clusters, saved views

create table if not exists app.org (
  org_id     uuid primary key default extensions.gen_random_uuid(),
  name       text not null,
  created_at timestamptz not null default now()
);

create table if not exists app.member (
  org_id  uuid not null references app.org(org_id) on delete cascade,
  user_id uuid not null references auth.users(id) on delete cascade,
  role    text not null default 'viewer' check (role in ('viewer','analyst','admin')),
  primary key (org_id, user_id)
);

comment on column app.member.role is
  'viewer reads public and internal metrics; analyst adds commercial metrics and may draw; admin manages membership.';

-- Which sensitivity tiers a role may read. Data, not a CASE buried in a policy.
create table if not exists app.role_sensitivity (
  role        text not null,
  sensitivity text not null,
  primary key (role, sensitivity)
);

insert into app.role_sensitivity (role, sensitivity) values
  ('viewer','public'),
  ('analyst','public'), ('analyst','internal'), ('analyst','commercial'),
  ('admin','public'),   ('admin','internal'),   ('admin','commercial')
on conflict do nothing;

-- ------------------------------------------------------------ clusters

create table if not exists app.cluster (
  cluster_id uuid primary key default extensions.gen_random_uuid(),
  org_id     uuid not null references app.org(org_id) on delete cascade,
  created_by uuid not null references auth.users(id),
  name       text not null,
  kind       text not null check (kind in ('drawn','selection','imported')),
  colour     text,
  geom       extensions.geometry(MultiPolygon, 4326),   -- kind = 'drawn'
  attrs      jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),

  -- A drawn cluster needs a shape; a selection needs members (checked below).
  constraint cluster_shape check (kind <> 'drawn' or geom is not null)
);

comment on table app.cluster is
  'Two kinds that behave very differently. A selection is a set of whole units: exact, no apportionment, and the right way to define anything contractual — the existing dealership scheme is precisely this. A drawn polygon cuts across units and every figure from it is an estimate.';

create table if not exists app.cluster_member (
  cluster_id uuid not null references app.cluster(cluster_id) on delete cascade,
  geo_id     text not null references geo.unit(geo_id) on delete cascade,
  primary key (cluster_id, geo_id)
);

create index if not exists cluster_org_idx  on app.cluster (org_id);
create index if not exists cluster_geom_gix on app.cluster using gist (geom) where geom is not null;

-- --------------------------------------------------------- saved views

create table if not exists app.saved_view (
  view_id    uuid primary key default extensions.gen_random_uuid(),
  org_id     uuid not null references app.org(org_id) on delete cascade,
  created_by uuid not null references auth.users(id),
  name       text not null,
  state      jsonb not null,     -- the same object the URL encodes
  created_at timestamptz not null default now()
);

comment on column app.saved_view.state is
  'The same shape the URL query string carries, so a saved view and a shared link are the same thing expressed twice. Invariant 8.';

create or replace function app.touch_updated_at()
returns trigger language plpgsql as $fn$
begin new.updated_at = now(); return new; end
$fn$;

drop trigger if exists cluster_touch on app.cluster;
create trigger cluster_touch before update on app.cluster
  for each row execute function app.touch_updated_at();
