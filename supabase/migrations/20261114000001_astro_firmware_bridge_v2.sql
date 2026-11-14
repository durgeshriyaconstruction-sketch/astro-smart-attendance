-- ============================================================================
-- Astro Smart Attendance - firmware RPC bridge (v2, PostgREST-correct)
-- ============================================================================
-- WHY THIS EXISTS
--   firmware/main.cpp calls POST /rest/v1/rpc/astro_* with FLAT body keys such as
--   {"device_code":"ASTRO-RNK-01","rfid_uid":"A1B2C3D4"}.
--   PostgREST resolves an RPC by matching those JSON keys to the function's
--   PARAMETER NAMES one-for-one. The previous bridge used "p_device_code" style
--   names, so every call still failed with PGRST202 "function not found".
--   Therefore every function below declares its parameters with the exact keys
--   the sketch sends - no "p_" prefix anywhere in the firmware-facing layer.
--
-- SAFETY
--   * Additive: the original p_-prefixed application functions are untouched.
--   * Auth: every call is verified against devices.secret_hash using the
--     device_secret JSON key OR the X-Astro-Secret header.
--   * Idempotent: safe to re-run.
-- ============================================================================

-- ---------------------------------------------------------------- 0. clean up
drop function if exists public.astro_device_handshake(text, text, text);
drop function if exists public.astro_get_settings(text, text);
drop function if exists public.astro_list_students(text, text);
drop function if exists public.astro_list_holidays(text, text);
drop function if exists public.astro_list_leaves(text, text);
drop function if exists public.astro_list_messages(text, text);
drop function if exists public.astro_list_notices(text, text);
drop function if exists public.astro_list_attendance(text, text, text);
drop function if exists public.astro_lookup_by_rfid(text, text, text, text);
drop function if exists public.astro_lookup_by_fingerprint(text, integer, integer, text);
drop function if exists public.astro_mark_attendance(text, text, text, text, text, text, text, text);
drop function if exists public.astro_create_student(text, text, text, text, text, text, text, text, text, integer, text, text, text, bigint, boolean, text);
drop function if exists public.astro_delete_student(text, text, text, text);
drop function if exists public.astro_create_notice(text, bigint, text, text, text, text, boolean, text, text);
drop function if exists public.astro_delete_notice(text, bigint, uuid, text);
drop function if exists public.astro_send_message(text, bigint, text, text, text, text, text, boolean, text);
drop function if exists public.astro_delete_message(text, bigint, uuid, text);
drop function if exists public.astro_approve_leave(text, bigint, uuid, text, text, text, text, text);
drop function if exists public.astro_create_holiday(text, text, text, text);
drop function if exists public.astro_delete_holiday(text, text, text);
drop function if exists public.astro_update_settings(text, text, text, text, text, bigint, bigint, bigint, boolean, text, text);
drop function if exists public.astro_factory_wipe(text, boolean, text);
drop function if exists public.astro_sync_batch(text, text, jsonb, jsonb, jsonb, jsonb, jsonb, jsonb, jsonb, jsonb, jsonb, jsonb, text);

-- ------------------------------------------- 1. stable integer ids for the LCD
-- notices / messages / leaves are uuid-keyed, but the sketch keys them by uint32.
create table if not exists public.astro_fw_id_map (
  school_id uuid not null,
  kind text not null,
  local_id bigint not null,
  entity_id uuid not null,
  created_at timestamptz not null default now(),
  constraint astro_fw_id_map_pk primary key (school_id, kind, local_id)
);
create index if not exists astro_fw_id_map_entity_idx on public.astro_fw_id_map (kind, entity_id);
alter table public.astro_fw_id_map enable row level security;

create or replace function public.astro_fw_int_id(p_id uuid) returns bigint
language sql immutable as $$
  select ((hashtext(p_id::text)::bigint % 1000000000) + 1000000000) % 1000000000 + 1
$$;

create or replace function public.astro_fw_map_local(p_school uuid, p_kind text, p_entity uuid) returns bigint
language sql stable security definer set search_path = public as $$
  select m.local_id from public.astro_fw_id_map m
   where m.school_id = p_school and m.kind = p_kind and m.entity_id = p_entity
   order by m.created_at desc limit 1
$$;

create or replace function public.astro_fw_map_entity(p_school uuid, p_kind text, p_local bigint) returns uuid
language sql stable security definer set search_path = public as $$
  select m.entity_id from public.astro_fw_id_map m
   where m.school_id = p_school and m.kind = p_kind and m.local_id = p_local
$$;

create or replace function public.astro_fw_map_put(p_school uuid, p_kind text, p_local bigint, p_entity uuid) returns void
language sql security definer set search_path = public as $$
  insert into public.astro_fw_id_map (school_id, kind, local_id, entity_id)
  values (p_school, p_kind, p_local, p_entity)
  on conflict (school_id, kind, local_id) do update set entity_id = excluded.entity_id
$$;

-- ------------------------------------------------------- 2. request primitives
create or replace function public.astro_fw_hdr() returns jsonb
language sql stable as $$
  select coalesce(nullif(current_setting('request.headers', true), ''), '{}')::jsonb
$$;

-- Authenticate the calling kiosk. Raises (-> non-2xx) on any problem, so the
-- firmware can never again mistake a broken cloud for a healthy one.
create or replace function public.astro_fw_auth(p_code text, p_secret text default null)
returns public.devices
language plpgsql security definer set search_path = public as $$
declare
  v_code text;
  v_secret text;
  d public.devices;
begin
  v_code := nullif(btrim(coalesce(p_code, '')), '');
  if v_code is null then
    v_code := nullif(btrim(coalesce(public.astro_fw_hdr() ->> 'x-astro-device', '')), '');
  end if;

  if v_code is null then
    select * into d from public.devices where active order by created_at limit 1;
  else
    select * into d from public.devices where device_code = upper(v_code) limit 1;
  end if;

  if d.id is null then
    raise exception 'DEVICE_NOT_FOUND' using errcode = '28000';
  end if;
  if not d.active then
    raise exception 'DEVICE_DISABLED' using errcode = '28000';
  end if;

  v_secret := nullif(btrim(coalesce(p_secret, '')), '');
  if v_secret is null then
    v_secret := nullif(btrim(coalesce(public.astro_fw_hdr() ->> 'x-astro-secret', '')), '');
  end if;
  if v_secret is null then
    raise exception 'DEVICE_SECRET_REQUIRED: send the device_secret or X-Astro-Secret header'
      using errcode = '28P01';
  end if;
  if d.secret_hash is distinct from public.astro_sha256_hex(v_secret) then
    raise exception 'BAD_DEVICE_SECRET' using errcode = '28P01';
  end if;

  update public.devices set last_seen = now() where id = d.id;
  return d;
