-- 0017 timing settings
-- "Late After" / "Absent After" that the terminal and the server both obey,
-- weekly off days, and a day-close job that follows each school's own clock.

alter table public.schools
  add column if not exists absent_after time,
  add column if not exists weekly_off smallint[] not null default '{0}',
  add column if not exists settings_updated_at timestamptz not null default now();

alter table public.schools drop constraint if exists schools_timing_order;
alter table public.schools add constraint schools_timing_order check (
  day_start < day_end and late_after >= day_start and late_after < day_end
  and (absent_after is null or (absent_after > late_after and absent_after <= day_end)));
alter table public.schools drop constraint if exists schools_weekly_off_check;
alter table public.schools add constraint schools_weekly_off_check check (weekly_off <@ '{0,1,2,3,4,5,6}'::smallint[]);

create or replace function public.astro_schools_guard() returns trigger
language plpgsql set search_path = public as $$
begin
  if not exists (select 1 from pg_timezone_names where name = new.timezone) then
    raise exception using message = 'BAD_TIMEZONE', errcode = '22023';
  end if;
  if tg_op = 'UPDATE' and (new.day_start, new.late_after, new.absent_after, new.day_end, new.timezone, new.weekly_off)
       is distinct from (old.day_start, old.late_after, old.absent_after, old.day_end, old.timezone, old.weekly_off) then
    new.settings_updated_at := now();
  end if;
  return new;
end $$;
drop trigger if exists schools_guard on public.schools;
create trigger schools_guard before insert or update on public.schools
  for each row execute function public.astro_schools_guard();

-- Admin "Timing Settings" form. Times are 'HH:MM'. Omitted values stay as they are.
create or replace function public.astro_update_settings(
  p_late_after text default null, p_absent_after text default null,
  p_day_start text default null, p_day_end text default null,
  p_alert_emails boolean default null, p_weekly_off integer[] default null,
  p_timezone text default null, p_clear_absent_after boolean default false,
  p_school_id uuid default null)
returns jsonb language plpgsql security definer set search_path = public as $$
declare sid uuid; s public.schools;
begin
  if auth.uid() is not null then
    if not public.is_admin() then raise exception using message = 'NOT_ADMIN', errcode = '42501'; end if;
    sid := public.current_school_id();
  else
    sid := p_school_id;
  end if;
  if sid is null then raise exception using message = 'SCHOOL_REQUIRED', errcode = '22023'; end if;
  begin
    update public.schools set
      day_start = coalesce(nullif(btrim(p_day_start), '')::time, day_start),
      late_after = coalesce(nullif(btrim(p_late_after), '')::time, late_after),
      absent_after = case when coalesce(p_clear_absent_after, false) then null
                          else coalesce(nullif(btrim(p_absent_after), '')::time, absent_after) end,
      day_end = coalesce(nullif(btrim(p_day_end), '')::time, day_end),
      alert_emails = coalesce(p_alert_emails, alert_emails),
      weekly_off = coalesce(p_weekly_off::smallint[], weekly_off),
      timezone = coalesce(nullif(btrim(p_timezone), ''), timezone)
    where id = sid returning * into s;
  exception
    when invalid_datetime_format or datetime_field_overflow or invalid_text_representation or numeric_value_out_of_range then
      raise exception using message = 'BAD_TIME', errcode = '22023', hint = 'Use 24-hour HH:MM, for example 08:20';
    when check_violation then
      raise exception using message = 'BAD_TIMING_ORDER', errcode = '22023',
        hint = 'Need day_start <= late_after < absent_after <= day_end, and weekly_off days between 0 (Sunday) and 6';
  end;
  if s.id is null then raise exception using message = 'SCHOOL_REQUIRED', errcode = '22023'; end if;
  return jsonb_build_object('ok', true,
    'day_start', to_char(s.day_start::interval, 'HH24:MI'), 'late_after', to_char(s.late_after::interval, 'HH24:MI'),
    'absent_after', to_char(s.absent_after::interval, 'HH24:MI'), 'day_end', to_char(s.day_end::interval, 'HH24:MI'),
    'weekly_off', to_jsonb(s.weekly_off), 'alert_emails', s.alert_emails, 'timezone', s.timezone,
    'settings_version', extract(epoch from s.settings_updated_at)::bigint);
