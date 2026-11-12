-- ============================================================================
-- ASTRO SMART ATTENDANCE — 0002 device API (this is what main.cpp calls)
--
-- All functions are SECURITY DEFINER and validate the device with
-- device_code + device_secret (sha256 compared against devices.secret_hash).
-- EXECUTE is granted to `anon`, so the ESP32 only needs the publishable key.
--
--   POST /rest/v1/rpc/astro_heartbeat
--   POST /rest/v1/rpc/astro_mark_attendance
--   POST /rest/v1/rpc/astro_sync_batch        <- offline queue replay
--   POST /rest/v1/rpc/astro_lookup_card
-- ============================================================================

create extension if not exists pgcrypto with schema extensions;

-- ---------------------------------------------------------------- helpers ---
create or replace function public.astro_norm_uid(p_uid text)
returns text
language sql immutable
as $$
  -- uppercase and drop only separators (space : - . _) so "a1:b2:c3:d4",
  -- "A1-B2-C3-D4" and "A1B2C3D4" all normalise to the same card
  select nullif(upper(regexp_replace(coalesce(p_uid, ''), '[\s:\-\._]', '', 'g')), '')
$$;

create or replace function public.astro_sha256_hex(p_text text)
returns text
language sql immutable
as $$
  select encode(extensions.digest(coalesce(p_text, ''), 'sha256'), 'hex')
$$;

create or replace function public.astro_try_uuid(p_text text)
returns uuid
language plpgsql immutable
as $$
begin
  if p_text is null or p_text !~* '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$' then
    return null;
  end if;
  return p_text::uuid;
exception when others then
  return null;
end $$;

create or replace function public.astro_try_ts(p_text text)
returns timestamptz
language plpgsql immutable
as $$
begin
  if p_text is null or p_text = '' then
    return null;
  end if;
  return p_text::timestamptz;
exception when others then
  return null;
end $$;

-- -------------------------------------------------------- device identity ---
create or replace function public.astro_verify_device(p_device_code text, p_device_secret text)
returns public.devices
language plpgsql stable security definer set search_path = public
as $$
declare
  d public.devices;
begin
  select * into d
  from public.devices
  where device_code = upper(btrim(coalesce(p_device_code, '')))
  limit 1;

  if d.id is null then
    raise exception using message = 'DEVICE_NOT_FOUND', errcode = '28000';
  end if;
  if not d.active then
    raise exception using message = 'DEVICE_DISABLED', errcode = '28000';
  end if;
  if d.secret_hash is distinct from public.astro_sha256_hex(p_device_secret) then
    raise exception using message = 'BAD_DEVICE_SECRET', errcode = '28P01';
  end if;

  return d;
end $$;

-- ------------------------------------------------------------- heartbeat ---
-- Call once after Wi-Fi connects and every few minutes. Returns the server time
-- (so the terminal can fix its clock) plus the school's late threshold.
create or replace function public.astro_heartbeat(
  p_device_code   text,
  p_device_secret text,
  p_firmware      text default null,
  p_rssi          integer default null,
  p_ip            text default null
)
returns jsonb
language plpgsql security definer set search_path = public
as $$
declare
  d        public.devices;
  s        public.schools;
  v_now    timestamptz := now();
begin
  d := public.astro_verify_device(p_device_code, p_device_secret);
  select * into s from public.schools where id = d.school_id;

  update public.devices
     set last_seen = v_now,
         last_boot = coalesce(last_boot, v_now),
         firmware  = coalesce(p_firmware, firmware),
         wifi_rssi = coalesce(p_rssi, wifi_rssi),
         ip        = coalesce(p_ip, ip)
   where id = d.id;

  return jsonb_build_object(
    'ok',           true,
    'code',         'HELLO',
    'device_code',  d.device_code,
    'school',       s.name,
    'school_code',  s.code,
    'timezone',     s.timezone,
    'late_after',   to_char(s.late_after::interval, 'HH24:MI'),
    'day_start',    to_char(s.day_start::interval, 'HH24:MI'),
    'day_end',      to_char(s.day_end::interval, 'HH24:MI'),
    'server_time',  to_char(v_now at time zone s.timezone, 'YYYY-MM-DD"T"HH24:MI:SS'),
    'server_epoch', extract(epoch from v_now)::bigint,
    'local_time',   to_char(v_now at time zone s.timezone, 'HH24:MI:SS'),
    'local_date',   to_char(v_now at time zone s.timezone, 'YYYY-MM-DD')
  );
end $$;

