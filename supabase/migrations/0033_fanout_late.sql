-- 0033_fanout_late.sql
-- A late tap is still an arrival, so it must reach the parent too.
--
-- Before this, astro_fanout_arrival() returned early for anything that was not
-- exactly status 'present': a child who tapped at 08:26 (late, because
-- schools.late_after is 08:20) produced no e-mail at all — the very case a
-- parent most wants to know about.
--
-- Now:
--   present -> kind 'present', "Arrived at school: <name> (12 Nov)"
--   late    -> kind 'late',    "Arrived late: <name> (16 Nov)"
--                              "... reached school at 08:26 ... after the 08:20 cut-off."
--
-- Still exactly one arrival mail per attendance row: the dedupe check accepts
-- either kind, so a correction late -> present (or the reverse) cannot send a
-- second mail.

create or replace function public.astro_fanout_arrival()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
declare
  st public.students;
  sc public.schools;
  v_local   timestamptz;
  v_kind    text;
  v_subject text;
  v_head    text;
begin
  if new.status not in ('present', 'late') then
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

  if exists (select 1 from public.alerts a
              where a.attendance_id = new.id and a.kind in ('present', 'late')) then
    return new;
  end if;

  v_local := coalesce(new.marked_at, now()) at time zone sc.timezone;

  if new.status = 'late' then
    v_kind    := 'late';
    v_subject := 'Arrived late: ' || st.full_name || ' (' || to_char(v_local, 'DD Mon') || ')';
    v_head    := st.full_name || ' (Roll ' || st.roll_no || ') reached school at '
                 || to_char(v_local, 'HH24:MI') || ' on ' || to_char(v_local, 'DD Mon YYYY')
                 || ', after the ' || to_char(sc.late_after, 'HH24:MI') || ' cut-off.';
  else
    v_kind    := 'present';
    v_subject := 'Arrived at school: ' || st.full_name || ' (' || to_char(v_local, 'DD Mon') || ')';
    v_head    := st.full_name || ' (Roll ' || st.roll_no || ') reached school at '
                 || to_char(v_local, 'HH24:MI') || ' on ' || to_char(v_local, 'DD Mon YYYY') || '.';
  end if;

  insert into public.alerts (school_id, student_id, attendance_id, kind, to_email, subject, body)
  values (
    st.school_id, st.id, new.id, v_kind, st.guardian_email, v_subject,
    'Dear Parent,' || chr(10) || chr(10) || v_head || chr(10) || chr(10)
      || '- ' || sc.name || ' / Astro Smart Attendance'
  );

  return new;
end;
$$;
