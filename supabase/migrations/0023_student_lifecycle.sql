-- 0023_student_lifecycle.sql
-- =====================================================================
-- Fixes for the "add / edit / remove a student" flow the admin screen needs.
--
-- 1. astro_save_student() erased guardian contact details on every edit that
--    did not repeat them: the UPDATE assigned p_guardian_* directly, so
--    renaming a class silently wiped guardian_email/phone/name. The update is
--    now partial — NULL means "leave it alone", '' means "clear it".
-- 2. A student could only be deleted, and `students -> attendance` was ON
--    DELETE CASCADE: one click in the table editor destroyed the whole
--    attendance history (the record the school must keep). Deletion is now
--    refused once history exists; astro_archive_student() is the supported
--    path (deactivate + release cards/fingerprints + cancel queued mail).
-- 3. There was no way to create a class, release a lost card, or remove a
--    dashboard user. Added astro_save_class / astro_delete_class,
--    astro_unassign_card and astro_remove_member.
-- =====================================================================

begin;

-- ---------------------------------------------------------------------
-- 1. Classes
-- ---------------------------------------------------------------------
create or replace function public.astro_save_class(
  p_name text,
  p_section text,
  p_teacher text default null,
  p_class_id uuid default null,
  p_school_id uuid default null
) returns jsonb
language plpgsql
security definer
set search_path = public
as $$
declare
  sid uuid := public.astro_ctx_school(p_school_id, 'staff');
  c public.classes;
  v_name text := nullif(btrim(coalesce(p_name, '')), '');
  v_section text := upper(nullif(btrim(coalesce(p_section, '')), ''));
begin
  if p_class_id is null and (v_name is null or v_section is null) then
    raise exception using message = 'NAME_AND_SECTION_REQUIRED', errcode = '22023';
  end if;
  begin
    if p_class_id is null then
      insert into public.classes (school_id, name, section, teacher)
      values (sid, v_name, v_section, nullif(btrim(coalesce(p_teacher, '')), ''))
      returning * into c;
    else
      update public.classes set
        name = coalesce(v_name, name),
        section = coalesce(v_section, section),
        teacher = case when p_teacher is null then teacher
                       else nullif(btrim(p_teacher), '') end
      where id = p_class_id and school_id = sid
      returning * into c;
      if c.id is null then
        raise exception using message = 'CLASS_NOT_FOUND', errcode = '22023';
      end if;
    end if;
  exception when unique_violation then
    return jsonb_build_object('ok', false, 'reason', 'CLASS_EXISTS',
      'name', v_name, 'section', v_section);
  end;
  return jsonb_build_object('ok', true, 'class_id', c.id, 'name', c.name,
    'section', c.section, 'label', c.name || '-' || c.section, 'teacher', c.teacher,
    'created', p_class_id is null,
    'students', (select count(*) from public.students st where st.class_id = c.id));
end
$$;

create or replace function public.astro_delete_class(
  p_class_id uuid,
  p_school_id uuid default null
) returns jsonb
language plpgsql
security definer
set search_path = public
as $$
declare
  sid uuid := public.astro_ctx_school(p_school_id, 'admin');
  c public.classes;
  n integer;
begin
  select * into c from public.classes where id = p_class_id and school_id = sid;
  if c.id is null then raise exception using message = 'CLASS_NOT_FOUND', errcode = '22023'; end if;
  -- classes -> students is ON DELETE SET NULL, which would silently orphan
  -- every student in the class. Refuse instead.
  select count(*) into n from public.students st where st.class_id = c.id;
  if n > 0 then
    raise exception using message = 'CLASS_NOT_EMPTY', errcode = '22023',
      hint = 'Move those students to another class first'; 
  end if;
  delete from public.classes where id = c.id;
  return jsonb_build_object('ok', true, 'class_id', c.id, 'deleted', 1);
end
$$;

