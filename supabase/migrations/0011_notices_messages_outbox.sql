-- ============================================================================
-- ASTRO SMART ATTENDANCE — 0011 notices, messages and a unified outbox
--
-- Adds the two missing admin actions and makes the delivery queue general:
--
--   notices   admin -> whole school / one class / one student
--   messages  admin -> one student (and their guardian)
--   alerts    becomes the single outbox for EVERYTHING that leaves the building
--             (attendance alerts, notices, messages) so there is one sender,
--             one retry policy, one log.
--
-- Fan-out happens in a trigger: posting a notice to class 9-A writes one outbox
-- row per guardian with an email address. Publishing and delivering are
-- therefore independent - the admin screen never waits for an email provider.
-- ============================================================================

-- ---------------------------------------------------------------- outbox ----
alter table public.alerts drop constraint if exists alerts_kind_check;
alter table public.alerts add constraint alerts_kind_check
  check (kind in ('absent','late','unknown_card','low_attendance','notice','message'));

alter table public.alerts drop constraint if exists alerts_channel_check;
alter table public.alerts add constraint alerts_channel_check
  check (channel in ('email','sms','push','inapp'));

alter table public.alerts add column if not exists ref_kind  text;
alter table public.alerts add column if not exists ref_id    uuid;
alter table public.alerts add column if not exists title     text;
alter table public.alerts add column if not exists attempts  integer not null default 0;
alter table public.alerts add column if not exists last_error text;
alter table public.alerts add column if not exists read_at   timestamptz;

create index if not exists alerts_ref_idx on public.alerts (ref_kind, ref_id);

-- --------------------------------------------------------------- notices ----
create table if not exists public.notices (
  id          uuid primary key default gen_random_uuid(),
  school_id   uuid not null references public.schools(id) on delete cascade,
  title       text not null,
  body        text not null,
  audience    text not null default 'all' check (audience in ('all','class','student')),
  class_id    uuid references public.classes(id) on delete cascade,
  student_id  uuid references public.students(id) on delete cascade,
  pinned      boolean not null default false,
  created_by  uuid,
  publish_at  timestamptz not null default now(),
  expires_at  timestamptz,
  created_at  timestamptz not null default now(),
  constraint notices_audience_target check (
    (audience = 'all'     and class_id is null and student_id is null) or
    (audience = 'class'   and class_id is not null) or
    (audience = 'student' and student_id is not null)
  )
);

create index if not exists notices_school_idx on public.notices (school_id, publish_at desc);

-- -------------------------------------------------------------- messages ----
create table if not exists public.messages (
  id          uuid primary key default gen_random_uuid(),
  school_id   uuid not null references public.schools(id) on delete cascade,
  student_id  uuid not null references public.students(id) on delete cascade,
  sender      uuid,
  subject     text not null,
  body        text not null,
  read_at     timestamptz,
  created_at  timestamptz not null default now()
);

create index if not exists messages_student_idx on public.messages (student_id, created_at desc);
create index if not exists messages_school_idx  on public.messages (school_id, created_at desc);

-- ------------------------------------------------------------------- RLS ----
alter table public.notices  enable row level security;
alter table public.messages enable row level security;

drop policy if exists notices_read on public.notices;
create policy notices_read on public.notices
  for select to authenticated
  using (
    school_id = public.current_school_id()
    or exists (
      select 1
      from public.student_links l
      join public.students s on s.id = l.student_id
      where l.user_id = auth.uid()
        and s.school_id = notices.school_id
        and (
          notices.audience = 'all'
          or (notices.audience = 'class'   and s.class_id = notices.class_id)
          or (notices.audience = 'student' and s.id       = notices.student_id)
        )
    )
  );

drop policy if exists notices_write on public.notices;
create policy notices_write on public.notices
  for all to authenticated
  using (school_id = public.current_school_id() and public.is_staff())
  with check (school_id = public.current_school_id() and public.is_staff());

