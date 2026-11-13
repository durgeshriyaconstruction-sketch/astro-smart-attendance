-- ============================================================================
--  ASTRO SMART ATTENDANCE — FIRMWARE ⇄ SUPABASE BRIDGE
--  Version 1.0  |  2026-11-13  |  Team Sun Rises India
-- ============================================================================
--
--  WHY THIS FILE EXISTS
--  --------------------
--  The firmware in main.cpp (v26.11.7) calls 23 RPC functions of the form
--  POST /rest/v1/rpc/astro_*. Of those, only 6 existed in this database and
--  NONE of those 6 had matching parameter names. The other 17 did not exist
--  at all, so every call returned HTTP 404 and the ESP32 could never sync.
--
--  This migration does NOT throw away or duplicate the existing well-built
--  schema/functions (astro_mark_attendance, astro_sync_batch, astro_verify_device,
--  astro_save_student, ...). It only ADDS thin, stateless wrapper functions
--  whose parameter names match exactly what main.cpp already sends, and which
--  delegate to the existing audited functions internally.
--
--  Result: the firmware needs no rewrite. Only two things must be set on the
--  device: the correct API key and the device secret.
--
--  AUTHENTICATION
--  --------------
--  Every wrapper resolves the device from, in order:
--     1. p_device_code in the JSON body
--     2. the X-Astro-Device request header
--     3. the single active row in public.devices (single-terminal installs)
--  and verifies X-Astro-Secret against devices.secret_hash (sha256).
--
--  Idempotent: safe to run more than once.
-- ============================================================================

-- ---------------------------------------------------------------------------
-- 0. Helpers
-- ---------------------------------------------------------------------------

-- Stable, non-zero 31-bit integer derived from a UUID.
-- The firmware stores notice / leave / message ids in a uint32_t, while the
-- schema correctly uses UUID primary keys. This gives a deterministic bridge
-- so the LCD never shows a zero id and re-syncs stay consistent.
create or replace function public.astro_int_id(p_uuid uuid)
returns integer
language sql
immutable
set search_path to 'public'
as $$
  select case
           when p_uuid is null then 0
           else (('x' || substr(md5(p_uuid::text), 1, 8))::bit(32)::bigint
                 & 2147483647)::integer
         end;
$$;

-- Resolve + verify the calling device. Raises 401-equivalent on failure.
create or replace function public.astro_dev(
  p_device_code   text default null,
  p_device_secret text default null
)
returns public.devices
language plpgsql
security definer
set search_path to 'public'
as $$
declare
  hdr   jsonb;
  v_code   text;
  v_secret text;
  d public.devices;
begin
  begin
    hdr := coalesce(current_setting('request.headers', true), '{}')::jsonb;
  exception when others then
    hdr := '{}'::jsonb;
  end;

  v_code := coalesce(
              nullif(btrim(coalesce(p_device_code, '')), ''),
              hdr->>'x-astro-device');

  v_secret := coalesce(
                nullif(btrim(coalesce(p_device_secret, '')), ''),
                hdr->>'x-astro-secret');

  if v_code is null then
    -- Single-terminal convenience: if exactly one active device exists, use it.
    select * into d from public.devices where active order by created_at limit 1;
  else
    select * into d from public.devices
     where device_code = upper(btrim(v_code)) limit 1;
  end if;

  if d.id is null then
    raise exception using message = 'DEVICE_NOT_FOUND', errcode = '28000';
  end if;
  if not d.active then
    raise exception using message = 'DEVICE_DISABLED', errcode = '28000';
  end if;
  if v_secret is null then
    raise exception using
      message = 'DEVICE_SECRET_MISSING: set ASTRO_DEVICE_SECRET on the device and send it as the X-Astro-Secret header',
      errcode = '28P01';
  end if;
  if d.secret_hash is distinct from public.astro_sha256_hex(v_secret) then
    raise exception using message = 'BAD_DEVICE_SECRET', errcode = '28P01';
  end if;

  return d;
end $$;

-- The bearer/token the client already used, echoed back by the handshake so the
-- firmware's subsequent calls keep working without needing a JS/Edge token mint.
create or replace function public.astro_request_bearer()
returns text
language plpgsql
stable
set search_path to 'public'
as $$
declare
  hdr jsonb;
  a   text;
begin
  begin
    hdr := coalesce(current_setting('request.headers', true), '{}')::jsonb;
  exception when others then
    hdr := '{}'::jsonb;
  end;
  a := coalesce(hdr->>'authorization', '');
  if a ilike 'bearer %' then return substr(a, 8); end if;
  return coalesce(nullif(a, ''), current_setting('request.headers', true));
end $$;

-- ===========================================================================
-- 1. HANDSHAKE  — was missing entirely (404)
-- ===========================================================================
create or replace function public.astro_device_handshake(
  p_device_code      text,
  p_device_secret    text default null,
  p_firmware_version text default null
)
returns jsonb
language plpgsql
security definer
set search_path to 'public'
as $$
declare
  d public.devices;
  s public.schools;
begin
  d := public.astro_dev(p_device_code, p_device_secret);

  update public.devices
     set last_seen = now(),
         last_boot = now(),
         firmware  = coalesce(nullif(btrim(coalesce(p_firmware_version, '')), ''), firmware)
   where id = d.id
  returning * into d;

  select * into s from public.schools where id = d.school_id;

  return jsonb_build_object(
    'ok',                true,
    'device_code',       d.device_code,
    'device_id',         d.id,
    'school_id',         d.school_id,
    'school_code',       s.code,
    'school_name',       s.name,
    'timezone',          s.timezone,
    'session_token',     public.astro_request_bearer(),
    'token',             public.astro_request_bearer(),
    'expires_in',        3600,
    'server_time',       now(),
    'firmware_version',  d.firmware
  );
end $$;

-- ===========================================================================
-- 2. SETTINGS READ  — was missing (404)
--    Keys match applyCloudSettings() in main.cpp exactly.
-- ===========================================================================
create or replace function public.astro_get_settings(
  p_device_code   text default null,
  p_device_secret text default null
)
returns jsonb
language plpgsql
security definer
set search_path to 'public'
as $$
declare
  d public.devices;
  s public.schools;
