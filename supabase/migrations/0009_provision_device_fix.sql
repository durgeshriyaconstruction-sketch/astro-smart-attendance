-- ============================================================================
-- ASTRO SMART ATTENDANCE — 0009 astro_provision_device() INSERT fix
--
-- Defect: since 0003 the function inserted FIVE values into a FOUR-column list
--          insert into devices (school_id, device_code, name, secret_hash)
--          values (sid, code, name, hash, 'unflashed');
-- so every call died with "42601 INSERT has more expressions than target
-- columns". Registering a second terminal — the documented onboarding path —
-- had never worked.
-- ============================================================================

create or replace function public.astro_provision_device(
  p_school_code text,
  p_device_code text,
  p_name        text default null,
  p_secret      text default null
)
returns jsonb
language plpgsql security definer set search_path = public
as $$
declare
  sid uuid;
  sec text := coalesce(nullif(p_secret, ''), encode(extensions.gen_random_bytes(24), 'hex'));
  did uuid;
begin
  select id into sid from public.schools where code = p_school_code;
  if sid is null then
    raise exception using message = 'SCHOOL_NOT_FOUND', errcode = '22023';
  end if;

  if auth.uid() is not null then
    if not public.is_staff() then
      raise exception using message = 'NOT_STAFF', errcode = '42501';
    end if;
    if sid <> public.current_school_id() then
      raise exception using message = 'SCHOOL_FORBIDDEN', errcode = '42501';
    end if;
  end if;

  insert into public.devices (school_id, device_code, name, secret_hash, firmware)
  values (sid, upper(btrim(p_device_code)), p_name, public.astro_sha256_hex(sec), 'unflashed')
  on conflict (device_code) do update
    set secret_hash = excluded.secret_hash,
        name        = coalesce(excluded.name, public.devices.name)
  returning id into did;

  return jsonb_build_object('ok', true, 'device_id', did,
                            'device_code', upper(btrim(p_device_code)),
                            'device_secret', sec,
                            'note', 'Copy this secret into the firmware now; it is not recoverable.');
end $$;

revoke all on function public.astro_provision_device(text, text, text, text) from anon, public;
grant execute on function public.astro_provision_device(text, text, text, text) to authenticated;
