-- 0018 holidays, leave requests, student calendar, admin day overview, manual corrections

create extension if not exists btree_gist with schema extensions;

alter table public.attendance drop constraint if exists attendance_status_check;
alter table public.attendance add constraint attendance_status_check
  check (status in ('present','late','absent','excused','left','half_day','leave'));
alter table public.alerts drop constraint if exists alerts_kind_check;
alter table public.alerts add constraint alerts_kind_check
  check (kind in ('absent','late','unknown_card','low_attendance','notice','message','leave'));

create or replace view public.v_daily_attendance with (security_invoker = true) as
  select school_id, attendance_date,
         count(*) filter (where status = 'present') as present,
         count(*) filter (where status = 'late') as late,
         count(*) filter (where status = 'absent') as absent,
         count(*) as total,
         count(*) filter (where status in ('leave','excused')) as on_leave
  from public.attendance where session = 'daily' group by school_id, attendance_date;

-- shared "who is calling and for which school" check
create or replace function public.astro_ctx_school(p_school_id uuid, p_need text default 'staff') returns uuid
language plpgsql stable security definer set search_path = public as $$
declare sid uuid;
begin
  if auth.uid() is null then
    sid := p_school_id;
    if sid is null then raise exception using message = 'SCHOOL_REQUIRED', errcode = '22023'; end if;
    return sid;
  end if;
  if p_need = 'admin' and not public.is_admin() then raise exception using message = 'NOT_ADMIN', errcode = '42501'; end if;
  if p_need = 'staff' and not public.is_staff() then raise exception using message = 'NOT_STAFF', errcode = '42501'; end if;
  sid := public.current_school_id();
  if sid is null then raise exception using message = 'NOT_A_MEMBER', errcode = '42501'; end if;
  return sid;
end $$;

-- ---------- holidays ----------
-- declaring a holiday after the day was closed must take the automatic absences (and their unsent emails) back
create or replace function public.astro_holiday_cleanup() returns trigger
language plpgsql security definer set search_path = public as $$
begin
  delete from public.alerts al where al.kind = 'absent' and al.status = 'queued' and al.attendance_id in (
    select a.id from public.attendance a
    where a.school_id = new.school_id and a.attendance_date = new.holiday_date and a.status = 'absent' and a.note = 'auto-closed');
  delete from public.attendance a
   where a.school_id = new.school_id and a.attendance_date = new.holiday_date and a.status = 'absent' and a.note = 'auto-closed';
  return new;
end $$;
drop trigger if exists school_holidays_cleanup on public.school_holidays;
create trigger school_holidays_cleanup after insert or update of holiday_date on public.school_holidays
  for each row execute function public.astro_holiday_cleanup();

create or replace function public.astro_set_holiday(p_date date, p_name text default null, p_school_id uuid default null)
returns jsonb language plpgsql security definer set search_path = public as $$
declare sid uuid := public.astro_ctx_school(p_school_id, 'staff'); n integer;
begin
  if p_date is null then raise exception using message = 'DATE_REQUIRED', errcode = '22023'; end if;
  select count(*) into n from public.attendance a
   where a.school_id = sid and a.attendance_date = p_date and a.status = 'absent' and a.note = 'auto-closed';
  insert into public.school_holidays (school_id, holiday_date, reason) values (sid, p_date, nullif(btrim(p_name), ''))
  on conflict (school_id, holiday_date) do update set reason = excluded.reason;
  return jsonb_build_object('ok', true, 'date', p_date, 'name', nullif(btrim(p_name), ''), 'auto_absences_removed', n);
end $$;

create or replace function public.astro_remove_holiday(p_date date, p_school_id uuid default null)
returns jsonb language plpgsql security definer set search_path = public as $$
declare sid uuid := public.astro_ctx_school(p_school_id, 'staff'); n integer;
begin
  delete from public.school_holidays where school_id = sid and holiday_date = p_date;
  get diagnostics n = row_count;
  return jsonb_build_object('ok', true, 'date', p_date, 'removed', n,
    'hint', 'If this date is already over, run astro_close_day(date) to mark who was absent');
end $$;