begin
  d := public.astro_dev(p_device_code, p_device_secret);
  select * into s from public.schools where id = d.school_id;
  if s.id is null then
    return jsonb_build_object('ok', false, 'code', 'SCHOOL_NOT_FOUND');
  end if;

  return jsonb_build_object(
    'ok',            true,
    'school_id',     s.id,
    'school_code',   s.code,
    'school_name',   s.name,
    'timezone',      s.timezone,
    'start_time',    to_char(s.day_start, 'HH24:MI'),
    'end_time',      to_char(s.day_end,   'HH24:MI'),
    'late_after',    to_char(s.late_after,   'HH24:MI'),
    'absent_after',  case when s.absent_after is null then null
                          else to_char(s.absent_after, 'HH24:MI') end,
    'late_after_min',   extract(hour from s.late_after)::int * 60
                        + extract(minute from s.late_after)::int,
    'alert_emails',  coalesce(s.alert_emails, false),
    'weekly_off',    coalesce(to_jsonb(s.weekly_off), '[]'::jsonb)
  );
end $$;

-- ===========================================================================
-- 3. HOLIDAYS  — astro_list_holidays / astro_create_holiday / astro_delete_holiday
--    all three were missing (404)
-- ===========================================================================
create or replace function public.astro_list_holidays(
  p_device_code   text default null,
  p_device_secret text default null
)
returns jsonb
language plpgsql
security definer
set search_path to 'public'
as $$
declare
  d public.devices;
  out jsonb;
begin
  d := public.astro_dev(p_device_code, p_device_secret);
  select coalesce(jsonb_agg(jsonb_build_object(
           'date',   h.holiday_date,
           'reason', h.reason
         ) order by h.holiday_date), '[]'::jsonb)
    into out
    from public.school_holidays h
   where h.school_id = d.school_id;
  return out;
end $$;

create or replace function public.astro_create_holiday(
  p_device_code   text  default null,
  p_date          text  default null,
  p_name          text  default null,
  p_device_secret text  default null
)
returns jsonb
language plpgsql
security definer
set search_path to 'public'
as $$
declare
  d public.devices;
  v_date date;
begin
  d := public.astro_dev(p_device_code, p_device_secret);
  v_date := public.astro_try_ts(p_date)::date;
  if v_date is null then
    return jsonb_build_object('ok', false, 'code', 'BAD_DATE', 'date', p_date);
  end if;

  perform public.astro_set_holiday(v_date, coalesce(nullif(btrim(p_name), ''), 'Holiday'), d.school_id);
  return jsonb_build_object('ok', true, 'code', 'HOLIDAY_SAVED', 'date', v_date);
end $$;

create or replace function public.astro_delete_holiday(
  p_device_code   text default null,
  p_date          text default null,
  p_device_secret text default null
)
returns jsonb
language plpgsql
security definer
set search_path to 'public'
as $$
declare
  d public.devices;
  v_date date;
begin
  d := public.astro_dev(p_device_code, p_device_secret);
  v_date := public.astro_try_ts(p_date)::date;
  if v_date is null then
    return jsonb_build_object('ok', false, 'code', 'BAD_DATE');
  end if;

  perform public.astro_remove_holiday(v_date, d.school_id);
  return jsonb_build_object('ok', true, 'code', 'HOLIDAY_REMOVED', 'date', v_date);
end $$;

-- ===========================================================================
-- 4. STUDENTS  — astro_list_students / astro_lookup_by_rfid / astro_lookup_by_fingerprint
--    all three were missing (404). This is why an unknown card could never be
--    resolved on the device.
-- ===========================================================================
create or replace function public.astro_list_students(
  p_device_code   text default null,
  p_device_secret text default null
)
returns jsonb
language plpgsql
security definer
set search_path to 'public'
as $$
declare
  d public.devices;
  out jsonb;
begin
  d := public.astro_dev(p_device_code, p_device_secret);

  select coalesce(jsonb_agg(x order by x->>'name'), '[]'::jsonb)
    into out
    from (
      select jsonb_build_object(
               'student_id',     st.id,
               'rfid_uid',       c.card_uid,
               'name',           st.full_name,
               'display_name',   st.full_name,
               'roll',           st.roll_no,
               'class_name',     cls.name,
               'section',        cls.section,
               'class',          case when cls.name is null then null
                                      else cls.name || '-' || cls.section end,
               'fingerprint_id', st.fingerprint_id,
               'guardian_email', st.guardian_email,
               'parent_contact', st.guardian_phone,
               'active',         st.active
             ) as x
        from public.students st
        left join public.classes cls on cls.id = st.class_id
        left join public.rfid_cards c on c.student_id = st.id and c.active
       where st.school_id = d.school_id
         and st.active
    ) t;

  return out;
end $$;

create or replace function public.astro_lookup_by_rfid(
  p_device_code   text default null,
  p_rfid_uid      text default null,
  p_uid           text default null,
  p_device_secret text default null
)
returns jsonb
language plpgsql
security definer
set search_path to 'public'
as $$
declare
  d public.devices;
  uid text;
  out jsonb;
begin
  d := public.astro_dev(p_device_code, p_device_secret);
  uid := public.astro_norm_uid(coalesce(p_rfid_uid, p_uid));

  if uid is null then
    return jsonb_build_object('ok', false, 'code', 'NO_UID');
  end if;

  select jsonb_build_object(
           'ok',             true,
           'student_id',     st.id,
           'rfid_uid',       c.card_uid,
           'name',           st.full_name,
           'display_name',   st.full_name,
           'roll',           st.roll_no,
           'class_name',     cls.name,
           'section',        cls.section,
           'class',          case when cls.name is null then null
                                  else cls.name || '-' || cls.section end,
           'fingerprint_id', st.fingerprint_id,
           'active',         st.active
         )
    into out
    from public.rfid_cards c
    join public.students st on st.id = c.student_id
    left join public.classes cls on cls.id = st.class_id
   where c.card_uid = uid
     and c.active
     and st.active
     and st.school_id = d.school_id
   limit 1;

  return coalesce(out, jsonb_build_object(
           'ok', false, 'code', 'UNKNOWN_CARD', 'uid', uid,
           'message', 'Card not registered for this school'));
