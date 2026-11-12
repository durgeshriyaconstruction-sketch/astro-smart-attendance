-- 0020 device command queue (Device Check: LCD / RFID / fingerprint, enrolment), Add-Student save, richer heartbeat
--
-- The web app is served over HTTPS and cannot call an ESP32 on the school LAN.
-- So the admin queues a command here, the terminal polls for it, runs it, and reports back.
-- The command row doubles as the device log.

create table if not exists public.device_commands (
  id uuid primary key default gen_random_uuid(),
  school_id uuid not null references public.schools(id) on delete cascade,
  device_id uuid not null references public.devices(id) on delete cascade,
  kind text not null check (kind in ('lcd_text','rfid_capture','fp_check','fp_enroll','fp_delete','reboot','refresh')),
  payload jsonb not null default '{}'::jsonb,
  status text not null default 'queued' check (status in ('queued','sent','done','failed','expired','cancelled')),
  result jsonb,
  created_by uuid references auth.users(id) on delete set null,
  created_at timestamptz not null default now(),
  sent_at timestamptz,
  done_at timestamptz,
  expires_at timestamptz not null
);
create index if not exists device_commands_device_idx on public.device_commands (device_id, status, created_at);
create index if not exists device_commands_school_idx on public.device_commands (school_id, created_at desc);
alter table public.device_commands enable row level security;
revoke all on public.device_commands from anon, authenticated;
grant select on public.device_commands to authenticated;
drop policy if exists device_commands_read on public.device_commands;
create policy device_commands_read on public.device_commands for select to authenticated
  using (public.is_staff() and school_id = public.current_school_id());

create or replace function public.astro_queue_command(p_device_code text, p_kind text, p_payload jsonb default '{}'::jsonb,
  p_ttl_seconds integer default 120, p_school_id uuid default null)
returns jsonb language plpgsql security definer set search_path = public as $$
declare sid uuid := public.astro_ctx_school(p_school_id, 'staff'); d public.devices; st public.students;
  v_kind text := lower(btrim(coalesce(p_kind, ''))); v_pl jsonb := coalesce(p_payload, '{}'::jsonb);
  v_ttl integer := least(greatest(coalesce(p_ttl_seconds, 120), 15), 600);
  v_text text; l1 text; l2 text; p integer; v_slot integer; v_sid uuid; cid uuid; v_online boolean;