end $$;

create or replace function public.astro_fw_date(p_text text, p_tz text default 'Asia/Kolkata') returns date
language plpgsql stable as $$
begin
  if coalesce(p_text, '') ~ '^\d{4}-\d{2}-\d{2}' then
    begin
      return substr(p_text, 1, 10)::date;
    exception when others then null;
    end;
  end if;
  return (now() at time zone coalesce(nullif(p_tz, ''), 'Asia/Kolkata'))::date;
end $$;

create or replace function public.astro_fw_ts(p_date date, p_time text, p_tz text default 'Asia/Kolkata') returns timestamptz
language plpgsql stable as $$
declare
  v_tz text := coalesce(nullif(p_tz, ''), 'Asia/Kolkata');
  v_hm text;
begin
  v_hm := case when coalesce(p_time, '') ~ '^\d{1,2}:\d{2}' then p_time else to_char(now() at time zone v_tz, 'HH24:MI') end;
  begin
    return (p_date::text || ' ' || v_hm || ' ' || v_tz)::timestamptz;
  exception when others then
    return now();
  end;
end $$;

create or replace function public.astro_fw_status(p_in text, p_ts timestamptz, p_tz text, p_late time) returns text
language plpgsql immutable as $$
declare
  v text := lower(btrim(coalesce(p_in, '')));
  v_local time;
begin
  v := replace(v, ' ', '_');
  if v in ('present', 'late', 'absent', 'excused', 'left', 'half_day', 'leave') then
    return v;
  end if;
  v_local := (p_ts at time zone coalesce(nullif(p_tz, ''), 'Asia/Kolkata'))::time;
  if p_late is not null and v_local > p_late then
    return 'late';
  end if;
  return 'present';
end $$;

create or replace function public.astro_fw_priority(p_in text) returns text
language sql immutable as $$
  select case lower(btrim(coalesce(p_in, '')))
    when 'critical' then 'critical'
    when 'urgent' then 'critical'
    when 'important' then 'important'
    when 'high' then 'important'
    else 'normal'
  end
$$;

create or replace function public.astro_fw_audience(p_in text) returns text
language sql immutable as $$
  select case
    when lower(btrim(coalesce(p_in, ''))) in ('staff', 'teachers') then 'staff'
    when lower(btrim(coalesce(p_in, ''))) in ('students', 'student', 'all', '') then 'students'
    else 'students'
  end
$$;

create or replace function public.astro_fw_audience_label(p_in text) returns text
language sql immutable as $$
  select case lower(coalesce(p_in, ''))
    when 'staff' then 'Staff'
    when 'all' then 'All'
    when 'students' then 'Students'
    else initcap(coalesce(p_in, 'All'))
  end
$$;

create or replace function public.astro_fw_status_label(p_in text) returns text
language sql immutable as $$
  select case lower(coalesce(p_in, ''))
    when 'present' then 'Present'
    when 'late' then 'Late'
    when 'absent' then 'Absent'
    when 'leave' then 'Leave'
    when 'excused' then 'Excused'
    when 'half_day' then 'Half Day'
    when 'left' then 'Left'
    else initcap(coalesce(p_in, 'Present'))
  end
$$;

-- ============================================================================
-- 3. HANDSHAKE + SETTINGS
-- ============================================================================
create or replace function public.astro_device_handshake(
  "device_code" text default null,
  "device_secret" text default null,
  "firmware_version" text default null
) returns jsonb
language plpgsql security definer set search_path = public as $$
declare
  d public.devices;
  sc public.schools;
  v_bearer text;
begin
  d := public.astro_fw_auth("device_code", "device_secret");

  update public.devices
     set firmware = coalesce(nullif(btrim(coalesce("firmware_version", '')), ''), firmware),
         last_seen = now(),
         last_boot = now()
   where id = d.id;

  select * into sc from public.schools where id = d.school_id;

  v_bearer := nullif(btrim(coalesce(public.astro_request_bearer(), '')), '');

  return jsonb_build_object(
    'ok', true,
    'code', 'HANDSHAKE_OK',
    'session_token', v_bearer,
    'token', v_bearer,
    'expires_in', 3600,
    'device_code', d.device_code,
    'school_id', d.school_id,
    'school_name', sc.name,
    'school_code', sc.code,
    'timezone', coalesce(sc.timezone, 'Asia/Kolkata'),
    'server_time', now(),
    'firmware_version', coalesce(nullif(btrim(coalesce("firmware_version", '')), ''), coalesce(d.firmware, 'unknown'))
  );
end $$;

create or replace function public.astro_get_settings(
  "device_code" text default null,
  "device_secret" text default null
) returns jsonb
language plpgsql security definer set search_path = public as $$
declare
  d public.devices;
  sc public.schools;
  v_late time;
  v_absent time;
begin
  d := public.astro_fw_auth("device_code", "device_secret");
  select * into sc from public.schools where id = d.school_id;

  v_late := coalesce(sc.late_after, time '09:30');
  v_absent := sc.absent_after;

  return jsonb_build_object(
    'start_time', to_char(coalesce(sc.day_start, time '09:00'), 'HH24:MI'),
    'end_time', to_char(coalesce(sc.day_end, time '15:00'), 'HH24:MI'),
    'late_after', to_char(v_late, 'HH24:MI'),
    'late_after_min', (extract(hour from v_late) * 60 + extract(minute from v_late))::int,
    'absent_after', case when v_absent is null then null else to_char(v_absent, 'HH24:MI') end,
    'absent_after_min', case when v_absent is null then null else (extract(hour from v_absent) * 60 + extract(minute from v_absent))::int end,
    'timezone', coalesce(sc.timezone, 'Asia/Kolkata'),
    'weekly_off', to_jsonb(coalesce(sc.weekly_off, '{}'::int[])),
    'alert_emails', coalesce(sc.alert_emails, false),
    'school_name', sc.name,
    'server_time', now()
  );
end $$;

