-- 0029_arrival_emails.sql
-- E-mail a guardian when the child actually arrives, not only when something is
-- wrong. Before this, a tap at 08:05 recorded attendance silently and only Late
-- or Absent produced an `alerts` row.
--
-- Shape of the change:
--   * schools.alert_arrivals — per-school switch, on by default only for schools
--     that already have alert_emails on; the trigger checks both.
--   * alerts.kind may now be 'present'.
--   * an AFTER trigger on attendance queues one 'present' e-mail per arrival, so
--     nothing in astro_mark_attendance had to be rewritten.
--
-- Duplicate safety: one 'present' alert per attendance row (checked by
-- attendance_id + kind), and the existing fan-out means a re-scan that keeps the
-- status at 'present' adds nothing.

alter table public.schools
  add column if not exists alert_arrivals boolean not null default true;

alter table public.alerts drop constraint if exists alerts_kind_check;
alter table public.alerts
  add constraint alerts_kind_check check (kind = any (array[
    'present', 'absent', 'late', 'unknown_card', 'low_attendance',
    'notice', 'message', 'leave'
  ]));

create or replace function public.astro_fanout_arrival()
returns trigger
language plpgsql
security definer
set search_path to 'public'
as $function$
declare
  st public.students;
  sc public.schools;
  v_local timestamptz;
begin
  if new.status <> 'present' then
    return new;
  end if;
  if tg_op = 'UPDATE' and old.status = new.status then
    return new;
  end if;

  select * into st from public.students where id = new.student_id;
  if st.id is null or not st.active then
    return new;
  end if;
  select * into sc from public.schools where id = st.school_id;
  if sc.id is null or not sc.alert_emails or not sc.alert_arrivals then
    return new;
  end if;
  if st.guardian_email is null then
    return new;
  end if;

  -- One e-mail per attendance row, even if the row is rewritten later.
  if exists (select 1 from public.alerts a
              where a.attendance_id = new.id and a.kind = 'present') then
    return new;
  end if;

  v_local := coalesce(new.marked_at, now()) at time zone sc.timezone;

  insert into public.alerts (school_id, student_id, attendance_id, kind, to_email, subject, body)
  values (
    st.school_id, st.id, new.id, 'present', st.guardian_email,
    'Arrived at school: ' || st.full_name || ' (' || to_char(v_local, 'DD Mon') || ')',
    'Dear Parent,' || chr(10) || chr(10)
      || st.full_name || ' (Roll ' || st.roll_no || ') reached school at '
      || to_char(v_local, 'HH24:MI') || ' on ' || to_char(v_local, 'DD Mon YYYY') || '.'
      || chr(10) || chr(10)
      || '- ' || sc.name || ' / Astro Smart Attendance'
  );

  return new;
end
$function$;

drop trigger if exists attendance_arrival_fanout on public.attendance;
create trigger attendance_arrival_fanout
  after insert or update of status on public.attendance
  for each row execute function public.astro_fanout_arrival();

comment on function public.astro_fanout_arrival() is
  'Queues one arrival e-mail per present attendance row, when the school has alert_emails and alert_arrivals on and the student has a guardian e-mail.';