end $$;

create or replace function public.astro_lookup_by_fingerprint(
  p_device_code   text    default null,
  p_fingerprint_id integer default null,
  p_finger_id     integer default null,
  p_device_secret text    default null
)
returns jsonb
language plpgsql
security definer
set search_path to 'public'
as $$
declare
  d public.devices;
  slot integer;
  out jsonb;
begin
  d := public.astro_dev(p_device_code, p_device_secret);
  slot := coalesce(p_fingerprint_id, p_finger_id);

  if slot is null then
    return jsonb_build_object('ok', false, 'code', 'NO_FINGERPRINT_ID');
  end if;

  select jsonb_build_object(
           'ok',             true,
           'student_id',     st.id,
           'name',           st.full_name,
           'display_name',   st.full_name,
           'roll',           st.roll_no,
           'class_name',     cls.name,
           'section',        cls.section,
           'class',          case when cls.name is null then null
                                  else cls.name || '-' || cls.section end,
           'fingerprint_id', slot,
           'active',         st.active
         )
    into out
    from public.students st
    left join public.classes cls on cls.id = st.class_id
   where st.school_id = d.school_id
     and st.active
     and (st.fingerprint_id = slot
          or exists (select 1 from public.fingerprints f
                      where f.student_id = st.id
                        and f.slot = slot
                        and f.device_id = d.id))
   limit 1;

  return coalesce(out, jsonb_build_object(
           'ok', false, 'code', 'UNKNOWN_FINGERPRINT', 'fingerprint_id', slot));
end $$;

-- ===========================================================================
-- 5. ATTENDANCE MARK  — signature mismatch with the existing function.
--    main.cpp sends: device_code, student_id, rfid_uid, date, status, time, method
--    Existing function wants: device_code, device_secret, card_uid, ...
--    This overload accepts the firmware shape and delegates.
-- ===========================================================================
create or replace function public.astro_mark_attendance(
  p_device_code   text    default null,
  p_student_id    text    default null,
  p_rfid_uid      text    default null,
  p_date          text    default null,
  p_status        text    default null,
  p_time          text    default null,
  p_method        text    default null,
  p_device_secret text    default null
)
returns jsonb
language plpgsql
security definer
set search_path to 'public'
as $$
declare
  d public.devices;
  s public.schools;
  uid text;
  stu public.students;
  v_ts timestamptz;
  res jsonb;
  v_status text := lower(btrim(coalesce(p_status, '')));
  v_method text := lower(btrim(coalesce(nullif(p_method, ''), 'rfid')));
begin
  d := public.astro_dev(p_device_code, p_device_secret);
  select * into s from public.schools where id = d.school_id;

  uid := public.astro_norm_uid(coalesce(p_rfid_uid, p_student_id));

  -- Resolve the event timestamp. The firmware's clock is HTTP-Date synced, so
  -- p_time is trusted only when a date is present and sane; otherwise use now().
  begin
    v_ts := (coalesce(public.astro_try_ts(p_date), now()::date)::text
             || ' ' || coalesce(nullif(btrim(p_time), ''), to_char(now(), 'HH24:MI'))
             || ' ' || coalesce(s.timezone, 'Asia/Kolkata'))::timestamptz;
  exception when others then
    v_ts := now();
  end;
  if v_ts < now() - interval '30 days' or v_ts > now() + interval '10 minutes' then
    v_ts := now();
  end if;

  if uid is not null then
    begin
      res := public.astro_mark_attendance(
               d.device_code, null, uid, null, v_method, 'daily', null, null, v_ts);
      return coalesce(res, jsonb_build_object('ok', true, 'code', 'MARKED'));
    exception when others then
      -- fall through to the explicit-status path below
      null;
    end;
  end if;

  -- Fingerprint or explicit status path: resolve the student, then write the
  -- row through astro_set_attendance so cut-off logic is not double-applied.
  select * into stu from public.students
   where school_id = d.school_id
     and active
     and id::text = coalesce(p_student_id, '')
   limit 1;

  if stu.id is null and uid is not null then
    select st.* into stu
      from public.students st
      left join public.rfid_cards c on c.student_id = st.id and c.active
     where st.school_id = d.school_id
       and st.active
       and c.card_uid = uid
     limit 1;
  end if;

  if stu.id is null then
    return jsonb_build_object('ok', false, 'code', 'UNKNOWN_CARD', 'uid', uid);
  end if;

  -- astro_set_attendance accepts: present | late | absent | leave | excused |
  -- half_day | left  (note: 'half_day', not 'half').
  perform public.astro_set_attendance(
            stu.id,
            v_ts::date,
            case
              when v_status in ('present')                    then 'present'
              when v_status in ('late')                       then 'late'
              when v_status in ('absent')                     then 'absent'
              when v_status in ('leave', 'excused')           then 'leave'
              when v_status in ('half day', 'half', 'half_day') then 'half_day'
              else 'present'
            end,
            null,
            d.school_id);

  return jsonb_build_object('ok', true, 'code', 'MARKED', 'uid', uid,
                            'student_id', stu.id, 'status', v_status);
end $$;

-- ===========================================================================
-- 6. ATTENDANCE READ  — astro_list_attendance was missing (404)
--    main.cpp keys rows by rfid and reads status/time/method.
-- ===========================================================================
create or replace function public.astro_list_attendance(
  p_device_code   text default null,
  p_date          text default null,
  p_device_secret text default null
)
returns jsonb
language plpgsql
security definer
set search_path to 'public'
as $$
declare
  d public.devices;
  s public.schools;
  v_date date;
  out jsonb;
