-- ============================================================================
-- ASTRO SMART ATTENDANCE — 0007 audit fixes (applied 2026-11-12)
--
-- Found by a systematic audit of 0001-0006. Each item is a real defect:
--
--  1. RLS RECURSION  members_write queried public.members from inside a policy
--     on public.members -> "42P17 infinite recursion detected in policy for
--     relation members". Any dashboard read/write of members failed.
--     Fixed with the SECURITY DEFINER helper public.is_admin().
--
--  2. daily rows could carry a period_no (session='daily', period_no=3) which
--     bypassed the "one row per day" unique slot. period_no is now forced NULL
--     for daily sessions and p_method is validated with a clean error code.
--
--  3. astro_provision_device() accepted any school code, so a teacher of
--     school A could create a terminal inside school B. It is now scoped to
--     current_school_id(); service-side callers (no JWT) are unaffected, which
--     also fixes the documented SQL-editor provisioning path that was failing
--     with NOT_STAFF, and the same fix is applied to rotate_device_secret().
--
--  4. devices.last_boot was only ever set once (coalesce), so it stayed at the
--     first boot forever. It now refreshes when the terminal was away >10 min.
--
--  5. astro_close_day() marked every active student absent on school holidays
--     and on Sundays, and also marked absent a student who only had period
--     rows that day. New table public.school_holidays is honoured, and a
--     student with ANY row for the day is never marked absent.
--
--  6. Fingerprint slot numbers live inside the R307 module, so they are only
--     unique per terminal. Multi-terminal schools could resolve a slot to the
--     wrong student. New table public.fingerprints(device_id, slot, student_id)
--     is now authoritative, with the old students.fingerprint_id as fallback.
--
--  7. No indexes on the school_id foreign keys that every RLS policy filters
--     on; added.
--
--  8. astro_sync_batch() only reported "accepted", which counted unknown cards
--     as successes. It now also reports marked / duplicates / unknown / failed.
-- ============================================================================

-- ---------------------------------------------------------------- 1. RLS ----
create or replace function public.is_admin()
returns boolean
language sql stable security definer set search_path = public
as $$
  select exists (
    select 1 from public.members m
    where m.user_id = auth.uid() and m.role = 'admin'
  )
$$;

drop policy if exists members_write on public.members;
create policy members_write on public.members
  for all to authenticated
  using (school_id = public.current_school_id() and public.is_admin())
  with check (school_id = public.current_school_id() and public.is_admin());

revoke all on function public.is_admin() from anon, public;
grant execute on function public.is_admin() to authenticated;

-- ------------------------------------------------------- 5. holidays table --
create table if not exists public.school_holidays (
  school_id    uuid not null references public.schools(id) on delete cascade,
  holiday_date date not null,
  reason       text,
  created_at   timestamptz not null default now(),
  primary key (school_id, holiday_date)
);

alter table public.school_holidays enable row level security;

drop policy if exists school_holidays_read on public.school_holidays;
create policy school_holidays_read on public.school_holidays
  for select to authenticated
  using (school_id = public.current_school_id());

drop policy if exists school_holidays_write on public.school_holidays;
create policy school_holidays_write on public.school_holidays
  for all to authenticated
  using (school_id = public.current_school_id() and public.is_staff())
  with check (school_id = public.current_school_id() and public.is_staff());

revoke all on table public.school_holidays from anon, public;
grant select, insert, update, delete on table public.school_holidays to authenticated;

-- --------------------------------------------------- 6. fingerprint mapping --
create table if not exists public.fingerprints (
  device_id   uuid not null references public.devices(id) on delete cascade,
  school_id   uuid not null references public.schools(id) on delete cascade,
  slot        integer not null check (slot between 0 and 999),
  student_id  uuid not null references public.students(id) on delete cascade,
  enrolled_at timestamptz not null default now(),
  primary key (device_id, slot)
);

create unique index if not exists fingerprints_one_per_student_uidx
  on public.fingerprints (device_id, student_id);

create index if not exists fingerprints_student_idx on public.fingerprints (student_id);

alter table public.fingerprints enable row level security;

drop policy if exists fingerprints_read on public.fingerprints;
create policy fingerprints_read on public.fingerprints
  for select to authenticated
  using (school_id = public.current_school_id());

drop policy if exists fingerprints_write on public.fingerprints;
create policy fingerprints_write on public.fingerprints
  for all to authenticated
  using (school_id = public.current_school_id() and public.is_staff())
  with check (school_id = public.current_school_id() and public.is_staff());

