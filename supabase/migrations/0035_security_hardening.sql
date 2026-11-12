-- 0035_security_hardening.sql
-- Findings from the full-project audit of 2026-11-12, applied live that evening.
--
-- 1. Internal plumbing was callable with the publishable key. That key ships
--    inside the firmware and is printed in the docs, so "anon can execute" means
--    "anyone on the internet can execute". Only the device-facing RPCs and the
--    staff RPCs may stay reachable.
-- 2. Six tables had a school-wide SELECT policy, i.e. every parent could read
--    every child's guardian phone number, every attendance row, every card UID
--    and the device's secret HASH. Parents now read their own child through the
--    `*_read_linked` policies and the SECURITY DEFINER RPCs, which is how the
--    dashboard already fetches data.
-- 3. pg_net stores every cron HTTP response forever (~1,440 rows/day at a
--    one-minute mail tick). A daily prune keeps the database from filling up.

-- ---------------------------------------------------------------- 1. grants --
revoke execute on function public.astro_defer_email(bigint, text)    from public, anon, authenticated;
revoke execute on function public.astro_finish_email(bigint, boolean, text) from public, anon, authenticated;
revoke execute on function public.astro_fanout_arrival()             from public, anon, authenticated;
revoke execute on function public.astro_fanout_message()             from public, anon, authenticated;
revoke execute on function public.astro_fanout_notice()              from public, anon, authenticated;
revoke execute on function public.astro_maintenance()                from public, anon, authenticated;
revoke execute on function public.astro_prune_events(integer)        from public, anon, authenticated;
revoke execute on function public.astro_outbox_sync()                from public, anon, authenticated;
revoke execute on function public.astro_leave_outbox_sync()          from public, anon, authenticated;
revoke execute on function public.astro_close_day(date)              from anon;

-- ------------------------------------------------------------ 2. row level --
drop policy if exists students_read    on public.students;
create policy students_read    on public.students    for select to authenticated
  using (school_id = public.current_school_id() and public.is_staff());

drop policy if exists attendance_read  on public.attendance;
create policy attendance_read  on public.attendance  for select to authenticated
  using (school_id = public.current_school_id() and public.is_staff());

drop policy if exists devices_read     on public.devices;
create policy devices_read     on public.devices     for select to authenticated
  using (school_id = public.current_school_id() and public.is_staff());

drop policy if exists device_events_read on public.device_events;
create policy device_events_read on public.device_events for select to authenticated
  using (school_id = public.current_school_id() and public.is_staff());

drop policy if exists fingerprints_read on public.fingerprints;
create policy fingerprints_read on public.fingerprints for select to authenticated
  using (school_id = public.current_school_id() and public.is_staff());

drop policy if exists rfid_cards_read  on public.rfid_cards;
create policy rfid_cards_read  on public.rfid_cards  for select to authenticated
  using (school_id = public.current_school_id() and public.is_staff());

create index if not exists students_class_idx on public.students (school_id, class_id);

-- -------------------------------------------------------- 3. pg_net hygiene --
create or replace function public.astro_prune_net(p_keep_days integer default 2)
returns integer
language plpgsql
security definer
set search_path = public
as $$
declare n integer;
begin
  delete from net._http_response where created < now() - make_interval(days => greatest(1, p_keep_days));
  get diagnostics n = row_count;
  return n;
end $$;

revoke execute on function public.astro_prune_net(integer) from public, anon, authenticated;

select cron.schedule('astro-prune-net', '15 3 * * *', 'select public.astro_prune_net(2)');
