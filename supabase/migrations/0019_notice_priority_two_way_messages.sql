-- 0019 notices: priority + targets + per-user dismiss; messages: two-way, deletable, rate-limited

-- ---------- notices ----------
alter table public.notices add column if not exists priority text not null default 'normal';
alter table public.notices drop constraint if exists notices_priority_check;
alter table public.notices add constraint notices_priority_check check (priority in ('normal','important','critical'));
-- all = everyone | students = students and parents only | staff = admin/teachers only | class | student
alter table public.notices drop constraint if exists notices_audience_check;
alter table public.notices add constraint notices_audience_check check (audience in ('all','students','staff','class','student'));
alter table public.notices drop constraint if exists notices_audience_target;
alter table public.notices add constraint notices_audience_target check (
  (audience in ('all','students','staff') and class_id is null and student_id is null)
  or (audience = 'class' and class_id is not null and student_id is null)
  or (audience = 'student' and student_id is not null));

create or replace function public.astro_notices_clean() returns trigger
language plpgsql security definer set search_path = public as $$
begin
  new.title := btrim(coalesce(new.title, ''));
  new.body := btrim(coalesce(new.body, ''));
  if new.title = '' then raise exception using message = 'TITLE_REQUIRED', errcode = '22023'; end if;
  if new.body = '' then raise exception using message = 'BODY_REQUIRED', errcode = '22023'; end if;
  if length(new.title) > 200 then raise exception using message = 'TITLE_TOO_LONG', errcode = '22023'; end if;
  if length(new.body) > 5000 then raise exception using message = 'BODY_TOO_LONG', errcode = '22023'; end if;
  new.priority := coalesce(nullif(lower(btrim(new.priority)), ''), 'normal');   -- missing priority = normal
  new.audience := coalesce(nullif(lower(btrim(new.audience)), ''), 'all');
  if new.audience = 'class' and not exists (select 1 from public.classes c where c.id = new.class_id and c.school_id = new.school_id) then
    raise exception using message = 'CLASS_NOT_FOUND', errcode = '22023';
  end if;
  if new.audience = 'student' and not exists (select 1 from public.students st where st.id = new.student_id and st.school_id = new.school_id) then
    raise exception using message = 'STUDENT_NOT_FOUND', errcode = '22023';
  end if;
  if tg_op = 'INSERT' and auth.uid() is not null then new.created_by := auth.uid(); end if;
  return new;
end $$;
drop trigger if exists notices_clean on public.notices;
create trigger notices_clean before insert or update on public.notices
  for each row execute function public.astro_notices_clean();

create or replace function public.astro_fanout_notice() returns trigger
language plpgsql security definer set search_path = public as $$
begin
  if new.audience = 'staff' or not coalesce((select sc.alert_emails from public.schools sc where sc.id = new.school_id), false) then
    return new;
  end if;
  insert into public.alerts (school_id, student_id, kind, channel, to_email, title, subject, body, ref_kind, ref_id)
  select st.school_id, st.id, 'notice', 'email', st.guardian_email, new.title,
         case new.priority when 'critical' then '[URGENT] ' when 'important' then '[Important] ' else '' end || new.title,
         new.body, 'notice', new.id
  from public.students st
  where st.school_id = new.school_id and st.active and st.guardian_email is not null
    and (new.audience in ('all','students')
         or (new.audience = 'class' and st.class_id = new.class_id)
         or (new.audience = 'student' and st.id = new.student_id));
  return new;
end $$;