begin
  d := public.astro_dev(p_device_code, p_device_secret);
  select * into s from public.schools where id = d.school_id;
  v_date := coalesce(public.astro_try_ts(p_date)::date, (now() at time zone coalesce(s.timezone, 'Asia/Kolkata'))::date);

  select coalesce(jsonb_agg(jsonb_build_object(
           'rfid_uid',   coalesce(c.card_uid, st.id::text),
           'student_id', st.id,
           'name',       st.full_name,
           'roll',       st.roll_no,
           'status',     initcap(a.status),
           'date',       a.attendance_date,
           'time',       to_char(a.marked_at at time zone coalesce(s.timezone, 'Asia/Kolkata'), 'HH24:MI'),
           'method',     a.method,
           'session',    a.session
         ) order by a.marked_at), '[]'::jsonb)
    into out
    from public.attendance a
    join public.students st on st.id = a.student_id
    left join public.rfid_cards c on c.student_id = st.id and c.active
   where a.school_id = d.school_id
     and a.attendance_date = v_date
     and a.session = 'daily';

  return out;
end $$;

-- ===========================================================================
-- 7. NOTICES  — astro_list_notices / astro_create_notice / astro_delete_notice
-- ===========================================================================
create or replace function public.astro_list_notices(
  p_device_code   text default null,
  p_device_secret text default null
)
returns jsonb
language plpgsql
security definer
set search_path to 'public'
as $$
declare
  d public.devices;
  out jsonb;
begin
  d := public.astro_dev(p_device_code, p_device_secret);

  select coalesce(jsonb_agg(jsonb_build_object(
           'id',         public.astro_int_id(n.id),
           'uuid',       n.id,
           'title',      n.title,
           'body',       n.body,
           'priority',   coalesce(n.priority, 'normal'),
           'target',     coalesce(n.audience, 'All'),
           'pinned',     coalesce(n.pinned, false),
           'created_at', to_char(n.created_at, 'YYYY-MM-DD"T"HH24:MI:SS')
         ) order by n.created_at desc), '[]'::jsonb)
    into out
    from public.notices n
   where n.school_id = d.school_id
     and (n.expires_at is null or n.expires_at > now())
   limit 200;

  return out;
end $$;

create or replace function public.astro_create_notice(
  p_device_code   text    default null,
  p_id            bigint  default null,
  p_title         text    default null,
  p_body          text    default null,
  p_priority      text    default null,
  p_target        text    default null,
  p_pinned        boolean default false,
  p_created_at    text    default null,
  p_device_secret text    default null
)
returns jsonb
language plpgsql
security definer
set search_path to 'public'
as $$
declare
  d public.devices;
  v_uuid uuid;
begin
  d := public.astro_dev(p_device_code, p_device_secret);

  insert into public.notices (school_id, title, body, audience, priority, pinned, publish_at)
  values (d.school_id,
          coalesce(nullif(btrim(p_title), ''), 'Notice'),
          coalesce(p_body, ''),
          coalesce(nullif(btrim(p_target), ''), 'All'),
          lower(coalesce(nullif(btrim(p_priority), ''), 'normal')),
          coalesce(p_pinned, false),
          coalesce(public.astro_try_ts(p_created_at), now()))
  returning id into v_uuid;

  return jsonb_build_object('ok', true, 'code', 'NOTICE_SAVED', 'uuid', v_uuid,
                            'id', public.astro_int_id(v_uuid));
end $$;

create or replace function public.astro_delete_notice(
  p_device_code   text   default null,
  p_id            bigint default null,
  p_uuid          uuid   default null,
  p_device_secret text   default null
)
returns jsonb
language plpgsql
security definer
set search_path to 'public'
as $$
declare
  d public.devices;
  n_rec record;
begin
  d := public.astro_dev(p_device_code, p_device_secret);

  for n_rec in
    select id, public.astro_int_id(id) as iid
      from public.notices
     where school_id = d.school_id
  loop
    if n_rec.iid = p_id or n_rec.id = p_uuid then
      delete from public.notices where id = n_rec.id;
      return jsonb_build_object('ok', true, 'code', 'NOTICE_DELETED', 'id', p_id);
    end if;
  end loop;

  return jsonb_build_object('ok', true, 'code', 'NOTICE_NOT_FOUND', 'id', p_id);
end $$;

-- ===========================================================================
-- 8. LEAVES  — astro_list_leaves / astro_approve_leave
-- ===========================================================================
create or replace function public.astro_list_leaves(
  p_device_code   text default null,
  p_device_secret text default null
)
returns jsonb
language plpgsql
security definer
set search_path to 'public'
as $$
declare
  d public.devices;
  out jsonb;
begin
  d := public.astro_dev(p_device_code, p_device_secret);

  select coalesce(jsonb_agg(jsonb_build_object(
           'id',         public.astro_int_id(l.id),
           'uuid',       l.id,
           'student_id', coalesce(c.card_uid, st.id::text),
           'name',       st.full_name,
           'from_date',  l.from_date,
           'to_date',    l.to_date,
           'reason',     l.reason,
           'status',     lower(coalesce(l.status, 'pending')),
           'created_at', to_char(l.created_at, 'YYYY-MM-DD"T"HH24:MI:SS')
         ) order by l.created_at desc), '[]'::jsonb)
    into out
    from public.leave_requests l
    join public.students st on st.id = l.student_id
    left join public.rfid_cards c on c.student_id = st.id and c.active
   where l.school_id = d.school_id
   limit 250;

  return out;
end $$;

create or replace function public.astro_approve_leave(
  p_device_code   text   default null,
  p_id            bigint default null,
  p_uuid          uuid   default null,
  p_student_id    text   default null,
  p_from_date     text   default null,
  p_to_date       text   default null,
  p_status        text   default null,
  p_device_secret text   default null
)
returns jsonb
language plpgsql
security definer
set search_path to 'public'
as $$
declare
  d public.devices;
  l_rec record;
  v_approve boolean := lower(coalesce(nullif(btrim(p_status), ''), 'approved')) in ('approved', 'approve', 'true');
begin
  d := public.astro_dev(p_device_code, p_device_secret);

  for l_rec in
    select id, public.astro_int_id(id) as iid
      from public.leave_requests
     where school_id = d.school_id
  loop
    if l_rec.iid = p_id or l_rec.id = p_uuid then
      perform public.astro_decide_leave(l_rec.id, v_approve, 'Decided on device');
      return jsonb_build_object('ok', true, 'code', 'LEAVE_DECIDED',
                                'id', p_id, 'approved', v_approve);
    end if;
  end loop;

  return jsonb_build_object('ok', false, 'code', 'LEAVE_NOT_FOUND', 'id', p_id);
