-- 0013: shrink the executable surface of `public` to the intended API.
--
-- After 0011/0012 every *public* RPC is correctly scoped, but the helper
-- functions that back triggers (fan-out writers) and SQL utilities were still
-- reachable as `authenticated`. They are internal: triggers run as the definer,
-- so revoking them from clients cannot break anything. Postgres will not let a
-- plain SELECT call a trigger function anyway, but the grant should not exist —
-- an audit should see only the API.
--
-- Deliberately NOT revoked:
--   public.is_staff(), public.current_school_id()  — used by RLS policies,
--     so they must stay executable for `authenticated`
--   the device RPCs granted to `anon` (heartbeat/lookup/mark/sync)

revoke all on function public.astro_fanout_notice() from anon, authenticated, public;
revoke all on function public.astro_fanout_message() from anon, authenticated, public;
revoke all on function public.astro_touch_updated_at() from anon, authenticated, public;
revoke all on function public.astro_norm_uid(text) from anon, authenticated, public;
revoke all on function public.astro_sha256_hex(text) from anon, authenticated, public;
revoke all on function public.astro_try_ts(text) from anon, authenticated, public;
revoke all on function public.astro_try_uuid(text) from anon, authenticated, public;

-- belt and braces: the two helpers RLS depends on stay open to signed-in users
grant execute on function public.is_staff() to authenticated;
grant execute on function public.current_school_id() to authenticated;
