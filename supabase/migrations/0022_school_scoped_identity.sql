-- 0022_school_scoped_identity.sql
-- =====================================================================
-- Fix: role checks were not scoped to a school.
--
-- Before: is_staff() / is_admin() returned true if the user held that role in
-- *any* school, while current_school_id() returned an arbitrary membership
-- (no ORDER BY). A user who is admin in school A and viewer in school B could
-- therefore satisfy `school_id = current_school_id() AND is_admin()` and act as
-- an admin in the wrong school. Single-school installs never noticed; the
-- moment a second school exists it is a privilege bleed.
--
-- After: current_school_id() is deterministic (oldest membership), and the
-- role helpers only answer for that school. Overloads is_staff(uuid) /
-- is_admin(uuid) let callers that already know the school ask directly.
--
-- Every RLS policy already ANDs the role helper with
-- `school_id = current_school_id()`, so policies keep working unchanged.
-- =====================================================================

begin;

create or replace function public.current_school_id()
returns uuid
language sql
stable
security definer
set search_path = public
as $$
  select m.school_id
  from public.members m
  where m.user_id = auth.uid()
  order by m.created_at, m.school_id
  limit 1
$$;

create or replace function public.is_staff()
returns boolean
language sql
stable
security definer
set search_path = public
as $$
  select exists (
    select 1 from public.members m
    where m.user_id = auth.uid()
      and m.school_id = public.current_school_id()
      and m.role in ('admin', 'teacher')
  )
$$;

create or replace function public.is_admin()
returns boolean
language sql
stable
security definer
set search_path = public
as $$
  select exists (
    select 1 from public.members m
    where m.user_id = auth.uid()
      and m.school_id = public.current_school_id()
      and m.role = 'admin'
  )
$$;

-- Ask about a specific school instead of "my first school".
create or replace function public.is_staff(p_school uuid)
returns boolean
language sql
stable
security definer
set search_path = public
as $$
  select p_school is not null and exists (
    select 1 from public.members m
    where m.user_id = auth.uid()
      and m.school_id = p_school
      and m.role in ('admin', 'teacher')
  )
$$;

create or replace function public.is_admin(p_school uuid)
returns boolean
language sql
stable
security definer
set search_path = public
as $$
  select p_school is not null and exists (
    select 1 from public.members m
    where m.user_id = auth.uid()
      and m.school_id = p_school
      and m.role = 'admin'
  )
$$;

-- astro_ctx_school(): resolve the school once and check the role against that
-- same school. Behaviour is unchanged for a normal user; it now rejects the
-- admin-in-A/viewer-in-B case instead of silently allowing it.
create or replace function public.astro_ctx_school(p_school_id uuid, p_need text default 'staff')
returns uuid
language plpgsql
stable
security definer
set search_path = public
as $$
declare
  sid uuid;
  v_need text := lower(btrim(coalesce(p_need, 'staff')));
begin
  -- Service side (SQL editor, cron, secret key): the caller is trusted and
  -- must name the school explicitly.
  if auth.uid() is null then
    if p_school_id is null then
      raise exception using message = 'SCHOOL_REQUIRED', errcode = '22023';
    end if;
    return p_school_id;
  end if;

  sid := public.current_school_id();
  if sid is null then
    raise exception using message = 'NOT_A_MEMBER', errcode = '42501';
  end if;
  if v_need not in ('member', 'staff', 'admin') then
    raise exception using message = 'BAD_NEED', errcode = '22023';
  end if;
  if v_need = 'admin' and not public.is_admin(sid) then
    raise exception using message = 'NOT_ADMIN', errcode = '42501';
  end if;
  if v_need = 'staff' and not public.is_staff(sid) then
    raise exception using message = 'NOT_STAFF', errcode = '42501';
  end if;
  return sid;
end
$$;

-- These helpers exist for policies and for other SECURITY DEFINER functions.
-- The browser may call is_staff()/is_admin()/current_school_id() because RLS
-- evaluates them as the signed-in user; nothing else here is public.
revoke all on function public.is_staff(uuid) from public, anon;
revoke all on function public.is_admin(uuid) from public, anon;
revoke all on function public.astro_ctx_school(uuid, text) from public, anon, authenticated;
grant execute on function public.is_staff(uuid) to authenticated, service_role;
grant execute on function public.is_admin(uuid) to authenticated, service_role;
grant execute on function public.astro_ctx_school(uuid, text) to service_role;

commit;
