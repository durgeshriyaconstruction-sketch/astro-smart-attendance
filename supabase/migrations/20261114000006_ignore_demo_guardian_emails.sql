-- The demo students built into the ESP32 sketch must not put strangers on the
-- school's mailing list.
--
-- When the device starts with empty storage it creates 18 demo students
-- (Data::defaults(), kSeed) and invents contact details for them:
--
--     parent1@gmail.com ... parent18@gmail.com      student1@school.edu ...
--
-- Those Gmail addresses belong to real people who have nothing to do with the
-- school. The device sends them up as "guardian_email", and from then on the
-- cloud would write to them every school day: astro_close_day() queues an
-- "Absent today" e-mail per student, and every card tap queues an "Arrived at
-- school" e-mail (trigger attendance_arrival_fanout).
--
-- So the device path now treats the sketch's made-up addresses as "no address".
-- A real address typed for a student is stored exactly as before, and an address
-- already stored is kept (the upsert keeps the old value when the new one is null).
-- Only the one expression that reads "guardian_email" in astro_create_student()
-- changes; astro_sync_batch() stores students through that same function.

create or replace function public.astro_fw_real_email(p_email text)
returns text
language sql
immutable
set search_path to 'public'
as $$
  select case
    when p_email is null or btrim(p_email) = '' then null
    -- parent<N>@gmail.com / student<N>@school.edu: the sketch's placeholders
    when lower(btrim(p_email)) ~ '^(parent|student)[0-9]+@(gmail\.com|school\.edu)$' then null
    else btrim(p_email)
  end
$$;

comment on function public.astro_fw_real_email(text) is
  'Guardian e-mail as sent by the ESP32, minus the made-up addresses of the sketch''s demo students.';

-- internal helper: only the device functions (security definer) call it
revoke all on function public.astro_fw_real_email(text) from public, anon, authenticated;

do $fix$
declare
  v_def text;
  v_new text;
  v_old constant text := 'nullif(btrim(coalesce("guardian_email",'''')),'''')';
  v_fix constant text := 'public.astro_fw_real_email("guardian_email")';
begin
  select pg_get_functiondef(p.oid) into strict v_def
    from pg_proc p join pg_namespace n on n.oid = p.pronamespace
   where n.nspname = 'public' and p.proname = 'astro_create_student';

  if position(v_fix in v_def) > 0 then
    raise notice 'astro_create_student already ignores the demo addresses';
    return;
  end if;

  v_new := replace(v_def, v_old, v_fix);
  if v_new = v_def then
    raise exception 'astro_create_student: the guardian_email line was not found';
  end if;

  execute v_new;
end
$fix$;

-- Nothing to clean up: no student row holds one of these addresses yet.
-- (If one ever did: update public.students set guardian_email = null
--   where guardian_email ~ '^(parent|student)[0-9]+@(gmail\.com|school\.edu)$';)