-- deleting or editing a notice/message must reach the e-mails that have not gone out yet
create or replace function public.astro_outbox_sync() returns trigger
language plpgsql security definer set search_path = public as $$
declare k text := case tg_table_name when 'notices' then 'notice' else 'message' end;
begin
  if tg_op = 'DELETE' then
    delete from public.alerts where ref_kind = k and ref_id = old.id and status = 'queued';
    return old;
  end if;
  if k = 'notice' then
    if (new.title, new.body, new.priority) is distinct from (old.title, old.body, old.priority) then
      update public.alerts set title = new.title, body = new.body,
             subject = case new.priority when 'critical' then '[URGENT] ' when 'important' then '[Important] ' else '' end || new.title
       where ref_kind = 'notice' and ref_id = new.id and status = 'queued';
    end if;
  else
    if new.body is distinct from old.body then
      update public.alerts set body = new.body where ref_kind = 'message' and ref_id = new.id and status = 'queued';
    end if;
  end if;
  return new;
end $$;
drop trigger if exists notices_outbox_sync on public.notices;
create trigger notices_outbox_sync after update or delete on public.notices
  for each row execute function public.astro_outbox_sync();

drop policy if exists notices_read on public.notices;
create policy notices_read on public.notices for select to authenticated using (
  school_id = public.current_school_id()
  or exists (select 1 from public.student_links l join public.students s on s.id = l.student_id
             where l.user_id = auth.uid() and s.school_id = notices.school_id
               and (notices.audience in ('all','students')
                    or (notices.audience = 'class' and s.class_id = notices.class_id)
                    or (notices.audience = 'student' and s.id = notices.student_id))));

-- a student's trash icon hides the notice for that user only; it never deletes it for the school
create table if not exists public.notice_dismissals (
  user_id uuid not null references auth.users(id) on delete cascade,
  notice_id uuid not null references public.notices(id) on delete cascade,
  dismissed_at timestamptz not null default now(),
  primary key (user_id, notice_id));
alter table public.notice_dismissals enable row level security;
revoke all on public.notice_dismissals from anon, authenticated;
grant select, insert, delete on public.notice_dismissals to authenticated;
drop policy if exists notice_dismissals_own_read on public.notice_dismissals;
create policy notice_dismissals_own_read on public.notice_dismissals for select to authenticated using (user_id = auth.uid());
drop policy if exists notice_dismissals_own_insert on public.notice_dismissals;
create policy notice_dismissals_own_insert on public.notice_dismissals for insert to authenticated
  with check (user_id = auth.uid() and exists (select 1 from public.notices n where n.id = notice_id));
drop policy if exists notice_dismissals_own_delete on public.notice_dismissals;
create policy notice_dismissals_own_delete on public.notice_dismissals for delete to authenticated using (user_id = auth.uid());

create or replace function public.astro_dismiss_notice(p_notice_id uuid, p_undo boolean default false)
returns jsonb language plpgsql security invoker set search_path = public as $$
begin
  if auth.uid() is null then raise exception using message = 'NOT_SIGNED_IN', errcode = '42501'; end if;
  if coalesce(p_undo, false) then
    delete from public.notice_dismissals where user_id = auth.uid() and notice_id = p_notice_id;
    return jsonb_build_object('ok', true, 'notice_id', p_notice_id, 'dismissed', false);
  end if;
  if not exists (select 1 from public.notices n where n.id = p_notice_id) then
    return jsonb_build_object('ok', false, 'reason', 'NOTICE_NOT_FOUND');
  end if;
  insert into public.notice_dismissals (user_id, notice_id) values (auth.uid(), p_notice_id) on conflict do nothing;
  return jsonb_build_object('ok', true, 'notice_id', p_notice_id, 'dismissed', true);
end $$;

drop function if exists public.astro_post_notice(text, text, text, uuid, uuid, boolean, uuid, timestamptz);
create or replace function public.astro_post_notice(
  p_title text, p_body text, p_priority text default 'normal', p_audience text default 'all',
  p_class_id uuid default null, p_student_id uuid default null, p_pinned boolean default false,
  p_expires_at timestamptz default null, p_school_id uuid default null)
returns jsonb language plpgsql security definer set search_path = public as $$
declare sid uuid := public.astro_ctx_school(p_school_id, 'staff'); nid uuid; n integer;
  v_aud text := lower(btrim(coalesce(p_audience, ''))); v_pri text := coalesce(nullif(lower(btrim(coalesce(p_priority, ''))), ''), 'normal');
