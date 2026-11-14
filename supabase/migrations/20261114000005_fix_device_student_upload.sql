-- Students sent up by the gate device were never stored.
--
-- astro_create_student() (the function behind the device's astro_sync_batch and
-- astro_create_student calls) creates the student's class with
--
--     insert into public.classes ... on conflict (school_id, name, section) do update ...
--
-- The function also has PARAMETERS called "name" and "section", and it is
-- declared with "#variable_conflict use_variable". Inside the ON CONFLICT list
-- PL/pgSQL therefore read "name" and "section" as the parameters, not as the
-- columns, and Postgres answered
--
--     there is no unique or exclusion constraint matching the ON CONFLICT specification
--
-- for every student. astro_sync_batch catches per-item errors and still answers
-- HTTP 200, so the device marked each student as "sent" and never tried again:
-- 18 students on the device, 0 in the database.
--
-- Naming the constraint instead of its columns leaves nothing to be misread.
-- Only that one line of the function changes.

do $fix$
declare
  v_def text;
  v_new text;
  v_old constant text := 'on conflict (school_id, name, section) do update set name = excluded.name';
  v_fix constant text := 'on conflict on constraint classes_unique do update set name = excluded.name';
begin
  select pg_get_functiondef(p.oid) into strict v_def
    from pg_proc p join pg_namespace n on n.oid = p.pronamespace
   where n.nspname = 'public' and p.proname = 'astro_create_student';

  if position(v_fix in v_def) > 0 then
    raise notice 'astro_create_student is already fixed';
    return;
  end if;

  v_new := replace(v_def, v_old, v_fix);
  if v_new = v_def then
    raise exception 'astro_create_student: the line to fix was not found';
  end if;
  execute v_new;   -- create or replace: owner and grants stay as they are
end
$fix$;
