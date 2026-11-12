-- 0012: keep the outbox private, and stop anyone marking somebody else's mail read.
--
-- 0011 unified alerts into an outbox (kinds notice/message). Two loose ends:
--
--   1. `alerts_read` was `school_id = current_school_id()`, so any *member* who is
--      not staff (a parent account kept in `public.members`, role 'parent') could
--      read every row in the outbox — other families' addresses, phone numbers and
--      message bodies. Read of the outbox is now staff-only, plus a guardian's own
--      children's rows so the parent screen can show delivery state.
--
--   2. `astro_mark_message_read()` updated on id alone: any signed-in user could
--      mark any message in the database read. It now requires the caller to be
--      staff of that school or a guardian/self link to that student.

-- 1. outbox visibility -------------------------------------------------------

drop policy if exists alerts_read on public.alerts;
create policy alerts_read on public.alerts for select to authenticated using (
  -- staff see the whole school outbox (delivery dashboard)
  (public.is_staff() and school_id = public.current_school_id())
  -- a guardian sees only the rows addressed to their own children
  or exists (
    select 1
    from public.student_links l
    join public.students s on s.id = l.student_id
    where l.user_id = auth.uid()
      and s.id = alerts.student_id
      and s.school_id = alerts.school_id
  )
);

-- 2. mark-read guard ---------------------------------------------------------

create or replace function public.astro_mark_message_read(p_message_id uuid)
returns jsonb
language plpgsql
security definer
set search_path = public
as $$
declare
  n integer;
  msg public.messages;
begin
  select * into msg from public.messages where id = p_message_id;

  if msg.id is null then
    return jsonb_build_object('ok', false, 'message_id', p_message_id, 'reason', 'MESSAGE_NOT_FOUND');
  end if;

  -- service role / cron (no end user) is allowed; end users must be entitled
  if auth.uid() is not null then
    if not (
      (public.is_staff() and msg.school_id = public.current_school_id())
      or exists (
        select 1 from public.student_links l
        where l.user_id = auth.uid() and l.student_id = msg.student_id
      )
    ) then
      raise exception using message = 'NOT_ALLOWED', errcode = '42501';
    end if;
  end if;

  update public.messages
     set read_at = coalesce(read_at, now())
   where id = p_message_id and read_at is null;

  get diagnostics n = row_count;

  return jsonb_build_object(
    'ok', true,
    'message_id', p_message_id,
    'read_at', (select read_at from public.messages where id = p_message_id),
    'newly_read', n = 1
  );
end $$;

revoke all on function public.astro_mark_message_read(uuid) from anon, public;
grant execute on function public.astro_mark_message_read(uuid) to authenticated;

-- 3. one call the parent screen can make ------------------------------------
-- Returns everything that student's family should see, newest first, already
-- filtered by audience so the client never has to join three tables.

create or replace function public.astro_student_feed(p_student_id uuid, p_limit integer default 50)
returns jsonb
language plpgsql
security definer
set search_path = public
as $$
declare
  st public.students;
  notices jsonb;
  msgs jsonb;
  feed jsonb;
begin
  select * into st from public.students where id = p_student_id;

  if st.id is null then
    raise exception using message = 'STUDENT_NOT_FOUND', errcode = '22023';
  end if;

  if auth.uid() is not null
     and not (
       (public.is_staff() and st.school_id = public.current_school_id())
       or exists (select 1 from public.student_links l
                  where l.user_id = auth.uid() and l.student_id = st.id)
     ) then
    raise exception using message = 'NOT_ALLOWED', errcode = '42501';
  end if;

  select coalesce(jsonb_agg(x order by x_pinned desc, x_at desc), '[]'::jsonb) into notices
  from (
    select n.id, n.title, n.body, n.pinned as x_pinned, n.publish_at as x_at,
           jsonb_build_object('id', n.id, 'title', n.title, 'body', n.body,
                              'pinned', n.pinned, 'published_at', n.publish_at,
                              'expires_at', n.expires_at, 'kind', 'notice') as x
    from public.notices n
    where n.school_id = st.school_id
      and n.publish_at <= now()
      and (n.expires_at is null or n.expires_at > now())
      and (n.audience = 'all'
           or (n.audience = 'class' and n.class_id = st.class_id)
           or (n.audience = 'student' and n.student_id = st.id))
    order by n.publish_at desc
    limit greatest(coalesce(p_limit, 50), 1)
  ) q;

  select coalesce(jsonb_agg(jsonb_build_object(
           'id', m.id, 'subject', m.subject, 'body', m.body,
           'read_at', m.read_at, 'created_at', m.created_at, 'kind', 'message')
         order by m.created_at desc), '[]'::jsonb) into msgs
  from (
    select * from public.messages
    where student_id = st.id
    order by created_at desc
    limit greatest(coalesce(p_limit, 50), 1)
  ) m;

  feed := notices || msgs;

  return jsonb_build_object(
    'ok', true,
    'student', jsonb_build_object('id', st.id, 'roll_no', st.roll_no, 'full_name', st.full_name),
    'unread_messages', (select count(*) from public.messages where student_id = st.id and read_at is null),
    'notices', notices,
    'messages', msgs,
    'count', jsonb_array_length(feed)
  );
end $$;

revoke all on function public.astro_student_feed(uuid, integer) from anon, public;
grant execute on function public.astro_student_feed(uuid, integer) to authenticated;
