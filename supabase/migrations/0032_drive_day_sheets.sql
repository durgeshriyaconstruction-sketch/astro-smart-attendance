-- 0032_drive_day_sheets.sql
-- One day, grouped by class and section, in the shape the Drive sheets need:
--
--   { date, file: "2026-11-12.xlsx",
--     school: { code, name, timezone },
--     classes: [ { class: "9", section: "A", label: "9-A",
--                  path: "2026/11/9/A",
--                  students: [ { roll_no, name, status, raw_status, time, method } ] } ] }
--
-- `status` is the word that goes in the sheet (Present / Late / Absent / Leave);
-- a student with no row for that day reads Absent, which is what astro_close_day
-- writes anyway after the school day ends.
--
-- Used by astro-export (?date=YYYY-MM-DD) -> tools/drive_sync/Code.gs.
-- Service role only.

create or replace function public.astro_drive_day(
  p_date        date default null,   -- default = today in the school's timezone
  p_school_code text default null
)
returns jsonb
language plpgsql
security definer
set search_path = public, pg_temp
as $$
declare
  v_school  public.schools;
  v_tz      text;
  v_day     date;
  v_classes jsonb;
begin
  if p_school_code is null then
    select * into v_school from public.schools order by created_at limit 1;
  else
    select * into v_school from public.schools where code = p_school_code;
  end if;
  if v_school.id is null then
    raise exception 'astro_drive_day: school not found (code=%)', p_school_code;
  end if;

  v_tz  := coalesce(v_school.timezone, 'Asia/Kolkata');
  v_day := coalesce(p_date, (now() at time zone v_tz)::date);

  select coalesce(jsonb_agg(jsonb_build_object(
           'class',   c.name,
           'section', coalesce(c.section, ''),
           'label',   c.name || coalesce('-' || nullif(c.section, ''), ''),
           'path',    to_char(v_day, 'YYYY') || '/' || to_char(v_day, 'MM')
                      || '/' || c.name || '/' || coalesce(c.section, ''),
           'students', coalesce((
             select jsonb_agg(jsonb_build_object(
                      'roll_no',    st.roll_no,
                      'name',       st.full_name,
                      'status',     case a.status
                                      when 'present' then 'Present'
                                      when 'late'    then 'Late'
                                      when 'absent'  then 'Absent'
                                      when 'leave'   then 'Leave'
                                      else 'Absent'
                                    end,
                      'raw_status', coalesce(a.status, 'absent'),
                      'time',       case when a.marked_at is null then ''
                                         else to_char(a.marked_at at time zone v_tz, 'HH24:MI')
                                    end,
                      'method',     coalesce(a.method, 'none')
                    ) order by st.roll_no)
               from public.students st
               left join lateral (
                 select x.*
                   from public.attendance x
                  where x.student_id = st.id
                    and x.attendance_date = v_day
                  order by (x.session = 'daily') desc, x.marked_at
                  limit 1
               ) a on true
              where st.class_id = c.id and st.active
           ), '[]'::jsonb)
         ) order by c.name, c.section), '[]'::jsonb)
    into v_classes
    from public.classes c
   where c.school_id = v_school.id;

  return jsonb_build_object(
           'date', v_day,
           'file', to_char(v_day, 'YYYY-MM-DD') || '.xlsx',
           'school', jsonb_build_object(
             'code', v_school.code, 'name', v_school.name, 'timezone', v_tz),
           'classes', v_classes
         );
end;
$$;

revoke all on function public.astro_drive_day(date, text) from public;
revoke all on function public.astro_drive_day(date, text) from anon;
revoke all on function public.astro_drive_day(date, text) from authenticated;
grant execute on function public.astro_drive_day(date, text) to service_role;

comment on function public.astro_drive_day(date, text) is
  'One day grouped by class/section for the Drive .xlsx sheets. Service role only.';
