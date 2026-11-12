-- 0025_grant_surface.sql
-- =====================================================================
-- Shrink what a signed-in browser and the publishable key may touch.
--
-- Supabase's ALTER DEFAULT PRIVILEGES grant EXECUTE on every new function to
-- anon and authenticated *explicitly*, so `revoke ... from public` is not
-- enough. After migrations 0016-0024 there were 63 functions in public and
-- several internal helpers were reachable straight from PostgREST:
--
--   astro_verify_device(p_device_code, p_device_secret) -> devices
--       returns the stored row, including secret_hash, to any caller that
--       already holds a secret. Nothing outside the device RPCs needs it.
--   astro_ctx_school / astro_norm_uid / astro_sha256_hex / astro_try_* /
--       trigger helpers - implementation detail, never a public endpoint.
--
-- Also: `authenticated` had INSERT/UPDATE/DELETE on both reporting views.
-- They are security_invoker so RLS still applied, but a view should not
-- advertise write privileges it does not support.
--
-- The six device RPCs stay callable with the publishable key, because that is
-- exactly how the ESP32 talks to the database.
-- =====================================================================

begin;

-- 1. Pin search_path on the helpers that never had it.
alter function public.astro_norm_uid(text) set search_path = public;
alter function public.astro_sha256_hex(text) set search_path = public;
alter function public.astro_try_ts(text) set search_path = public;
alter function public.astro_try_uuid(text) set search_path = public;
alter function public.astro_touch_updated_at() set search_path = public;

-- 2. Internal helpers are not endpoints.
do $$
declare f text;
begin
  foreach f in array array[
    'astro_verify_device(text, text)',
    'astro_norm_uid(text)',
    'astro_sha256_hex(text)',
    'astro_try_ts(text)',
    'astro_try_uuid(text)',
    'astro_touch_updated_at()',
    'astro_cards_normalise()',
    'astro_holiday_cleanup()',
    'astro_outbox_sync()',
    'astro_fanout_notice()',
    'astro_fanout_message()',
    'astro_members_guard()',
    'astro_schools_guard()',
    'astro_students_clean()',
    'astro_messages_clean()',
    'astro_notices_clean()',
    'astro_dismiss_notice(uuid, boolean)'
  ] loop
    begin
      execute format('revoke all on function public.%s from public, anon', f);
      -- astro_dismiss_notice is user facing: keep it for authenticated only.
      if f not like 'astro_dismiss_notice%' then
        execute format('revoke all on function public.%s from authenticated', f);
      end if;
      execute format('grant execute on function public.%s to service_role', f);
    exception when undefined_function then
      raise notice 'skip %', f;
    end;
  end loop;
end
$$;

-- 3. Views are read-only for the dashboard.
revoke insert, update, delete, truncate on public.v_attendance_feed from authenticated;
revoke insert, update, delete, truncate on public.v_daily_attendance from authenticated;
grant select on public.v_attendance_feed to authenticated;
grant select on public.v_daily_attendance to authenticated;

-- 4. Service role keeps everything it needs (PostgREST + mailer worker).
grant execute on function public.astro_claim_emails(integer) to service_role;
grant execute on function public.astro_finish_email(bigint, boolean, text) to service_role;
grant execute on function public.astro_release_stale_sending(integer) to service_role;
grant execute on function public.astro_outbox_stats() to service_role;
grant execute on function public.astro_requeue_failed() to service_role;
grant execute on function public.astro_prune_events(integer) to service_role;
grant execute on function public.astro_close_day(date) to service_role;

commit;
