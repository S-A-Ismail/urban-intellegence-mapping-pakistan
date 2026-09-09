-- 001 — extensions, schemas, conventions
--
-- Run in order: 001 → 007. Idempotent; safe to re-run.
-- Target: Supabase (Postgres 15+). Extensions live in the `extensions`
-- schema by Supabase convention, so `search_path` must include it.

create extension if not exists postgis      with schema extensions;
create extension if not exists pgcrypto     with schema extensions;
create extension if not exists pg_trgm      with schema extensions;  -- fuzzy name matching in ETL

-- Reference and warehouse schemas. None of these are exposed to PostgREST
-- directly; the browser only ever sees `api` (007), which wraps them in
-- security-invoker views so RLS still applies.
create schema if not exists geo;      -- geographic identity, vintages, containment
create schema if not exists src;      -- source registry and ingest runs
create schema if not exists bronze;   -- raw landing, immutable
create schema if not exists silver;   -- conformed observations
create schema if not exists gold;     -- metric facts
create schema if not exists app;      -- user-generated: orgs, clusters, saved views
create schema if not exists api;      -- the only schema PostgREST exposes

comment on schema geo    is 'Geographic identity. Units are vintaged; containment is computed from geometry, never asserted from names.';
comment on schema bronze is 'Raw payloads as fetched. Never edited. Deleted only by retention policy (src.source.retention_days).';
comment on schema gold   is 'Long-format metric facts: one row per (geo_id, metric_id, period).';
comment on schema api    is 'The public surface. Everything here is security_invoker so RLS is preserved.';

-- Supabase note: after running these, add `api` to the exposed schemas list
-- (Dashboard → Settings → API → Exposed schemas). Do NOT expose geo/gold/app.
