-- ============================================================================
-- Astro Smart Attendance - bridge v2 hotfixes
-- ============================================================================
-- These three changes were required after live end-to-end testing against the
-- project database. They are applied as a separate migration so the history
-- matches what actually ran.
-- ============================================================================

-- 1. The late cut-off must be decided by the SERVER, not by the kiosk clock.
--    Before: an explicit "Present" from the sketch won even at 09:10 (> 08:20).
--    After : present/late is always recomputed from the event time; only the
--            non-arrival statuses (absent/leave/excused/left/half_day) are
--            taken at face value.
create or replace function public.astro_fw_status(p_in text, p_ts timestamptz, p_tz text, p_late time) returns text
language plpgsql immutable as $$
declare
  v text := replace(lower(btrim(coalesce(p_in, ''))), ' ', '_');
  v_local time;
begin
  if v in ('absent', 'excused', 'left', 'half_day', 'leave') then
    return v;
  end if;
  if v not in ('present', 'late') then
    v := 'present';
  end if;
  v_local := (p_ts at time zone coalesce(nullif(p_tz, ''), 'Asia/Kolkata'))::time;
  if p_late is not null and v_local > p_late then
    return 'late';
  end if;
  return 'present';
end $$;

-- 2. attendance_slot_uidx is an EXPRESSION index, so "ON CONFLICT
--    (student_id, attendance_date, session, (coalesce(period_no,0)))" does not
--    match it ("42P10: there is no unique or exclusion constraint matching the
--    ON CONFLICT specification"). Replaced with an explicit read-then-write,
--    which also lets a re-scan refresh an earlier present/late.
create or replace function public.astro_mark_attendance(
  "device_code" text default null,
  "student_id" text default null,
  "rfid_uid" text default null,
  "date" text default null,
  "status" text default null,
  "time" text default null,
  "method" text default null,
  "device_secret" text default null
) returns jsonb
language plpgsql security definer set search_path = public as $$
#variable_conflict use_variable
declare
  d public.devices;
  sc public.schools;
  st public.students;
  v_tz text;
  v_date date;
  v_ts timestamptz;
  v_status text;
  v_method text;
  v_card text;
  v_id bigint;
  v_ex public.attendance;
begin
  d := public.astro_fw_auth("device_code", "device_secret");
  select * into sc from public.schools where id = d.school_id;
  v_tz := coalesce(sc.timezone, 'Asia/Kolkata');
  v_date := public.astro_fw_date("date", v_tz);
  v_ts := public.astro_fw_ts(v_date, "time", v_tz);
  v_card := upper(btrim(coalesce("rfid_uid", '')));

  if v_card <> '' then
    select st2.* into st from public.rfid_cards c
      join public.students st2 on st2.id = c.student_id
     where c.school_id = d.school_id and upper(c.card_uid) = v_card
       and c.active and st2.active limit 1;
  end if;
  if st.id is null and coalesce("student_id", '') <> '' then
    select st2.* into st from public.students st2
     where st2.school_id = d.school_id
       and (st2.id::text = "student_id" or upper(coalesce(st2.roll_no, '')) = upper(btrim("student_id")))
       and st2.active limit 1;
  end if;
  if st.id is null then
    return jsonb_build_object('ok', false, 'code', 'UNKNOWN_CARD', 'rfid_uid', v_card);
  end if;

  v_method := lower(btrim(coalesce("method", '')));
  if v_method not in ('rfid', 'fingerprint', 'manual', 'face', 'keypad', 'import') then
    v_method := case when v_card <> '' then 'rfid' else 'fingerprint' end;
  end if;
  v_status := public.astro_fw_status("status", v_ts, v_tz, coalesce(sc.late_after, time '09:30'));

  select * into v_ex from public.attendance a
   where a.student_id = st.id and a.attendance_date = v_date
     and a.session = 'daily' and a.period_no is null
   limit 1;

  if v_ex.id is null then
    insert into public.attendance (
      school_id, student_id, class_id, device_id, attendance_date, session, period_no,
      status, method, marked_at, note, created_at
    ) values (
      d.school_id, st.id, st.class_id, d.id, v_date, 'daily', null,
      v_status, v_method, v_ts, null, now()
    ) returning id into v_id;

    return jsonb_build_object('ok', true, 'code', 'MARKED', 'attendance_id', v_id,
      'student_id', st.id::text, 'name', st.full_name, 'roll', coalesce(st.roll_no, ''),
      'status', public.astro_fw_status_label(v_status), 'date', to_char(v_date, 'YYYY-MM-DD'),
      'time', to_char(v_ts at time zone v_tz, 'HH24:MI'), 'method', v_method);
  end if;

  if v_ex.status not in ('absent', 'leave', 'present', 'late') then
    return jsonb_build_object('ok', true, 'code', 'ALREADY_MARKED', 'attendance_id', v_ex.id,
      'student_id', st.id::text, 'name', st.full_name, 'roll', coalesce(st.roll_no, ''),
      'status', public.astro_fw_status_label(v_ex.status),
      'date', to_char(v_date, 'YYYY-MM-DD'),
      'time', to_char(v_ex.marked_at at time zone v_tz, 'HH24:MI'));
  end if;

  update public.attendance a
     set status = v_status, method = v_method, marked_at = v_ts, device_id = d.id,
         note = case when a.status = 'absent' and coalesce(a.note, '') = 'auto-closed'
                     then 'marked-by-device' else a.note end
   where a.id = v_ex.id
  returning a.id into v_id;

  return jsonb_build_object('ok', true, 'code', 'MARKED', 'attendance_id', v_id,
    'student_id', st.id::text, 'name', st.full_name, 'roll', coalesce(st.roll_no, ''),
    'status', public.astro_fw_status_label(v_status), 'date', to_char(v_date, 'YYYY-MM-DD'),
    'time', to_char(v_ts at time zone v_tz, 'HH24:MI'), 'method', v_method);
end $$;

-- 3. device_events.event_uid is NOT NULL with no default, which made the
--    firmware's device_logs array fail with
--    "null value in column event_uid ... violates not-null constraint".
alter table public.device_events alter column event_uid set default gen_random_uuid();

notify pgrst, 'reload schema';
