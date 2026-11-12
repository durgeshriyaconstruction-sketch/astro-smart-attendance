-- Demo history for the sample school (ABPS-RNK / DEMO-01).
--
-- Why this exists: a student row created today makes every earlier day of the
-- month read "before joining", so the parent dashboard showed an empty calendar
-- with 0% attendance and the admin reports had nothing to add up. This script
-- backdates the join date and writes a fortnight of attendance, one approved
-- leave and one holiday, so every colour in the legend has something to show.
--
-- Safe to re-run: it deletes exactly the rows it creates before inserting them.
-- Run it once against the demo project; do NOT run it on a real school.
--
--   psql "<connection string>" -f tools/demo_seed.sql
--   or paste into the Supabase SQL editor.

begin;

-- 1. The demo child joined in April, so the calendar has a term behind it.
update public.students s
   set created_at    = timestamptz '2026-04-01 09:00:00+05:30',
       guardian_name = coalesce(s.guardian_name, 'Demo Parent'),
       guardian_phone = coalesce(s.guardian_phone, '9876500000')
 where s.roll_no = 'DEMO-01'
   and s.school_id = (select id from public.schools where code = 'ABPS-RNK');

-- 2. A fortnight of attendance: mostly present, one late, one absent,
--    and two days covered by the approved leave below.
delete from public.attendance a
 using public.students s
 where a.student_id = s.id
   and s.roll_no = 'DEMO-01'
   and a.attendance_date between date '2026-11-02' and date '2026-11-11';

insert into public.attendance (school_id, student_id, class_id, attendance_date, session, status, method, marked_at)
select s.school_id, s.id, s.class_id, d::date, 'daily',
       case d::date
         when date '2026-11-02' then 'late'
         when date '2026-11-05' then 'leave'
         when date '2026-11-06' then 'leave'
         when date '2026-11-09' then 'absent'
         else 'present'
       end,
       case when d::date in (date '2026-11-05', date '2026-11-06', date '2026-11-09')
            then 'manual' else 'fingerprint' end,
       case
         when d::date = date '2026-11-02' then timestamptz '2026-11-02 08:37:00+05:30'
         when d::date in (date '2026-11-05', date '2026-11-06', date '2026-11-09')
              then timestamptz '2026-11-09 09:00:00+05:30'
         else (d::date + time '08:04') at time zone 'Asia/Kolkata'
       end
  from generate_series(date '2026-11-02', date '2026-11-11', interval '1 day') d
  join public.students s on s.roll_no = 'DEMO-01'
 where extract(dow from d) <> 0;          -- Sundays are the weekly off

-- 3. One approved leave, so the Leave colour and the leave list have a row.
delete from public.leave_requests lr
 using public.students s
 where lr.student_id = s.id
   and s.roll_no = 'DEMO-01'
   and lr.from_date = date '2026-11-05';

insert into public.leave_requests
  (school_id, student_id, from_date, to_date, reason, status,
   requested_by, decided_by, decided_at, decision_note, created_at)
select s.school_id, s.id, date '2026-11-05', date '2026-11-06',
       'Family function out of town', 'approved',
       (select user_id from public.student_links where student_id = s.id order by created_at limit 1),
       (select user_id from public.members where school_id = s.school_id and role = 'admin' order by created_at limit 1),
       timestamptz '2026-11-04 18:20:00+05:30', 'Approved, enjoy the function',
       timestamptz '2026-11-04 16:05:00+05:30'
  from public.students s
 where s.roll_no = 'DEMO-01';

-- 4. One holiday ahead of us, so the slate colour appears on the calendar.
insert into public.school_holidays (school_id, holiday_date, reason)
select id, date '2026-11-19', 'Founders Day'
  from public.schools
 where code = 'ABPS-RNK'
on conflict (school_id, holiday_date) do nothing;

commit;

-- Check: as the guard of DEMO-01 this should now read
--   present 5 · late 1 · absent 2 · leave 2 · holiday 1 · weekly off 5 · 75%
select public.astro_student_calendar(
  (select id from public.students where roll_no = 'DEMO-01'), date '2026-11-01') -> 'summary';