-- ============================================================================
-- 4. READ / DOWN-SYNC
-- ============================================================================
create or replace function public.astro_list_students(
  "device_code" text default null,
  "device_secret" text default null
) returns jsonb
language plpgsql security definer set search_path = public as $$
declare
  d public.devices;
begin
  d := public.astro_fw_auth("device_code", "device_secret");

  return coalesce((
    select jsonb_agg(jsonb_build_object(
             'student_id', st.id::text,
             'rfid_uid', c.card_uid,
             'name', st.full_name,
             'roll', coalesce(st.roll_no, ''),
             'class_name', cl.name,
             'section', cl.section,
             'fingerprint_id', st.fingerprint_id
           ) order by st.roll_no nulls last, st.full_name)
      from public.students st
      join lateral (
        select rc.card_uid
          from public.rfid_cards rc
         where rc.student_id = st.id and rc.active
         order by rc.assigned_at desc
         limit 1
      ) c on true
      left join public.classes cl on cl.id = st.class_id
     where st.school_id = d.school_id and st.active
  ), '[]'::jsonb);
end $$;

create or replace function public.astro_list_holidays(
  "device_code" text default null,
  "device_secret" text default null
) returns jsonb
language plpgsql security definer set search_path = public as $$
declare
  d public.devices;
begin
  d := public.astro_fw_auth("device_code", "device_secret");

  return coalesce((
    select jsonb_agg(jsonb_build_object(
             'date', to_char(h.holiday_date, 'YYYY-MM-DD'),
             'reason', h.reason
           ) order by h.holiday_date)
      from public.school_holidays h
     where h.school_id = d.school_id
       and h.holiday_date >= (now() at time zone 'Asia/Kolkata')::date - 30
  ), '[]'::jsonb);
end $$;

create or replace function public.astro_list_attendance(
  "device_code" text default null,
  "date" text default null,
  "device_secret" text default null
) returns jsonb
language plpgsql security definer set search_path = public as $$
declare
  d public.devices;
  sc public.schools;
  v_tz text;
  v_date date;
begin
  d := public.astro_fw_auth("device_code", "device_secret");
  select * into sc from public.schools where id = d.school_id;
  v_tz := coalesce(sc.timezone, 'Asia/Kolkata');
  v_date := public.astro_fw_date("date", v_tz);

  return coalesce((
    select jsonb_agg(jsonb_build_object(
             'rfid_uid', c.card_uid,
             'student_id', a.student_id::text,
             'status', public.astro_fw_status_label(a.status),
             'time', to_char(a.marked_at at time zone v_tz, 'HH24:MI'),
             'method', coalesce(a.method, 'rfid')
           ) order by a.marked_at)
      from public.attendance a
      join lateral (
        select rc.card_uid
          from public.rfid_cards rc
         where rc.student_id = a.student_id and rc.active
         order by rc.assigned_at desc
         limit 1
      ) c on true
     where a.school_id = d.school_id
       and a.attendance_date = v_date
       and coalesce(a.session, 'daily') = 'daily'
  ), '[]'::jsonb);
end $$;

create or replace function public.astro_list_notices(
  "device_code" text default null,
  "device_secret" text default null
) returns jsonb
language plpgsql security definer set search_path = public as $$
declare
  d public.devices;
begin
  d := public.astro_fw_auth("device_code", "device_secret");

  return coalesce((
    select jsonb_agg(jsonb_build_object(
             'id', coalesce(public.astro_fw_map_local(d.school_id, 'notice', n.id), public.astro_fw_int_id(n.id)),
             'title', n.title,
             'body', coalesce(n.body, ''),
             'priority', coalesce(n.priority, 'normal'),
             'target', public.astro_fw_audience_label(n.audience),
             'created_at', to_char(n.created_at, 'YYYY-MM-DD')
           ) order by n.created_at desc)
      from public.notices n
     where n.school_id = d.school_id
       and coalesce(n.audience, 'all') in ('all', 'students')
       and (n.expires_at is null or n.expires_at > now())
       and (n.publish_at is null or n.publish_at <= now())
  ), '[]'::jsonb);
end $$;

create or replace function public.astro_list_leaves(
  "device_code" text default null,
  "device_secret" text default null
) returns jsonb
language plpgsql security definer set search_path = public as $$
declare
  d public.devices;
begin
  d := public.astro_fw_auth("device_code", "device_secret");

  return coalesce((
    select jsonb_agg(jsonb_build_object(
             'id', coalesce(public.astro_fw_map_local(d.school_id, 'leave', l.id), public.astro_fw_int_id(l.id)),
             'student_id', coalesce(c.card_uid, st.id::text),
             'name', st.full_name,
             'from_date', to_char(l.from_date, 'YYYY-MM-DD'),
             'to_date', to_char(l.to_date, 'YYYY-MM-DD'),
             'reason', coalesce(l.reason, ''),
             'status', coalesce(l.status, 'pending')
           ) order by l.created_at desc)
      from public.leave_requests l
      join public.students st on st.id = l.student_id
      left join lateral (
        select rc.card_uid
          from public.rfid_cards rc
         where rc.student_id = st.id and rc.active
         order by rc.assigned_at desc
         limit 1
      ) c on true
     where l.school_id = d.school_id
       and l.to_date >= (now() at time zone 'Asia/Kolkata')::date - 30
  ), '[]'::jsonb);
end $$;

create or replace function public.astro_list_messages(
  "device_code" text default null,
  "device_secret" text default null
) returns jsonb
language plpgsql security definer set search_path = public as $$
declare
  d public.devices;
begin
  d := public.astro_fw_auth("device_code", "device_secret");

  return coalesce((
    select jsonb_agg(jsonb_build_object(
             'id', coalesce(public.astro_fw_map_local(d.school_id, 'message', m.id), public.astro_fw_int_id(m.id)),
             'to', coalesce(c.card_uid, st.id::text),
             'name', st.full_name,
             'from', 'Admin',
             'subject', coalesce(m.subject, 'Message'),
             'text', coalesce(m.body, ''),
             'created_at', to_char(m.created_at, 'YYYY-MM-DD HH24:MI'),
             'read', (m.read_at is not null)
           ) order by m.created_at desc)
      from public.messages m
      join public.students st on st.id = m.student_id
      left join lateral (
        select rc.card_uid
          from public.rfid_cards rc
         where rc.student_id = st.id and rc.active
         order by rc.assigned_at desc
         limit 1
      ) c on true
     where m.school_id = d.school_id
       and coalesce(m.direction, 'to_student') = 'to_student'
       and m.student_hidden_at is null
  ), '[]'::jsonb);