revoke all on table public.fingerprints from anon, public;
grant select, insert, update, delete on table public.fingerprints to authenticated;

-- ------------------------------------------------------------- 7. indexes ---
create index if not exists students_school_idx      on public.students (school_id);
create index if not exists classes_school_idx       on public.classes (school_id);
create index if not exists rfid_cards_school_idx    on public.rfid_cards (school_id);
create index if not exists devices_school_idx       on public.devices (school_id);
create index if not exists members_school_idx       on public.members (school_id);
create index if not exists alerts_school_idx        on public.alerts (school_id, created_at desc);
create index if not exists device_events_school_idx on public.device_events (school_id, received_at desc);

-- ============================================================================
-- 4. heartbeat
-- ============================================================================
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
  d     public.devices;
  s     public.schools;
  v_now timestamptz := now();
begin
  d := public.astro_verify_device(p_device_code, p_device_secret);
  select * into s from public.schools where id = d.school_id;

  update public.devices
     set last_seen = v_now,
         last_boot = case
                       when last_seen is null or last_seen < v_now - interval '10 minutes'
                         then v_now
                       else last_boot
                     end,
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

-- ============================================================================
-- 2 + 6. mark attendance
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
  d          public.devices;
  s          public.schools;
  stu        public.students;
  cls        text;
  uid        text;
  v_method   text := coalesce(nullif(lower(btrim(p_method)), ''), 'rfid');
  v_session  text := coalesce(nullif(lower(btrim(p_session)), ''), 'daily');
  v_period   integer;
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
  if v_method not in ('rfid', 'fingerprint', 'manual', 'face', 'keypad', 'import') then
    raise exception using message = 'BAD_METHOD', errcode = '22023';
  end if;
  if v_session = 'period' and p_period_no is null then
    raise exception using message = 'PERIOD_NO_REQUIRED', errcode = '22023';
  end if;

  -- a daily row must never carry a period number, or it would sidestep the
  -- one-row-per-day unique slot
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
    -- authoritative: the slot is only meaningful on THIS terminal
    select st.* into stu
    from public.fingerprints f
    join public.students st on st.id = f.student_id
    where f.device_id = d.id and f.slot = p_fingerprint_id and st.active
    limit 1;

    -- fallback for data created before the fingerprints table existed
    if stu.id is null then
      select * into stu
      from public.students
      where school_id = d.school_id
        and fingerprint_id = p_fingerprint_id
        and active
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

  insert into public.attendance
      (school_id, student_id, class_id, device_id, attendance_date, session,
       period_no, status, method, marked_at, event_uid)
  values
      (d.school_id, stu.id, stu.class_id, d.id, v_local::date, v_session,
       v_period, v_status, v_method, v_ts, v_event)
  on conflict (student_id, attendance_date, session, (coalesce(period_no, 0))) do nothing
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
    v_result := jsonb_build_object(
      'ok', true, 'code', 'MARKED', 'action', 'marked',
      'uid', uid, 'status', to_jsonb(v_att.status),
      'date', v_att.attendance_date, 'time', to_char(v_local, 'HH24:MI'),
      'marked_at', v_att.marked_at, 'method', v_method, 'session', v_session,
      'period_no', v_period,
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

revoke all on function public.astro_mark_attendance(text, text, text, integer, text, text, integer, uuid, timestamptz) from anon, public;
grant execute on function public.astro_mark_attendance(text, text, text, integer, text, text, integer, uuid, timestamptz) to anon, authenticated;

-- ============================================================================
-- 5. close day (holidays + period-only students)
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
  n_skip   integer := 0;
begin
  if auth.uid() is not null and not public.is_staff() then
    raise exception using message = 'NOT_STAFF', errcode = '42501';
  end if;

  for r in select * from public.schools loop
    d := coalesce(p_date, (now() at time zone r.timezone)::date);

    -- never mark a holiday absent
    if exists (select 1 from public.school_holidays h
               where h.school_id = r.id and h.holiday_date = d) then
      n_skip := n_skip + 1;
      continue;
    end if;

    -- students with ANY row for the day (daily or period) are not absent
    insert into public.attendance
        (school_id, student_id, class_id, attendance_date, session, status, method, note)
    select r.id, st.id, st.class_id, d, 'daily', 'absent', 'import', 'auto-closed'
    from public.students st
    where st.school_id = r.id and st.active
      and not exists (select 1 from public.attendance a
                      where a.student_id = st.id and a.attendance_date = d)
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
                            'absent_marked', n_abs, 'alerts_queued', n_alerts,
                            'holidays_skipped', n_skip);
end $$;