-- ---------------------------------------------------------------------
-- 2. astro_save_student() — partial update, no data loss
-- ---------------------------------------------------------------------
create or replace function public.astro_save_student(
  p_roll_no text,
  p_full_name text,
  p_class_id uuid default null,
  p_guardian_name text default null,
  p_guardian_email text default null,
  p_guardian_phone text default null,
  p_card_uid text default null,
  p_fingerprint_slot integer default null,
  p_device_code text default null,
  p_student_id uuid default null,
  p_school_id uuid default null
) returns jsonb
language plpgsql
security definer
set search_path = public
as $$
declare
  sid uuid := public.astro_ctx_school(p_school_id, 'staff');
  st public.students;
  card public.rfid_cards;
  d public.devices;
  uid text := public.astro_norm_uid(p_card_uid);
  v_roll text := nullif(btrim(coalesce(p_roll_no, '')), '');
  v_name text := nullif(regexp_replace(btrim(coalesce(p_full_name, '')), '\s+', ' ', 'g'), '');
  v_email text := nullif(lower(btrim(coalesce(p_guardian_email, ''))), '');
begin
  -- ---- validation -------------------------------------------------
  if p_student_id is null then
    if v_roll is null then raise exception using message = 'ROLL_REQUIRED', errcode = '22023'; end if;
    if v_name is null then raise exception using message = 'NAME_REQUIRED', errcode = '22023'; end if;
  end if;
  if v_email is not null and v_email !~ '^[^@\s]+@[^@\s]+\.[^@\s]+$' then
    raise exception using message = 'BAD_EMAIL', errcode = '22023';
  end if;
  if p_class_id is not null and not exists (
       select 1 from public.classes c where c.id = p_class_id and c.school_id = sid) then
    raise exception using message = 'CLASS_NOT_FOUND', errcode = '22023';
  end if;

  -- ---- card conflicts ---------------------------------------------
  if uid is not null then
    if uid !~ '^[0-9A-F]{8,20}$' then raise exception using message = 'BAD_CARD_UID', errcode = '22023'; end if;
    select * into card from public.rfid_cards where card_uid = uid;
    if card.id is not null and card.school_id <> sid then
      return jsonb_build_object('ok', false, 'reason', 'CARD_IN_USE');
    end if;
    if card.student_id is not null and card.student_id is distinct from p_student_id then
      return jsonb_build_object('ok', false, 'reason', 'CARD_IN_USE',
        'owner', (select s2.full_name || ' (' || s2.roll_no || ')' from public.students s2 where s2.id = card.student_id));
    end if;
  end if;

  -- ---- fingerprint conflicts --------------------------------------
  if p_fingerprint_slot is not null then
    if p_fingerprint_slot not between 1 and 999 then raise exception using message = 'BAD_SLOT', errcode = '22023'; end if;
    if nullif(btrim(coalesce(p_device_code, '')), '') is not null then
      select * into d from public.devices where device_code = upper(btrim(p_device_code)) and school_id = sid;
      if d.id is null then raise exception using message = 'DEVICE_NOT_FOUND', errcode = '22023'; end if;
    end if;
    if exists (select 1 from public.students s2
                where s2.school_id = sid and s2.fingerprint_id = p_fingerprint_slot
                  and s2.id is distinct from p_student_id)
       or (d.id is not null and exists (select 1 from public.fingerprints f
                where f.device_id = d.id and f.slot = p_fingerprint_slot
                  and f.student_id is distinct from p_student_id)) then
      return jsonb_build_object('ok', false, 'reason', 'FINGERPRINT_IN_USE');
    end if;
  end if;

  -- ---- write ------------------------------------------------------
  begin
    if p_student_id is null then
      insert into public.students (school_id, class_id, roll_no, full_name, guardian_name, guardian_email, guardian_phone)
      values (sid, p_class_id, v_roll, v_name,
              nullif(btrim(coalesce(p_guardian_name, '')), ''),
              v_email,
              nullif(btrim(coalesce(p_guardian_phone, '')), ''))
      returning * into st;
    else
      -- NULL = keep what is stored; '' = clear it. A rename can no longer
      -- erase the guardian's email.
      update public.students set
        class_id = coalesce(p_class_id, class_id),
        roll_no = coalesce(v_roll, roll_no),
        full_name = coalesce(v_name, full_name),
        guardian_name = case when p_guardian_name is null then guardian_name
                             else nullif(btrim(p_guardian_name), '') end,
        guardian_email = case when p_guardian_email is null then guardian_email
                              else nullif(lower(btrim(p_guardian_email)), '') end,
        guardian_phone = case when p_guardian_phone is null then guardian_phone
                              else nullif(btrim(p_guardian_phone), '') end
      where id = p_student_id and school_id = sid
      returning * into st;
      if st.id is null then raise exception using message = 'STUDENT_NOT_FOUND', errcode = '22023'; end if;
    end if;
  exception when unique_violation then
    return jsonb_build_object('ok', false, 'reason', 'ROLL_EXISTS', 'roll_no', v_roll);
  end;

  -- ---- card / fingerprint assignment ------------------------------
  if uid is not null then
    if card.id is null then
      insert into public.rfid_cards (school_id, student_id, card_uid) values (sid, st.id, uid);
    else
      update public.rfid_cards set student_id = st.id, active = true, assigned_at = now() where id = card.id;
    end if;
  end if;

  if p_fingerprint_slot is not null then
    update public.students set fingerprint_id = p_fingerprint_slot where id = st.id returning * into st;
    if d.id is not null then
      delete from public.fingerprints where device_id = d.id and student_id = st.id and slot <> p_fingerprint_slot;
      insert into public.fingerprints (device_id, school_id, slot, student_id)
      values (d.id, sid, p_fingerprint_slot, st.id)
      on conflict (device_id, slot) do update set student_id = excluded.student_id, enrolled_at = now();
    end if;
  end if;

  return jsonb_build_object('ok', true, 'created', p_student_id is null,
    'student', jsonb_build_object('id', st.id, 'roll_no', st.roll_no, 'full_name', st.full_name,
      'class_id', st.class_id, 'active', st.active,
      'guardian_name', st.guardian_name, 'guardian_email', st.guardian_email,
      'guardian_phone', st.guardian_phone, 'fingerprint_id', st.fingerprint_id),
    'cards', coalesce((select jsonb_agg(rc.card_uid) from public.rfid_cards rc where rc.student_id = st.id and rc.active), '[]'::jsonb));