-- ---------- leave ----------
create table if not exists public.leave_requests (
  id uuid primary key default gen_random_uuid(),
  school_id uuid not null references public.schools(id) on delete cascade,
  student_id uuid not null references public.students(id) on delete cascade,
  from_date date not null,
  to_date date not null,
  reason text not null default '',
  status text not null default 'pending' check (status in ('pending','approved','rejected','cancelled')),
  requested_by uuid references auth.users(id) on delete set null,
  decided_by uuid references auth.users(id) on delete set null,
  decided_at timestamptz,
  decision_note text,
  created_at timestamptz not null default now(),
  constraint leave_requests_dates check (to_date >= from_date and to_date - from_date <= 60),
  -- two live requests of one student can never cover the same day, even under a race
  constraint leave_requests_no_overlap exclude using gist
    (student_id with =, daterange(from_date, to_date, '[]') with &&) where (status in ('pending','approved'))
);
create index if not exists leave_requests_school_idx on public.leave_requests (school_id, status, created_at desc);
create index if not exists leave_requests_student_idx on public.leave_requests (student_id, from_date desc);
alter table public.leave_requests enable row level security;
revoke all on public.leave_requests from anon, authenticated;
grant select on public.leave_requests to authenticated;
drop policy if exists leave_requests_read on public.leave_requests;
create policy leave_requests_read on public.leave_requests for select to authenticated
  using ((public.is_staff() and school_id = public.current_school_id()) or public.linked_student(student_id));

create or replace function public.astro_request_leave(p_student_id uuid, p_from date, p_to date default null, p_reason text default null)
returns jsonb language plpgsql security definer set search_path = public as $$
declare st public.students; s public.schools; v_to date := coalesce(p_to, p_from); v_today date; lid uuid;
  v_staff boolean; v_reason text := left(btrim(coalesce(p_reason, '')), 500);
begin
  select * into st from public.students where id = p_student_id and active;
  if st.id is null then raise exception using message = 'STUDENT_NOT_FOUND', errcode = '22023'; end if;
  v_staff := auth.uid() is null or (public.is_staff() and st.school_id = public.current_school_id());
  if not v_staff and not public.linked_student(st.id) then raise exception using message = 'NOT_ALLOWED', errcode = '42501'; end if;
  select * into s from public.schools where id = st.school_id;
  v_today := (now() at time zone s.timezone)::date;
  if p_from is null or v_to < p_from then raise exception using message = 'BAD_DATES', errcode = '22023'; end if;
  if v_to - p_from > 60 then raise exception using message = 'LEAVE_TOO_LONG', errcode = '22023', hint = 'At most 61 days per request'; end if;
  if p_from < v_today - (case when v_staff then 60 else 7 end) then raise exception using message = 'TOO_FAR_BACK', errcode = '22023'; end if;
  if v_to > v_today + 365 then raise exception using message = 'TOO_FAR_AHEAD', errcode = '22023'; end if;
  if (select count(*) from public.leave_requests where student_id = st.id and status = 'pending') >= 5 then
    return jsonb_build_object('ok', false, 'reason', 'TOO_MANY_PENDING');
  end if;
  begin
    insert into public.leave_requests (school_id, student_id, from_date, to_date, reason, requested_by)
    values (st.school_id, st.id, p_from, v_to, v_reason, auth.uid()) returning id into lid;
  exception when exclusion_violation then
    return jsonb_build_object('ok', false, 'reason', 'LEAVE_OVERLAP', 'hint', 'Another pending or approved leave already covers one of these days');
  end;
  return jsonb_build_object('ok', true, 'leave_id', lid, 'status', 'pending', 'from', p_from, 'to', v_to, 'days', v_to - p_from + 1);
end $$;

-- approve: writes status 'leave' for every working day in the range (not weekly offs, not holidays),
-- replaces absences, never overwrites a day the student actually attended
create or replace function public.astro_decide_leave(p_leave_id uuid, p_approve boolean, p_note text default null)
returns jsonb language plpgsql security definer set search_path = public as $$
declare lr public.leave_requests; st public.students; s public.schools; v_tag text; n_marked integer := 0; n_kept integer := 0;
  v_subject text; v_when text;