begin
  v_aud := case
    when v_aud in ('', 'everyone') then 'all'
    when v_aud in ('admin', 'admins', 'teacher', 'teachers') then 'staff'
    when v_aud = 'student' and p_student_id is null then 'students'
    else v_aud end;
  if v_aud not in ('all','students','staff','class','student') then raise exception using message = 'BAD_AUDIENCE', errcode = '22023'; end if;
  if v_pri not in ('normal','important','critical') then raise exception using message = 'BAD_PRIORITY', errcode = '22023'; end if;
  if p_expires_at is not null and p_expires_at <= now() then raise exception using message = 'EXPIRY_IN_PAST', errcode = '22023'; end if;
  insert into public.notices (school_id, title, body, priority, audience, class_id, student_id, pinned, created_by, expires_at)
  values (sid, p_title, p_body, v_pri, v_aud,
          case when v_aud = 'class' then p_class_id end, case when v_aud = 'student' then p_student_id end,
          coalesce(p_pinned, false), auth.uid(), p_expires_at)
  returning id into nid;
  select count(*) into n from public.alerts where ref_kind = 'notice' and ref_id = nid;
  return jsonb_build_object('ok', true, 'notice_id', nid, 'priority', v_pri, 'audience', v_aud, 'recipients', n, 'email_queued', n > 0);
end $$;

create or replace function public.astro_delete_notice(p_notice_id uuid)
returns jsonb language plpgsql security definer set search_path = public as $$
declare n integer; c integer;
begin
  if auth.uid() is not null and not public.is_staff() then raise exception using message = 'NOT_STAFF', errcode = '42501'; end if;
  select count(*) into c from public.alerts where ref_kind = 'notice' and ref_id = p_notice_id and status = 'queued';
  delete from public.notices where id = p_notice_id and (auth.uid() is null or school_id = public.current_school_id());
  get diagnostics n = row_count;
  return jsonb_build_object('ok', true, 'deleted', n, 'emails_cancelled', case when n > 0 then c else 0 end);
end $$;

-- ---------- messages ----------
alter table public.messages add column if not exists direction text not null default 'to_student';
alter table public.messages drop constraint if exists messages_direction_check;
alter table public.messages add constraint messages_direction_check check (direction in ('to_student','from_student'));
alter table public.messages add column if not exists student_hidden_at timestamptz;
alter table public.messages alter column subject set default '';
create index if not exists messages_unread_idx on public.messages (school_id, student_id) where read_at is null;

-- direction is decided by the server (which RPC wrote the row), never by the client
create or replace function public.astro_messages_clean() returns trigger
language plpgsql security definer set search_path = public as $$
begin
  new.body := btrim(coalesce(new.body, ''));
  if new.body = '' then raise exception using message = 'EMPTY_MESSAGE', errcode = '22023'; end if;
  if length(new.body) > 4000 then raise exception using message = 'MESSAGE_TOO_LONG', errcode = '22023'; end if;
  new.subject := left(btrim(coalesce(new.subject, '')), 200);
  if tg_op = 'UPDATE' then
    if (new.direction, new.student_id, new.school_id) is distinct from (old.direction, old.student_id, old.school_id) then
      raise exception using message = 'MESSAGE_IMMUTABLE', errcode = '22023';
    end if;
    return new;
  end if;
  if not exists (select 1 from public.students st where st.id = new.student_id and st.school_id = new.school_id) then
    raise exception using message = 'STUDENT_NOT_FOUND', errcode = '22023';
  end if;
  new.direction := case when current_setting('astro.msg_direction', true) = 'from_student' then 'from_student' else 'to_student' end;
  if auth.uid() is not null then
    new.sender := auth.uid();
    new.read_at := null;
    new.student_hidden_at := null;
  end if;
  return new;
end $$;
drop trigger if exists messages_clean on public.messages;
create trigger messages_clean before insert or update on public.messages
  for each row execute function public.astro_messages_clean();

