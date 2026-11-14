-- ============================================================================
-- 20261114000003  Lock the public (anon) key back down to the device RPCs
-- ============================================================================
-- WHAT WAS WRONG
--   Section 8 of 20261114000001_astro_firmware_bridge_v2.sql granted EXECUTE on
--   EVERY public.astro_* function to `anon` so that the kiosk could reach its
--   23 RPCs. That also re-opened ~90 functions that migrations 0025 and 0035
--   had deliberately closed. The anon key ships in the firmware, in the web
--   page and in this public repository, so "anon can execute" means "anyone on
--   the internet can execute". With nothing but that key a stranger could:
--
--     astro_rotate_device_secret('ASTRO-RNK-01')  -> be handed a fresh device
--                                                    secret (and cut the real
--                                                    kiosk off), then read the
--                                                    whole roster with it
--     astro_provision_device('<school code>', ..) -> register a rogue kiosk
--     astro_drive_day()                           -> every student's name and
--                                                    attendance for any date
--     astro_claim_emails()                        -> parents' e-mail addresses
--     astro_close_day('<date>')                   -> mark the school absent and
--                                                    e-mail every parent
--     astro_save_student / astro_set_attendance / astro_add_member /
--     astro_delete_notice / astro_decide_leave ... with p_school_id supplied
--
--   Those staff functions trust a caller that has no JWT ("auth.uid() is null")
--   because that branch was written for the service role and for cron. It is
--   only safe while anon cannot reach them.
--
-- WHAT THIS DOES
--   1. anon / PUBLIC lose EXECUTE on every public.astro_* function ...
--   2. ... except the 30 device RPCs, each of which authenticates the caller
--      against devices.secret_hash before doing anything.
--   3. Internal plumbing (mail worker, Drive export, device-secret verifiers,
--      the firmware id map) is not an endpoint for signed-in users either.
--   4. The firmware id-map table is only touched from SECURITY DEFINER code.
--
-- WHAT IT DOES NOT CHANGE
--   * The ESP32: it calls only the 23 flat-key RPCs listed below.
--   * Signed-in staff: every staff RPC stays callable by `authenticated`.
--   * Edge functions (astro-mail, astro-export) and pg_cron: they run as the
--     service role / postgres, which keep everything.
--   * resolve_login_email(text): still anon, it is what name-login needs.
--
-- Idempotent. To undo (do not): re-run the old "section 8" loop.
-- ============================================================================

begin;

-- 1. Nothing in public.astro_* is reachable with the public key ...
do $$
declare
  r record;
begin
  for r in
    select p.oid::regprocedure as sig
      from pg_proc p
      join pg_namespace n on n.oid = p.pronamespace
     where n.nspname = 'public'
       and p.prokind = 'f'
       and p.proname like 'astro\_%'
  loop
    execute format('revoke execute on function %s from public, anon', r.sig);
    execute format('grant execute on function %s to service_role', r.sig);
  end loop;
end $$;

-- 2. ... except the device RPCs. Every one of them calls astro_fw_auth() or
--    astro_verify_device()/astro_dev() first, so the public key alone is useless
--    without the kiosk's secret.
do $$
declare
  f text;
  p regprocedure;
begin
  foreach f in array array[
    -- the 23 RPCs firmware v26.11.7 calls (flat JSON keys)
    'astro_approve_leave(text,bigint,text,text,text,text,text)',
    'astro_create_holiday(text,text,text,text)',
    'astro_create_notice(text,bigint,text,text,text,text,boolean,text,text)',
    'astro_create_student(text,text,text,text,text,text,text,text,text,integer,text,text,text,bigint,boolean,text)',
    'astro_delete_holiday(text,text,text)',
    'astro_delete_message(text,bigint,text)',
    'astro_delete_notice(text,bigint,text)',
    'astro_delete_student(text,text,text,text)',
    'astro_device_handshake(text,text,text)',
    'astro_factory_wipe(text,boolean,text)',
    'astro_get_settings(text,text)',
    'astro_list_attendance(text,text,text)',
    'astro_list_holidays(text,text)',
    'astro_list_leaves(text,text)',
    'astro_list_messages(text,text)',
    'astro_list_notices(text,text)',
    'astro_list_students(text,text)',
    'astro_lookup_by_fingerprint(text,integer,integer,text)',
    'astro_lookup_by_rfid(text,text,text,text)',
    'astro_mark_attendance(text,text,text,text,text,text,text,text)',
    'astro_send_message(text,bigint,text,text,text,text,boolean,text,text)',
    'astro_sync_batch(text,text,jsonb,jsonb,jsonb,jsonb,jsonb,jsonb,jsonb,jsonb,jsonb,jsonb,text)',
    'astro_update_settings(text,integer,integer,text,text,text,text,bigint,text)',
    -- the earlier p_-prefixed device client (also secret-authenticated)
    'astro_command_result(text,text,uuid,boolean,jsonb)',
    'astro_device_ping(text,integer,text,text,text)',
    'astro_heartbeat(text,text,text,integer,text)',
    'astro_lookup_card(text,text,text)',
    'astro_mark_attendance(text,text,text,integer,text,text,integer,uuid,timestamp with time zone)',
    'astro_poll_commands(text,text,integer)',
    'astro_sync_batch(text,text,jsonb)'
  ] loop
    p := to_regprocedure('public.' || f);
    if p is null then
      raise notice 'device RPC not found, skipped: %', f;
      continue;
    end if;
    execute format('grant execute on function %s to anon, authenticated, service_role', p);
  end loop;
end $$;

-- 3. Internal plumbing is not an endpoint for signed-in users either. All of
--    these are SECURITY DEFINER and have no caller check of their own.
do $$
declare
  f text;
  p regprocedure;
begin
  foreach f in array array[
    'astro_claim_emails(integer)',
    'astro_defer_email(bigint,text)',
    'astro_finish_email(bigint,boolean,text)',
    'astro_release_stale_sending(integer)',
    'astro_maintenance()',
    'astro_prune_events(integer)',
    'astro_prune_net(integer)',
    'astro_drive_day(date,text)',
    'astro_drive_month(text,text)',
    'astro_dev(text,text)',
    'astro_verify_device(text,text)',
    'astro_fw_auth(text,text)',
    'astro_fw_map_entity(uuid,text,bigint)',
    'astro_fw_map_local(uuid,text,uuid)',
    'astro_fw_map_put(uuid,text,bigint,uuid)'
  ] loop
    p := to_regprocedure('public.' || f);
    if p is null then
      raise notice 'internal function not found, skipped: %', f;
      continue;
    end if;
    execute format('revoke execute on function %s from public, anon, authenticated', p);
    execute format('grant execute on function %s to service_role', p);
  end loop;
end $$;

-- 4. Only SECURITY DEFINER code reads or writes the firmware id map.
revoke all on table public.astro_fw_id_map from public, anon, authenticated;

commit;

notify pgrst, 'reload schema';
