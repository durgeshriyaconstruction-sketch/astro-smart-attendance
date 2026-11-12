-- ============================================================================
-- ASTRO SMART ATTENDANCE — 0004 automation (end-of-day closure + housekeeping)
-- Runs inside Postgres with pg_cron, in UTC.
--   09:15 UTC = 14:45 IST  -> close the school day, mark absentees, queue alerts
-- ============================================================================

create extension if not exists pg_cron;

-- ---------------------------------------------------------------------------
-- Marks every active student who never tapped as ABSENT for the given day and
-- queues a guardian alert for each one. Safe to run twice: the unique slot
-- index + note filter make the second run a no-op.
-- ---------------------------------------------------------------------------
create or replace function public.astro_close_day(p_date date default null)
returns jsonb
language plpgsql security definer set search_path = public
as $$
declare
  r        record;
  d        date;
  n_abs    integer := 0;
  n_alerts integer := 0;
  n        integer;
begin
  for r in select * from public.schools loop
    d := coalesce(p_date, (now() at time zone r.timezone)::date);

    insert into public.attendance
        (school_id, student_id, class_id, attendance_date, session, status, method, note)
    select r.id, st.id, st.class_id, d, 'daily', 'absent', 'import', 'auto-closed'
    from public.students st
    where st.school_id = r.id and st.active
    on conflict (student_id, attendance_date, session, (coalesce(period_no, 0))) do nothing;
    get diagnostics n = row_count;
    n_abs := n_abs + n;

    insert into public.alerts (school_id, student_id, attendance_id, kind, to_email, subject, body)
    select r.id, st.id, a.id, 'absent', st.guardian_email,
           'Absent today: ' || st.full_name || ' (' || to_char(d, 'DD Mon') || ')',
           'Dear Parent,' || chr(10) || chr(10) ||
           'Our records show ' || st.full_name || ' (Roll ' || st.roll_no || ') as ABSENT on ' ||
           to_char(d, 'DD Mon YYYY') || '.' || chr(10) ||
           'If this is a mistake, please contact the class teacher.' || chr(10) || chr(10) ||
           '- ' || r.name || ' / Astro Smart Attendance'
    from public.students st
    join public.attendance a
      on a.student_id = st.id and a.attendance_date = d
     and a.session = 'daily' and a.status = 'absent' and a.note = 'auto-closed'
    where st.school_id = r.id and st.active
      and st.guardian_email is not null
      and r.alert_emails
      and not exists (select 1 from public.alerts al where al.attendance_id = a.id);
    get diagnostics n = row_count;
    n_alerts := n_alerts + n;
  end loop;

  return jsonb_build_object('ok', true, 'date', coalesce(p_date, current_date),
                            'absent_marked', n_abs, 'alerts_queued', n_alerts);
end $$;

-- ---------------------------------------------------------------------------
-- Keeps device_events from growing forever. 90 days is plenty for audit.
-- ---------------------------------------------------------------------------
create or replace function public.astro_prune_events(p_keep_days integer default 90)
returns integer
language plpgsql security definer set search_path = public
as $$
declare n integer;
begin
  delete from public.device_events
   where received_at < now() - make_interval(days => greatest(p_keep_days, 7));
  get diagnostics n = row_count;
  return n;
end $$;

revoke all on function public.astro_close_day(date) from public;
revoke all on function public.astro_prune_events(integer) from public;
grant execute on function public.astro_close_day(date) to authenticated;

-- ---------------------------------------------------------------------------
-- Schedules (UTC). Re-running this file is safe: unschedule first.
-- ---------------------------------------------------------------------------
select cron.unschedule(jobid) from cron.job where jobname in ('astro-close-day', 'astro-prune-events');

select cron.schedule('astro-close-day',   '15 9 * * 1-6', $$select public.astro_close_day()$$);
select cron.schedule('astro-prune-events', '30 20 * * 0', $$select public.astro_prune_events(90)$$);