create or replace function public.astro_fanout_message() returns trigger
language plpgsql security definer set search_path = public as $$
begin
  if new.direction <> 'to_student' then return new; end if;   -- a parent is not e-mailed their own message
  insert into public.alerts (school_id, student_id, kind, channel, to_email, title, subject, body, ref_kind, ref_id)
  select st.school_id, st.id, 'message', 'email', st.guardian_email,
         coalesce(nullif(new.subject, ''), 'Message from ' || sc.name), coalesce(nullif(new.subject, ''), 'Message from ' || sc.name),
         new.body, 'message', new.id
  from public.students st join public.schools sc on sc.id = st.school_id
  where st.id = new.student_id and st.guardian_email is not null and sc.alert_emails;
  return new;
end $$;
drop trigger if exists messages_outbox_sync on public.messages;
create trigger messages_outbox_sync after update or delete on public.messages
  for each row execute function public.astro_outbox_sync();

-- 'viewer' members could read every conversation before
drop policy if exists messages_read on public.messages;
create policy messages_read on public.messages for select to authenticated using (
  (public.is_staff() and school_id = public.current_school_id())
  or (public.linked_student(student_id) and student_hidden_at is null));

-- student / parent -> school. p_client_id makes a retry after a network failure safe (no duplicate).
create or replace function public.astro_student_send_message(p_student_id uuid, p_body text, p_client_id uuid default null)
returns jsonb language plpgsql security definer set search_path = public as $$
declare st public.students; m public.messages; n integer; v_dup boolean := false;
begin
  select * into st from public.students where id = p_student_id and active;
  if st.id is null then raise exception using message = 'STUDENT_NOT_FOUND', errcode = '22023'; end if;
  if auth.uid() is not null and not public.linked_student(st.id) then raise exception using message = 'NOT_ALLOWED', errcode = '42501'; end if;
  if p_client_id is not null then
    select * into m from public.messages where id = p_client_id;
    if m.id is not null then
      if m.student_id <> st.id or m.direction <> 'from_student' then raise exception using message = 'ID_IN_USE', errcode = '22023'; end if;
      v_dup := true;
    end if;
  end if;
  if not v_dup then
    select count(*) into n from public.messages
     where student_id = st.id and direction = 'from_student' and created_at > now() - interval '10 minutes';
    if n >= 20 then return jsonb_build_object('ok', false, 'reason', 'RATE_LIMITED', 'retry_after_seconds', 600); end if;
    perform set_config('astro.msg_direction', 'from_student', true);
    insert into public.messages (id, school_id, student_id, sender, subject, body)
    values (coalesce(p_client_id, gen_random_uuid()), st.school_id, st.id, auth.uid(), '', p_body) returning * into m;
    perform set_config('astro.msg_direction', '', true);
  end if;
  return jsonb_build_object('ok', true, 'duplicate', v_dup, 'message', jsonb_build_object(
    'id', m.id, 'student_id', m.student_id, 'direction', m.direction, 'body', m.body, 'created_at', m.created_at, 'read_at', m.read_at));
end $$;

-- staff: deletes for everyone. sender of a from_student message: deletes it. receiver on the student side: hides it for the student side only.
create or replace function public.astro_delete_message(p_message_id uuid)
returns jsonb language plpgsql security definer set search_path = public as $$
declare m public.messages;
begin
  select * into m from public.messages where id = p_message_id for update;
  if m.id is null then return jsonb_build_object('ok', true, 'message_id', p_message_id, 'mode', 'already_gone'); end if;
  if auth.uid() is null or (public.is_staff() and m.school_id = public.current_school_id()) then
    delete from public.messages where id = m.id;
    return jsonb_build_object('ok', true, 'message_id', m.id, 'mode', 'deleted');
  end if;
  if not public.linked_student(m.student_id) then raise exception using message = 'NOT_ALLOWED', errcode = '42501'; end if;
  if m.direction = 'from_student' and m.sender = auth.uid() then
    delete from public.messages where id = m.id;
    return jsonb_build_object('ok', true, 'message_id', m.id, 'mode', 'deleted');
  end if;
  update public.messages set student_hidden_at = coalesce(student_hidden_at, now()) where id = m.id;
  return jsonb_build_object('ok', true, 'message_id', m.id, 'mode', 'hidden');
