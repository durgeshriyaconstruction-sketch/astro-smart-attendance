-- ============================================================================
-- ASTRO SMART ATTENDANCE — 0005 hardening (applied 2026-11-12)
--
-- Two gaps found while auditing 0001-0004:
--
--  1. astro_close_day() was granted to `authenticated` with no staff check.
--     Any signed-up account could mark the whole school absent for any date.
--     Cron runs as the table owner (auth.uid() is null) and is unaffected.
--
--  2. astro_mark_attendance() trusted p_event_ts completely, so one device with
--     a bad clock could backfill years of attendance. Timestamps are now
--     clamped to [now - 30 days, now + 5 minutes] - which still covers a
--     realistic offline queue, but not a forged history.
-- ============================================================================

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
  -- cron / service_role have no JWT; a real dashboard user must be staff
  if auth.uid() is not null and not public.is_staff() then
    raise exception using message = 'NOT_STAFF', errcode = '42501';
  end if;

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

revoke all on function public.astro_close_day(date) from public;
grant execute on function public.astro_close_day(date) to authenticated;

-- ---------------------------------------------------------------------------
-- same function as 0002 with the timestamp clamp added (one changed line)
-- ---------------------------------------------------------------------------
create or replace function public.astro_mark_attendance(
  p_device_code    text,
  p_device_secret  text,
  p_card_uid       text    default null,
  p_fingerprint_id integer default null,
  p_method         text    default null,
  p_session        text    default 'daily',
  p_period_no      integer default null,
  p_event_uid      uuid    default null,
  p_event_ts       timestamptz default null
)
returns jsonb
language plpgsql security definer set search_path = public
as $$
declare
  d          public.devices;
  s          public.schools;
  stu        public.students;
  cls        text;
  uid        text;
  v_method   text := coalesce(nullif(lower(btrim(p_method)), ''), 'rfid');
  v_session  text := coalesce(nullif(lower(btrim(p_session)), ''), 'daily');
  v_event    uuid := coalesce(p_event_uid, gen_random_uuid());
  v_ts       timestamptz := least(
                            greatest(coalesce(p_event_ts, now()),
                                     now() - interval '30 days'),
                            now() + interval '5 minutes');
  v_local    timestamp;
  v_status   text;
  v_att      public.attendance;
  v_prev     jsonb;
  v_result   jsonb;
