-- 0016 access and identity
-- Tenant-scoped visibility, parent/student read access to what the calendar needs,
-- admin-only settings and student deletion, card/student input hygiene,
-- and the RPCs that give people their roles.

create or replace function public.linked_school(p_school uuid) returns boolean
language sql stable security definer set search_path = public as $$
  select exists (select 1 from public.student_links l join public.students s on s.id = l.student_id
                 where l.user_id = auth.uid() and s.school_id = p_school) $$;
revoke all on function public.linked_school(uuid) from public, anon;
grant execute on function public.linked_school(uuid) to authenticated;

-- members / links: staff could previously read rows of every school
drop policy if exists members_read_self on public.members;
drop policy if exists members_read on public.members;
create policy members_read on public.members for select to authenticated
  using (user_id = auth.uid() or (public.is_staff() and school_id = public.current_school_id()));

drop policy if exists student_links_self on public.student_links;
drop policy if exists student_links_read on public.student_links;
create policy student_links_read on public.student_links for select to authenticated
  using (user_id = auth.uid() or (public.is_staff() and exists (
    select 1 from public.students s where s.id = student_links.student_id and s.school_id = public.current_school_id())));

-- school settings: admin only (teachers could change timings before)
drop policy if exists schools_write on public.schools;
create policy schools_write on public.schools for update to authenticated
  using (id = public.current_school_id() and public.is_admin())
  with check (id = public.current_school_id() and public.is_admin());

-- students / guardians have no members row, so they could not read the school,
-- their class or the holiday list -> the calendar could never paint a holiday
drop policy if exists schools_read_linked on public.schools;
create policy schools_read_linked on public.schools for select to authenticated using (public.linked_school(id));
drop policy if exists school_holidays_read_linked on public.school_holidays;
create policy school_holidays_read_linked on public.school_holidays for select to authenticated using (public.linked_school(school_id));
drop policy if exists classes_read_linked on public.classes;
create policy classes_read_linked on public.classes for select to authenticated
  using (exists (select 1 from public.student_links l join public.students s on s.id = l.student_id
                 where l.user_id = auth.uid() and s.class_id = classes.id));

-- deleting a student cascades to the whole attendance history: admin only
drop policy if exists students_write on public.students;
drop policy if exists students_insert on public.students;
drop policy if exists students_update on public.students;
drop policy if exists students_delete on public.students;
create policy students_insert on public.students for insert to authenticated
  with check (school_id = public.current_school_id() and public.is_staff());
create policy students_update on public.students for update to authenticated
  using (school_id = public.current_school_id() and public.is_staff())
  with check (school_id = public.current_school_id() and public.is_staff());
create policy students_delete on public.students for delete to authenticated
  using (school_id = public.current_school_id() and public.is_admin());

-- TRUNCATE ignores RLS; nothing in the app needs these
revoke truncate, references, trigger on all tables in schema public from anon, authenticated;

-- a school must never lose its last admin through the dashboard
create or replace function public.astro_members_guard() returns trigger
language plpgsql security definer set search_path = public as $$
begin
  if auth.uid() is null then return coalesce(new, old); end if;
  if old.role = 'admin' and (tg_op = 'DELETE' or new.role <> 'admin' or new.school_id <> old.school_id)
     and not exists (select 1 from public.members m where m.school_id = old.school_id and m.role = 'admin' and m.user_id <> old.user_id) then
    raise exception using message = 'LAST_ADMIN', errcode = '42501';
  end if;
  return coalesce(new, old);
end $$;
drop trigger if exists members_guard on public.members;
create trigger members_guard before update or delete on public.members
  for each row execute function public.astro_members_guard();

-- cards typed by hand ("a1:b2:c3:d4") must match what the reader sends ("A1B2C3D4")
create or replace function public.astro_cards_normalise() returns trigger
language plpgsql security definer set search_path = public as $$
begin
  new.card_uid := public.astro_norm_uid(new.card_uid);
  if new.card_uid is null or new.card_uid !~ '^[0-9A-F]{8,20}$' then
    raise exception using message = 'BAD_CARD_UID', errcode = '22023';
  end if;
  return new;
end $$;
drop trigger if exists rfid_cards_normalise on public.rfid_cards;
create trigger rfid_cards_normalise before insert or update of card_uid on public.rfid_cards
  for each row execute function public.astro_cards_normalise();

-- students: trimmed fields, blank -> null, lower-case email, one fingerprint number per school
create or replace function public.astro_students_clean() returns trigger
language plpgsql set search_path = public as $$
begin
  new.roll_no := btrim(coalesce(new.roll_no, ''));
  new.full_name := btrim(regexp_replace(coalesce(new.full_name, ''), '\s+', ' ', 'g'));
  if new.roll_no = '' then raise exception using message = 'ROLL_REQUIRED', errcode = '22023'; end if;
  if new.full_name = '' then raise exception using message = 'NAME_REQUIRED', errcode = '22023'; end if;
  new.guardian_name := nullif(btrim(new.guardian_name), '');
  new.guardian_phone := nullif(btrim(new.guardian_phone), '');
  new.guardian_email := nullif(lower(btrim(new.guardian_email)), '');
  if new.guardian_email is not null and new.guardian_email !~ '^[^@\s]+@[^@\s]+\.[^@\s]+$' then
    raise exception using message = 'BAD_EMAIL', errcode = '22023';
  end if;
  return new;
end $$;
drop trigger if exists students_clean on public.students;
create trigger students_clean before insert or update on public.students
  for each row execute function public.astro_students_clean();
create unique index if not exists students_fingerprint_uidx on public.students (school_id, fingerprint_id) where fingerprint_id is not null;