begin
  select * into d from public.devices where device_code = upper(btrim(coalesce(p_device_code, ''))) and school_id = sid;
  if d.id is null then raise exception using message = 'DEVICE_NOT_FOUND', errcode = '22023'; end if;
  if not d.active then raise exception using message = 'DEVICE_DISABLED', errcode = '22023'; end if;
  if v_kind not in ('lcd_text','rfid_capture','fp_check','fp_enroll','fp_delete','reboot','refresh') then
    raise exception using message = 'BAD_COMMAND', errcode = '22023';
  end if;
  if jsonb_typeof(v_pl) <> 'object' then raise exception using message = 'BAD_PAYLOAD', errcode = '22023'; end if;
  if v_kind = 'reboot' and auth.uid() is not null and not public.is_admin() then raise exception using message = 'NOT_ADMIN', errcode = '42501'; end if;

  v_sid := public.astro_try_uuid(v_pl->>'student_id');
  if v_pl ? 'student_id' then
    select * into st from public.students where id = v_sid and school_id = sid and active;
    if st.id is null then raise exception using message = 'STUDENT_NOT_FOUND', errcode = '22023'; end if;
  end if;

  if v_kind = 'lcd_text' then
    if v_pl ? 'line1' or v_pl ? 'line2' then
      l1 := coalesce(v_pl->>'line1', ''); l2 := coalesce(v_pl->>'line2', '');
    else
      -- "2-3 words" -> wrapped at a word boundary onto the two 16-character rows
      v_text := btrim(regexp_replace(coalesce(v_pl->>'text', ''), '\s+', ' ', 'g'));
      p := position(' ' in reverse(left(v_text, 17)));
      if length(v_text) <= 16 then l1 := v_text; l2 := '';
      elsif p > 0 and p < 17 then l1 := left(v_text, 17 - p); l2 := substr(v_text, 19 - p);
      else l1 := left(v_text, 16); l2 := substr(v_text, 17);
      end if;
    end if;
    l1 := left(regexp_replace(l1, '[^\x20-\x7E]', '?', 'g'), 16);   -- HD44780 shows ASCII only
    l2 := left(regexp_replace(l2, '[^\x20-\x7E]', '?', 'g'), 16);
    if btrim(l1 || l2) = '' then raise exception using message = 'EMPTY_TEXT', errcode = '22023'; end if;
    v_pl := jsonb_build_object('line1', l1, 'line2', l2,
      'hold_seconds', case when v_pl->>'hold_seconds' ~ '^\d{1,2}$' then least(greatest((v_pl->>'hold_seconds')::int, 1), 30) else 5 end);
  elsif v_kind = 'fp_enroll' then
    if v_pl->>'slot' ~ '^\d{1,3}$' then
      v_slot := (v_pl->>'slot')::int;
      if v_slot < 1 or exists (select 1 from public.fingerprints f where f.device_id = d.id and f.slot = v_slot and f.student_id is distinct from st.id) then
        raise exception using message = 'FINGERPRINT_SLOT_IN_USE', errcode = '22023';
      end if;
    else
      if st.id is not null then
        select f.slot into v_slot from public.fingerprints f where f.device_id = d.id and f.student_id = st.id order by f.enrolled_at desc limit 1;
      end if;
      if v_slot is null then
        select min(g) into v_slot from generate_series(1, 999) g
         where not exists (select 1 from public.fingerprints f where f.device_id = d.id and f.slot = g)
           and not exists (select 1 from public.students s2 where s2.school_id = sid and s2.fingerprint_id = g)
           and not exists (select 1 from public.device_commands c where c.device_id = d.id and c.kind = 'fp_enroll'
                             and c.status in ('queued','sent') and c.expires_at > now() and c.payload->>'slot' = g::text);
      end if;
      if v_slot is null then raise exception using message = 'NO_FREE_SLOT', errcode = '22023'; end if;
    end if;
    v_pl := jsonb_build_object('slot', v_slot) || case when st.id is not null
              then jsonb_build_object('student_id', st.id, 'name', left(regexp_replace(st.full_name, '[^\x20-\x7E]', '?', 'g'), 16)) else '{}'::jsonb end;
  elsif v_kind = 'fp_delete' then
    if coalesce(v_pl->>'slot', '') !~ '^\d{1,3}$' then raise exception using message = 'SLOT_REQUIRED', errcode = '22023'; end if;
    v_pl := jsonb_build_object('slot', (v_pl->>'slot')::int);
  elsif v_kind = 'rfid_capture' then
    v_pl := case when st.id is not null
              then jsonb_build_object('student_id', st.id, 'name', left(regexp_replace(st.full_name, '[^\x20-\x7E]', '?', 'g'), 16)) else '{}'::jsonb end;
  else
    v_pl := '{}'::jsonb;
  end if;

  update public.device_commands set status = 'expired', done_at = now()
   where device_id = d.id and status in ('queued','sent') and expires_at < now();
  -- pressing "Arm" twice must not leave two captures waiting
  update public.device_commands set status = 'cancelled', done_at = now(), result = jsonb_build_object('reason', 'superseded')
   where device_id = d.id and kind = v_kind and status in ('queued','sent');
  if (select count(*) from public.device_commands where device_id = d.id and status = 'queued') >= 10 then
    return jsonb_build_object('ok', false, 'reason', 'TOO_MANY_QUEUED');
  end if;
  insert into public.device_commands (school_id, device_id, kind, payload, created_by, expires_at)
  values (sid, d.id, v_kind, v_pl, auth.uid(), now() + make_interval(secs => v_ttl)) returning id into cid;
  v_online := d.last_seen is not null and d.last_seen > now() - interval '90 seconds';
  return jsonb_build_object('ok', true, 'command_id', cid, 'kind', v_kind, 'payload', v_pl, 'device_online', v_online,
    'last_seen', d.last_seen, 'expires_in', v_ttl,
    'hint', case when not v_online then 'Terminal has not been heard from in the last 90 seconds; the command expires if it stays offline' end);
