-- ============================================================================
-- ASTRO SMART ATTENDANCE — 0008 late arrival after auto-close (applied 2026-11-12)
--
-- Defect: astro_close_day() runs at 14:45 IST and writes status='absent' with
-- note='auto-closed'. If a student then taps at 15:05 (late bus, dental
-- appointment, exam), the ON CONFLICT DO NOTHING kept them ABSENT for the day,
-- and the guardian had already been queued an "absent" email that was now wrong.
--
-- Fix: a tap may upgrade an auto-closed ABSENT row to present/late. A manual or
-- imported ABSENT (anything not written by the cron job) is never overwritten,
-- and any still-queued "absent" alert for that row is withdrawn.
-- ============================================================================

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
  d             public.devices;
  s             public.schools;
  stu           public.students;
  cls           text;
  uid           text;
  v_method      text := coalesce(nullif(lower(btrim(p_method)), ''), 'rfid');
  v_session     text := coalesce(nullif(lower(btrim(p_session)), ''), 'daily');
  v_period      integer;
  v_event       uuid := coalesce(p_event_uid, gen_random_uuid());
  v_ts          timestamptz := least(
                              greatest(coalesce(p_event_ts, now()),
                                       now() - interval '30 days'),
                              now() + interval '5 minutes');
  v_local       timestamp;
  v_status      text;
  v_att         public.attendance;
  v_prev        jsonb;
  v_result      jsonb;
  v_prev_status text;
  v_prev_note   text;
  v_upgraded    boolean := false;
begin
  d := public.astro_verify_device(p_device_code, p_device_secret);
  select * into s from public.schools where id = d.school_id;

  if v_session not in ('daily', 'period') then
    raise exception using message = 'BAD_SESSION', errcode = '22023';
  end if;
  if v_method not in ('rfid', 'fingerprint', 'manual', 'face', 'keypad', 'import') then
    raise exception using message = 'BAD_METHOD', errcode = '22023';
  end if;
  if v_session = 'period' and p_period_no is null then
    raise exception using message = 'PERIOD_NO_REQUIRED', errcode = '22023';
  end if;

  -- a daily row must never carry a period number
  v_period := case when v_session = 'period' then p_period_no else null end;

  v_local := (v_ts at time zone s.timezone);
  uid := public.astro_norm_uid(p_card_uid);

  if uid is null and p_fingerprint_id is null then
    raise exception using message = 'NO_CREDENTIAL', errcode = '22023';
  end if;

  insert into public.device_events
      (event_uid, school_id, device_id, card_uid, fingerprint_id, method, event_ts, payload)
  values
      (v_event, d.school_id, d.id, uid, p_fingerprint_id, v_method, v_ts,
       jsonb_build_object('session', v_session, 'period_no', v_period))
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
    select st.* into stu
    from public.fingerprints f
    join public.students st on st.id = f.student_id
    where f.device_id = d.id and f.slot = p_fingerprint_id and st.active
    limit 1;

    if stu.id is null then
      select * into stu
      from public.students
      where school_id = d.school_id and fingerprint_id = p_fingerprint_id and active
      limit 1;
    end if;
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

  -- remember what is already there so an upgrade can be reported
  select a.status, a.note
    into v_prev_status, v_prev_note
  from public.attendance a
  where a.student_id = stu.id
    and a.attendance_date = v_local::date
    and a.session = v_session
    and coalesce(a.period_no, 0) = coalesce(v_period, 0);

  insert into public.attendance
      (school_id, student_id, class_id, device_id, attendance_date, session,
       period_no, status, method, marked_at, event_uid)
  values
      (d.school_id, stu.id, stu.class_id, d.id, v_local::date, v_session,
       v_period, v_status, v_method, v_ts, v_event)
  on conflict (student_id, attendance_date, session, (coalesce(period_no, 0))) do update
     set status    = excluded.status,
         method    = excluded.method,
         marked_at = excluded.marked_at,
         event_uid = excluded.event_uid,
         note      = null
   where public.attendance.status = 'absent'
     and coalesce(public.attendance.note, '') = 'auto-closed'
  returning * into v_att;

  if v_att.id is null then
    select * into v_att
    from public.attendance
    where student_id = stu.id and attendance_date = v_local::date
      and session = v_session and coalesce(period_no, 0) = coalesce(v_period, 0);

    v_result := jsonb_build_object(
      'ok', true, 'code', 'ALREADY_MARKED', 'action', 'already_marked',
      'uid', uid, 'status', to_jsonb(v_att.status),
      'date', v_att.attendance_date,
      'time', to_char(v_att.marked_at at time zone s.timezone, 'HH24:MI'),
      'marked_at', v_att.marked_at,
      'student', jsonb_build_object(
        'id', stu.id, 'roll_no', stu.roll_no, 'name', stu.full_name, 'class', cls)
    );
  else
    v_upgraded := (v_prev_status = 'absent' and coalesce(v_prev_note, '') = 'auto-closed');

    v_result := jsonb_build_object(
      'ok', true, 'code', 'MARKED', 'action', 'marked',
      'uid', uid, 'status', to_jsonb(v_att.status),
      'date', v_att.attendance_date, 'time', to_char(v_local, 'HH24:MI'),
      'marked_at', v_att.marked_at, 'method', v_method, 'session', v_session,
      'period_no', v_period,
      'upgraded_from_absent', v_upgraded,
      'student', jsonb_build_object(
        'id', stu.id, 'roll_no', stu.roll_no, 'name', stu.full_name, 'class', cls)
    );

    -- the "absent" email the cron queued is no longer true
    if v_upgraded then
      delete from public.alerts
       where attendance_id = v_att.id and kind = 'absent' and status = 'queued';
    end if;

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

revoke all on function public.astro_mark_attendance(text, text, text, integer, text, text, integer, uuid, timestamptz) from anon, public;
grant execute on function public.astro_mark_attendance(text, text, text, integer, text, text, integer, uuid, timestamptz) to anon, authenticated;