begin
  select * into lr from public.leave_requests where id = p_leave_id for update;
  if lr.id is null then raise exception using message = 'LEAVE_NOT_FOUND', errcode = '22023'; end if;
  if auth.uid() is not null and not (public.is_staff() and lr.school_id = public.current_school_id()) then
    raise exception using message = 'NOT_STAFF', errcode = '42501';
  end if;
  if p_approve is null then raise exception using message = 'DECISION_REQUIRED', errcode = '22023'; end if;
  if lr.status <> 'pending' then return jsonb_build_object('ok', false, 'reason', 'ALREADY_DECIDED', 'status', lr.status); end if;
  select * into st from public.students where id = lr.student_id;
  select * into s from public.schools where id = lr.school_id;
  update public.leave_requests set status = case when p_approve then 'approved' else 'rejected' end,
         decided_by = auth.uid(), decided_at = now(), decision_note = nullif(left(btrim(coalesce(p_note, '')), 500), '')
   where id = lr.id;
  if p_approve then
    v_tag := 'leave:' || lr.id;
    with up as (
      insert into public.attendance (school_id, student_id, class_id, attendance_date, session, status, method, note)
      select lr.school_id, st.id, st.class_id, g::date, 'daily', 'leave', 'manual', v_tag
      from generate_series(lr.from_date::timestamp, lr.to_date::timestamp, interval '1 day') g
      where not (extract(dow from g)::int = any (s.weekly_off))
        and not exists (select 1 from public.school_holidays h where h.school_id = lr.school_id and h.holiday_date = g::date)
      on conflict (student_id, attendance_date, session, (coalesce(period_no, 0))) do update
         set status = 'leave', method = 'manual', note = excluded.note, marked_at = now()
       where public.attendance.status = 'absent'
      returning id)
    select count(*) into n_marked from up;
    delete from public.alerts al where al.kind = 'absent' and al.status = 'queued' and al.attendance_id in (
      select a.id from public.attendance a where a.student_id = st.id and a.note = v_tag);
    select count(*) into n_kept from public.attendance a
     where a.student_id = st.id and a.session = 'daily' and a.attendance_date between lr.from_date and lr.to_date
       and coalesce(a.note, '') <> v_tag;
  end if;
  if s.alert_emails and st.guardian_email is not null then
    v_when := to_char(lr.from_date, 'DD Mon YYYY') || case when lr.to_date > lr.from_date then ' to ' || to_char(lr.to_date, 'DD Mon YYYY') else '' end;
    v_subject := 'Leave ' || case when p_approve then 'approved' else 'not approved' end || ': ' || st.full_name || ' (' || v_when || ')';
    insert into public.alerts (school_id, student_id, kind, to_email, title, subject, body, ref_kind, ref_id)
    values (lr.school_id, st.id, 'leave', st.guardian_email, v_subject, v_subject,
      'Dear Parent,' || chr(10) || chr(10) || 'The leave request for ' || st.full_name || ' (Roll ' || st.roll_no || ') for ' || v_when || ' has been '
      || case when p_approve then 'APPROVED.' else 'DECLINED.' end
      || case when nullif(btrim(coalesce(p_note, '')), '') is not null then chr(10) || 'Note from school: ' || left(btrim(p_note), 500) else '' end
      || chr(10) || chr(10) || '- ' || s.name || ' / Astro Smart Attendance', 'leave', lr.id);
  end if;
  return jsonb_build_object('ok', true, 'leave_id', lr.id, 'status', case when p_approve then 'approved' else 'rejected' end,
    'days_marked_leave', n_marked, 'days_kept_as_attended', n_kept);
end $$;

-- requester may withdraw a pending request; staff may also revoke an approved one
create or replace function public.astro_cancel_leave(p_leave_id uuid)
returns jsonb language plpgsql security definer set search_path = public as $$
declare lr public.leave_requests; s public.schools; v_staff boolean; v_today date; v_tag text; n_abs integer := 0; n_del integer := 0;
begin
  select * into lr from public.leave_requests where id = p_leave_id for update;
  if lr.id is null then raise exception using message = 'LEAVE_NOT_FOUND', errcode = '22023'; end if;
  v_staff := auth.uid() is null or (public.is_staff() and lr.school_id = public.current_school_id());
  if not v_staff and not public.linked_student(lr.student_id) then raise exception using message = 'NOT_ALLOWED', errcode = '42501'; end if;
  if lr.status in ('cancelled','rejected') then return jsonb_build_object('ok', false, 'reason', 'ALREADY_CLOSED', 'status', lr.status); end if;
  if lr.status = 'approved' then
    if not v_staff then raise exception using message = 'ONLY_STAFF_CAN_REVOKE', errcode = '42501'; end if;
    select * into s from public.schools where id = lr.school_id;
    v_today := (now() at time zone s.timezone)::date;
    v_tag := 'leave:' || lr.id;
    update public.attendance set status = 'absent', note = 'leave-revoked', marked_at = now()
     where student_id = lr.student_id and note = v_tag and status = 'leave' and attendance_date < v_today;
    get diagnostics n_abs = row_count;
    delete from public.attendance where student_id = lr.student_id and note = v_tag and status = 'leave' and attendance_date >= v_today;
    get diagnostics n_del = row_count;
  end if;
  update public.leave_requests set status = 'cancelled', decided_at = coalesce(decided_at, now()) where id = lr.id;
  return jsonb_build_object('ok', true, 'leave_id', lr.id, 'status', 'cancelled', 'was', lr.status,
    'past_days_now_absent', n_abs, 'upcoming_days_cleared', n_del);