begin
  d := public.astro_verify_device(p_device_code, p_device_secret);
  select * into s from public.schools where id = d.school_id;

  if v_session not in ('daily', 'period') then
    raise exception using message = 'BAD_SESSION', errcode = '22023';
  end if;
  if v_session = 'period' and p_period_no is null then
    raise exception using message = 'PERIOD_NO_REQUIRED', errcode = '22023';
  end if;

  v_local := (v_ts at time zone s.timezone);
  uid := public.astro_norm_uid(p_card_uid);

  if uid is null and p_fingerprint_id is null then
    raise exception using message = 'NO_CREDENTIAL', errcode = '22023';
  end if;

  insert into public.device_events
      (event_uid, school_id, device_id, card_uid, fingerprint_id, method, event_ts, payload)
  values
      (v_event, d.school_id, d.id, uid, p_fingerprint_id, v_method, v_ts,
       jsonb_build_object('session', v_session, 'period_no', p_period_no))
  on conflict (event_uid) do nothing;

  if not found then
    select result into v_prev from public.device_events where event_uid = v_event;
    if v_prev is not null then
      return v_prev || jsonb_build_object('duplicate', true);
    end if;
  end if;

  if uid is not null then
    select st.* into stu
    from public.rfid_cards card
    join public.students st on st.id = card.student_id
    where card.card_uid = uid and card.active and st.active
      and st.school_id = d.school_id
    limit 1;
  else
    select * into stu
    from public.students
    where school_id = d.school_id and fingerprint_id = p_fingerprint_id and active
    limit 1;
  end if;

  if stu.id is null then
    v_result := jsonb_build_object(
      'ok', false, 'code', 'UNKNOWN_CARD', 'uid', uid,
      'fingerprint_id', p_fingerprint_id,
      'message', 'Card not registered for this school'
    );
    update public.device_events
       set status = 'unknown_card', result = v_result, processed = true
     where event_uid = v_event;
    return v_result;
  end if;

  select case when c.name is null then null else c.name || '-' || c.section end
    into cls from public.classes c where c.id = stu.class_id;

  v_status := case
                when v_session = 'daily' and v_local::time > s.late_after then 'late'
                else 'present'
              end;

  insert into public.attendance
      (school_id, student_id, class_id, device_id, attendance_date, session,
       period_no, status, method, marked_at, event_uid)
  values
      (d.school_id, stu.id, stu.class_id, d.id, v_local::date, v_session,
       p_period_no, v_status, v_method, v_ts, v_event)
  on conflict (student_id, attendance_date, session, (coalesce(period_no, 0))) do nothing
  returning * into v_att;

  if v_att.id is null then
    select * into v_att
    from public.attendance
    where student_id = stu.id and attendance_date = v_local::date
      and session = v_session and coalesce(period_no, 0) = coalesce(p_period_no, 0);

    v_result := jsonb_build_object(
      'ok', true, 'code', 'ALREADY_MARKED', 'action', 'already_marked',
      'uid', uid, 'status', to_jsonb(v_att.status),
      'date', v_att.attendance_date, 'time', to_char(v_att.marked_at at time zone s.timezone, 'HH24:MI'),
      'marked_at', v_att.marked_at,
      'student', jsonb_build_object(
        'id', stu.id, 'roll_no', stu.roll_no, 'name', stu.full_name, 'class', cls)
    );
  else
    v_result := jsonb_build_object(
      'ok', true, 'code', 'MARKED', 'action', 'marked',
      'uid', uid, 'status', to_jsonb(v_att.status),
      'date', v_att.attendance_date, 'time', to_char(v_local, 'HH24:MI'),
      'marked_at', v_att.marked_at, 'method', v_method, 'session', v_session,
      'period_no', p_period_no,
      'student', jsonb_build_object(
        'id', stu.id, 'roll_no', stu.roll_no, 'name', stu.full_name, 'class', cls)
    );

    if v_status = 'late' and s.alert_emails and stu.guardian_email is not null then
      insert into public.alerts
          (school_id, student_id, attendance_id, kind, to_email, subject, body)
      values
          (d.school_id, stu.id, v_att.id, 'late', stu.guardian_email,
           'Late arrival: ' || stu.full_name || ' (' || to_char(v_local, 'DD Mon') || ')',
           'Dear Parent,' || chr(10) || chr(10) ||
           stu.full_name || ' (Roll ' || stu.roll_no || ') reached school at ' ||
           to_char(v_local, 'HH24:MI') || ' on ' || to_char(v_local, 'DD Mon YYYY') ||
           ', after the ' || to_char(s.late_after::interval, 'HH24:MI') || ' cut-off, so the arrival is marked LATE.' ||
           chr(10) || chr(10) || '- ' || s.name || ' / Astro Smart Attendance');
    end if;
  end if;

  update public.device_events
     set status = v_result->>'code', result = v_result, processed = true
   where event_uid = v_event;

  update public.devices set last_seen = now() where id = d.id;

  return v_result;
end $$;

revoke all on function
  public.astro_mark_attendance(text, text, text, integer, text, text, integer, uuid, timestamptz)
from public;
grant execute on function
  public.astro_mark_attendance(text, text, text, integer, text, text, integer, uuid, timestamptz)
to anon, authenticated;

-- ---------------------------------------------------------------------------
-- students.updated_at was declared in 0001 but nothing maintained it
-- ---------------------------------------------------------------------------
create or replace function public.astro_touch_updated_at()
returns trigger language plpgsql as $$
begin
  new.updated_at := now();
  return new;
end $$;

drop trigger if exists students_touch on public.students;
create trigger students_touch
  before update on public.students
  for each row execute function public.astro_touch_updated_at();