end $$;

create or replace function public.astro_cancel_command(p_command_id uuid)
returns jsonb language plpgsql security definer set search_path = public as $$
declare n integer;
begin
  if auth.uid() is not null and not public.is_staff() then raise exception using message = 'NOT_STAFF', errcode = '42501'; end if;
  update public.device_commands set status = 'cancelled', done_at = now(), result = jsonb_build_object('reason', 'cancelled')
   where id = p_command_id and status in ('queued','sent') and (auth.uid() is null or school_id = public.current_school_id());
  get diagnostics n = row_count;
  return jsonb_build_object('ok', true, 'cancelled', n);
end $$;

-- terminal: fetch work (each command is handed out exactly once)
create or replace function public.astro_poll_commands(p_device_code text, p_device_secret text, p_max integer default 3)
returns jsonb language plpgsql security definer set search_path = public as $$
declare d public.devices; v jsonb;
begin
  d := public.astro_verify_device(p_device_code, p_device_secret);
  update public.devices set last_seen = now() where id = d.id;
  update public.device_commands set status = 'expired', done_at = now()
   where device_id = d.id and status in ('queued','sent') and expires_at < now();
  with c as (
    update public.device_commands x set status = 'sent', sent_at = now()
     where x.id in (select y.id from public.device_commands y where y.device_id = d.id and y.status = 'queued'
                    order by y.created_at limit least(greatest(coalesce(p_max, 3), 1), 5) for update skip locked)
    returning x.id, x.kind, x.payload, x.created_at, x.expires_at)
  select coalesce(jsonb_agg(jsonb_build_object('id', c.id, 'kind', c.kind, 'payload', c.payload,
           'expires_in', greatest(extract(epoch from c.expires_at - now())::int, 0)) order by c.created_at), '[]'::jsonb)
    into v from c;
  return jsonb_build_object('ok', true, 'code', 'COMMANDS', 'count', jsonb_array_length(v), 'commands', v);
end $$;

-- terminal: report the outcome. Server links cards / fingerprints so the admin page only has to watch the row.
create or replace function public.astro_command_result(p_device_code text, p_device_secret text, p_command_id uuid,
  p_ok boolean, p_result jsonb default '{}'::jsonb)
returns jsonb language plpgsql security definer set search_path = public as $$
declare d public.devices; c public.device_commands; st public.students; card public.rfid_cards;
  v_res jsonb := coalesce(p_result, '{}'::jsonb); v_ok boolean := coalesce(p_ok, false); uid text; v_slot integer; v_sid uuid;