end $$;

create or replace function public.astro_lookup_by_rfid(
  "device_code" text default null,
  "rfid_uid" text default null,
  "uid" text default null,
  "device_secret" text default null
) returns jsonb
language plpgsql security definer set search_path = public as $$
declare
  d public.devices;
  v_uid text;
  v jsonb;
begin
  d := public.astro_fw_auth("device_code", "device_secret");
  v_uid := upper(btrim(coalesce(nullif(btrim(coalesce("rfid_uid", '')), ''), coalesce("uid", ''), '')));

  if v_uid = '' then
    return null;
  end if;

  select jsonb_build_object(
           'student_id', st.id::text,
           'rfid_uid', c.card_uid,
           'name', st.full_name,
           'roll', coalesce(st.roll_no, ''),
           'class_name', cl.name,
           'section', cl.section,
           'fingerprint_id', st.fingerprint_id
         )
    into v
    from public.rfid_cards c
    join public.students st on st.id = c.student_id
    left join public.classes cl on cl.id = st.class_id
   where c.school_id = d.school_id
     and upper(c.card_uid) = v_uid
     and c.active
     and st.active
   limit 1;

  return v;
end $$;

create or replace function public.astro_lookup_by_fingerprint(
  "device_code" text default null,
  "fingerprint_id" integer default null,
  "finger_id" integer default null,
  "device_secret" text default null
) returns jsonb
language plpgsql security definer set search_path = public as $$
declare
  d public.devices;
  v_fp integer;
  v jsonb;
begin
  d := public.astro_fw_auth("device_code", "device_secret");
  v_fp := coalesce("fingerprint_id", "finger_id");

  if v_fp is null or v_fp <= 0 then
    return null;
  end if;

  select jsonb_build_object(
           'student_id', st.id::text,
           'rfid_uid', c.card_uid,
           'name', st.full_name,
           'roll', coalesce(st.roll_no, ''),
           'class_name', cl.name,
           'section', cl.section,
           'fingerprint_id', st.fingerprint_id
         )
    into v
    from public.students st
    left join lateral (
      select rc.card_uid
        from public.rfid_cards rc
       where rc.student_id = st.id and rc.active
       order by rc.assigned_at desc
       limit 1
    ) c on true
    left join public.classes cl on cl.id = st.class_id
   where st.school_id = d.school_id
     and st.fingerprint_id = v_fp
     and st.active
   limit 1;

  return v;
end $$;

-- ============================================================================
-- 5. ATTENDANCE + STUDENTS
-- ============================================================================
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
  v_existing public.attendance;
begin
  d := public.astro_fw_auth("device_code", "device_secret");
  select * into sc from public.schools where id = d.school_id;
  v_tz := coalesce(sc.timezone, 'Asia/Kolkata');
  v_date := public.astro_fw_date("date", v_tz);
  v_ts := public.astro_fw_ts(v_date, "time", v_tz);

  v_card := upper(btrim(coalesce("rfid_uid", '')));

  if v_card <> '' then
    select st2.* into st
      from public.rfid_cards c
      join public.students st2 on st2.id = c.student_id
     where c.school_id = d.school_id and upper(c.card_uid) = v_card and c.active and st2.active
     limit 1;
  end if;

  if st.id is null and coalesce("student_id", '') <> '' then
    select st2.* into st
      from public.students st2
     where st2.school_id = d.school_id
       and (st2.id::text = "student_id" or upper(coalesce(st2.roll_no, '')) = upper(btrim("student_id")))
       and st2.active
     limit 1;
  end if;

  if st.id is null then
    return jsonb_build_object('ok', false, 'code', 'UNKNOWN_CARD', 'rfid_uid', v_card);
  end if;

  v_method := lower(btrim(coalesce("method", '')));
  if v_method not in ('rfid', 'fingerprint', 'manual', 'face', 'keypad', 'import') then
    v_method := case when v_card <> '' then 'rfid' else 'fingerprint' end;
  end if;

  v_status := public.astro_fw_status("status", v_ts, v_tz, coalesce(sc.late_after, time '09:30'));

  insert into public.attendance as a (
    school_id, student_id, class_id, device_id, attendance_date, session, period_no,
    status, method, marked_at, note, created_at
  ) values (
    d.school_id, st.id, st.class_id, d.id, v_date, 'daily', null,
    v_status, v_method, v_ts, null, now()
  )
  on conflict (student_id, attendance_date, session, (coalesce(period_no, 0))) do update
     set status = excluded.status,
         method = excluded.method,
         marked_at = excluded.marked_at,
         device_id = excluded.device_id,
         note = case when a.status = 'absent' and coalesce(a.note, '') = 'auto-closed'
                     then 'marked-by-device' else a.note end
   where a.status in ('absent', 'leave')
      or a.status = excluded.status
  returning a.id into v_id;

  if v_id is null then
    select * into v_existing
      from public.attendance x
     where x.student_id = st.id and x.attendance_date = v_date
       and x.session = 'daily' and coalesce(x.period_no, 0) = 0
     limit 1;
    return jsonb_build_object(
      'ok', true, 'code', 'ALREADY_MARKED', 'attendance_id', v_existing.id,
      'student_id', st.id::text, 'name', st.full_name, 'roll', coalesce(st.roll_no, ''),
      'status', public.astro_fw_status_label(v_existing.status),
      'date', to_char(v_date, 'YYYY-MM-DD'),
      'time', to_char(v_existing.marked_at at time zone v_tz, 'HH24:MI')
    );
  end if;

  return jsonb_build_object(
    'ok', true, 'code', 'MARKED', 'attendance_id', v_id,
    'student_id', st.id::text, 'name', st.full_name, 'roll', coalesce(st.roll_no, ''),
    'status', public.astro_fw_status_label(v_status),
    'date', to_char(v_date, 'YYYY-MM-DD'),
    'time', to_char(v_ts at time zone v_tz, 'HH24:MI'),
    'method', v_method
  );
end $$;

