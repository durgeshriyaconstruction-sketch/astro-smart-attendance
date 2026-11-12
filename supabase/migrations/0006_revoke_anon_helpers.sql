-- ============================================================================
-- ASTRO SMART ATTENDANCE — 0006 revoke accidental anon grants
--
-- WHY THIS EXISTS
-- Supabase sets ALTER DEFAULT PRIVILEGES so that every function created in
-- `public` by `postgres` gets EXECUTE granted explicitly to anon, authenticated
-- and service_role. `revoke ... from public` removes the PUBLIC pseudo-role but
-- NOT those explicit grants, so after 0001-0005 the publishable key could still
-- call every helper - including astro_close_day() (mark the whole school absent
-- for any date) and astro_prune_events() (delete device_events).
--
-- Fix: revoke from anon explicitly, then re-grant only what the terminal needs.
-- Verified afterwards with has_function_privilege('anon', ...).
-- ============================================================================

revoke all on function
  public.astro_close_day(date),
  public.astro_prune_events(integer),
  public.astro_provision_device(text, text, text, text),
  public.astro_rotate_device_secret(text),
  public.astro_verify_device(text, text),
  public.astro_sha256_hex(text),
  public.astro_norm_uid(text),
  public.astro_try_uuid(text),
  public.astro_try_ts(text),
  public.astro_touch_updated_at()
from anon, public;

-- real dashboard users keep the end-of-day job (the function checks is_staff())
revoke all on function public.astro_close_day(date) from authenticated;
grant execute on function public.astro_close_day(date) to authenticated;

revoke all on function public.astro_rotate_device_secret(text) from authenticated;
grant execute on function public.astro_rotate_device_secret(text) to authenticated;

revoke all on function public.astro_provision_device(text, text, text, text) from authenticated;
grant execute on function public.astro_provision_device(text, text, text, text) to authenticated;

-- the device API is the only surface anon may touch
revoke all on function
  public.astro_heartbeat(text, text, text, integer, text),
  public.astro_lookup_card(text, text, text),
  public.astro_mark_attendance(text, text, text, integer, text, text, integer, uuid, timestamptz),
  public.astro_sync_batch(text, text, jsonb)
from public;

grant execute on function
  public.astro_heartbeat(text, text, text, integer, text),
  public.astro_lookup_card(text, text, text),
  public.astro_mark_attendance(text, text, text, integer, text, text, integer, uuid, timestamptz),
  public.astro_sync_batch(text, text, jsonb)
to anon, authenticated;

-- the two dashboard views had the same accidental anon grant
revoke all on table public.v_attendance_feed, public.v_daily_attendance from anon;
grant select on table public.v_attendance_feed, public.v_daily_attendance to authenticated;

-- ============================================================================
-- Fail-closed default for anything added later by this project's migrations
-- ============================================================================
alter default privileges for role postgres in schema public
  revoke execute on functions from anon;