end $$;

-- ===========================================================================
-- 9. MESSAGES  — astro_list_messages / astro_send_message / astro_delete_message
-- ===========================================================================
create or replace function public.astro_list_messages(
  p_device_code   text default null,
  p_device_secret text default null
)
returns jsonb
language plpgsql
security definer
set search_path to 'public'
as $$
declare
  d public.devices;
  out jsonb;
begin
  d := public.astro_dev(p_device_code, p_device_secret);

  select coalesce(jsonb_agg(jsonb_build_object(
           'id',         public.astro_int_id(m.id),
           'uuid',       m.id,
           'from',       'Admin',
           'to',         coalesce(c.card_uid, st.id::text),
           'name',       st.full_name,
           'subject',    coalesce(nullif(m.subject, ''), 'Message'),
           'text',       m.body,
           'body',       m.body,
           'read',       m.read_at is not null,
           'created_at', to_char(m.created_at, 'YYYY-MM-DD"T"HH24:MI:SS')
         ) order by m.created_at desc), '[]'::jsonb)
    into out
    from public.messages m
    join public.students st on st.id = m.student_id
    left join public.rfid_cards c on c.student_id = st.id and c.active
   where m.school_id = d.school_id
     and (m.direction is null or m.direction <> 'out')
   limit 250;

  return out;
end $$;

create or replace function public.astro_send_message(
  p_device_code   text    default null,
  p_id            bigint  default null,
  p_from          text    default null,
  p_to            text    default null,
  p_text          text    default null,
  p_subject       text    default null,
  p_created_at    text    default null,
  p_read          boolean default null,
  p_device_secret text    default null
)
returns jsonb
language plpgsql
security definer
set search_path to 'public'
as $$
declare
  d public.devices;
  stu public.students;
  uid text;
  v_uuid uuid;
begin
  d := public.astro_dev(p_device_code, p_device_secret);
  uid := public.astro_norm_uid(p_to);

  select st.* into stu
    from public.students st
    left join public.rfid_cards c on c.student_id = st.id and c.active
   where st.school_id = d.school_id
     and st.active
     and (c.card_uid = uid or st.id::text = coalesce(p_to, ''))
   limit 1;

  if stu.id is null then
    return jsonb_build_object('ok', false, 'code', 'STUDENT_NOT_FOUND', 'to', p_to);
  end if;

  insert into public.messages (school_id, student_id, subject, body, direction, created_at)
  values (d.school_id, stu.id,
          coalesce(nullif(btrim(p_subject), ''), 'Message'),
          coalesce(p_text, ''),
          'in',
          coalesce(public.astro_try_ts(p_created_at), now()))
  returning id into v_uuid;

  return jsonb_build_object('ok', true, 'code', 'MESSAGE_SENT',
                            'uuid', v_uuid, 'id', public.astro_int_id(v_uuid));
end $$;

create or replace function public.astro_delete_message(
  p_device_code   text   default null,
  p_id            bigint default null,
  p_uuid          uuid   default null,
  p_device_secret text   default null
)
returns jsonb
language plpgsql
security definer
set search_path to 'public'
as $$
declare
  d public.devices;
  m_rec record;
begin
  d := public.astro_dev(p_device_code, p_device_secret);

  for m_rec in
    select id, public.astro_int_id(id) as iid
      from public.messages
     where school_id = d.school_id
  loop
    if m_rec.iid = p_id or m_rec.id = p_uuid then
      delete from public.messages where id = m_rec.id;
      return jsonb_build_object('ok', true, 'code', 'MESSAGE_DELETED', 'id', p_id);
    end if;
  end loop;

  return jsonb_build_object('ok', true, 'code', 'MESSAGE_NOT_FOUND', 'id', p_id);
end $$;

-- ===========================================================================
-- 10. STUDENT CREATE / DELETE from the device
-- ===========================================================================
create or replace function public.astro_create_student(
  p_device_code         text    default null,
  p_student_id          text    default null,
  p_display_name        text    default null,
  p_name                text    default null,
  p_class               text    default null,
  p_class_name          text    default null,
  p_section             text    default null,
  p_roll                text    default null,
  p_rfid_uid            text    default null,
  p_fingerprint_id      integer default null,
  p_parent_contact      text    default null,
  p_guardian_email      text    default null,
  p_password_hash       text    default null,
  p_password_seq        bigint  default null,
  p_must_change_password boolean default null,
  p_device_secret       text    default null
)
returns jsonb
language plpgsql
security definer
set search_path to 'public'
as $$
declare
  d public.devices;
  v_class_name text;
  v_section    text;
  v_class_id   uuid;
  v_name       text;
  v_roll       text;
  v_uid        text;
  stu public.students;
  v_new boolean := false;