end $$;
revoke all on function public.astro_schools_guard() from public, anon, authenticated;
revoke all on function public.astro_update_settings(text, text, text, text, boolean, integer[], text, boolean, uuid) from public, anon;
grant execute on function public.astro_update_settings(text, text, text, text, boolean, integer[], text, boolean, uuid) to authenticated;

-- Scan -> status:  <= late_after  present | <= absent_after  late | after  absent ('after-cutoff')
-- A real scan replaces an auto-closed absence, and replaces approved leave unless it is itself after the cut-off.
create or replace function public.astro_mark_attendance(p_device_code text, p_device_secret text, p_card_uid text DEFAULT NULL::text, p_fingerprint_id integer DEFAULT NULL::integer, p_method text DEFAULT NULL::text, p_session text DEFAULT 'daily'::text, p_period_no integer DEFAULT NULL::integer, p_event_uid uuid DEFAULT NULL::uuid, p_event_ts timestamp with time zone DEFAULT NULL::timestamp with time zone)
 RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path TO 'public'
AS $function$
declare
  d public.devices; s public.schools; stu public.students; cls text; uid text;
  v_method text := coalesce(nullif(lower(btrim(p_method)), ''), 'rfid');
  v_session text := coalesce(nullif(lower(btrim(p_session)), ''), 'daily');
  v_period integer;
  v_event uuid := coalesce(p_event_uid, gen_random_uuid());
  v_ts timestamptz := least(greatest(coalesce(p_event_ts, now()), now() - interval '30 days'), now() + interval '5 minutes');
  v_local timestamp; v_status text; v_note text; v_att public.attendance; v_prev jsonb; v_result jsonb;
  v_prev_status text; v_prev_note text; v_upgraded boolean := false;