end $$;

-- ---------- student calendar (one call paints the month) ----------
-- status per day: present | late | half_day | left | absent | leave | excused | holiday | weekly_off | upcoming | not_enrolled | not_marked
create or replace function public.astro_student_calendar(p_student_id uuid, p_month date default null)
returns jsonb language plpgsql stable security definer set search_path = public as $$
declare st public.students; s public.schools; v_today date; m0 date; m1 date; v_days jsonb; v_sum jsonb;
begin
  select * into st from public.students where id = p_student_id;
  if st.id is null then raise exception using message = 'STUDENT_NOT_FOUND', errcode = '22023'; end if;
  if auth.uid() is not null and not (st.school_id = public.current_school_id() or public.linked_student(st.id)) then
    raise exception using message = 'NOT_ALLOWED', errcode = '42501';
  end if;
  select * into s from public.schools where id = st.school_id;
  v_today := (now() at time zone s.timezone)::date;
  m0 := date_trunc('month', coalesce(p_month, v_today))::date;
  m1 := (m0 + interval '1 month')::date - 1;
  with cal as (
    select g::date as d, a.status as a_status, a.method as a_method, a.marked_at as a_at, a.note as a_note,
           h.reason as h_reason, (h.holiday_date is not null) as is_h,
           (extract(dow from g)::int = any (s.weekly_off)) as is_off
    from generate_series(m0::timestamp, m1::timestamp, interval '1 day') g
    left join public.attendance a on a.student_id = st.id and a.attendance_date = g::date and a.session = 'daily'
    left join public.school_holidays h on h.school_id = st.school_id and h.holiday_date = g::date),
  x as (
    select cal.*, case
        when a_status in ('present','late','half_day','left') then a_status
        when is_h then 'holiday'
        when a_status is not null then a_status
        when is_off then 'weekly_off'
        when d > v_today then 'upcoming'
        when d < (st.created_at at time zone s.timezone)::date then 'not_enrolled'
        else 'not_marked' end as display
    from cal)
  select jsonb_agg(jsonb_build_object('date', d, 'status', display,
             'time', case when a_status in ('present','late','half_day','left') or a_note = 'after-cutoff' then to_char(a_at at time zone s.timezone, 'HH24:MI') end,
             'method', case when a_status in ('present','late','half_day','left') or a_note = 'after-cutoff' then a_method end,
             'holiday', case when is_h then coalesce(h_reason, 'Holiday') end) order by d),
         jsonb_build_object(
           'present', count(*) filter (where display = 'present'),
           'late', count(*) filter (where display = 'late'),
           'absent', count(*) filter (where display = 'absent'),
           'leave', count(*) filter (where display in ('leave','excused')),
           'holiday', count(*) filter (where display = 'holiday'),
           'weekly_off', count(*) filter (where display = 'weekly_off'),
           'not_marked', count(*) filter (where display = 'not_marked'),
           'attendance_percent', round(100.0 * count(*) filter (where display in ('present','late','half_day','left'))
               / nullif(count(*) filter (where display in ('present','late','half_day','left','absent')), 0), 1))
    into v_days, v_sum from x;
  return jsonb_build_object('ok', true, 'student', jsonb_build_object('id', st.id, 'roll_no', st.roll_no, 'full_name', st.full_name),
    'month', to_char(m0, 'YYYY-MM'), 'today', v_today, 'days', v_days, 'summary', v_sum);
end $$;

-- ---------- admin "Global Attendance Overview" (every active student, marked or not) ----------
create or replace function public.astro_day_overview(p_date date default null, p_class_id uuid default null, p_school_id uuid default null)
returns jsonb language plpgsql stable security definer set search_path = public as $$
declare sid uuid := public.astro_ctx_school(p_school_id, 'member'); s public.schools; v_d date; v_rows jsonb; v_counts jsonb; v_hol text; v_is_h boolean;
begin
  select * into s from public.schools where id = sid;
  v_d := coalesce(p_date, (now() at time zone s.timezone)::date);
  select h.reason into v_hol from public.school_holidays h where h.school_id = sid and h.holiday_date = v_d;
  v_is_h := found;
  select jsonb_agg(jsonb_build_object('student_id', st.id, 'roll_no', st.roll_no, 'name', st.full_name,
             'class', c.name || '-' || c.section, 'status', coalesce(a.status, 'not_marked'),
             'time', case when a.method <> 'import' and a.status <> 'leave' then to_char(a.marked_at at time zone s.timezone, 'HH24:MI') end,
             'method', a.method, 'note', a.note) order by c.name, c.section, st.roll_no),
         jsonb_build_object('total', count(*),
           'present', count(*) filter (where a.status = 'present'),
           'late', count(*) filter (where a.status = 'late'),
           'absent', count(*) filter (where a.status = 'absent'),
           'leave', count(*) filter (where a.status in ('leave','excused')),
           'other', count(*) filter (where a.status in ('half_day','left')),
           'not_marked', count(*) filter (where a.status is null))
    into v_rows, v_counts
  from public.students st
  left join public.classes c on c.id = st.class_id
  left join public.attendance a on a.student_id = st.id and a.attendance_date = v_d and a.session = 'daily'
  where st.school_id = sid and st.active and (p_class_id is null or st.class_id = p_class_id);
  return jsonb_build_object('ok', true, 'date', v_d, 'is_holiday', v_is_h, 'holiday', case when v_is_h then coalesce(v_hol, 'Holiday') end,
    'is_weekly_off', extract(dow from v_d)::int = any (s.weekly_off), 'counts', v_counts, 'students', coalesce(v_rows, '[]'::jsonb));