create or replace function public.astro_create_student(
  "device_code" text default null,
  "student_id" text default null,
  "display_name" text default null,
  "name" text default null,
  "class" text default null,
  "class_name" text default null,
  "section" text default null,
  "roll" text default null,
  "rfid_uid" text default null,
  "fingerprint_id" integer default null,
  "parent_contact" text default null,
  "guardian_email" text default null,
  "password_hash" text default null,
  "password_seq" bigint default null,
  "must_change_password" boolean default null,
  "device_secret" text default null
) returns jsonb
language plpgsql security definer set search_path = public as $$
#variable_conflict use_variable
declare
  d public.devices;
  v_cls_name text;
  v_cls_section text;
  v_class_id uuid;
  v_roll text;
  v_name text;
  v_student uuid;
  v_card text;
  v_card_owner uuid;
begin
  d := public.astro_fw_auth("device_code", "device_secret");

  v_name := nullif(btrim(coalesce(nullif(btrim(coalesce("display_name", '')), ''), coalesce("name", ''), '')), '');
  if v_name is null then
    return jsonb_build_object('ok', false, 'code', 'NAME_REQUIRED');
  end if;

  v_roll := nullif(btrim(coalesce("roll", '')), '');
  if v_roll is null then
    v_roll := left(coalesce(nullif(btrim(coalesce("student_id", '')), ''), v_name), 40);
  end if;

  -- class name/section: the sketch sends "class" as "9-A" plus class_name/section
  v_cls_name := nullif(btrim(coalesce(nullif(btrim(coalesce("class_name", '')), ''), coalesce("class", ''), '')), '');
  v_cls_section := nullif(btrim(coalesce("section", '')), '');
  if v_cls_name is not null and position('-' in v_cls_name) > 0 and v_cls_section is null then
    v_cls_section := split_part(v_cls_name, '-', 2);
    v_cls_name := split_part(v_cls_name, '-', 1);
  end if;
  v_cls_name := coalesce(v_cls_name, 'General');
  v_cls_section := coalesce(v_cls_section, 'A');

  insert into public.classes as cl (school_id, name, section, created_at)
  values (d.school_id, v_cls_name, v_cls_section, now())
  on conflict (school_id, name, section) do update set name = excluded.name
  returning cl.id into v_class_id;

  insert into public.students as st (
    school_id, class_id, roll_no, full_name, guardian_phone, guardian_email,
    fingerprint_id, active, created_at, updated_at
  ) values (
    d.school_id, v_class_id, v_roll, v_name,
    nullif(btrim(coalesce("parent_contact", '')), ''),
    nullif(btrim(coalesce("guardian_email", '')), ''),
    nullif("fingerprint_id", 0), true, now(), now()
  )
  on conflict (school_id, roll_no) do update
     set full_name = excluded.full_name,
         class_id = excluded.class_id,
         guardian_phone = coalesce(excluded.guardian_phone, st.guardian_phone),
         guardian_email = coalesce(excluded.guardian_email, st.guardian_email),
         fingerprint_id = coalesce(excluded.fingerprint_id, st.fingerprint_id),
         active = true,
         updated_at = now()
  returning st.id into v_student;

  v_card := upper(btrim(coalesce("rfid_uid", '')));
  if v_card <> '' then
    select rc.student_id into v_card_owner
      from public.rfid_cards rc
     where upper(rc.card_uid) = v_card
     limit 1;

    if v_card_owner is not null and v_card_owner <> v_student then
      -- never silently steal a card that already belongs to someone else
      return jsonb_build_object('ok', false, 'code', 'CARD_IN_USE', 'student_id', v_student::text,
                                'rfid_uid', v_card);
    end if;

    insert into public.rfid_cards as rc (school_id, student_id, card_uid, label, active, assigned_at)
    values (d.school_id, v_student, v_card, v_name, true, now())
    on conflict (card_uid) do update
       set student_id = excluded.student_id,
           school_id = excluded.school_id,
           active = true,
           label = excluded.label
    returning rc.card_uid into v_card;
  end if;

  return jsonb_build_object(
    'ok', true, 'code', 'SAVED',
    'student_id', v_student::text,
    'name', v_name, 'roll', v_roll,
    'class_name', v_cls_name, 'section', v_cls_section,
    'rfid_uid', coalesce(v_card, '')
  );
end $$;

create or replace function public.astro_delete_student(
  "device_code" text default null,
  "student_id" text default null,
  "rfid_uid" text default null,
  "device_secret" text default null
) returns jsonb
language plpgsql security definer set search_path = public as $$
#variable_conflict use_variable
declare
  d public.devices;
  v_student uuid;
  v_card text;
begin
  d := public.astro_fw_auth("device_code", "device_secret");
  v_card := upper(btrim(coalesce("rfid_uid", '')));

  if v_card <> '' then
    select rc.student_id into v_student
      from public.rfid_cards rc
     where rc.school_id = d.school_id and upper(rc.card_uid) = v_card
     limit 1;
  end if;

  if v_student is null and coalesce("student_id", '') <> '' then
    select st.id into v_student
      from public.students st
     where st.school_id = d.school_id
       and (st.id::text = "student_id" or upper(coalesce(st.roll_no, '')) = upper(btrim("student_id")))
     limit 1;
  end if;

  if v_student is null then
    return jsonb_build_object('ok', true, 'code', 'NOT_FOUND');
  end if;

  update public.students set active = false, updated_at = now() where id = v_student and school_id = d.school_id;
  update public.rfid_cards set active = false where student_id = v_student and school_id = d.school_id;

  return jsonb_build_object('ok', true, 'code', 'ARCHIVED', 'student_id', v_student::text);
end $$;

-- ============================================================================
-- 6. NOTICES / MESSAGES / LEAVES / HOLIDAYS
-- ============================================================================
create or replace function public.astro_create_notice(
  "device_code" text default null,
  "id" bigint default null,
  "title" text default null,
  "body" text default null,
  "priority" text default null,
  "target" text default null,
  "pinned" boolean default null,
  "created_at" text default null,
  "device_secret" text default null
) returns jsonb
language plpgsql security definer set search_path = public as $$
#variable_conflict use_variable
declare
  d public.devices;
  v_notice uuid;
  v_ts timestamptz;