begin
  d := public.astro_dev(p_device_code, p_device_secret);

  v_name := coalesce(nullif(btrim(p_name), ''), nullif(btrim(p_display_name), ''), 'Unnamed');
  v_roll := coalesce(nullif(btrim(p_roll), ''), '');
  v_uid  := public.astro_norm_uid(p_rfid_uid);

  -- "6-A" coming from the firmware, or separate class_name + section fields.
  v_class_name := coalesce(nullif(btrim(p_class_name), ''),
                           nullif(split_part(coalesce(p_class, ''), '-', 1), ''));
  v_section    := coalesce(nullif(btrim(p_section), ''),
                           nullif(split_part(coalesce(p_class, ''), '-', 2), ''));

  if v_class_name is not null then
    select id into v_class_id from public.classes
     where school_id = d.school_id
       and lower(name) = lower(v_class_name)
       and coalesce(section, '') = coalesce(v_section, '')
     limit 1;

    if v_class_id is null then
      insert into public.classes (school_id, name, section)
      values (d.school_id, v_class_name, v_section)
      returning id into v_class_id;
    end if;
  end if;

  -- Find an existing student by card, then by roll number.
  if v_uid is not null then
    select st.* into stu
      from public.students st
      join public.rfid_cards c on c.student_id = st.id
     where c.card_uid = v_uid and c.active and st.school_id = d.school_id
     limit 1;
  end if;

  if stu.id is null and v_roll <> '' then
    select * into stu from public.students
     where school_id = d.school_id and roll_no = v_roll limit 1;
  end if;

  if stu.id is null then
    insert into public.students
      (school_id, class_id, roll_no, full_name, guardian_email, guardian_phone, fingerprint_id, active)
    values
      (d.school_id, v_class_id, v_roll, v_name,
       nullif(btrim(p_guardian_email), ''), nullif(btrim(p_parent_contact), ''),
       p_fingerprint_id, true)
    returning * into stu;
    v_new := true;
  else
    update public.students
       set full_name      = coalesce(v_name, full_name),
           class_id       = coalesce(v_class_id, class_id),
           roll_no        = case when v_roll <> '' then v_roll else roll_no end,
           guardian_email = coalesce(nullif(btrim(p_guardian_email), ''), guardian_email),
           guardian_phone = coalesce(nullif(btrim(p_parent_contact), ''), guardian_phone),
           fingerprint_id = coalesce(p_fingerprint_id, fingerprint_id),
           updated_at     = now()
     where id = stu.id
    returning * into stu;
  end if;

  if v_uid is not null then
    insert into public.rfid_cards (school_id, student_id, card_uid, active)
    values (d.school_id, stu.id, v_uid, true)
    on conflict (card_uid) do update
      set student_id = excluded.student_id,
          school_id  = excluded.school_id,
          active     = true;
  end if;

  if p_fingerprint_id is not null then
    insert into public.fingerprints (device_id, school_id, slot, student_id)
    values (d.id, d.school_id, p_fingerprint_id, stu.id)
    on conflict (device_id, slot) do update
      set student_id = excluded.student_id;
  end if;

  return jsonb_build_object('ok', true, 'code', case when v_new then 'STUDENT_CREATED' else 'STUDENT_UPDATED' end,
                            'student_id', stu.id, 'rfid_uid', v_uid, 'name', stu.full_name);
exception
  when unique_violation then
    raise exception using message = 'CARD_ALREADY_ASSIGNED', errcode = '23505';
end $$;

create or replace function public.astro_delete_student(
  p_device_code   text default null,
  p_student_id    text default null,
  p_rfid_uid      text default null,
  p_device_secret text default null
)
returns jsonb
language plpgsql
security definer
set search_path to 'public'
as $$
declare
  d public.devices;
  uid text;
  stu public.students;
begin
  d := public.astro_dev(p_device_code, p_device_secret);
  uid := public.astro_norm_uid(coalesce(p_rfid_uid, p_student_id));

  select st.* into stu
    from public.students st
    left join public.rfid_cards c on c.student_id = st.id and c.active
   where st.school_id = d.school_id
     and (c.card_uid = uid or st.id::text = coalesce(p_student_id, ''))
   limit 1;

  if stu.id is null then
    return jsonb_build_object('ok', true, 'code', 'STUDENT_NOT_FOUND');
  end if;

  -- Soft archive only: attendance history is never destroyed from a device.
  perform public.astro_archive_student(stu.id, false, d.school_id);
  update public.rfid_cards set active = false where student_id = stu.id;

  return jsonb_build_object('ok', true, 'code', 'STUDENT_ARCHIVED', 'student_id', stu.id);
end $$;

-- ===========================================================================
-- 11. SETTINGS WRITE  — firmware shape differs from the existing signature
-- ===========================================================================
create or replace function public.astro_update_settings(
  p_device_code    text    default null,
  p_start_time     text    default null,
  p_end_time       text    default null,
  p_late_after     text    default null,
  p_absent_after   text    default null,
  p_late_after_min bigint  default null,
  p_absent_after_min bigint default null,
  p_next_student_password bigint default null,
  p_alert_emails   boolean default null,
  p_timezone       text    default null,
  p_device_secret  text    default null
)
returns jsonb
language plpgsql
security definer
set search_path to 'public'
as $$
declare
  d public.devices;
  s public.schools;
begin
  d := public.astro_dev(p_device_code, p_device_secret);
  select * into s from public.schools where id = d.school_id;

  update public.schools
     set day_start    = coalesce(nullif(btrim(p_start_time), '')::time,   day_start),
         day_end      = coalesce(nullif(btrim(p_end_time), '')::time,     day_end),
         late_after   = coalesce(nullif(btrim(p_late_after), '')::time,   late_after),
         absent_after = coalesce(nullif(btrim(p_absent_after), '')::time, absent_after),
         alert_emails = coalesce(p_alert_emails, alert_emails),
         timezone     = coalesce(nullif(btrim(p_timezone), ''), timezone),
         settings_updated_at = now()
   where id = d.school_id;

  return jsonb_build_object('ok', true, 'code', 'SETTINGS_SAVED',
                            'start_time', to_char(s.day_start, 'HH24:MI'));
exception
  when invalid_datetime_format then
    return jsonb_build_object('ok', false, 'code', 'BAD_TIME_FORMAT');
end $$;

-- ===========================================================================
-- 12. OFFLINE BATCH SYNC  — the whole point of the exercise.
--     The firmware posts one rich object: students, attendance, notices,
--     leaves, messages, device_logs and deleted_* tombstones. The existing
--     3-argument astro_sync_batch only accepts a flat event array, so this
--     overload accepts the firmware's shape and processes each section with
--     per-item error isolation (one bad row can never fail the batch).
-- ===========================================================================
create or replace function public.astro_sync_batch(
  p_device_code       text,
  p_firmware_version  text    default null,
  p_students          jsonb   default '[]'::jsonb,
  p_attendance        jsonb   default '[]'::jsonb,
  p_notices           jsonb   default '[]'::jsonb,
  p_leaves            jsonb   default '[]'::jsonb,
  p_messages          jsonb   default '[]'::jsonb,
  p_device_logs       jsonb   default '[]'::jsonb,
  p_deleted_students  jsonb   default '[]'::jsonb,
  p_deleted_notices   jsonb   default '[]'::jsonb,
  p_deleted_messages  jsonb   default '[]'::jsonb,
  p_deleted_holidays  jsonb   default '[]'::jsonb,
  p_device_secret     text    default null
)
returns jsonb
language plpgsql
security definer
set search_path to 'public'
as $$
declare
  d public.devices;
  s public.schools;
  it jsonb;
  res jsonb;
  n_students int := 0;
  n_att      int := 0;
  n_notices  int := 0;
  n_leaves   int := 0;
  n_msgs     int := 0;
  n_logs     int := 0;
  n_del      int := 0;
  n_fail     int := 0;
  errs jsonb := '[]'::jsonb;