drop policy if exists messages_read on public.messages;
create policy messages_read on public.messages
  for select to authenticated
  using (
    school_id = public.current_school_id()
    or exists (select 1 from public.student_links l
               where l.user_id = auth.uid() and l.student_id = messages.student_id)
  );

drop policy if exists messages_write on public.messages;
create policy messages_write on public.messages
  for all to authenticated
  using (school_id = public.current_school_id() and public.is_staff())
  with check (school_id = public.current_school_id() and public.is_staff());

revoke all on table public.notices, public.messages from anon, public;
grant select, insert, update, delete on table public.notices, public.messages to authenticated;

-- ============================================================================
-- Fan-out: one outbox row per guardian, written as the table owner so RLS on
-- alerts never blocks it.
-- ============================================================================
create or replace function public.astro_fanout_notice()
returns trigger
language plpgsql security definer set search_path = public
as $$
begin
  insert into public.alerts
      (school_id, student_id, kind, channel, to_email, title, subject, body,
       ref_kind, ref_id)
  select st.school_id, st.id, 'notice', 'email', st.guardian_email,
         new.title, new.title, new.body, 'notice', new.id
  from public.students st
  where st.school_id  = new.school_id
    and st.active
    and st.guardian_email is not null
    and (
      new.audience = 'all'
      or (new.audience = 'class'   and st.class_id = new.class_id)
      or (new.audience = 'student' and st.id       = new.student_id)
    );
  return new;
end $$;

drop trigger if exists notices_fanout on public.notices;
create trigger notices_fanout
  after insert on public.notices
  for each row execute function public.astro_fanout_notice();

create or replace function public.astro_fanout_message()
returns trigger
language plpgsql security definer set search_path = public
as $$
begin
  insert into public.alerts
      (school_id, student_id, kind, channel, to_email, title, subject, body,
       ref_kind, ref_id)
  select st.school_id, st.id, 'message', 'email', st.guardian_email,
         new.subject, new.subject, new.body, 'message', new.id
  from public.students st
  where st.id = new.student_id
    and st.guardian_email is not null;
  return new;
end $$;

drop trigger if exists messages_fanout on public.messages;
create trigger messages_fanout
  after insert on public.messages
  for each row execute function public.astro_fanout_message();

-- ============================================================================
-- Admin API (dashboard calls these; no direct table access needed)
-- ============================================================================

create or replace function public.astro_post_notice(
  p_title      text,
  p_body       text,
  p_audience   text default 'all',
  p_class_id   uuid default null,
  p_student_id uuid default null,
  p_pinned     boolean default false,
  p_school_id  uuid default null,
  p_expires_at timestamptz default null
)
returns jsonb
language plpgsql security definer set search_path = public
as $$
declare
  sid uuid := coalesce(public.current_school_id(), p_school_id);
  nid uuid;
  n   integer;
begin
  if auth.uid() is not null and not public.is_staff() then
    raise exception using message = 'NOT_STAFF', errcode = '42501';
  end if;
  if sid is null then
    raise exception using message = 'SCHOOL_REQUIRED', errcode = '22023';
  end if;

  insert into public.notices (school_id, title, body, audience, class_id,
                              student_id, pinned, created_by, expires_at)
  values (sid, p_title, p_body, coalesce(p_audience, 'all'), p_class_id,
          p_student_id, coalesce(p_pinned, false), auth.uid(), p_expires_at)
  returning id into nid;

  select count(*) into n from public.alerts where ref_kind = 'notice' and ref_id = nid;

  return jsonb_build_object('ok', true, 'notice_id', nid, 'recipients', n,
                            'email_queued', n > 0);
end $$;

create or replace function public.astro_send_message(
  p_student_id uuid,
  p_subject    text,
  p_body       text,
  p_school_id  uuid default null
)
returns jsonb
language plpgsql security definer set search_path = public
as $$
declare
  sid uuid := coalesce(public.current_school_id(), p_school_id);
  st  public.students;
  mid uuid;
  n   integer;