end $$;

-- only the receiving side can produce a read receipt
create or replace function public.astro_mark_message_read(p_message_id uuid)
returns jsonb language plpgsql security definer set search_path = public as $$
declare n integer; msg public.messages; v_staff boolean; v_linked boolean;
begin
  select * into msg from public.messages where id = p_message_id;
  if msg.id is null then return jsonb_build_object('ok', false, 'message_id', p_message_id, 'reason', 'MESSAGE_NOT_FOUND'); end if;
  v_staff := auth.uid() is not null and public.is_staff() and msg.school_id = public.current_school_id();
  v_linked := auth.uid() is not null and public.linked_student(msg.student_id);
  if auth.uid() is not null and not v_staff and not v_linked then raise exception using message = 'NOT_ALLOWED', errcode = '42501'; end if;
  update public.messages set read_at = now()
   where id = p_message_id and read_at is null
     and (auth.uid() is null or (direction = 'from_student' and v_staff) or (direction = 'to_student' and v_linked));
  get diagnostics n = row_count;
  return jsonb_build_object('ok', true, 'message_id', p_message_id,
    'read_at', (select read_at from public.messages where id = p_message_id), 'newly_read', n = 1);
end $$;

create or replace function public.astro_mark_thread_read(p_student_id uuid)
returns jsonb language plpgsql security definer set search_path = public as $$
declare st public.students; n integer; v_staff boolean; v_linked boolean;
begin
  select * into st from public.students where id = p_student_id;
  if st.id is null then raise exception using message = 'STUDENT_NOT_FOUND', errcode = '22023'; end if;
  v_staff := auth.uid() is not null and public.is_staff() and st.school_id = public.current_school_id();
  v_linked := auth.uid() is not null and public.linked_student(st.id);
  if auth.uid() is not null and not v_staff and not v_linked then raise exception using message = 'NOT_ALLOWED', errcode = '42501'; end if;
  update public.messages set read_at = now()
   where student_id = st.id and read_at is null
     and (auth.uid() is null or (direction = 'from_student' and v_staff) or (direction = 'to_student' and v_linked));
  get diagnostics n = row_count;
  return jsonb_build_object('ok', true, 'student_id', st.id, 'marked_read', n);
end $$;

-- admin DM inbox: one row per conversation, newest first, with unread counts
create or replace function public.astro_inbox(p_limit integer default 100, p_school_id uuid default null)
returns jsonb language plpgsql stable security definer set search_path = public as $$
declare sid uuid := public.astro_ctx_school(p_school_id, 'staff'); v_rows jsonb;
begin
  select jsonb_agg(o order by last_at desc) into v_rows from (
    select jsonb_build_object('student_id', st.id, 'roll_no', st.roll_no, 'name', st.full_name, 'class', c.name || '-' || c.section,
             'last_message', left(lm.body, 140), 'last_direction', lm.direction, 'last_at', lm.created_at,
             'unread', u.unread, 'total', u.total) as o, lm.created_at as last_at
    from public.students st
    join lateral (select m.body, m.direction, m.created_at from public.messages m where m.student_id = st.id order by m.created_at desc limit 1) lm on true
    join lateral (select count(*) filter (where m.direction = 'from_student' and m.read_at is null) as unread, count(*) as total
                  from public.messages m where m.student_id = st.id) u on true
    left join public.classes c on c.id = st.class_id
    where st.school_id = sid
    order by lm.created_at desc
    limit greatest(coalesce(p_limit, 100), 1)) q;
  return jsonb_build_object('ok', true,
    'unread_total', (select count(*) from public.messages m where m.school_id = sid and m.direction = 'from_student' and m.read_at is null),
    'conversations', coalesce(v_rows, '[]'::jsonb));