end
$$;

-- ---------------------------------------------------------------------
-- 3. Archive instead of delete
-- ---------------------------------------------------------------------
create or replace function public.astro_archive_student(
  p_student_id uuid,
  p_active boolean default false,
  p_school_id uuid default null
) returns jsonb
language plpgsql
security definer
set search_path = public
as $$
declare
  sid uuid := public.astro_ctx_school(p_school_id, 'staff');
  st public.students;
  n_cards integer := 0;
  n_fp integer := 0;
  n_alerts integer := 0;
  n_leaves integer := 0;
begin
  select * into st from public.students where id = p_student_id and school_id = sid;
  if st.id is null then raise exception using message = 'STUDENT_NOT_FOUND', errcode = '22023'; end if;

  if coalesce(p_active, false) then
    update public.students set active = true where id = st.id returning * into st;
    return jsonb_build_object('ok', true, 'student_id', st.id, 'active', true,
      'cards_released', 0, 'fingerprints_released', 0, 'emails_cancelled', 0);
  end if;

  update public.students set active = false, fingerprint_id = null
   where id = st.id returning * into st;

  update public.rfid_cards set active = false, student_id = null where student_id = st.id;
  get diagnostics n_cards = row_count;

  delete from public.fingerprints where student_id = st.id;
  get diagnostics n_fp = row_count;

  update public.alerts set status = 'skipped', last_error = 'student_archived'
   where student_id = st.id and status = 'queued';
  get diagnostics n_alerts = row_count;

  if to_regclass('public.leave_requests') is not null then
    execute 'update public.leave_requests set status = ''cancelled'', decided_at = now(),
                    decision_note = coalesce(decision_note, ''student archived'')
              where student_id = $1 and status = ''pending''' using st.id;
    get diagnostics n_leaves = row_count;
    n_leaves := coalesce(n_leaves, 0);
  end if;

  return jsonb_build_object('ok', true, 'student_id', st.id, 'active', false,
    'cards_released', n_cards, 'fingerprints_released', n_fp,
    'emails_cancelled', n_alerts, 'leaves_cancelled', n_leaves);
end
$$;

create or replace function public.astro_unassign_card(
  p_card_uid text,
  p_school_id uuid default null
) returns jsonb
language plpgsql
security definer
set search_path = public
as $$
declare
  sid uuid := public.astro_ctx_school(p_school_id, 'staff');
  uid text := public.astro_norm_uid(p_card_uid);
  c public.rfid_cards;
begin
  if uid is null or uid !~ '^[0-9A-F]{8,20}$' then
    raise exception using message = 'BAD_CARD_UID', errcode = '22023';
  end if;
  update public.rfid_cards set student_id = null, active = false
   where card_uid = uid and school_id = sid
   returning * into c;
  if c.id is null then raise exception using message = 'CARD_NOT_FOUND', errcode = '22023'; end if;
  return jsonb_build_object('ok', true, 'card_uid', c.card_uid, 'released', true);
end
$$;

-- ---------------------------------------------------------------------
-- 4. Members
-- ---------------------------------------------------------------------
create or replace function public.astro_remove_member(
  p_user_id uuid,
  p_school_id uuid default null
) returns jsonb
language plpgsql
security definer
set search_path = public
as $$
declare
  sid uuid := public.astro_ctx_school(p_school_id, 'admin');
  n integer;
begin
  delete from public.members where user_id = p_user_id and school_id = sid;
  get diagnostics n = row_count;
  if n = 0 then raise exception using message = 'MEMBER_NOT_FOUND', errcode = '22023'; end if;
  return jsonb_build_object('ok', true, 'user_id', p_user_id, 'removed', n);
end
$$;

-- ---------------------------------------------------------------------
-- 5. Protect attendance history
-- ---------------------------------------------------------------------
-- students -> attendance was ON DELETE CASCADE: deleting a student silently
-- deleted every attendance row of theirs. Keep the history.
alter table public.attendance drop constraint attendance_student_id_fkey;
alter table public.attendance
  add constraint attendance_student_id_fkey
  foreign key (student_id) references public.students(id) on delete restrict;

create or replace function public.astro_students_guard_delete()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
  if exists (select 1 from public.attendance a where a.student_id = old.id) then
    raise exception using message = 'STUDENT_HAS_ATTENDANCE', errcode = '22023',
      hint = 'Use astro_archive_student() to deactivate the student and keep the history';
  end if;
  return old;
end
$$;

drop trigger if exists students_guard_delete on public.students;
create trigger students_guard_delete
  before delete on public.students
  for each row execute function public.astro_students_guard_delete();

-- ---------------------------------------------------------------------
-- 6. Grants
-- ---------------------------------------------------------------------
revoke all on function public.astro_save_class(text, text, text, uuid, uuid) from public, anon;
revoke all on function public.astro_delete_class(uuid, uuid) from public, anon;
revoke all on function public.astro_archive_student(uuid, boolean, uuid) from public, anon;
revoke all on function public.astro_unassign_card(text, uuid) from public, anon;
revoke all on function public.astro_remove_member(uuid, uuid) from public, anon;
revoke all on function public.astro_students_guard_delete() from public, anon, authenticated;

grant execute on function public.astro_save_class(text, text, text, uuid, uuid) to authenticated, service_role;
grant execute on function public.astro_delete_class(uuid, uuid) to authenticated, service_role;
grant execute on function public.astro_archive_student(uuid, boolean, uuid) to authenticated, service_role;
grant execute on function public.astro_unassign_card(text, uuid) to authenticated, service_role;
grant execute on function public.astro_remove_member(uuid, uuid) to authenticated, service_role;

commit;