end $$;

-- ---------- manual correction by a teacher ("if this is a mistake, contact the class teacher") ----------
create or replace function public.astro_set_attendance(p_student_id uuid, p_date date, p_status text, p_note text default null, p_school_id uuid default null)
returns jsonb language plpgsql security definer set search_path = public as $$
declare sid uuid := public.astro_ctx_school(p_school_id, 'staff'); st public.students; s public.schools; v_today date;
  v_status text := lower(btrim(coalesce(p_status, ''))); a public.attendance; n integer;
begin
  select * into st from public.students where id = p_student_id and school_id = sid;
  if st.id is null then raise exception using message = 'STUDENT_NOT_FOUND', errcode = '22023'; end if;
  select * into s from public.schools where id = sid;
  v_today := (now() at time zone s.timezone)::date;
  if p_date is null or p_date < v_today - 366 then raise exception using message = 'BAD_DATE', errcode = '22023'; end if;
  if v_status = 'clear' then
    delete from public.alerts al where al.status = 'queued' and al.attendance_id in (
      select x.id from public.attendance x where x.student_id = st.id and x.attendance_date = p_date and x.session = 'daily');
    delete from public.attendance where student_id = st.id and attendance_date = p_date and session = 'daily';
    get diagnostics n = row_count;
    return jsonb_build_object('ok', true, 'date', p_date, 'status', 'not_marked', 'cleared', n);
  end if;
  if v_status not in ('present','late','absent','leave','excused','half_day','left') then raise exception using message = 'BAD_STATUS', errcode = '22023'; end if;
  if p_date > v_today and v_status not in ('leave','excused') then raise exception using message = 'FUTURE_DATE', errcode = '22023'; end if;
  insert into public.attendance (school_id, student_id, class_id, attendance_date, session, status, method, note)
  values (sid, st.id, st.class_id, p_date, 'daily', v_status, 'manual', coalesce(nullif(left(btrim(coalesce(p_note, '')), 200), ''), 'manual'))
  on conflict (student_id, attendance_date, session, (coalesce(period_no, 0))) do update
     set status = excluded.status, method = 'manual', note = excluded.note, marked_at = now()
  returning * into a;
  if v_status <> 'absent' then
    delete from public.alerts al where al.attendance_id = a.id and al.kind in ('absent','late') and al.status = 'queued';
  end if;
  return jsonb_build_object('ok', true, 'attendance_id', a.id, 'date', a.attendance_date, 'status', a.status, 'student', st.full_name);
end $$;

revoke all on function public.astro_ctx_school(uuid, text), public.astro_holiday_cleanup() from public, anon, authenticated;
revoke all on function public.astro_set_holiday(date, text, uuid), public.astro_remove_holiday(date, uuid),
  public.astro_request_leave(uuid, date, date, text), public.astro_decide_leave(uuid, boolean, text), public.astro_cancel_leave(uuid),
  public.astro_student_calendar(uuid, date), public.astro_day_overview(date, uuid, uuid),
  public.astro_set_attendance(uuid, date, text, text, uuid) from public, anon;
grant execute on function public.astro_set_holiday(date, text, uuid), public.astro_remove_holiday(date, uuid),
  public.astro_request_leave(uuid, date, date, text), public.astro_decide_leave(uuid, boolean, text), public.astro_cancel_leave(uuid),
  public.astro_student_calendar(uuid, date), public.astro_day_overview(date, uuid, uuid),
  public.astro_set_attendance(uuid, date, text, text, uuid) to authenticated;