begin
  if auth.uid() is not null and not public.is_staff() then
    raise exception using message = 'NOT_STAFF', errcode = '42501';
  end if;
  if sid is null then
    raise exception using message = 'SCHOOL_REQUIRED', errcode = '22023';
  end if;

  select * into st from public.students
   where id = p_student_id and school_id = sid and active;
  if st.id is null then
    raise exception using message = 'STUDENT_NOT_FOUND', errcode = '22023';
  end if;

  insert into public.messages (school_id, student_id, sender, subject, body)
  values (sid, st.id, auth.uid(), p_subject, p_body)
  returning id into mid;

  select count(*) into n from public.alerts where ref_kind = 'message' and ref_id = mid;

  return jsonb_build_object('ok', true, 'message_id', mid,
                            'student', st.full_name, 'roll_no', st.roll_no,
                            'email_queued', n > 0,
                            'guardian_email_on_file', st.guardian_email is not null);
end $$;

create or replace function public.astro_mark_message_read(p_message_id uuid)
returns jsonb
language plpgsql security definer set search_path = public
as $$
declare n integer;
begin
  update public.messages
     set read_at = coalesce(read_at, now())
   where id = p_message_id
  returning 1 into n;

  return jsonb_build_object('ok', n = 1, 'message_id', p_message_id);
end $$;

-- Admin screen widgets
create or replace function public.astro_outbox_stats()
returns jsonb
language plpgsql security definer set search_path = public
as $$
declare sid uuid := public.current_school_id();
begin
  if auth.uid() is not null and not public.is_staff() then
    raise exception using message = 'NOT_STAFF', errcode = '42501';
  end if;

  return jsonb_build_object(
    'queued',   (select count(*) from public.alerts where status = 'queued' and (sid is null or school_id = sid)),
    'sent',     (select count(*) from public.alerts where status = 'sent'   and (sid is null or school_id = sid)),
    'failed',   (select count(*) from public.alerts where status = 'failed' and (sid is null or school_id = sid)),
    'skipped',  (select count(*) from public.alerts where status = 'skipped' and (sid is null or school_id = sid)),
    'oldest_queued', (select min(created_at) from public.alerts where status = 'queued' and (sid is null or school_id = sid))
  );
end $$;

-- Put failed deliveries back in the queue (after fixing the provider, say)
create or replace function public.astro_requeue_failed()
returns jsonb
language plpgsql security definer set search_path = public
as $$
declare n integer;
begin
  if auth.uid() is not null and not public.is_staff() then
    raise exception using message = 'NOT_STAFF', errcode = '42501';
  end if;

  update public.alerts
     set status = 'queued', attempts = 0, last_error = null
   where status = 'failed'
     and (public.current_school_id() is null or school_id = public.current_school_id());
  get diagnostics n = row_count;

  return jsonb_build_object('ok', true, 'requeued', n);
end $$;

revoke all on function public.astro_post_notice(text, text, text, uuid, uuid, boolean, uuid, timestamptz) from anon, public;
revoke all on function public.astro_send_message(uuid, text, text, uuid) from anon, public;
revoke all on function public.astro_mark_message_read(uuid) from anon, public;
revoke all on function public.astro_outbox_stats() from anon, public;
revoke all on function public.astro_requeue_failed() from anon, public;

grant execute on function public.astro_post_notice(text, text, text, uuid, uuid, boolean, uuid, timestamptz) to authenticated;
grant execute on function public.astro_send_message(uuid, text, text, uuid) to authenticated;
grant execute on function public.astro_mark_message_read(uuid) to authenticated;
grant execute on function public.astro_outbox_stats() to authenticated;
grant execute on function public.astro_requeue_failed() to authenticated;

-- Device/anon side gains nothing
revoke all on function public.astro_fanout_notice() from anon, public;
revoke all on function public.astro_fanout_message() from anon, public;
