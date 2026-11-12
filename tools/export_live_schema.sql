-- tools/export_live_schema.sql
-- =====================================================================
-- Two ways to get the live schema back out of Supabase, since the SQL
-- editor is the only channel this project has.
--
--   Query 1  replays the exact SQL of every recorded migration into one
--            text column. This is the authoritative source for migrations
--            0016-0021 (astro_access_and_identity ... astro_realtime),
--            whose .sql files are not in this repository yet.
--   Query 2  dumps the *current* definitions (functions, policies,
--            triggers, constraints, indexes, grants) so you can check for
--            drift after someone edits the dashboard by hand.
--
-- Use: Supabase Studio -> SQL Editor -> paste one query -> Run ->
--      copy the single text cell into supabase/migrations/00NN_name.sql
-- =====================================================================

-- ---------------------------------------------------------------- query 1
-- Exact migration replay (safe to read: it only selects).
select string_agg(
         format(E'-- ===== %s  %s =====\n%s', m.version, m.name,
                array_to_string(m.statements, E';\n')),
         E'\n\n' order by m.version) as migration_sql
from supabase_migrations.schema_migrations m
where m.name like 'astro_%';

-- ---------------------------------------------------------------- query 2
-- Current-state snapshot. Run this after any manual change in the dashboard
-- and diff it against the migration files.
with f as (
  select 'FUNCTION ' || p.oid::regprocedure::text || E'\n' ||
         pg_get_functiondef(p.oid) as ddl
  from pg_proc p
  where p.pronamespace = 'public'::regnamespace
),
c as (
  select 'ALTER TABLE public.' || conrelid::regclass::text ||
         ' ADD CONSTRAINT ' || conname || ' ' || pg_get_constraintdef(oid) || ';' as ddl
  from pg_constraint
  where connamespace = 'public'::regnamespace and contype in ('c', 'u', 'f', 'p')
),
i as (
  select pg_get_indexdef(indexrelid) || ';' as ddl
  from pg_index where indrelid in (
    select oid from pg_class where relnamespace = 'public'::regnamespace and relkind = 'r')
),
pol as (
  select 'CREATE POLICY ' || policyname || ' ON public.' || tablename ||
         ' FOR ' || cmd || ' TO ' || array_to_string(roles, ',') ||
         coalesce(' USING (' || qual || ')', '') ||
         coalesce(' WITH CHECK (' || with_check || ')', '') || ';' as ddl
  from pg_policies where schemaname = 'public'
),
trg as (
  select pg_get_triggerdef(t.oid) || ';' as ddl
  from pg_trigger t join pg_class cl on cl.oid = t.tgrelid
  where not t.tgisinternal and cl.relnamespace = 'public'::regnamespace
),
g as (
  select 'GRANT ' || privilege_type || ' ON public.' || table_name ||
         ' TO ' || grantee || ';' as ddl
  from information_schema.table_privileges
  where table_schema = 'public' and grantee in ('anon', 'authenticated', 'service_role')
)
select string_agg(ddl, E'\n\n' order by ddl) as schema_snapshot
from (select ddl from f union all select ddl from c union all select ddl from i
      union all select ddl from pol union all select ddl from trg union all select ddl from g) x;
