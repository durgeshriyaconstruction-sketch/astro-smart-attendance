-- ============================================================================
-- ASTRO SMART ATTENDANCE — 0010 tighten the RLS helper functions
--
-- current_school_id(), is_staff() and linked_student() were created in 0001 and
-- kept PostgreSQL's implicit GRANT EXECUTE TO PUBLIC, so `anon` could call them
-- even after 0006. They leak nothing (they return NULL / false without a JWT),
-- but the publishable key should reach exactly four functions, so revoke PUBLIC
-- and grant only `authenticated`, which is the role the RLS policies run as.
--
-- Verified afterwards: has_function_privilege('anon', …) is true for
-- astro_heartbeat, astro_lookup_card, astro_mark_attendance, astro_sync_batch
-- and false for everything else in schema public.
-- ============================================================================

revoke all on function public.current_school_id(), public.is_staff(),
                       public.linked_student(uuid)
  from public, anon;

grant execute on function public.current_school_id(), public.is_staff(),
                          public.linked_student(uuid)
  to authenticated;