-- ------------------------------------------------------------ card lookup ---
-- Read-only "is this card known?" used by the LCD enrol/diagnostic screen.
create or replace function public.astro_lookup_card(
  p_device_code   text,
  p_device_secret text,
  p_card_uid      text
)
returns jsonb
language plpgsql security definer set search_path = public
as $$
declare
  d   public.devices;
  uid text;
  stu record;
begin
  d := public.astro_verify_device(p_device_code, p_device_secret);
  uid := public.astro_norm_uid(p_card_uid);

  select s.id, s.roll_no, s.full_name, c.name || '-' || c.section as class_name,
         card.active as card_active
    into stu
  from public.rfid_cards card
  join public.students s on s.id = card.student_id
  left join public.classes c on c.id = s.class_id
  where card.card_uid = uid and s.school_id = d.school_id
  limit 1;

  if stu.id is null then
    return jsonb_build_object('ok', false, 'code', 'UNKNOWN_CARD', 'uid', uid);
  end if;

  return jsonb_build_object(
    'ok', true, 'code', 'KNOWN_CARD', 'uid', uid,
    'card_active', stu.card_active,
    'student', jsonb_build_object(
      'id', stu.id, 'roll_no', stu.roll_no, 'name', stu.full_name, 'class', stu.class_name
    )
  );
end $$;

-- --------------------------------------------------------- mark attendance ---
-- Idempotent: the same p_event_uid can be sent any number of times (offline
-- replay) and it returns the stored result instead of writing a second row.
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
  v_ts       timestamptz := coalesce(p_event_ts, now());
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

  -- 1. idempotency: has this exact tap already been ingested?
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

  -- 2. who tapped?
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

  -- 3. daily status: late once the school's late_after time has passed
  v_status := case
                when v_session = 'daily' and v_local::time > s.late_after then 'late'
                else 'present'
              end;

  -- 4. write (the unique slot index makes a second write a no-op)
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

    -- 5. parent alert for every late arrival (queued, never sent from here)
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

  -- 6. housekeeping
  update public.device_events
     set status = v_result->>'code', result = v_result, processed = true
   where event_uid = v_event;

  update public.devices set last_seen = now() where id = d.id;

  return v_result;
end $$;

-- ----------------------------------------------------------- batch replay ---
-- Body: {"p_device_code":"...","p_device_secret":"...","p_events":[{...},{...}]}
-- Each element uses the same keys as astro_mark_attendance.
create or replace function public.astro_sync_batch(
  p_device_code   text,
  p_device_secret text,
  p_events        jsonb
)
returns jsonb
language plpgsql security definer set search_path = public
as $$
declare
  e        jsonb;
  one      jsonb;
  results  jsonb := '[]'::jsonb;
  n_ok     integer := 0;
  n_fail   integer := 0;
begin
  perform public.astro_verify_device(p_device_code, p_device_secret);

  if p_events is null or jsonb_typeof(p_events) <> 'array' then
    raise exception using message = 'EVENTS_MUST_BE_ARRAY', errcode = '22023';
  end if;

  for e in select * from jsonb_array_elements(p_events) loop
    begin
      one := public.astro_mark_attendance(
               p_device_code,
               p_device_secret,
               e->>'card_uid',
               nullif(e->>'fingerprint_id', '')::integer,
               coalesce(e->>'method', 'rfid'),
               coalesce(e->>'session', 'daily'),
               nullif(e->>'period_no', '')::integer,
               public.astro_try_uuid(e->>'event_uid'),
               public.astro_try_ts(e->>'event_ts'));
      n_ok := n_ok + 1;
    exception when others then
      one := jsonb_build_object(
               'ok', false, 'code', 'ERROR', 'message', sqlerrm,
               'event_uid', e->>'event_uid');
      n_fail := n_fail + 1;
    end;
    results := results || jsonb_build_array(one);
  end loop;

  return jsonb_build_object('ok', true, 'code', 'BATCH_DONE',
                            'accepted', n_ok, 'failed', n_fail, 'results', results);
end $$;

-- ============================================================================
-- Privileges
-- ============================================================================
revoke all on function
  public.astro_norm_uid(text),
  public.astro_sha256_hex(text),
  public.astro_try_uuid(text),
  public.astro_try_ts(text),
  public.astro_verify_device(text, text),
  public.astro_heartbeat(text, text, text, integer, text),
  public.astro_lookup_card(text, text, text),
  public.astro_mark_attendance(text, text, text, integer, text, text, integer, uuid, timestamptz),
  public.astro_sync_batch(text, text, jsonb)
from public;

grant execute on function
  public.astro_heartbeat(text, text, text, integer, text),
  public.astro_lookup_card(text, text, text),
  public.astro_mark_attendance(text, text, text, integer, text, text, integer, uuid, timestamptz),
  public.astro_sync_batch(text, text, jsonb)
to anon, authenticated;