begin
  d := public.astro_verify_device(p_device_code, p_device_secret);
  select * into s from public.schools where id = d.school_id;
  if v_session not in ('daily','period') then raise exception using message = 'BAD_SESSION', errcode = '22023'; end if;
  if v_method not in ('rfid','fingerprint','manual','face','keypad','import') then raise exception using message = 'BAD_METHOD', errcode = '22023'; end if;
  if v_session = 'period' and p_period_no is null then raise exception using message = 'PERIOD_NO_REQUIRED', errcode = '22023'; end if;
  v_period := case when v_session = 'period' then p_period_no else null end;
  v_local := (v_ts at time zone s.timezone);
  uid := public.astro_norm_uid(p_card_uid);
  if uid is null and p_fingerprint_id is null then raise exception using message = 'NO_CREDENTIAL', errcode = '22023'; end if;

  insert into public.device_events (event_uid, school_id, device_id, card_uid, fingerprint_id, method, event_ts, payload)
  values (v_event, d.school_id, d.id, uid, p_fingerprint_id, v_method, v_ts, jsonb_build_object('session', v_session, 'period_no', v_period))
  on conflict (event_uid) do nothing;

  if not found then
    select result into v_prev from public.device_events where event_uid = v_event;
    if v_prev is not null then return v_prev || jsonb_build_object('duplicate', true); end if;
  end if;

  if uid is not null then
    select st.* into stu from public.rfid_cards card join public.students st on st.id = card.student_id where card.card_uid = uid and card.active and st.active and st.school_id = d.school_id limit 1;
  else
    select st.* into stu from public.fingerprints f join public.students st on st.id = f.student_id where f.device_id = d.id and f.slot = p_fingerprint_id and st.active limit 1;
    if stu.id is null then
      select * into stu from public.students where school_id = d.school_id and fingerprint_id = p_fingerprint_id and active limit 1;
    end if;
  end if;

  if stu.id is null then
    v_result := jsonb_build_object('ok', false, 'code', 'UNKNOWN_CARD', 'uid', uid, 'fingerprint_id', p_fingerprint_id, 'message', 'Card not registered for this school');
    update public.device_events set status = 'unknown_card', result = v_result, processed = true where event_uid = v_event;
    return v_result;
  end if;

  select case when c.name is null then null else c.name || '-' || c.section end into cls from public.classes c where c.id = stu.class_id;
  v_status := case when v_session <> 'daily' then 'present'
                   when s.absent_after is not null and v_local::time > s.absent_after then 'absent'
                   when v_local::time > s.late_after then 'late'
                   else 'present' end;
  v_note := case when v_status = 'absent' then 'after-cutoff' end;

  select a.status, a.note into v_prev_status, v_prev_note
  from public.attendance a
  where a.student_id = stu.id and a.attendance_date = v_local::date and a.session = v_session and coalesce(a.period_no, 0) = coalesce(v_period, 0);

  insert into public.attendance (school_id, student_id, class_id, device_id, attendance_date, session, period_no, status, method, marked_at, event_uid, note)
  values (d.school_id, stu.id, stu.class_id, d.id, v_local::date, v_session, v_period, v_status, v_method, v_ts, v_event, v_note)
  on conflict (student_id, attendance_date, session, (coalesce(period_no, 0))) do update
     set status = excluded.status, method = excluded.method, marked_at = excluded.marked_at, event_uid = excluded.event_uid,
         device_id = excluded.device_id, note = excluded.note
   where (public.attendance.status = 'absent' and coalesce(public.attendance.note, '') = 'auto-closed')
      or (public.attendance.status = 'leave' and excluded.status <> 'absent')
  returning * into v_att;

  if v_att.id is null then
    select * into v_att from public.attendance where student_id = stu.id and attendance_date = v_local::date and session = v_session and coalesce(period_no, 0) = coalesce(v_period, 0);
    v_result := jsonb_build_object('ok', true, 'code', 'ALREADY_MARKED', 'action', 'already_marked', 'uid', uid, 'status', to_jsonb(v_att.status), 'date', v_att.attendance_date, 'time', to_char(v_att.marked_at at time zone s.timezone, 'HH24:MI'), 'marked_at', v_att.marked_at, 'student', jsonb_build_object('id', stu.id, 'roll_no', stu.roll_no, 'name', stu.full_name, 'class', cls));
  else
    v_upgraded := (v_prev_status = 'absent' and coalesce(v_prev_note, '') = 'auto-closed');
    v_result := jsonb_build_object('ok', true, 'code', 'MARKED', 'action', 'marked', 'uid', uid, 'status', to_jsonb(v_att.status), 'date', v_att.attendance_date, 'time', to_char(v_local, 'HH24:MI'), 'marked_at', v_att.marked_at, 'method', v_method, 'session', v_session, 'period_no', v_period, 'upgraded_from_absent', v_upgraded, 'replaced_leave', coalesce(v_prev_status = 'leave', false), 'note', v_note, 'student', jsonb_build_object('id', stu.id, 'roll_no', stu.roll_no, 'name', stu.full_name, 'class', cls));
    if v_upgraded then
      delete from public.alerts where attendance_id = v_att.id and kind = 'absent' and status = 'queued';
    end if;
    if v_status = 'late' and s.alert_emails and stu.guardian_email is not null then
      insert into public.alerts (school_id, student_id, attendance_id, kind, to_email, subject, body)
      values (d.school_id, stu.id, v_att.id, 'late', stu.guardian_email, 'Late arrival: ' || stu.full_name || ' (' || to_char(v_local, 'DD Mon') || ')', 'Dear Parent,' || chr(10) || chr(10) || stu.full_name || ' (Roll ' || stu.roll_no || ') reached school at ' || to_char(v_local, 'HH24:MI') || ' on ' || to_char(v_local, 'DD Mon YYYY') || ', after the ' || to_char(s.late_after::interval, 'HH24:MI') || ' cut-off, so the arrival is marked LATE.' || chr(10) || chr(10) || '- ' || s.name || ' / Astro Smart Attendance');
    elsif v_status = 'absent' and s.alert_emails and stu.guardian_email is not null then
      insert into public.alerts (school_id, student_id, attendance_id, kind, to_email, subject, body)
      values (d.school_id, stu.id, v_att.id, 'absent', stu.guardian_email, 'Arrived after cut-off: ' || stu.full_name || ' (' || to_char(v_local, 'DD Mon') || ')', 'Dear Parent,' || chr(10) || chr(10) || stu.full_name || ' (Roll ' || stu.roll_no || ') reached school at ' || to_char(v_local, 'HH24:MI') || ' on ' || to_char(v_local, 'DD Mon YYYY') || ', after the ' || to_char(s.absent_after::interval, 'HH24:MI') || ' attendance cut-off, so the day is recorded as ABSENT.' || chr(10) || 'If this is a mistake, please contact the class teacher.' || chr(10) || chr(10) || '- ' || s.name || ' / Astro Smart Attendance');
    end if;
  end if;

  update public.device_events set status = v_result->>'code', result = v_result, processed = true where event_uid = v_event;
  update public.devices set last_seen = now() where id = d.id;
  return v_result;