begin
  d := public.astro_fw_auth("device_code", "device_secret");

  v_ts := case when coalesce("created_at", '') ~ '^\d{4}-\d{2}-\d{2}'
               then coalesce(nullif("created_at", '')::timestamptz, now())
               else now() end;

  insert into public.notices (
    school_id, title, body, audience, class_id, student_id, pinned,
    publish_at, created_at, priority
  ) values (
    d.school_id,
    coalesce(nullif(btrim(coalesce("title", '')), ''), 'Notice'),
    coalesce("body", ''),
    public.astro_fw_audience("target"),
    null, null,
    coalesce("pinned", false),
    now(), v_ts,
    public.astro_fw_priority("priority")
  )
  returning notices.id into v_notice;

  if "id" is not null then
    perform public.astro_fw_map_put(d.school_id, 'notice', "id", v_notice);
  end if;

  return jsonb_build_object('ok', true, 'code', 'SAVED', 'notice_id', v_notice::text,
                            'id', coalesce("id", public.astro_fw_int_id(v_notice)));
end $$;

create or replace function public.astro_delete_notice(
  "device_code" text default null,
  "id" bigint default null,
  "device_secret" text default null
) returns jsonb
language plpgsql security definer set search_path = public as $$
#variable_conflict use_variable
declare
  d public.devices;
  v_notice uuid;
begin
  d := public.astro_fw_auth("device_code", "device_secret");
  if "id" is null then
    return jsonb_build_object('ok', true, 'code', 'NOOP');
  end if;

  v_notice := public.astro_fw_map_entity(d.school_id, 'notice', "id");

  if v_notice is null then
    select n.id into v_notice
      from public.notices n
     where n.school_id = d.school_id and public.astro_fw_int_id(n.id) = "id"
     limit 1;
  end if;

  if v_notice is null then
    return jsonb_build_object('ok', true, 'code', 'NOT_FOUND');
  end if;

  delete from public.notices where id = v_notice and school_id = d.school_id;
  delete from public.astro_fw_id_map where school_id = d.school_id and kind = 'notice' and entity_id = v_notice;

  return jsonb_build_object('ok', true, 'code', 'DELETED');
end $$;

create or replace function public.astro_send_message(
  "device_code" text default null,
  "id" bigint default null,
  "from" text default null,
  "to" text default null,
  "subject" text default null,
  "text" text default null,
  "read" boolean default null,
  "created_at" text default null,
  "device_secret" text default null
) returns jsonb
language plpgsql security definer set search_path = public as $$
#variable_conflict use_variable
declare
  d public.devices;
  v_student uuid;
  v_msg uuid;
  v_card text;
  v_ts timestamptz;
begin
  d := public.astro_fw_auth("device_code", "device_secret");
  v_card := upper(btrim(coalesce("to", '')));

  if v_card <> '' then
    select rc.student_id into v_student
      from public.rfid_cards rc
     where rc.school_id = d.school_id and upper(rc.card_uid) = v_card
     limit 1;
  end if;

  if v_student is null then
    return jsonb_build_object('ok', true, 'code', 'NO_STUDENT');
  end if;

  v_ts := case when coalesce("created_at", '') ~ '^\d{4}-\d{2}-\d{2}'
               then coalesce(nullif("created_at", '')::timestamptz, now())
               else now() end;

  insert into public.messages (
    school_id, student_id, subject, body, direction, created_at, read_at
  ) values (
    d.school_id, v_student,
    coalesce(nullif(btrim(coalesce("subject", '')), ''), 'Message'),
    coalesce("text", ''),
    'to_student',
    v_ts,
    case when coalesce("read", false) then now() else null end
  )
  returning messages.id into v_msg;

  if "id" is not null then
    perform public.astro_fw_map_put(d.school_id, 'message', "id", v_msg);
  end if;

  return jsonb_build_object('ok', true, 'code', 'SAVED', 'message_id', v_msg::text,
                            'id', coalesce("id", public.astro_fw_int_id(v_msg)));
end $$;

create or replace function public.astro_delete_message(
  "device_code" text default null,
  "id" bigint default null,
  "device_secret" text default null
) returns jsonb
language plpgsql security definer set search_path = public as $$
#variable_conflict use_variable
declare
  d public.devices;
  v_msg uuid;
begin
  d := public.astro_fw_auth("device_code", "device_secret");
  if "id" is null then
    return jsonb_build_object('ok', true, 'code', 'NOOP');
  end if;

  v_msg := public.astro_fw_map_entity(d.school_id, 'message', "id");

  if v_msg is null then
    select m.id into v_msg
      from public.messages m
     where m.school_id = d.school_id and public.astro_fw_int_id(m.id) = "id"
     limit 1;
  end if;

  if v_msg is null then
    return jsonb_build_object('ok', true, 'code', 'NOT_FOUND');
  end if;

  update public.messages set student_hidden_at = now() where id = v_msg and school_id = d.school_id;
  delete from public.astro_fw_id_map where school_id = d.school_id and kind = 'message' and entity_id = v_msg;

  return jsonb_build_object('ok', true, 'code', 'DELETED');
end $$;

create or replace function public.astro_approve_leave(
  "device_code" text default null,
  "id" bigint default null,
  "student_id" text default null,
  "from_date" text default null,
  "to_date" text default null,
  "status" text default null,
  "device_secret" text default null
) returns jsonb
language plpgsql security definer set search_path = public as $$
#variable_conflict use_variable
declare
  d public.devices;
  v_leave uuid;
  v_status text;
  v_student uuid;
  v_tz text := 'Asia/Kolkata';
begin
  d := public.astro_fw_auth("device_code", "device_secret");

  v_status := lower(btrim(coalesce("status", 'pending')));
  if v_status not in ('pending', 'approved', 'rejected', 'cancelled') then
    v_status := 'pending';
  end if;

  if "id" is not null then
    v_leave := public.astro_fw_map_entity(d.school_id, 'leave', "id");

    if v_leave is null then
      select l.id into v_leave
        from public.leave_requests l
       where l.school_id = d.school_id and public.astro_fw_int_id(l.id) = "id"
       limit 1;
    end if;
  end if;

  if v_leave is null and coalesce("student_id", '') <> '' then
    select rc.student_id into v_student
      from public.rfid_cards rc
     where rc.school_id = d.school_id and upper(rc.card_uid) = upper(btrim("student_id"))
     limit 1;

    if v_student is not null then
      select l.id into v_leave
        from public.leave_requests l
       where l.school_id = d.school_id
         and l.student_id = v_student
         and l.from_date = public.astro_fw_date("from_date", v_tz)
         and l.to_date = public.astro_fw_date("to_date", v_tz)
       order by l.created_at desc
       limit 1;
    end if;
  end if;

  if v_leave is null then
    return jsonb_build_object('ok', true, 'code', 'NOT_FOUND');
  end if;

  update public.leave_requests
     set status = v_status,
         decided_at = case when v_status = 'pending' then decided_at else now() end
   where id = v_leave and school_id = d.school_id;

  if "id" is not null then
    perform public.astro_fw_map_put(d.school_id, 'leave', "id", v_leave);
  end if;

  return jsonb_build_object('ok', true, 'code', 'SAVED', 'leave_id', v_leave::text, 'status', v_status);