begin
  d := public.astro_dev(p_device_code, p_device_secret);
  select * into s from public.schools where id = d.school_id;

  update public.devices
     set last_seen = now(),
         firmware  = coalesce(nullif(btrim(coalesce(p_firmware_version, '')), ''), firmware)
   where id = d.id;

  -- ---- students -----------------------------------------------------------
  for it in select * from jsonb_array_elements(coalesce(p_students, '[]'::jsonb)) loop
    begin
      perform public.astro_create_student(
        d.device_code,
        it->>'student_id', it->>'display_name', it->>'name',
        it->>'class', it->>'class_name', it->>'section', it->>'roll',
        it->>'rfid_uid',
        nullif(it->>'fingerprint_id', '')::integer,
        it->>'parent_contact', it->>'guardian_email',
        it->>'password_hash', nullif(it->>'password_seq', '')::bigint,
        nullif(it->>'must_change_password', '')::boolean,
        null);
      n_students := n_students + 1;
    exception when others then
      n_fail := n_fail + 1;
      errs := errs || jsonb_build_array(jsonb_build_object(
                'section', 'students', 'rfid_uid', it->>'rfid_uid', 'error', sqlerrm));
    end;
  end loop;

  -- ---- attendance ---------------------------------------------------------
  for it in select * from jsonb_array_elements(coalesce(p_attendance, '[]'::jsonb)) loop
    begin
      res := public.astro_mark_attendance(
               d.device_code,
               it->>'student_id', it->>'rfid_uid', it->>'date',
               it->>'status', it->>'time', coalesce(it->>'method', 'rfid'), null);
      if coalesce((res->>'ok')::boolean, false) then
        n_att := n_att + 1;
      else
        n_fail := n_fail + 1;
        errs := errs || jsonb_build_array(jsonb_build_object(
                  'section', 'attendance', 'rfid_uid', it->>'rfid_uid',
                  'code', res->>'code'));
      end if;
    exception when others then
      n_fail := n_fail + 1;
      errs := errs || jsonb_build_array(jsonb_build_object(
                'section', 'attendance', 'rfid_uid', it->>'rfid_uid', 'error', sqlerrm));
    end;
  end loop;

  -- ---- notices ------------------------------------------------------------
  for it in select * from jsonb_array_elements(coalesce(p_notices, '[]'::jsonb)) loop
    begin
      perform public.astro_create_notice(
        d.device_code,
        nullif(it->>'id', '')::bigint, it->>'title', it->>'body',
        it->>'priority', coalesce(it->>'target', it->>'audience'),
        nullif(it->>'pinned', '')::boolean, it->>'created_at', null);
      n_notices := n_notices + 1;
    exception when others then
      n_fail := n_fail + 1;
      errs := errs || jsonb_build_array(jsonb_build_object(
                'section', 'notices', 'id', it->>'id', 'error', sqlerrm));
    end;
  end loop;

  -- ---- leaves -------------------------------------------------------------
  for it in select * from jsonb_array_elements(coalesce(p_leaves, '[]'::jsonb)) loop
    begin
      declare
        stu public.students;
        uid text := public.astro_norm_uid(it->>'student_id');
        v_from date := public.astro_try_ts(it->>'from_date')::date;
        v_to   date := public.astro_try_ts(it->>'to_date')::date;
      begin
        select st.* into stu
          from public.students st
          left join public.rfid_cards c on c.student_id = st.id and c.active
         where st.school_id = d.school_id
           and (c.card_uid = uid or st.id::text = coalesce(it->>'student_id', ''))
         limit 1;

        if stu.id is null or v_from is null or v_to is null then
          n_fail := n_fail + 1;
        else
          insert into public.leave_requests
            (school_id, student_id, from_date, to_date, reason, status)
          values
            (d.school_id, stu.id, v_from, v_to,
             coalesce(it->>'reason', ''),
             lower(coalesce(nullif(it->>'status', ''), 'pending')))
          on conflict do nothing;
          n_leaves := n_leaves + 1;
        end if;
      end;
    exception when others then
      n_fail := n_fail + 1;
      errs := errs || jsonb_build_array(jsonb_build_object(
                'section', 'leaves', 'student', it->>'student_id', 'error', sqlerrm));
    end;
  end loop;

  -- ---- messages -----------------------------------------------------------
  for it in select * from jsonb_array_elements(coalesce(p_messages, '[]'::jsonb)) loop
    begin
      perform public.astro_send_message(
        d.device_code, nullif(it->>'id', '')::bigint, it->>'from',
        it->>'to', coalesce(it->>'text', it->>'body'),
        it->>'subject', it->>'created_at', null);
      n_msgs := n_msgs + 1;
    exception when others then
      n_fail := n_fail + 1;
      errs := errs || jsonb_build_array(jsonb_build_object(
                'section', 'messages', 'id', it->>'id', 'error', sqlerrm));
    end;
  end loop;

  -- ---- device logs --------------------------------------------------------
  for it in select * from jsonb_array_elements(coalesce(p_device_logs, '[]'::jsonb)) loop
    begin
      insert into public.device_events
        (event_uid, school_id, device_id, method, event_ts, status, payload, processed)
      values
        (gen_random_uuid(), d.school_id, d.id, 'log',
         coalesce(public.astro_try_ts(it->>'created_at'), now()),
         left(coalesce(it->>'event', 'log'), 120),
         jsonb_build_object('event', it->>'event', 'payload', it->>'payload'),
         true);
      n_logs := n_logs + 1;
    exception when others then
      n_fail := n_fail + 1;
    end;
  end loop;

  -- ---- tombstones ---------------------------------------------------------
  for it in select * from jsonb_array_elements(coalesce(p_deleted_students, '[]'::jsonb)) loop
    begin
      perform public.astro_delete_student(d.device_code, it #>> '{}', it #>> '{}', null);
      n_del := n_del + 1;
    exception when others then
      n_fail := n_fail + 1;
    end;
  end loop;

  for it in select * from jsonb_array_elements(coalesce(p_deleted_notices, '[]'::jsonb)) loop
    begin
      perform public.astro_delete_notice(d.device_code, (it #>> '{}')::bigint, null, null);
      n_del := n_del + 1;
    exception when others then
      n_fail := n_fail + 1;
    end;
  end loop;

  for it in select * from jsonb_array_elements(coalesce(p_deleted_messages, '[]'::jsonb)) loop
    begin
      perform public.astro_delete_message(d.device_code, (it #>> '{}')::bigint, null, null);
      n_del := n_del + 1;
    exception when others then
      n_fail := n_fail + 1;
    end;
  end loop;

  for it in select * from jsonb_array_elements(coalesce(p_deleted_holidays, '[]'::jsonb)) loop
    begin
      perform public.astro_delete_holiday(d.device_code, it #>> '{}', null);
      n_del := n_del + 1;
    exception when others then
      n_fail := n_fail + 1;
    end;
  end loop;

  return jsonb_build_object(
    'ok',        true,
    'code',      'BATCH_DONE',
    'accepted',  n_students + n_att + n_notices + n_leaves + n_msgs + n_logs + n_del,
    'students',  n_students,
    'attendance', n_att,
    'notices',   n_notices,
    'leaves',    n_leaves,
    'messages',  n_msgs,
    'logs',      n_logs,
    'deleted',   n_del,
    'failed',    n_fail,
    'results',   errs,
    'server_time', now()
  );
end $$;

-- ===========================================================================
-- 13. FACTORY WIPE — deliberately non-destructive.
--     A device must never be able to erase a school's attendance history.
--     It only clears the device's own row (last_seen/firmware bookkeeping).
-- ===========================================================================
create or replace function public.astro_factory_wipe(
  p_device_code   text default null,
  p_confirm       boolean default null,
  p_device_secret text default null
)
returns jsonb
language plpgsql
security definer
set search_path to 'public'
as $$
declare
  d public.devices;
begin
  d := public.astro_dev(p_device_code, p_device_secret);

  insert into public.device_events
    (event_uid, school_id, device_id, method, status, payload, processed)
  values (gen_random_uuid(), d.school_id, d.id, 'factory_wipe', 'refused',
          jsonb_build_object('device_code', d.device_code), true);

  return jsonb_build_object(
    'ok', false,
    'code', 'WIPE_REFUSED',
    'message', 'Cloud data is never erased by a device. Reset the terminal locally; school records stay intact.');
end $$;

-- ===========================================================================
-- 14. HEARTBEAT (used by the dashboard to show ONLINE/OFFLINE)
-- ===========================================================================
create or replace function public.astro_device_ping(
  p_device_code   text    default null,
  p_rssi          integer default null,
  p_ip            text    default null,
  p_firmware      text    default null,
  p_device_secret text    default null
)
returns jsonb
language plpgsql
security definer
set search_path to 'public'
as $$
declare
  d public.devices;
begin
  d := public.astro_dev(p_device_code, p_device_secret);

  update public.devices
     set last_seen  = now(),
         wifi_rssi  = coalesce(p_rssi, wifi_rssi),
         ip         = coalesce(nullif(btrim(p_ip), ''), ip),
         firmware   = coalesce(nullif(btrim(p_firmware), ''), firmware)
   where id = d.id;

  return jsonb_build_object('ok', true, 'device_code', d.device_code,
                            'server_time', now());
end $$;

-- ===========================================================================
-- 15. GRANTS
--     The firmware authenticates with the publishable/anon key, so anon must be
--     able to execute the wrappers. Each wrapper re-verifies the device secret
--     internally, so this does not open the tables themselves.
-- ===========================================================================
do $$
declare
  f text;
begin
  foreach f in array array[
    'astro_int_id(text)',
    'astro_dev(text,text)',
    'astro_request_bearer()',
    'astro_device_handshake(text,text,text)',
    'astro_get_settings(text,text)',
    'astro_list_holidays(text,text)',
    'astro_create_holiday(text,text,text,text)',
    'astro_delete_holiday(text,text,text)',
    'astro_list_students(text,text)',
    'astro_lookup_by_rfid(text,text,text,text)',
    'astro_lookup_by_fingerprint(text,integer,integer,text)',
    'astro_list_attendance(text,text,text)',
    'astro_list_notices(text,text)',
    'astro_create_notice(text,bigint,text,text,text,text,boolean,text,text)',
    'astro_delete_notice(text,bigint,uuid,text)',
    'astro_list_leaves(text,text)',
    'astro_approve_leave(text,bigint,uuid,text,text,text,text,text)',
    'astro_list_messages(text,text)',
    'astro_send_message(text,bigint,text,text,text,text,text,boolean,text)',
    'astro_delete_message(text,bigint,uuid,text)',
    'astro_create_student(text,text,text,text,text,text,text,text,text,integer,text,text,text,bigint,boolean,text)',
    'astro_delete_student(text,text,text,text)',
    'astro_update_settings(text,text,text,text,text,bigint,bigint,bigint,boolean,text,text)',
    'astro_sync_batch(text,text,jsonb,jsonb,jsonb,jsonb,jsonb,jsonb,jsonb,jsonb,jsonb,jsonb,text)',
    'astro_mark_attendance(text,text,text,text,text,text,text,text)',
    'astro_factory_wipe(text,boolean,text)',
    'astro_device_ping(text,integer,text,text,text)'
  ]
  loop
    begin
      execute format('grant execute on function public.%s to anon, authenticated, service_role;', f);
    exception when others then
      raise notice 'grant skipped for %: %', f, sqlerrm;
    end;
  end loop;
end $$;

-- PostgREST: reload the schema cache so the new functions are callable at once.
notify pgrst, 'reload schema';
