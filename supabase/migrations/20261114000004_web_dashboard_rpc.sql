-- ============================================================================
-- 20261114000004  RPCs for the web dashboard (web/supabase-bridge.js)
-- ============================================================================
-- The dashboard in web/index.html was written for the ESP32: every screen asks
-- the device for /api/... . On the website web/supabase-bridge.js answers those
-- requests from this database instead. It needs three things the existing staff
-- RPCs did not offer:
--
--   astro_web_bundle          everything the dashboard shows, in ONE round trip,
--                             with a change token so the 8-second poll costs
--                             ~200 bytes when nothing happened
--   astro_web_remove_student  "Delete student": removes a student who never
--                             attended (frees the roll number and the card),
--                             archives one who has history
--   astro_web_update_notice   edit / pin / unpin / publish / unpublish a notice
--
-- All three are for signed-in STAFF only (admin or teacher of the school):
-- astro_ctx_school(null, 'staff') raises for anyone else, and because the
-- school id is never taken from the caller there is no "trusted, no JWT" path.
-- EXECUTE is granted to `authenticated` only - see 20261114000003 for why new
-- functions must never be left open to anon.
-- ============================================================================

-- ----------------------------------------------------------------- bundle ---
create or replace function public.astro_web_bundle(
  p_token text default null,
  p_days  integer default 100
) returns jsonb
language plpgsql
stable
security definer
set search_path = public
as $$
declare
  sid     uuid := public.astro_ctx_school(null, 'staff');
  sc      public.schools;
  v_today date;
  v_from  date;
  v_days  integer := least(greatest(coalesce(p_days, 100), 7), 400);
  v_data  jsonb;
  v_token text;
  v_dev   jsonb;