begin
  d := public.astro_verify_device(p_device_code, p_device_secret);
  select * into c from public.device_commands where id = p_command_id and device_id = d.id for update;
  if c.id is null then return jsonb_build_object('ok', false, 'code', 'COMMAND_NOT_FOUND'); end if;
  if c.status in ('done','failed') then return jsonb_build_object('ok', true, 'code', 'ALREADY_RECORDED', 'status', c.status); end if;
  if c.status = 'cancelled' then
    return jsonb_build_object('ok', false, 'code', 'CANCELLED', 'hint', 'Discard the result; after fp_enroll delete the stored template');
  end if;
  if jsonb_typeof(v_res) <> 'object' or length(v_res::text) > 4000 then v_res := jsonb_build_object('truncated', true); end if;
  v_sid := public.astro_try_uuid(c.payload->>'student_id');
  if v_sid is not null and not exists (select 1 from public.students s2 where s2.id = v_sid and s2.school_id = d.school_id) then v_sid := null; end if;

  if v_ok and c.kind = 'rfid_capture' then
    uid := public.astro_norm_uid(v_res->>'uid');
    if uid is null or uid !~ '^[0-9A-F]{8,20}$' then
      v_ok := false; v_res := v_res || jsonb_build_object('error', 'BAD_UID');
    else
      select * into card from public.rfid_cards where card_uid = uid;
      if card.student_id is not null and card.school_id = d.school_id then
        select * into st from public.students where id = card.student_id;
      end if;
      v_res := v_res || jsonb_build_object('uid', uid,
        'known', st.id is not null,
        'in_other_school', card.id is not null and card.school_id <> d.school_id,
        'owner', case when st.id is not null then jsonb_build_object('id', st.id, 'name', st.full_name, 'roll_no', st.roll_no, 'active', st.active) end);
      if v_sid is not null then
        if card.id is null then
          insert into public.rfid_cards (school_id, student_id, card_uid, label) values (d.school_id, v_sid, uid, 'Enrolled at ' || d.device_code);
          v_res := v_res || jsonb_build_object('assigned', true);
        elsif card.school_id = d.school_id and (card.student_id is null or card.student_id = v_sid) then
          update public.rfid_cards set student_id = v_sid, active = true, assigned_at = now() where id = card.id;
          v_res := v_res || jsonb_build_object('assigned', true);
        else
          v_res := v_res || jsonb_build_object('assigned', false, 'reason', 'CARD_IN_USE');
        end if;
      end if;
    end if;
  elsif v_ok and c.kind = 'fp_enroll' then
    v_slot := case when v_res->>'slot' ~ '^\d{1,3}$' then (v_res->>'slot')::int else (c.payload->>'slot')::int end;
    v_res := v_res || jsonb_build_object('slot', v_slot, 'linked', v_sid is not null);
    if v_sid is not null then
      delete from public.fingerprints where device_id = d.id and student_id = v_sid and slot <> v_slot;
      insert into public.fingerprints (device_id, school_id, slot, student_id) values (d.id, d.school_id, v_slot, v_sid)
      on conflict (device_id, slot) do update set student_id = excluded.student_id, enrolled_at = now();
      begin
        update public.students set fingerprint_id = v_slot where id = v_sid;
      exception when unique_violation then null;   -- number already used on another terminal; fingerprints row is authoritative
      end;
    end if;
  elsif v_ok and c.kind = 'fp_check' then
    if v_res->>'slot' ~ '^\d{1,3}$' then
      select s2.* into st from public.fingerprints f join public.students s2 on s2.id = f.student_id
       where f.device_id = d.id and f.slot = (v_res->>'slot')::int;
      if st.id is null then
        select * into st from public.students where school_id = d.school_id and fingerprint_id = (v_res->>'slot')::int limit 1;
      end if;
      v_res := v_res || jsonb_build_object('enrolled', st.id is not null,
        'student', case when st.id is not null then jsonb_build_object('id', st.id, 'name', st.full_name, 'roll_no', st.roll_no) end);
    end if;
  elsif v_ok and c.kind = 'fp_delete' then
    v_slot := (c.payload->>'slot')::int;
    update public.students set fingerprint_id = null
     where school_id = d.school_id and fingerprint_id = v_slot
       and id in (select f.student_id from public.fingerprints f where f.device_id = d.id and f.slot = v_slot);
    delete from public.fingerprints where device_id = d.id and slot = v_slot;
  end if;

  update public.device_commands set status = case when v_ok then 'done' else 'failed' end, result = v_res, done_at = now() where id = c.id;
  update public.devices set last_seen = now() where id = d.id;
  return jsonb_build_object('ok', true, 'code', 'RECORDED', 'status', case when v_ok then 'done' else 'failed' end, 'result', v_res);
end $$;

-- "Add New Student" Save button: student + card + fingerprint in one transaction, with every clash reported by name
create or replace function public.astro_save_student(
  p_roll_no text, p_full_name text, p_class_id uuid default null,
  p_guardian_name text default null, p_guardian_email text default null, p_guardian_phone text default null,
  p_card_uid text default null, p_fingerprint_slot integer default null, p_device_code text default null,
  p_student_id uuid default null, p_school_id uuid default null)
returns jsonb language plpgsql security definer set search_path = public as $$
declare sid uuid := public.astro_ctx_school(p_school_id, 'staff'); st public.students; card public.rfid_cards; d public.devices;
  uid text := public.astro_norm_uid(p_card_uid);
