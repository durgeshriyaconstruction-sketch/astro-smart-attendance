-- ============================================================================
-- ASTRO SMART ATTENDANCE — 0001 core schema
-- Project ref: nrjchonjlncamfyzmfye   (region ap-southeast-2)
-- Applied: 2026-11-12 by Agent Mode
--
-- Design rules
--  * every table is school-scoped (multi-school ready, one row per school today)
--  * devices authenticate with device_code + device_secret (never the service key)
--  * the ESP32 never touches a table directly: it may only EXECUTE the RPCs in
--    0002_device_api.sql (SECURITY DEFINER, granted to `anon`)
--  * raw taps are stored in device_events so an offline replay is idempotent
-- ============================================================================

create extension if not exists pgcrypto with schema extensions;

-- ---------------------------------------------------------------- schools ---
create table if not exists public.schools (
  id            uuid primary key default gen_random_uuid(),
  name          text not null,
  code          text not null unique,
  timezone      text not null default 'Asia/Kolkata',
  day_start     time not null default '08:00',
  late_after    time not null default '08:20',
  day_end       time not null default '14:00',
  alert_emails  boolean not null default true,
  created_at    timestamptz not null default now()
);

-- ---------------------------------------------------------------- classes ---
create table if not exists public.classes (
  id         uuid primary key default gen_random_uuid(),
  school_id  uuid not null references public.schools(id) on delete cascade,
  name       text not null,                       -- '9', '10'
  section    text not null default 'A',
  teacher    text,
  created_at timestamptz not null default now(),
  constraint classes_unique unique (school_id, name, section)
);

-- --------------------------------------------------------------- students ---
create table if not exists public.students (
  id             uuid primary key default gen_random_uuid(),
  school_id      uuid not null references public.schools(id) on delete cascade,
  class_id       uuid references public.classes(id) on delete set null,
  roll_no        text not null,
  full_name      text not null,
  guardian_name  text,
  guardian_email text,
  guardian_phone text,
  fingerprint_id integer,                          -- R307 template slot 0..999
  active         boolean not null default true,
  created_at     timestamptz not null default now(),
  updated_at     timestamptz not null default now(),
  constraint students_roll_unique unique (school_id, roll_no),
  constraint students_fingerprint_range
    check (fingerprint_id is null or fingerprint_id between 0 and 999)
);

create unique index if not exists students_fingerprint_uidx
  on public.students (school_id, fingerprint_id)
  where fingerprint_id is not null;

-- ------------------------------------------------------------- RFiD cards ---
-- card_uid = the RC522 UID, normalised to UPPERCASE HEX with no separators.
create table if not exists public.rfid_cards (
  id          uuid primary key default gen_random_uuid(),
  school_id   uuid not null references public.schools(id) on delete cascade,
  student_id  uuid references public.students(id) on delete set null,
  card_uid    text not null,
  label       text,
  active      boolean not null default true,
  assigned_at timestamptz not null default now(),
  constraint rfid_cards_uid_unique unique (card_uid)
);

create index if not exists rfid_cards_student_idx on public.rfid_cards (student_id);