begin
  select * into sc from public.schools where id = sid;
  v_today := (now() at time zone sc.timezone)::date;
  v_from  := v_today - v_days;

  v_data := jsonb_build_object(
    'school', jsonb_build_object(
      'id', sc.id, 'name', sc.name, 'code', sc.code, 'timezone', sc.timezone,
      'day_start', to_char(sc.day_start, 'HH24:MI'),
      'late_after', to_char(sc.late_after, 'HH24:MI'),
      'absent_after', case when sc.absent_after is null then null else to_char(sc.absent_after, 'HH24:MI') end,
      'day_end', to_char(sc.day_end, 'HH24:MI'),
      'weekly_off', to_jsonb(sc.weekly_off),
      'alert_emails', sc.alert_emails),
    'role', (select m.role from public.members m where m.user_id = auth.uid() and m.school_id = sid),
    'today', v_today,
    'from', v_from,
    -- next free 4+ digit roll number, counting archived students too (the
    -- unique index on (school_id, roll_no) does)
    'next_roll', (
      select coalesce(max(st.roll_no::bigint), 1000) + 1
        from public.students st
       where st.school_id = sid and st.roll_no ~ '^[0-9]{4,9}$'),
    'classes', (
      select coalesce(jsonb_agg(jsonb_build_object(
               'id', c.id, 'name', c.name, 'section', c.section, 'teacher', c.teacher)
             order by c.name, c.section), '[]'::jsonb)
        from public.classes c
       where c.school_id = sid),
    'students', (
      select coalesce(jsonb_agg(x.j order by x.roll_no, x.full_name), '[]'::jsonb)
        from (
          select st.roll_no, st.full_name,
                 jsonb_build_object(
                   'id', st.id, 'roll', st.roll_no, 'name', st.full_name,
                   'class_id', st.class_id, 'cls', c.name, 'sec', c.section,
                   'g_name', st.guardian_name, 'g_email', st.guardian_email, 'g_phone', st.guardian_phone,
                   'fp', st.fingerprint_id,
                   'card', (select rc.card_uid
                              from public.rfid_cards rc
                             where rc.student_id = st.id and rc.active
                             order by rc.assigned_at desc, rc.id
                             limit 1),
                   -- all-time daily totals
                   'n', (select jsonb_build_object(
                                  'p',  count(*) filter (where a.status = 'present'),
                                  'l',  count(*) filter (where a.status = 'late'),
                                  'a',  count(*) filter (where a.status = 'absent'),
                                  'lv', count(*) filter (where a.status in ('leave', 'excused')),
                                  'h',  count(*) filter (where a.status in ('half_day', 'left')))
                           from public.attendance a
                          where a.student_id = st.id and a.session = 'daily')
                 ) as j
            from public.students st
            left join public.classes c on c.id = st.class_id
           where st.school_id = sid and st.active
        ) x),
    -- daily marks inside the window, oldest first:
    --   [attendance id, student id, date, status, HH:MM (school time), method]
    'attendance', (
      select coalesce(jsonb_agg(jsonb_build_array(
               a.id, a.student_id, a.attendance_date, a.status,
               to_char(a.marked_at at time zone sc.timezone, 'HH24:MI'), a.method)
             order by a.attendance_date, a.marked_at, a.id), '[]'::jsonb)
        from public.attendance a
        join public.students st on st.id = a.student_id and st.active
       where a.school_id = sid and a.session = 'daily' and a.attendance_date >= v_from),
    'holidays', (
      select coalesce(jsonb_agg(jsonb_build_object('date', h.holiday_date, 'reason', h.reason)
             order by h.holiday_date), '[]'::jsonb)
        from public.school_holidays h
       where h.school_id = sid and h.holiday_date >= v_from),
    'notices', (
      select coalesce(jsonb_agg(n.j order by n.created_at desc), '[]'::jsonb)
        from (
          select nt.created_at,
                 jsonb_build_object(
                   'id', nt.id, 'title', nt.title, 'body', nt.body, 'priority', nt.priority,
                   'audience', nt.audience, 'class_id', nt.class_id, 'student_id', nt.student_id,
                   'pinned', nt.pinned,
                   'date', (nt.created_at at time zone sc.timezone)::date,
                   'published', nt.publish_at <= now() and (nt.expires_at is null or nt.expires_at > now())
                 ) as j
            from public.notices nt
           where nt.school_id = sid
           order by nt.created_at desc
           limit 100
        ) n),
    'leaves', (
      select coalesce(jsonb_agg(l.j order by l.created_at desc), '[]'::jsonb)
        from (
          select lr.created_at,
                 jsonb_build_object(
                   'id', lr.id, 'student_id', lr.student_id, 'from', lr.from_date, 'to', lr.to_date,
                   'reason', lr.reason, 'status', lr.status,
                   'applied', (lr.created_at at time zone sc.timezone)::date,
                   'note', lr.decision_note) as j
            from public.leave_requests lr
           where lr.school_id = sid
             and (lr.status = 'pending' or lr.to_date >= v_from)
           order by lr.created_at desc
           limit 300
        ) l),
    'messages', (
      select coalesce(jsonb_agg(m.j order by m.created_at desc), '[]'::jsonb)
        from (
          select ms.created_at,
                 jsonb_build_object(
                   'id', ms.id, 'student_id', ms.student_id, 'subject', ms.subject, 'body', ms.body,
                   'direction', ms.direction, 'read', ms.read_at is not null,
                   'date', (ms.created_at at time zone sc.timezone)::date,
                   'time', to_char(ms.created_at at time zone sc.timezone, 'HH24:MI')) as j
            from public.messages ms
           where ms.school_id = sid
           order by ms.created_at desc
           limit 200
        ) m)
  );

  -- Kiosk check-ins change every few seconds, so they stay out of the token.
  select coalesce(jsonb_agg(jsonb_build_object(
           'code', d.device_code, 'name', d.name, 'location', d.location, 'firmware', d.firmware,
           'ip', d.ip, 'rssi', d.wifi_rssi, 'active', d.active,
           'last_seen', d.last_seen, 'last_boot', d.last_boot,
           'age_s', case when d.last_seen is null then null
                         else greatest(0, round(extract(epoch from now() - d.last_seen)))::int end)
         order by d.last_seen desc nulls last, d.device_code), '[]'::jsonb)
    into v_dev
    from public.devices d
   where d.school_id = sid;

  v_token := md5(v_data::text);

  if p_token is not null and p_token = v_token then
    return jsonb_build_object('ok', true, 'unchanged', true, 'token', v_token,
                              'now', now(), 'devices', v_dev);
  end if;

  return jsonb_build_object('ok', true, 'unchanged', false, 'token', v_token,
                            'now', now(), 'devices', v_dev, 'data', v_data);