begin
  if p_class_id is not null and not exists (select 1 from public.classes c where c.id = p_class_id and c.school_id = sid) then
    raise exception using message = 'CLASS_NOT_FOUND', errcode = '22023';
  end if;
  if uid is not null then
    if uid !~ '^[0-9A-F]{8,20}$' then raise exception using message = 'BAD_CARD_UID', errcode = '22023'; end if;
    select * into card from public.rfid_cards where card_uid = uid;
    if card.id is not null and card.school_id <> sid then return jsonb_build_object('ok', false, 'reason', 'CARD_IN_USE'); end if;
    if card.student_id is not null and card.student_id is distinct from p_student_id then
      return jsonb_build_object('ok', false, 'reason', 'CARD_IN_USE',
        'owner', (select s2.full_name || ' (' || s2.roll_no || ')' from public.students s2 where s2.id = card.student_id));
    end if;
  end if;
  if p_fingerprint_slot is not null then
    if p_fingerprint_slot not between 1 and 999 then raise exception using message = 'BAD_SLOT', errcode = '22023'; end if;
    if nullif(btrim(coalesce(p_device_code, '')), '') is not null then
      select * into d from public.devices where device_code = upper(btrim(p_device_code)) and school_id = sid;
      if d.id is null then raise exception using message = 'DEVICE_NOT_FOUND', errcode = '22023'; end if;
    end if;
    if exists (select 1 from public.students s2 where s2.school_id = sid and s2.fingerprint_id = p_fingerprint_slot and s2.id is distinct from p_student_id)
       or (d.id is not null and exists (select 1 from public.fingerprints f where f.device_id = d.id and f.slot = p_fingerprint_slot and f.student_id is distinct from p_student_id)) then
      return jsonb_build_object('ok', false, 'reason', 'FINGERPRINT_IN_USE');
    end if;
  end if;
  begin
    if p_student_id is null then
      insert into public.students (school_id, class_id, roll_no, full_name, guardian_name, guardian_email, guardian_phone)
      values (sid, p_class_id, p_roll_no, p_full_name, p_guardian_name, p_guardian_email, p_guardian_phone) returning * into st;
    else
      update public.students set class_id = p_class_id,
             roll_no = coalesce(nullif(btrim(coalesce(p_roll_no, '')), ''), roll_no),
             full_name = coalesce(nullif(btrim(coalesce(p_full_name, '')), ''), full_name),
             guardian_name = p_guardian_name, guardian_email = p_guardian_email, guardian_phone = p_guardian_phone
       where id = p_student_id and school_id = sid returning * into st;
      if st.id is null then raise exception using message = 'STUDENT_NOT_FOUND', errcode = '22023'; end if;
    end if;
  exception when unique_violation then
    return jsonb_build_object('ok', false, 'reason', 'ROLL_EXISTS', 'roll_no', btrim(coalesce(p_roll_no, '')));
  end;
  if uid is not null then
    if card.id is null then
      insert into public.rfid_cards (school_id, student_id, card_uid) values (sid, st.id, uid);
    else
      update public.rfid_cards set student_id = st.id, active = true, assigned_at = now() where id = card.id;
    end if;
  end if;
  if p_fingerprint_slot is not null then
    update public.students set fingerprint_id = p_fingerprint_slot where id = st.id returning * into st;
    if d.id is not null then
      delete from public.fingerprints where device_id = d.id and student_id = st.id and slot <> p_fingerprint_slot;
      insert into public.fingerprints (device_id, school_id, slot, student_id) values (d.id, sid, p_fingerprint_slot, st.id)
      on conflict (device_id, slot) do update set student_id = excluded.student_id, enrolled_at = now();
    end if;
  end if;
  return jsonb_build_object('ok', true, 'created', p_student_id is null,
    'student', jsonb_build_object('id', st.id, 'roll_no', st.roll_no, 'full_name', st.full_name, 'class_id', st.class_id,
                                  'guardian_email', st.guardian_email, 'fingerprint_id', st.fingerprint_id),
    'cards', coalesce((select jsonb_agg(rc.card_uid) from public.rfid_cards rc where rc.student_id = st.id and rc.active), '[]'::jsonb));
end $$;