end $$;

-- student dashboard feed: critical -> important -> normal, newest first; dismissed notices and hidden messages left out
create or replace function public.astro_student_feed(p_student_id uuid, p_limit integer default 50)
returns jsonb language plpgsql security definer set search_path = public as $$
declare st public.students; nt jsonb; ms jsonb; v_staff boolean;
begin
  select * into st from public.students where id = p_student_id;
  if st.id is null then raise exception using message = 'STUDENT_NOT_FOUND', errcode = '22023'; end if;
  v_staff := auth.uid() is null or (public.is_staff() and st.school_id = public.current_school_id());
  if not v_staff and not public.linked_student(st.id) then raise exception using message = 'NOT_ALLOWED', errcode = '42501'; end if;

  select coalesce(jsonb_agg(o order by rk desc, pinned desc, published_at desc), '[]'::jsonb) into nt
  from (
    select jsonb_build_object('id', n.id, 'title', n.title, 'body', n.body, 'priority', n.priority, 'audience', n.audience,
             'pinned', n.pinned, 'published_at', n.publish_at, 'expires_at', n.expires_at, 'kind', 'notice') as o,
           case n.priority when 'critical' then 3 when 'important' then 2 else 1 end as rk,
           n.pinned, n.publish_at as published_at
    from public.notices n
    where n.school_id = st.school_id
      and n.publish_at <= now()
      and (n.expires_at is null or n.expires_at > now())
      and (n.audience in ('all','students')
           or (n.audience = 'class' and n.class_id = st.class_id)
           or (n.audience = 'student' and n.student_id = st.id))
      and not exists (select 1 from public.notice_dismissals nd where nd.notice_id = n.id and nd.user_id = auth.uid())
    order by 2 desc, n.publish_at desc
    limit greatest(coalesce(p_limit, 50), 1)) q;

  select coalesce(jsonb_agg(o order by created_at desc), '[]'::jsonb) into ms
  from (
    select jsonb_build_object('id', m.id, 'direction', m.direction, 'subject', m.subject, 'body', m.body,
             'read_at', m.read_at, 'created_at', m.created_at, 'kind', 'message') as o, m.created_at
    from public.messages m
    where m.student_id = st.id and (v_staff or m.student_hidden_at is null)
    order by m.created_at desc
    limit greatest(coalesce(p_limit, 50), 1)) q;

  return jsonb_build_object('ok', true,
    'student', jsonb_build_object('id', st.id, 'roll_no', st.roll_no, 'full_name', st.full_name),
    'class_id', st.class_id,
    'unread_messages', (select count(*) from public.messages where student_id = st.id and direction = 'to_student' and read_at is null and student_hidden_at is null),
    'notices', nt, 'messages', ms,
    'count', jsonb_array_length(nt) + jsonb_array_length(ms));
end $$;

revoke all on function public.astro_notices_clean(), public.astro_messages_clean(), public.astro_outbox_sync() from public, anon, authenticated;
revoke all on function public.astro_dismiss_notice(uuid, boolean),
  public.astro_post_notice(text, text, text, text, uuid, uuid, boolean, timestamptz, uuid), public.astro_delete_notice(uuid),
  public.astro_student_send_message(uuid, text, uuid), public.astro_delete_message(uuid),
  public.astro_mark_thread_read(uuid), public.astro_inbox(integer, uuid) from public, anon;
grant execute on function public.astro_dismiss_notice(uuid, boolean),
  public.astro_post_notice(text, text, text, text, uuid, uuid, boolean, timestamptz, uuid), public.astro_delete_notice(uuid),
  public.astro_student_send_message(uuid, text, uuid), public.astro_delete_message(uuid),
  public.astro_mark_thread_read(uuid), public.astro_inbox(integer, uuid) to authenticated;
