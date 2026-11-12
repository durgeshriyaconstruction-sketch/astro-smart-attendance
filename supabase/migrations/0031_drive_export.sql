-- 0031_drive_export.sql
-- One call that returns a whole month of school records in exactly the shape
-- tools/archive and the Google-Drive backup write:
--
--   { school, month, from, to, generated_at,
--     days:    [ { date, file, counts, data { date, school, attendance,
--                                             notices, messages, emails,
--                                             leave_requests } } ],
--     summary: { month, from, to, school, school_days, students[], totals } }
--
-- Used by the astro-export Edge Function, which the Google Apps Script in
-- tools/drive_sync calls once a day. Service role only: it reads every table.

create or replace function public.astro_drive_month(
  p_month       text default null,   -- 'YYYY-MM', default = current month (school tz)
  p_school_code text default null    -- default = the first school
)
returns jsonb
language plpgsql
security definer
set search_path = public, pg_temp
as $$
declare
  v_school  public.schools;
  v_tz      text;
  v_month   text;
  v_from    date;
  v_to      date;
  v_days    jsonb;
  v_summary jsonb;
begin
  if p_school_code is null then
    select * into v_school from public.schools order by created_at limit 1;
  else
    select * into v_school from public.schools where code = p_school_code;
  end if;
  if v_school.id is null then
    raise exception 'astro_drive_month: school not found (code=%)', p_school_code;
  end if;

  v_tz    := coalesce(v_school.timezone, 'Asia/Kolkata');
  v_month := coalesce(p_month, to_char(now() at time zone v_tz, 'YYYY-MM'));
  v_from  := (v_month || '-01')::date;
  v_to    := (v_from + interval '1 month - 1 day')::date;

  -- every day in the month that has something on it
  with touched as (
    select attendance_date as day
      from public.attendance
     where school_id = v_school.id and attendance_date between v_from and v_to
    union
    select (created_at at time zone v_tz)::date
      from public.notices
     where school_id = v_school.id
    union
    select (created_at at time zone v_tz)::date
      from public.messages
     where school_id = v_school.id
    union
    select (created_at at time zone v_tz)::date
      from public.alerts
     where school_id = v_school.id
    union
    select d::date
      from public.leave_requests l,
           generate_series(l.from_date, l.to_date, interval '1 day') d
     where l.school_id = v_school.id
  ),
  in_month as (
    select day from touched where day between v_from and v_to
  )
  select coalesce(jsonb_agg(day_json order by day), '[]'::jsonb)
    into v_days
    from (
      select m.day,
             jsonb_build_object(
               'date', m.day,
               'file', to_char(m.day, 'YYYY/MM/YYYY-MM-DD') || '.json',
               'counts', jsonb_build_object(
                 'attendance',
                   (select count(*) from public.attendance a
                     where a.school_id = v_school.id and a.attendance_date = m.day),
                 'notices',
                   (select count(*) from public.notices n
                     where n.school_id = v_school.id
                       and (n.created_at at time zone v_tz)::date = m.day),
                 'messages',
                   (select count(*) from public.messages ms
                     where ms.school_id = v_school.id
                       and (ms.created_at at time zone v_tz)::date = m.day),
                 'emails',
                   (select count(*) from public.alerts al
                     where al.school_id = v_school.id
                       and (al.created_at at time zone v_tz)::date = m.day),
                 'leave_requests',
                   (select count(*) from public.leave_requests lr
                     where lr.school_id = v_school.id
                       and m.day between lr.from_date and lr.to_date)
               ),
               'data', jsonb_build_object(
                 'date', m.day,
                 'school', jsonb_build_object(
                   'code', v_school.code,
                   'name', v_school.name,
                   'timezone', v_tz
                 ),
                 'attendance', coalesce((
                    select jsonb_agg(jsonb_build_object(
                             'roll_no', st.roll_no,
                             'name', st.full_name,
                             'student_id', a.student_id,
                             'status', a.status,
                             'method', a.method,
                             'session', a.session,
                             'period_no', a.period_no,
                             'marked_at', a.marked_at,
                             'note', a.note) order by st.roll_no)
                      from public.attendance a
                      join public.students st on st.id = a.student_id
                     where a.school_id = v_school.id and a.attendance_date = m.day
                 ), '[]'::jsonb),
                 'notices', coalesce((
                    select jsonb_agg(jsonb_build_object(
                             'id', n.id,
                             'title', n.title,
                             'body', n.body,
                             'priority', n.priority,
                             'audience', n.audience,
                             'pinned', n.pinned,
                             'created_at', n.created_at,
                             'expires_at', n.expires_at) order by n.created_at)
                      from public.notices n
                     where n.school_id = v_school.id
                       and (n.created_at at time zone v_tz)::date = m.day
                 ), '[]'::jsonb),
                 'messages', coalesce((
                    select jsonb_agg(jsonb_build_object(
                             'id', ms.id,
                             'student_id', ms.student_id,
                             'subject', ms.subject,
                             'body', ms.body,
                             'direction', ms.direction,
                             'read_at', ms.read_at,
                             'created_at', ms.created_at,
                             'roll_no', st.roll_no,
                             'name', st.full_name) order by ms.created_at)
                      from public.messages ms
                      left join public.students st on st.id = ms.student_id
                     where ms.school_id = v_school.id
                       and (ms.created_at at time zone v_tz)::date = m.day
                 ), '[]'::jsonb),
                 'emails', coalesce((
                    select jsonb_agg(jsonb_build_object(
                             'id', al.id,
                             'student_id', al.student_id,
                             'kind', al.kind,
                             'to_email', al.to_email,
                             'subject', al.subject,
                             'status', al.status,
                             'attempts', al.attempts,
                             'sent_at', al.sent_at,
                             'last_error', al.last_error,
                             'created_at', al.created_at,
                             'roll_no', st.roll_no,
                             'name', st.full_name) order by al.id)
                      from public.alerts al
                      left join public.students st on st.id = al.student_id
                     where al.school_id = v_school.id
                       and (al.created_at at time zone v_tz)::date = m.day
                 ), '[]'::jsonb),
                 'leave_requests', coalesce((
                    select jsonb_agg(jsonb_build_object(
                             'id', lr.id,
                             'student_id', lr.student_id,
                             'from_date', lr.from_date,
                             'to_date', lr.to_date,
                             'reason', lr.reason,
                             'status', lr.status,
                             'roll_no', st.roll_no,
                             'name', st.full_name) order by lr.from_date)
                      from public.leave_requests lr
                      left join public.students st on st.id = lr.student_id
                     where lr.school_id = v_school.id
                       and m.day between lr.from_date and lr.to_date
                 ), '[]'::jsonb)
               )
             ) as day_json
        from in_month m
    ) s;

  -- month-summary: per-student present / late / absent / leave, percent
  -- The month summary follows the attendance sheet, so a student's total
  -- always equals the rows the school can see: present + late + absent +
  -- leave (+ other) = days marked. 'leave' is a status on attendance, not a
  -- count of request rows.
  with per_student as (
    select st.id,
           st.roll_no,
           st.full_name,
           cl.name || coalesce('-' || nullif(cl.section, ''), '') as class_name,
           count(a.id) filter (where a.status = 'present') as present,
           count(a.id) filter (where a.status = 'late')    as late,
           count(a.id) filter (where a.status = 'absent')  as absent,
           count(a.id) filter (where a.status = 'leave')   as leave_days,
           count(a.id) filter (where a.status not in ('present','late','absent','leave')) as other
      from public.students st
      left join public.classes cl on cl.id = st.class_id
      left join public.attendance a
             on a.student_id = st.id
            and a.attendance_date between v_from and v_to
     where st.school_id = v_school.id
     group by st.id, st.roll_no, st.full_name, cl.name, cl.section
  )
  select jsonb_build_object(
           'month', v_month,
           'from', v_from,
           'to', v_to,
           'school', jsonb_build_object(
             'code', v_school.code, 'name', v_school.name, 'timezone', v_tz),
           'school_days', (
             select count(distinct attendance_date)
               from public.attendance
              where school_id = v_school.id
                and attendance_date between v_from and v_to),
           'students', coalesce(jsonb_agg(jsonb_build_object(
             'student_id', ps.id,
             'roll_no', ps.roll_no,
             'name', ps.full_name,
             'class', ps.class_name,
             'present', ps.present,
             'late', ps.late,
             'absent', ps.absent,
             'leave', ps.leave_days,
             'other', ps.other,
             'percent', case
                          when (ps.present + ps.late + ps.absent) = 0 then null
                          else round(100.0 * (ps.present + ps.late)
                                     / (ps.present + ps.late + ps.absent))
                        end
           ) order by ps.roll_no), '[]'::jsonb),
           'totals', jsonb_build_object(
             'students', count(*),
             'present', coalesce(sum(ps.present), 0),
             'late', coalesce(sum(ps.late), 0),
             'absent', coalesce(sum(ps.absent), 0),
             'leave', coalesce(sum(ps.leave_days), 0),
             'other', coalesce(sum(ps.other), 0))
         )
    into v_summary
    from per_student ps;

  return jsonb_build_object(
           'school', jsonb_build_object(
             'code', v_school.code, 'name', v_school.name, 'timezone', v_tz),
           'month', v_month,
           'from', v_from,
           'to', v_to,
           'generated_at', to_char(now() at time zone 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS"+00:00"'),
           'days', v_days,
           'summary', v_summary
         );
end;
$$;

revoke all on function public.astro_drive_month(text, text) from public;
revoke all on function public.astro_drive_month(text, text) from anon;
revoke all on function public.astro_drive_month(text, text) from authenticated;
grant execute on function public.astro_drive_month(text, text) to service_role;

comment on function public.astro_drive_month(text, text) is
  'Whole-month export for the Google Drive backup (astro-export Edge Function). '
  'Service role only — returns every table for one school.';