end $$;

create or replace function public.astro_create_holiday(
  "device_code" text default null,
  "date" text default null,
  "name" text default null,
  "device_secret" text default null
) returns jsonb
language plpgsql security definer set search_path = public as $$
#variable_conflict use_variable
declare
  d public.devices;
  v_date date;
begin
  d := public.astro_fw_auth("device_code", "device_secret");

  if coalesce("date", '') !~ '^\d{4}-\d{2}-\d{2}' then
    return jsonb_build_object('ok', false, 'code', 'BAD_DATE');
  end if;
  v_date := substr("date", 1, 10)::date;

  insert into public.school_holidays as h (school_id, holiday_date, reason, created_at)
  values (d.school_id, v_date, coalesce(nullif(btrim(coalesce("name", '')), ''), 'Holiday'), now())
  on conflict (school_id, holiday_date) do update set reason = excluded.reason;

  return jsonb_build_object('ok', true, 'code', 'SAVED', 'date', to_char(v_date, 'YYYY-MM-DD'));
end $$;

create or replace function public.astro_delete_holiday(
  "device_code" text default null,
  "date" text default null,
  "device_secret" text default null
) returns jsonb
language plpgsql security definer set search_path = public as $$
#variable_conflict use_variable
declare
  d public.devices;
  v_date date;
begin
  d := public.astro_fw_auth("device_code", "device_secret");

  if coalesce("date", '') !~ '^\d{4}-\d{2}-\d{2}' then
    return jsonb_build_object('ok', false, 'code', 'BAD_DATE');
  end if;
  v_date := substr("date", 1, 10)::date;

  delete from public.school_holidays where school_id = d.school_id and holiday_date = v_date;

  return jsonb_build_object('ok', true, 'code', 'DELETED', 'date', to_char(v_date, 'YYYY-MM-DD'));
end $$;

create or replace function public.astro_update_settings(
  "device_code" text default null,
  "late_after_min" integer default null,
  "absent_after_min" integer default null,
  "late_after" text default null,
  "absent_after" text default null,
  "start_time" text default null,
  "end_time" text default null,
  "next_student_password" bigint default null,
  "device_secret" text default null
) returns jsonb
language plpgsql security definer set search_path = public as $$
#variable_conflict use_variable
declare
  d public.devices;
  v_start time;
  v_late time;
  v_absent time;
  v_end time;
begin
  d := public.astro_fw_auth("device_code", "device_secret");

  v_start := case when coalesce("start_time", '') ~ '^\d{1,2}:\d{2}' then nullif("start_time", '')::time else null end;
  v_end := case when coalesce("end_time", '') ~ '^\d{1,2}:\d{2}' then nullif("end_time", '')::time else null end;
  v_late := case when coalesce("late_after", '') ~ '^\d{1,2}:\d{2}' then nullif("late_after", '')::time
                 when "late_after_min" is not null then (make_interval(mins => "late_after_min"))::time
                 else null end;
  v_absent := case when coalesce("absent_after", '') ~ '^\d{1,2}:\d{2}' then nullif("absent_after", '')::time
                   when "absent_after_min" is not null then (make_interval(mins => "absent_after_min"))::time
                   else null end;

  update public.schools
     set day_start = coalesce(v_start, day_start),
         day_end = coalesce(v_end, day_end),
         late_after = coalesce(v_late, late_after),
         absent_after = coalesce(v_absent, absent_after),
         settings_updated_at = now()
   where id = d.school_id;

  return jsonb_build_object('ok', true, 'code', 'SAVED');
end $$;

create or replace function public.astro_factory_wipe(
  "device_code" text default null,
  "confirm" boolean default null,
  "device_secret" text default null
) returns jsonb
language plpgsql security definer set search_path = public as $$
#variable_conflict use_variable
declare
  d public.devices;
begin
  d := public.astro_fw_auth("device_code", "device_secret");

  -- Intentionally NOT destructive. A stolen kiosk must not be able to erase the
  -- school's records. Real wipes are done from the staff dashboard.
  insert into public.device_events (school_id, device_id, method, status, event_ts, payload, result)
  values (d.school_id, d.id, 'manual', 'wipe-requested', now(),
          jsonb_build_object('confirm', coalesce("confirm", false)),
          jsonb_build_object('ok', true, 'note', 'server-side wipe disabled'));

  return jsonb_build_object('ok', true, 'code', 'WIPE_ACK',
                            'note', 'Server records were left intact; clear the device locally.');
end $$;