end $function$;

-- Day close: per school, only after its own day_end, never on a weekly off day or holiday,
-- never for a future date, and a staff caller only closes their own school.
create or replace function public.astro_close_day(p_date date DEFAULT NULL::date)
 RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path TO 'public'
AS $function$
declare r record; d date; v_local timestamp; n_abs integer := 0; n_alerts integer := 0; n integer; n_skip integer := 0; n_wait integer := 0;
begin
  if auth.uid() is not null and not public.is_staff() then raise exception using message = 'NOT_STAFF', errcode = '42501'; end if;
  for r in select * from public.schools sc where auth.uid() is null or sc.id = public.current_school_id() loop
    v_local := now() at time zone r.timezone;
    d := coalesce(p_date, v_local::date);
    if d > v_local::date then raise exception using message = 'FUTURE_DATE', errcode = '22023'; end if;
    if p_date is null and v_local::time < r.day_end then n_wait := n_wait + 1; continue; end if;
    if extract(dow from d)::int = any (r.weekly_off)
       or exists (select 1 from public.school_holidays h where h.school_id = r.id and h.holiday_date = d) then
      n_skip := n_skip + 1;
      continue;
    end if;
    insert into public.attendance (school_id, student_id, class_id, attendance_date, session, status, method, note)
    select r.id, st.id, st.class_id, d, 'daily', 'absent', 'import', 'auto-closed'
    from public.students st
    where st.school_id = r.id and st.active
      and st.created_at < ((d + 1)::timestamp at time zone r.timezone)
      and not exists (select 1 from public.attendance a where a.student_id = st.id and a.attendance_date = d)
    on conflict (student_id, attendance_date, session, (coalesce(period_no, 0))) do nothing;
    get diagnostics n = row_count;
    n_abs := n_abs + n;
    insert into public.alerts (school_id, student_id, attendance_id, kind, to_email, subject, body)
    select r.id, st.id, a.id, 'absent', st.guardian_email, 'Absent today: ' || st.full_name || ' (' || to_char(d, 'DD Mon') || ')', 'Dear Parent,' || chr(10) || chr(10) || 'Our records show ' || st.full_name || ' (Roll ' || st.roll_no || ') as ABSENT on ' || to_char(d, 'DD Mon YYYY') || '.' || chr(10) || 'If this is a mistake, please contact the class teacher.' || chr(10) || chr(10) || '- ' || r.name || ' / Astro Smart Attendance'
    from public.students st
    join public.attendance a on a.student_id = st.id and a.attendance_date = d and a.session = 'daily' and a.status = 'absent' and a.note = 'auto-closed'
    where st.school_id = r.id and st.active and st.guardian_email is not null and r.alert_emails
      and not exists (select 1 from public.alerts al where al.attendance_id = a.id);
    get diagnostics n = row_count;
    n_alerts := n_alerts + n;
  end loop;
  return jsonb_build_object('ok', true, 'date', coalesce(p_date, current_date), 'absent_marked', n_abs, 'alerts_queued', n_alerts, 'holidays_skipped', n_skip, 'not_due_yet', n_wait);
end $function$;

-- was 09:15 UTC Mon-Sat (fixed 14:45 IST); now follows each school's day_end and weekly_off
select cron.schedule('astro-close-day', '*/30 * * * *', 'select public.astro_close_day()');