end $$;

-- --------------------------------------------------------- remove student ---
create or replace function public.astro_web_remove_student(p_student_id uuid)
returns jsonb
language plpgsql
security definer
set search_path = public
as $$
declare
  sid   uuid := public.astro_ctx_school(null, 'staff');
  st    public.students;
  n_att bigint;
  r     jsonb;
begin
  select * into st from public.students where id = p_student_id and school_id = sid;
  if st.id is null then
    raise exception using message = 'STUDENT_NOT_FOUND', errcode = '22023';
  end if;

  select count(*) into n_att from public.attendance a where a.student_id = st.id;

  -- Never attended: there is no history to protect, so really delete and free
  -- the roll number and the card for the next student. Admins only, matching
  -- the students_delete row policy.
  if n_att = 0 and public.is_admin(sid) then
    begin
      delete from public.rfid_cards where student_id = st.id and school_id = sid;
      delete from public.students where id = st.id;
      return jsonb_build_object('ok', true, 'mode', 'deleted', 'student_id', st.id,
                                'name', st.full_name, 'roll_no', st.roll_no);
    exception when foreign_key_violation or raise_exception then
      null;  -- something still points at the student: fall through and archive
    end;
  end if;

  -- Has history (or the caller is a teacher): keep the records, hide the student.
  r := public.astro_archive_student(st.id, false, null);
  return r || jsonb_build_object('mode', 'archived', 'name', st.full_name,
                                 'roll_no', st.roll_no, 'attendance_rows_kept', n_att);
end $$;

-- ---------------------------------------------------------- update notice ---
create or replace function public.astro_web_update_notice(
  p_notice_id uuid,
  p_title     text    default null,
  p_body      text    default null,
  p_priority  text    default null,
  p_pinned    boolean default null,
  p_published boolean default null
) returns jsonb
language plpgsql
security definer
set search_path = public
as $$
declare
  sid   uuid := public.astro_ctx_school(null, 'staff');
  n     public.notices;
  v_pri text := nullif(lower(btrim(coalesce(p_priority, ''))), '');
begin
  if v_pri is not null and v_pri not in ('normal', 'important', 'critical') then
    raise exception using message = 'BAD_PRIORITY', errcode = '22023';
  end if;

  update public.notices set
    title      = coalesce(nullif(btrim(coalesce(p_title, '')), ''), title),
    body       = coalesce(nullif(btrim(coalesce(p_body, '')), ''), body),
    priority   = coalesce(v_pri, priority),
    pinned     = coalesce(p_pinned, pinned),
    -- "unpublish" hides the notice from students and the kiosk by expiring it;
    -- "publish" clears the expiry again
    expires_at = case when p_published is null then expires_at
                      when p_published then null
                      else now() end,
    publish_at = case when p_published is true and publish_at > now() then now() else publish_at end
  where id = p_notice_id and school_id = sid
  returning * into n;

  if n.id is null then
    raise exception using message = 'NOTICE_NOT_FOUND', errcode = '22023';
  end if;

  return jsonb_build_object('ok', true, 'notice_id', n.id, 'title', n.title,
    'priority', n.priority, 'pinned', n.pinned,
    'published', n.publish_at <= now() and (n.expires_at is null or n.expires_at > now()));
end $$;

-- ------------------------------------------------------------------ grants --
revoke all on function public.astro_web_bundle(text, integer) from public, anon;
revoke all on function public.astro_web_remove_student(uuid) from public, anon;
revoke all on function public.astro_web_update_notice(uuid, text, text, text, boolean, boolean) from public, anon;

grant execute on function public.astro_web_bundle(text, integer) to authenticated, service_role;
grant execute on function public.astro_web_remove_student(uuid) to authenticated, service_role;
grant execute on function public.astro_web_update_notice(uuid, text, text, text, boolean, boolean) to authenticated, service_role;

notify pgrst, 'reload schema';