-- ============================================================================
-- 7. OFFLINE BATCH SYNC (the sketch's store-and-forward queue)
-- ============================================================================
create or replace function public.astro_sync_batch(
  "device_code" text default null,
  "firmware_version" text default null,
  "students" jsonb default null,
  "attendance" jsonb default null,
  "notices" jsonb default null,
  "leaves" jsonb default null,
  "messages" jsonb default null,
  "device_logs" jsonb default null,
  "deleted_students" jsonb default null,
  "deleted_notices" jsonb default null,
  "deleted_messages" jsonb default null,
  "deleted_holidays" jsonb default null,
  "device_secret" text default null
) returns jsonb
language plpgsql security definer set search_path = public as $$
#variable_conflict use_variable
declare
  d public.devices;
  it jsonb;
  v_txt text;
  v_ok int := 0;
  v_fail int := 0;
  v_students int := 0;
  v_att int := 0;
  v_notices int := 0;
  v_leaves int := 0;
  v_msgs int := 0;
  v_logs int := 0;
  v_deleted int := 0;
  v_err text;
begin
  d := public.astro_fw_auth("device_code", "device_secret");

  if coalesce("firmware_version", '') <> '' then
    update public.devices set firmware = "firmware_version", last_seen = now() where id = d.id;
  end if;

  -- ---- students -----------------------------------------------------------
  for it in select * from jsonb_array_elements(coalesce("students", '[]'::jsonb)) loop
    begin
      perform public.astro_create_student(
        "device_code", it ->> 'student_id', it ->> 'display_name', it ->> 'name',
        it ->> 'class', it ->> 'class_name', it ->> 'section', it ->> 'roll',
        it ->> 'rfid_uid', nullif(it ->> 'fingerprint_id', '')::int,
        it ->> 'parent_contact', it ->> 'guardian_email',
        it ->> 'password_hash', nullif(it ->> 'password_seq', '')::bigint,
        nullif(it ->> 'must_change_password', '')::boolean, "device_secret");
      v_students := v_students + 1; v_ok := v_ok + 1;
    exception when others then
      v_fail := v_fail + 1; v_err := sqlerrm;
    end;
  end loop;

  -- ---- attendance ---------------------------------------------------------
  for it in select * from jsonb_array_elements(coalesce("attendance", '[]'::jsonb)) loop
    begin
      perform public.astro_mark_attendance(
        "device_code", it ->> 'student_id', it ->> 'rfid_uid', it ->> 'date',
        it ->> 'status', it ->> 'time',
        coalesce(it ->> 'method', 'rfid'), "device_secret");
      v_att := v_att + 1; v_ok := v_ok + 1;
    exception when others then
      v_fail := v_fail + 1; v_err := sqlerrm;
    end;
  end loop;

  -- ---- notices ------------------------------------------------------------
  for it in select * from jsonb_array_elements(coalesce("notices", '[]'::jsonb)) loop
    begin
      perform public.astro_create_notice(
        "device_code", nullif(it ->> 'id', '')::bigint, it ->> 'title', it ->> 'body',
        it ->> 'priority', coalesce(it ->> 'target', it ->> 'audience'),
        nullif(it ->> 'pinned', '')::boolean, it ->> 'created_at', "device_secret");
      v_notices := v_notices + 1; v_ok := v_ok + 1;
    exception when others then
      v_fail := v_fail + 1; v_err := sqlerrm;
    end;
  end loop;

  -- ---- leaves -------------------------------------------------------------
  for it in select * from jsonb_array_elements(coalesce("leaves", '[]'::jsonb)) loop
    begin
      perform public.astro_approve_leave(
        "device_code", nullif(it ->> 'id', '')::bigint, it ->> 'student_id',
        it ->> 'from_date', it ->> 'to_date', it ->> 'status', "device_secret");
      v_leaves := v_leaves + 1; v_ok := v_ok + 1;
    exception when others then
      v_fail := v_fail + 1; v_err := sqlerrm;
    end;
  end loop;

  -- ---- messages -----------------------------------------------------------
  for it in select * from jsonb_array_elements(coalesce("messages", '[]'::jsonb)) loop
    begin
      perform public.astro_send_message(
        "device_code", nullif(it ->> 'id', '')::bigint, it ->> 'from', it ->> 'to',
        it ->> 'subject', coalesce(it ->> 'text', it ->> 'body'),
        nullif(it ->> 'read', '')::boolean, it ->> 'created_at', "device_secret");
      v_msgs := v_msgs + 1; v_ok := v_ok + 1;
    exception when others then
      v_fail := v_fail + 1; v_err := sqlerrm;
    end;
  end loop;

  -- ---- device logs --------------------------------------------------------
  for it in select * from jsonb_array_elements(coalesce("device_logs", '[]'::jsonb)) loop
    begin
      insert into public.device_events (school_id, device_id, method, status, event_ts, payload, result)
      values (
        d.school_id, d.id,
        coalesce(nullif(it ->> 'method', ''), 'log'),
        coalesce(nullif(it ->> 'status', ''), 'info'),
        coalesce(nullif(it ->> 'ts', '')::timestamptz, now()),
        it,
        jsonb_build_object('source', 'firmware')
      );
      v_logs := v_logs + 1; v_ok := v_ok + 1;
    exception when others then
      v_fail := v_fail + 1; v_err := sqlerrm;
    end;
  end loop;

  -- ---- tombstones ---------------------------------------------------------
  for it in select * from jsonb_array_elements(coalesce("deleted_students", '[]'::jsonb)) loop
    begin
      v_txt := it #>> '{}';
      perform public.astro_delete_student("device_code", v_txt, v_txt, "device_secret");
      v_deleted := v_deleted + 1; v_ok := v_ok + 1;
    exception when others then v_fail := v_fail + 1; v_err := sqlerrm;
    end;
  end loop;

  for it in select * from jsonb_array_elements(coalesce("deleted_notices", '[]'::jsonb)) loop
    begin
      perform public.astro_delete_notice("device_code", (it #>> '{}')::bigint, "device_secret");
      v_deleted := v_deleted + 1; v_ok := v_ok + 1;
    exception when others then v_fail := v_fail + 1; v_err := sqlerrm;
    end;
  end loop;

  for it in select * from jsonb_array_elements(coalesce("deleted_messages", '[]'::jsonb)) loop
    begin
      perform public.astro_delete_message("device_code", (it #>> '{}')::bigint, "device_secret");
      v_deleted := v_deleted + 1; v_ok := v_ok + 1;
    exception when others then v_fail := v_fail + 1; v_err := sqlerrm;
    end;
  end loop;

  for it in select * from jsonb_array_elements(coalesce("deleted_holidays", '[]'::jsonb)) loop
    begin
      perform public.astro_delete_holiday("device_code", it #>> '{}', "device_secret");
      v_deleted := v_deleted + 1; v_ok := v_ok + 1;
    exception when others then v_fail := v_fail + 1; v_err := sqlerrm;
    end;
  end loop;

  return jsonb_build_object(
    'ok', true,
    'code', 'BATCH_DONE',
    'accepted', v_ok,
    'failed', v_fail,
    'students', v_students,
    'attendance', v_att,
    'notices', v_notices,
    'leaves', v_leaves,
    'messages', v_msgs,
    'logs', v_logs,
    'deleted', v_deleted,
    'last_error', v_err
  );
end $$;

-- ============================================================================
-- 8. PERMISSIONS (the kiosk authenticates with the public anon key)
-- ============================================================================
do $$
declare
  r record;
begin
  for r in
    select p.oid::regprocedure as sig
      from pg_proc p
      join pg_namespace n on n.oid = p.pronamespace
     where n.nspname = 'public'
       and p.proname like 'astro\_%'
  loop
    execute format('grant execute on function %s to anon, authenticated, service_role', r.sig);
  end loop;
end $$;

notify pgrst, 'reload schema';