revoke all on function public.astro_close_day(date) from anon, public;
grant execute on function public.astro_close_day(date) to authenticated;

-- ============================================================================
-- 3. device provisioning scoped to the caller's school (service-side allowed)
-- ============================================================================
create or replace function public.astro_provision_device(
  p_school_code text,
  p_device_code text,
  p_name        text default null,
  p_secret      text default null
)
returns jsonb
language plpgsql security definer set search_path = public
as $$
declare
  sid uuid;
  sec text := coalesce(nullif(p_secret, ''), encode(extensions.gen_random_bytes(24), 'hex'));
  did uuid;
begin
  select id into sid from public.schools where code = p_school_code;
  if sid is null then
    raise exception using message = 'SCHOOL_NOT_FOUND', errcode = '22023';
  end if;

  -- dashboard users are limited to their own school and must be staff
  if auth.uid() is not null then
    if not public.is_staff() then
      raise exception using message = 'NOT_STAFF', errcode = '42501';
    end if;
    if sid <> public.current_school_id() then
      raise exception using message = 'SCHOOL_FORBIDDEN', errcode = '42501';
    end if;
  end if;

  insert into public.devices (school_id, device_code, name, secret_hash)
  values (sid, upper(btrim(p_device_code)), p_name, public.astro_sha256_hex(sec), 'unflashed')
  on conflict (device_code) do update
    set secret_hash = excluded.secret_hash,
        name        = coalesce(excluded.name, public.devices.name)
  returning id into did;

  return jsonb_build_object('ok', true, 'device_id', did,
                            'device_code', upper(btrim(p_device_code)),
                            'device_secret', sec,
                            'note', 'Copy this secret into the firmware now; it is not recoverable.');
end $$;

create or replace function public.astro_rotate_device_secret(p_device_code text)
returns jsonb
language plpgsql security definer set search_path = public
as $$
declare
  sec text := encode(extensions.gen_random_bytes(24), 'hex');
  d   public.devices;
begin
  if auth.uid() is not null and not public.is_staff() then
    raise exception using message = 'NOT_STAFF', errcode = '42501';
  end if;

  update public.devices
     set secret_hash = public.astro_sha256_hex(sec)
   where device_code = upper(btrim(p_device_code))
     and (auth.uid() is null or school_id = public.current_school_id())
  returning * into d;

  if d.id is null then
    raise exception using message = 'DEVICE_NOT_FOUND', errcode = '22023';
  end if;

  return jsonb_build_object('ok', true, 'device_code', d.device_code,
                            'device_secret', sec);
end $$;

revoke all on function public.astro_provision_device(text, text, text, text) from anon, public;
revoke all on function public.astro_rotate_device_secret(text) from anon, public;
grant execute on function public.astro_provision_device(text, text, text, text) to authenticated;
grant execute on function public.astro_rotate_device_secret(text) to authenticated;

-- ============================================================================
-- 8. batch with honest counters
-- ============================================================================
create or replace function public.astro_sync_batch(
  p_device_code   text,
  p_device_secret text,
  p_events        jsonb
)
returns jsonb
language plpgsql security definer set search_path = public
as $$
declare
  e         jsonb;
  one       jsonb;
  results   jsonb := '[]'::jsonb;
  n_marked  integer := 0;
  n_dup     integer := 0;
  n_unknown integer := 0;
  n_failed  integer := 0;
  v_code    text;
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
      v_code := one->>'code';
      if v_code = 'MARKED' then
        if (one->>'duplicate')::boolean is true then n_dup := n_dup + 1;
        else n_marked := n_marked + 1;
        end if;
      elsif v_code = 'ALREADY_MARKED' then
        n_dup := n_dup + 1;
      elsif v_code = 'UNKNOWN_CARD' then
        n_unknown := n_unknown + 1;
      else
        n_failed := n_failed + 1;
      end if;
    exception when others then
      one := jsonb_build_object('ok', false, 'code', 'ERROR', 'message', sqlerrm,
                                'event_uid', e->>'event_uid');
      n_failed := n_failed + 1;
    end;
    results := results || jsonb_build_array(one);
  end loop;

  return jsonb_build_object('ok', true, 'code', 'BATCH_DONE',
                            'accepted', n_marked + n_dup + n_unknown,
                            'marked', n_marked, 'duplicates', n_dup,
                            'unknown', n_unknown, 'failed', n_failed,
                            'results', results);
end $$;

revoke all on function public.astro_sync_batch(text, text, jsonb) from anon, public;
grant execute on function public.astro_sync_batch(text, text, jsonb) to anon, authenticated;