-- who am I: lets the web app route to the admin or the student dashboard
create or replace function public.astro_whoami() returns jsonb
language sql stable security definer set search_path = public as $$
  select jsonb_build_object(
    'user_id', auth.uid(),
    'role', coalesce((select m.role from public.members m where m.user_id = auth.uid()),
                     case when exists (select 1 from public.student_links l where l.user_id = auth.uid()) then 'student' else 'none' end),
    'school', (select jsonb_build_object('id', s.id, 'name', s.name, 'code', s.code, 'timezone', s.timezone)
               from public.schools s
               where s.id = coalesce(public.current_school_id(),
                 (select st.school_id from public.student_links l join public.students st on st.id = l.student_id where l.user_id = auth.uid() limit 1))),
    'students', coalesce((select jsonb_agg(jsonb_build_object('id', st.id, 'roll_no', st.roll_no, 'full_name', st.full_name,
                            'relation', l.relation, 'class', c.name || '-' || c.section) order by st.full_name)
                          from public.student_links l join public.students st on st.id = l.student_id
                          left join public.classes c on c.id = st.class_id
                          where l.user_id = auth.uid()), '[]'::jsonb)) $$;

-- give a signed-up user a staff role (admin only; SQL editor may pass p_school_id to create the first admin)
create or replace function public.astro_add_member(p_email text, p_role text default 'teacher', p_school_id uuid default null)
returns jsonb language plpgsql security definer set search_path = public as $$
declare sid uuid; uid uuid; v_role text := lower(btrim(coalesce(p_role, 'teacher'))); cur public.members;
begin
  if auth.uid() is not null then
    if not public.is_admin() then raise exception using message = 'NOT_ADMIN', errcode = '42501'; end if;
    sid := public.current_school_id();
  else
    sid := p_school_id;
  end if;
  if sid is null or not exists (select 1 from public.schools where id = sid) then raise exception using message = 'SCHOOL_REQUIRED', errcode = '22023'; end if;
  if v_role not in ('admin','teacher','viewer') then raise exception using message = 'BAD_ROLE', errcode = '22023'; end if;
  select u.id into uid from auth.users u where lower(u.email) = lower(btrim(coalesce(p_email, ''))) limit 1;
  if uid is null then return jsonb_build_object('ok', false, 'reason', 'USER_NOT_FOUND', 'hint', 'The person must sign up first'); end if;
  select * into cur from public.members where user_id = uid;
  if cur.user_id is not null and cur.school_id <> sid then return jsonb_build_object('ok', false, 'reason', 'MEMBER_OF_OTHER_SCHOOL'); end if;
  if cur.user_id is null then
    insert into public.members (user_id, school_id, role) values (uid, sid, v_role);
  else
    update public.members set role = v_role where user_id = uid;
  end if;
  return jsonb_build_object('ok', true, 'user_id', uid, 'role', v_role, 'was', cur.role);
end $$;

-- connect a signed-up user to a student as 'self' or 'guardian' (staff)
create or replace function public.astro_link_student(p_email text, p_student_id uuid, p_relation text default 'guardian', p_school_id uuid default null)
returns jsonb language plpgsql security definer set search_path = public as $$
declare sid uuid; uid uuid; st public.students; v_rel text := lower(btrim(coalesce(p_relation, 'guardian')));
begin
  if auth.uid() is not null then
    if not public.is_staff() then raise exception using message = 'NOT_STAFF', errcode = '42501'; end if;
    sid := public.current_school_id();
  else
    sid := p_school_id;
  end if;
  if v_rel not in ('self','guardian') then raise exception using message = 'BAD_RELATION', errcode = '22023'; end if;
  select * into st from public.students where id = p_student_id and (sid is null or school_id = sid);
  if st.id is null or (auth.uid() is not null and sid is null) then raise exception using message = 'STUDENT_NOT_FOUND', errcode = '22023'; end if;
  select u.id into uid from auth.users u where lower(u.email) = lower(btrim(coalesce(p_email, ''))) limit 1;
  if uid is null then return jsonb_build_object('ok', false, 'reason', 'USER_NOT_FOUND', 'hint', 'The person must sign up first'); end if;
  insert into public.student_links (user_id, student_id, relation) values (uid, st.id, v_rel)
  on conflict (user_id, student_id) do update set relation = excluded.relation;
  return jsonb_build_object('ok', true, 'user_id', uid, 'student_id', st.id, 'student', st.full_name, 'relation', v_rel);
end $$;

create or replace function public.astro_unlink_student(p_user_id uuid, p_student_id uuid)
returns jsonb language plpgsql security definer set search_path = public as $$
declare n integer;
begin
  if auth.uid() is not null and not (public.is_staff() and exists (
       select 1 from public.students s where s.id = p_student_id and s.school_id = public.current_school_id())) then
    raise exception using message = 'NOT_ALLOWED', errcode = '42501';
  end if;
  delete from public.student_links where user_id = p_user_id and student_id = p_student_id;
  get diagnostics n = row_count;
  return jsonb_build_object('ok', true, 'removed', n);
end $$;

revoke all on function public.astro_members_guard(), public.astro_cards_normalise(), public.astro_students_clean() from public, anon, authenticated;
revoke all on function public.astro_whoami(), public.astro_add_member(text, text, uuid),
  public.astro_link_student(text, uuid, text, uuid), public.astro_unlink_student(uuid, uuid) from public, anon;
grant execute on function public.astro_whoami(), public.astro_add_member(text, text, uuid),
  public.astro_link_student(text, uuid, text, uuid), public.astro_unlink_student(uuid, uuid) to authenticated;
