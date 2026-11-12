-- 0024_admin_insights_and_maintenance.sql
-- =====================================================================
-- What the admin screen was missing, plus housekeeping.
--
--   astro_attendance_report()  per-student present/late/absent/leave and a
--                              percentage for any date range (the "global
--                              attendance overview" + CSV/PDF export source)
--   astro_outbox_list()        what is actually in the email queue, so
--                              "no email arrived" can be diagnosed
--   astro_requeue_alert()      retry one email instead of all of them
--   astro_pending_leaves()     the leave approval screen
--   astro_device_health()      the terminal status pills (online / last seen /
--                              taps today / queue depth)
--   astro_prune_alerts()       sent/skipped rows are kept 180 days, not forever
--   astro_maintenance()        one cron entry: prune events, prune outbox,
--                              release stuck 'sending' rows
--   fingerprints guard         a missing slot now fails with BAD_SLOT instead
--                              of a raw 23502 not-null violation
-- =====================================================================

begin;

-- ---------------------------------------------------------------------
-- 1. Attendance report
-- ---------------------------------------------------------------------
create or replace function public.astro_attendance_report(
  p_from date,
  p_to date,
  p_class_id uuid default null,
  p_school_id uuid default null
) returns jsonb
language plpgsql
stable
security definer
set search_path = public
as $$
declare
  sid uuid := public.astro_ctx_school(p_school_id, 'staff');
  s public.schools;
  v_from date;
  v_to date;
  v_days integer;
  v_rows jsonb;
  v_totals jsonb;
begin
  if p_from is null or p_to is null then
    raise exception using message = 'DATES_REQUIRED', errcode = '22023';
  end if;
  if p_to < p_from then
    raise exception using message = 'BAD_DATES', errcode = '22023', hint = 'p_to must be on or after p_from';
  end if;
  if p_to - p_from > 366 then
    raise exception using message = 'RANGE_TOO_LONG', errcode = '22023', hint = 'One year at most';
  end if;

  select * into s from public.schools where id = sid;
  v_from := p_from;
  v_to := least(p_to, (now() at time zone s.timezone)::date);

  if v_to < v_from then
    return jsonb_build_object('ok', true, 'from', p_from, 'to', p_to, 'school_days', 0,
      'students', '[]'::jsonb, 'totals', jsonb_build_object('students', 0, 'present', 0, 'late', 0,
        'absent', 0, 'leave', 0, 'other', 0));
  end if;

  select count(*) into v_days
  from generate_series(v_from::timestamp, v_to::timestamp, interval '1 day') g
  where not (extract(dow from g)::int = any (s.weekly_off))
    and not exists (select 1 from public.school_holidays h
                     where h.school_id = sid and h.holiday_date = g::date);

  select coalesce(jsonb_agg(o order by class_name, roll_no), '[]'::jsonb) into v_rows
  from (
    select st.roll_no,
           coalesce(c.name || '-' || c.section, '') as class_name,
           jsonb_build_object(
             'student_id', st.id, 'roll_no', st.roll_no, 'name', st.full_name,
             'class', case when c.id is null then null else c.name || '-' || c.section end,
             'present', a.present, 'late', a.late, 'absent', a.absent,
             'leave', a.leave, 'other', a.other,
             'percent', case when a.present + a.late + a.absent = 0 then null
                             else round(100.0 * (a.present + a.late) / (a.present + a.late + a.absent), 1) end
           ) as o
    from public.students st
    left join public.classes c on c.id = st.class_id
    cross join lateral (
      select count(*) filter (where x.status = 'present') as present,
             count(*) filter (where x.status = 'late') as late,
             count(*) filter (where x.status = 'absent') as absent,
             count(*) filter (where x.status in ('leave','excused')) as leave,
             count(*) filter (where x.status in ('half_day','left')) as other
      from public.attendance x
      where x.student_id = st.id and x.session = 'daily'
        and x.attendance_date between v_from and v_to
    ) a
    where st.school_id = sid and st.active
      and (p_class_id is null or st.class_id = p_class_id)
  ) q;

  select jsonb_build_object(
           'students', jsonb_array_length(v_rows),
           'present', coalesce(sum((e->>'present')::int), 0),
           'late', coalesce(sum((e->>'late')::int), 0),
           'absent', coalesce(sum((e->>'absent')::int), 0),
           'leave', coalesce(sum((e->>'leave')::int), 0),
           'other', coalesce(sum((e->>'other')::int), 0))
    into v_totals
  from jsonb_array_elements(v_rows) e;

  return jsonb_build_object('ok', true, 'from', v_from, 'to', v_to, 'school_days', v_days,
    'class_id', p_class_id, 'totals', v_totals, 'students', v_rows);
end
$$;

-- ---------------------------------------------------------------------
-- 2. Outbox inspection
-- ---------------------------------------------------------------------
create or replace function public.astro_outbox_list(
  p_status text default null,
  p_limit integer default 50,
  p_school_id uuid default null
) returns jsonb
language plpgsql
stable
security definer
set search_path = public
as $$
declare
  sid uuid := public.astro_ctx_school(p_school_id, 'staff');
  v text := nullif(lower(btrim(coalesce(p_status, ''))), '');
  v_rows jsonb;
begin
  if v is not null and v not in ('queued','sending','sent','failed','skipped') then
    raise exception using message = 'BAD_STATUS', errcode = '22023';
  end if;
  select coalesce(jsonb_agg(jsonb_build_object(
           'id', a.id, 'kind', a.kind, 'student_id', a.student_id,
           'roll_no', st.roll_no, 'student', st.full_name, 'to_email', a.to_email,
           'subject', a.subject, 'status', a.status, 'attempts', a.attempts,
           'last_error', a.last_error, 'created_at', a.created_at, 'sent_at', a.sent_at,
           'ref_kind', a.ref_kind, 'ref_id', a.ref_id) order by a.created_at desc), '[]'::jsonb)
    into v_rows
  from (select al.* from public.alerts al
         where al.school_id = sid and (v is null or al.status = v)
         order by al.created_at desc
         limit greatest(coalesce(p_limit, 50), 1)) a
  left join public.students st on st.id = a.student_id;

  return jsonb_build_object('ok', true, 'status', v, 'count', jsonb_array_length(v_rows), 'rows', v_rows);
end
$$;

create or replace function public.astro_requeue_alert(
  p_alert_id bigint,
  p_school_id uuid default null
) returns jsonb
language plpgsql
security definer
set search_path = public
as $$
declare
  sid uuid := public.astro_ctx_school(p_school_id, 'staff');
  a public.alerts;
begin
  update public.alerts
     set status = 'queued', attempts = 0, last_error = null, sent_at = null
   where id = p_alert_id and school_id = sid and status in ('failed', 'skipped')
   returning * into a;
  if a.id is null then
    select * into a from public.alerts where id = p_alert_id and school_id = sid;
    if a.id is null then raise exception using message = 'ALERT_NOT_FOUND', errcode = '22023'; end if;
    return jsonb_build_object('ok', false, 'reason', 'NOT_REQUEUEABLE', 'status', a.status,
      'hint', 'Only failed or skipped rows can be requeued');
  end if;
  return jsonb_build_object('ok', true, 'alert_id', a.id, 'status', a.status, 'to_email', a.to_email);
end
$$;

-- ---------------------------------------------------------------------
-- 3. Leave approval screen
-- ---------------------------------------------------------------------
create or replace function public.astro_pending_leaves(
  p_limit integer default 100,
  p_school_id uuid default null
) returns jsonb
language plpgsql
stable
security definer
set search_path = public
as $$
declare
  sid uuid := public.astro_ctx_school(p_school_id, 'staff');
  v_rows jsonb;
begin
  if to_regclass('public.leave_requests') is null then
    return jsonb_build_object('ok', true, 'count', 0, 'leaves', '[]'::jsonb);
  end if;
  select coalesce(jsonb_agg(o order by from_date, roll_no), '[]'::jsonb) into v_rows
  from (
    select jsonb_build_object(
             'id', lr.id, 'student_id', st.id, 'student', st.full_name, 'roll_no', st.roll_no,
             'class', case when c.id is null then null else c.name || '-' || c.section end,
             'from_date', lr.from_date, 'to_date', lr.to_date,
             'days', lr.to_date - lr.from_date + 1, 'reason', lr.reason,
             'requested_by', lr.requested_by, 'created_at', lr.created_at) as o,
           lr.from_date as from_date, st.roll_no as roll_no
    from public.leave_requests lr
    join public.students st on st.id = lr.student_id
    left join public.classes c on c.id = st.class_id
    where lr.school_id = sid and lr.status = 'pending'
    order by lr.from_date
    limit greatest(coalesce(p_limit, 100), 1)
  ) q;
  return jsonb_build_object('ok', true, 'count', jsonb_array_length(v_rows), 'leaves', v_rows);
end
$$;

-- ---------------------------------------------------------------------
-- 4. Device health
-- ---------------------------------------------------------------------
create or replace function public.astro_device_health(p_school_id uuid default null)
returns jsonb
language plpgsql
stable
security definer
set search_path = public
as $$
declare
  sid uuid := public.astro_ctx_school(p_school_id, 'member');
  s public.schools;
  v_today date;
  v_rows jsonb;
begin
  select * into s from public.schools where id = sid;
  v_today := (now() at time zone s.timezone)::date;
  select coalesce(jsonb_agg(jsonb_build_object(
           'device_id', d.id, 'device_code', d.device_code, 'name', d.name,
           'location', d.location, 'active', d.active, 'firmware', d.firmware,
           'ip', d.ip, 'wifi_rssi', d.wifi_rssi,
           'last_seen', d.last_seen,
           'seconds_since_seen', case when d.last_seen is null then null
                                      else round(extract(epoch from now() - d.last_seen))::int end,
           'online', coalesce(d.last_seen > now() - interval '90 seconds', false),
           'last_boot', d.last_boot,
           'taps_today', (select count(*) from public.device_events e
                           where e.device_id = d.id and e.event_ts >= v_today::timestamp at time zone s.timezone),
           'pending_commands', (select count(*) from public.device_commands c
                                 where c.device_id = d.id and c.status = 'queued' and c.expires_at > now())
         ) order by d.device_code), '[]'::jsonb) into v_rows
  from public.devices d
  where d.school_id = sid;
  return jsonb_build_object('ok', true, 'date', v_today, 'devices', v_rows);
end
$$;

-- ---------------------------------------------------------------------
-- 5. Housekeeping
-- ---------------------------------------------------------------------
create or replace function public.astro_prune_alerts(
  p_keep_days integer default 180,
  p_school_id uuid default null
) returns jsonb
language plpgsql
security definer
set search_path = public
as $$
declare
  sid uuid := public.astro_ctx_school(p_school_id, 'staff');
  v_days integer := least(greatest(coalesce(p_keep_days, 180), 30), 3650);
  n integer;
begin
  delete from public.alerts
   where school_id = sid and status in ('sent', 'skipped', 'failed')
     and created_at < now() - make_interval(days => v_days);
  get diagnostics n = row_count;
  return jsonb_build_object('ok', true, 'deleted', n, 'keep_days', v_days);
end
$$;

create or replace function public.astro_maintenance()
returns jsonb
language plpgsql
security definer
set search_path = public
as $$
declare
  n_events integer;
  n_alerts integer;
begin
  n_events := public.astro_prune_events(90);
  delete from public.alerts
   where status in ('sent', 'skipped', 'failed')
     and created_at < now() - interval '180 days';
  get diagnostics n_alerts = row_count;
  perform public.astro_release_stale_sending(15);
  return jsonb_build_object('ok', true, 'events_pruned', n_events,
    'alerts_pruned', n_alerts, 'ran_at', now());
end
$$;

-- One weekly job instead of two.
do $$
declare j bigint;
begin
  for j in select jobid from cron.job where jobname in ('astro-prune-events', 'astro-maintenance') loop
    perform cron.unschedule(j);
  end loop;
  perform cron.schedule('astro-maintenance', '30 20 * * 0', 'select public.astro_maintenance()');
exception when undefined_table then
  raise notice 'pg_cron not available - schedule astro_maintenance() yourself';
end
$$;

-- ---------------------------------------------------------------------
-- 6. Fingerprint slot guard
-- ---------------------------------------------------------------------
create or replace function public.astro_fingerprints_guard()
returns trigger
language plpgsql
set search_path = public
as $$
begin
  if new.slot is null then
    raise exception using message = 'BAD_SLOT', errcode = '22023', hint = 'Slot 1-999 is required';
  end if;
  return new;
end
$$;

drop trigger if exists fingerprints_guard on public.fingerprints;
create trigger fingerprints_guard
  before insert or update on public.fingerprints
  for each row execute function public.astro_fingerprints_guard();

-- ---------------------------------------------------------------------
-- 7. Grants
-- ---------------------------------------------------------------------
revoke all on function public.astro_attendance_report(date, date, uuid, uuid) from public, anon;
revoke all on function public.astro_outbox_list(text, integer, uuid) from public, anon;
revoke all on function public.astro_requeue_alert(bigint, uuid) from public, anon;
revoke all on function public.astro_pending_leaves(integer, uuid) from public, anon;
revoke all on function public.astro_device_health(uuid) from public, anon;
revoke all on function public.astro_prune_alerts(integer, uuid) from public, anon;
revoke all on function public.astro_maintenance() from public, anon, authenticated;
revoke all on function public.astro_fingerprints_guard() from public, anon, authenticated;

grant execute on function public.astro_attendance_report(date, date, uuid, uuid) to authenticated, service_role;
grant execute on function public.astro_outbox_list(text, integer, uuid) to authenticated, service_role;
grant execute on function public.astro_requeue_alert(bigint, uuid) to authenticated, service_role;
grant execute on function public.astro_pending_leaves(integer, uuid) to authenticated, service_role;
grant execute on function public.astro_device_health(uuid) to authenticated, service_role;
grant execute on function public.astro_prune_alerts(integer, uuid) to authenticated, service_role;
grant execute on function public.astro_maintenance() to service_role;

commit;