-- heartbeat now carries everything the terminal needs every 30 s: timings (incl. absent_after),
-- a settings version, holiday / weekly-off flags, today's counts for the LCD, and whether commands are waiting
create or replace function public.astro_heartbeat(p_device_code text, p_device_secret text, p_firmware text DEFAULT NULL::text, p_rssi integer DEFAULT NULL::integer, p_ip text DEFAULT NULL::text)
 RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path TO 'public'
AS $function$
declare d public.devices; s public.schools; v_now timestamptz := now(); v_d date; v_today jsonb; v_hol text; v_is_h boolean;
begin
  d := public.astro_verify_device(p_device_code, p_device_secret);
  select * into s from public.schools where id = d.school_id;
  v_d := (v_now at time zone s.timezone)::date;
  update public.devices set last_seen = v_now, last_boot = case when last_seen is null or last_seen < v_now - interval '10 minutes' then v_now else last_boot end, firmware = coalesce(left(p_firmware, 40), firmware), wifi_rssi = coalesce(p_rssi, wifi_rssi), ip = coalesce(left(p_ip, 45), ip) where id = d.id;
  select h.reason into v_hol from public.school_holidays h where h.school_id = s.id and h.holiday_date = v_d;
  v_is_h := found;
  select jsonb_build_object(
           'present', count(*) filter (where a.status = 'present'), 'late', count(*) filter (where a.status = 'late'),
           'absent', count(*) filter (where a.status = 'absent'), 'leave', count(*) filter (where a.status in ('leave','excused')),
           'students', (select count(*) from public.students st where st.school_id = s.id and st.active))
    into v_today from public.attendance a where a.school_id = s.id and a.attendance_date = v_d and a.session = 'daily';
  return jsonb_build_object('ok', true, 'code', 'HELLO', 'device_code', d.device_code, 'school', s.name, 'school_code', s.code, 'timezone', s.timezone,
    'late_after', to_char(s.late_after::interval, 'HH24:MI'), 'absent_after', to_char(s.absent_after::interval, 'HH24:MI'),
    'day_start', to_char(s.day_start::interval, 'HH24:MI'), 'day_end', to_char(s.day_end::interval, 'HH24:MI'),
    'weekly_off', to_jsonb(s.weekly_off), 'settings_version', extract(epoch from s.settings_updated_at)::bigint,
    'is_holiday', v_is_h, 'holiday', case when v_is_h then coalesce(v_hol, 'Holiday') end,
    'is_weekly_off', extract(dow from v_d)::int = any (s.weekly_off),
    'today', v_today,
    'pending_commands', (select count(*) from public.device_commands c where c.device_id = d.id and c.status = 'queued' and c.expires_at > v_now),
    'server_time', to_char(v_now at time zone s.timezone, 'YYYY-MM-DD"T"HH24:MI:SS'), 'server_epoch', extract(epoch from v_now)::bigint,
    'local_time', to_char(v_now at time zone s.timezone, 'HH24:MI:SS'), 'local_date', to_char(v_now at time zone s.timezone, 'YYYY-MM-DD'));
end $function$;

create or replace function public.astro_prune_events(p_keep_days integer DEFAULT 90)
 RETURNS integer LANGUAGE plpgsql SECURITY DEFINER SET search_path TO 'public'
AS $function$
declare n integer;
begin
  delete from public.device_commands where created_at < now() - interval '30 days';
  delete from public.device_events where received_at < now() - make_interval(days => greatest(p_keep_days, 7));
  get diagnostics n = row_count;
  return n;
end $function$;

revoke all on function public.astro_queue_command(text, text, jsonb, integer, uuid), public.astro_cancel_command(uuid),
  public.astro_save_student(text, text, uuid, text, text, text, text, integer, text, uuid, uuid) from public, anon;
grant execute on function public.astro_queue_command(text, text, jsonb, integer, uuid), public.astro_cancel_command(uuid),
  public.astro_save_student(text, text, uuid, text, text, text, text, integer, text, uuid, uuid) to authenticated;
revoke all on function public.astro_poll_commands(text, text, integer), public.astro_command_result(text, text, uuid, boolean, jsonb) from public;
grant execute on function public.astro_poll_commands(text, text, integer), public.astro_command_result(text, text, uuid, boolean, jsonb) to anon, authenticated;