-- ---------------------------------------------------------------- devices ---
-- secret_hash = hex(sha256(device_secret)). The plain secret lives ONLY in the
-- firmware (and in the team's password manager). It is never stored in clear.
create table if not exists public.devices (
  id          uuid primary key default gen_random_uuid(),
  school_id   uuid not null references public.schools(id) on delete cascade,
  device_code text not null unique,               -- 'ASTRO-RNK-01'
  name        text,
  location    text,
  secret_hash text not null,
  firmware    text,
  ip          text,
  wifi_rssi   integer,
  last_seen   timestamptz,
  last_boot   timestamptz,
  active      boolean not null default true,
  created_at  timestamptz not null default now()
);

-- ------------------------------------------------------------- attendance ---
create table if not exists public.attendance (
  id              bigint generated always as identity primary key,
  school_id       uuid not null references public.schools(id) on delete cascade,
  student_id      uuid not null references public.students(id) on delete cascade,
  class_id        uuid references public.classes(id) on delete set null,
  device_id       uuid references public.devices(id) on delete set null,
  attendance_date date not null,
  session         text not null default 'daily'
                    check (session in ('daily','period')),
  period_no       integer check (period_no is null or period_no between 1 and 12),
  status          text not null
                    check (status in ('present','late','absent','excused','left','half_day')),
  method          text not null default 'rfid'
                    check (method in ('rfid','fingerprint','manual','face','keypad','import')),
  marked_at       timestamptz not null default now(),
  event_uid       uuid,
  note            text,
  created_at      timestamptz not null default now()
);

-- one row per student per day per session (and per period when session='period')
create unique index if not exists attendance_slot_uidx
  on public.attendance (student_id, attendance_date, session, coalesce(period_no, 0));

create index if not exists attendance_day_idx  on public.attendance (school_id, attendance_date desc);
create index if not exists attendance_stu_idx  on public.attendance (student_id, attendance_date desc);

-- ---------------------------------------------------------- device events ---
-- every tap the terminal ever makes, including replays from the offline queue.
-- event_uid is generated on the ESP32 -> replaying the same tap is harmless.
create table if not exists public.device_events (
  id          bigint generated always as identity primary key,
  event_uid   uuid not null unique,
  school_id   uuid references public.schools(id) on delete cascade,
  device_id   uuid references public.devices(id) on delete set null,
  card_uid    text,
  fingerprint_id integer,
  method      text,
  status      text,                               -- marked / already_marked / unknown_card / error
  event_ts    timestamptz not null,
  received_at timestamptz not null default now(),
  payload     jsonb,
  result      jsonb,
  processed   boolean not null default false
);

create index if not exists device_events_dev_idx on public.device_events (device_id, received_at desc);

-- ----------------------------------------------------------------- alerts ---
-- queued by the RPCs, drained by the `dispatch-alerts` edge function (or any
-- SMTP sender you prefer). status: queued -> sent | failed | skipped
create table if not exists public.alerts (
  id            bigint generated always as identity primary key,
  school_id     uuid not null references public.schools(id) on delete cascade,
  student_id    uuid references public.students(id) on delete cascade,
  attendance_id bigint references public.attendance(id) on delete set null,
  kind          text not null
                  check (kind in ('absent','late','unknown_card','low_attendance')),
  channel       text not null default 'email' check (channel in ('email','sms','push')),
  to_email      text,
  subject       text,
  body          text,
  status        text not null default 'queued'
                  check (status in ('queued','sent','failed','skipped')),
  error         text,
  created_at    timestamptz not null default now(),
  sent_at       timestamptz
);

create index if not exists alerts_queue_idx on public.alerts (status, created_at);

-- ------------------------------------------------- dashboard user mapping ---
create table if not exists public.members (
  user_id    uuid primary key references auth.users(id) on delete cascade,
  school_id  uuid not null references public.schools(id) on delete cascade,
  role       text not null default 'teacher'
               check (role in ('admin','teacher','viewer')),
  created_at timestamptz not null default now()
);

-- a student or a guardian only sees their own rows
create table if not exists public.student_links (
  user_id    uuid not null references auth.users(id) on delete cascade,
  student_id uuid not null references public.students(id) on delete cascade,
  relation   text not null default 'guardian' check (relation in ('self','guardian')),
  primary key (user_id, student_id)
);

-- ============================================================================
-- RLS helpers
-- ============================================================================
create or replace function public.current_school_id()
returns uuid
language sql stable security definer set search_path = public
as $$
  select m.school_id from public.members m where m.user_id = auth.uid() limit 1
$$;

create or replace function public.is_staff()
returns boolean
language sql stable security definer set search_path = public
as $$
  select exists (
    select 1 from public.members m
    where m.user_id = auth.uid() and m.role in ('admin','teacher')
  )
$$;

create or replace function public.linked_student(p_student uuid)
returns boolean
language sql stable security definer set search_path = public
as $$
  select exists (
    select 1 from public.student_links l
    where l.user_id = auth.uid() and l.student_id = p_student
  )
$$;

-- ============================================================================
-- RLS policies
-- ============================================================================
alter table public.schools       enable row level security;
alter table public.classes       enable row level security;
alter table public.students      enable row level security;
alter table public.rfid_cards    enable row level security;
alter table public.devices       enable row level security;
alter table public.attendance    enable row level security;
alter table public.device_events enable row level security;
alter table public.alerts        enable row level security;
alter table public.members       enable row level security;
alter table public.student_links enable row level security;

do $$
declare
  t text;
  school_tables text[] := array['classes','students','rfid_cards','devices',
                                'attendance','device_events','alerts'];
begin
  foreach t in array school_tables loop
    -- read: any member of the school
    execute format($f$
      drop policy if exists %1$s_read on public.%1$s;
      create policy %1$s_read on public.%1$s
        for select to authenticated
        using (school_id = public.current_school_id());
    $f$, t);

    -- write: admin/teacher of the school
    execute format($f$
      drop policy if exists %1$s_write on public.%1$s;
      create policy %1$s_write on public.%1$s
        for all to authenticated
        using (school_id = public.current_school_id() and public.is_staff())
        with check (school_id = public.current_school_id() and public.is_staff());
    $f$, t);
  end loop;
end $$;

-- students / attendance: a linked student or guardian also sees their rows
drop policy if exists students_read_linked on public.students;
create policy students_read_linked on public.students
  for select to authenticated
  using (public.linked_student(id));

drop policy if exists attendance_read_linked on public.attendance;
create policy attendance_read_linked on public.attendance
  for select to authenticated
  using (public.linked_student(student_id));

drop policy if exists schools_read on public.schools;
create policy schools_read on public.schools
  for select to authenticated
  using (id = public.current_school_id());

drop policy if exists schools_write on public.schools;
create policy schools_write on public.schools
  for update to authenticated
  using (id = public.current_school_id() and public.is_staff())
  with check (id = public.current_school_id());

drop policy if exists members_read_self on public.members;
create policy members_read_self on public.members
  for select to authenticated
  using (user_id = auth.uid() or public.is_staff());

drop policy if exists members_write on public.members;
create policy members_write on public.members
  for all to authenticated
  using (school_id = public.current_school_id()
         and exists (select 1 from public.members m
                     where m.user_id = auth.uid() and m.role = 'admin'))
  with check (school_id = public.current_school_id());

drop policy if exists student_links_self on public.student_links;
create policy student_links_self on public.student_links
  for select to authenticated
  using (user_id = auth.uid() or public.is_staff());

-- ============================================================================
-- Privileges: anon gets NOTHING on tables, only EXECUTE on the device RPCs.
-- ============================================================================
revoke all on public.schools, public.classes, public.students, public.rfid_cards,
              public.devices, public.attendance, public.device_events, public.alerts,
              public.members, public.student_links
  from anon, public;

grant select, insert, update, delete on public.schools, public.classes, public.students,
      public.rfid_cards, public.devices, public.attendance, public.device_events,
      public.alerts, public.members, public.student_links
  to authenticated;

grant usage, select on all sequences in schema public to authenticated;

-- ============================================================================
-- Convenience views for the dashboard
-- ============================================================================
create or replace view public.v_attendance_feed
with (security_invoker = true) as
select a.id,
       a.school_id,
       a.attendance_date,
       a.session,
       a.period_no,
       a.status,
       a.method,
       a.marked_at,
       s.id            as student_id,
       s.roll_no,
       s.full_name,
       c.name || '-' || c.section as class_name,
       d.device_code
from public.attendance a
join public.students s on s.id = a.student_id
left join public.classes c on c.id = a.class_id
left join public.devices d on d.id = a.device_id;

create or replace view public.v_daily_attendance
with (security_invoker = true) as
select school_id,
       attendance_date,
       count(*) filter (where status = 'present') as present,
       count(*) filter (where status = 'late')    as late,
       count(*) filter (where status = 'absent')  as absent,
       count(*)                                   as total
from public.attendance
where session = 'daily'
group by school_id, attendance_date;

grant select on public.v_attendance_feed, public.v_daily_attendance to authenticated;
