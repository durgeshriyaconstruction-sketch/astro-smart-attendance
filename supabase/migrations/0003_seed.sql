-- ============================================================================
-- ASTRO SMART ATTENDANCE — 0003 seed + device provisioning
-- ============================================================================

-- ------------------------------------------------------------- the school ---
insert into public.schools (name, code, timezone, day_start, late_after, day_end, alert_emails)
values ('The Aditya Birla Public School, Renukoot', 'ABPS-RNK', 'Asia/Kolkata',
        '08:00', '08:20', '14:00', true)
on conflict (code) do nothing;

insert into public.classes (school_id, name, section, teacher)
select s.id, '9', 'A', 'Class Teacher'
from public.schools s
where s.code = 'ABPS-RNK'
on conflict (school_id, name, section) do nothing;

-- ------------------------------------------------------------ the terminal ---
-- The plaintext device secret was generated once and handed to the team
-- out-of-band (it lives in firmware/astro_attendance/astro_config.h only).
-- Only its sha256 is stored here. Rotate any time with
--   select public.astro_rotate_device_secret('ASTRO-RNK-01');
-- which returns a fresh secret and rewrites this hash.
insert into public.devices (school_id, device_code, name, location, secret_hash, firmware)
select s.id, 'ASTRO-RNK-01', 'Main gate terminal', 'Main gate',
       '1c994c3527f7c9012042b082e31d5643dcd43e8680d55878e6e8e4551506b132', 'unflashed'
from public.schools s
where s.code = 'ABPS-RNK'
on conflict (device_code) do nothing;

-- ---------------------------- demo student + card (delete before go-live) ---
insert into public.students (school_id, class_id, roll_no, full_name, guardian_email)
select s.id, c.id, 'DEMO-01', 'Demo Student', 'demo.parent@example.com'
from public.schools s
join public.classes c on c.school_id = s.id and c.name = '9' and c.section = 'A'
where s.code = 'ABPS-RNK'
on conflict (school_id, roll_no) do nothing;

insert into public.rfid_cards (school_id, student_id, card_uid, label)
select s.id, st.id, 'A1B2C3D4', 'Bench-test card (not a real card)'
from public.schools s
join public.students st on st.school_id = s.id and st.roll_no = 'DEMO-01'
where s.code = 'ABPS-RNK'
on conflict (card_uid) do nothing;

-- ============================================================================
-- Provisioning helpers (dashboard / service side only)
-- ============================================================================

-- Creates a device and returns its secret ONCE. Store that secret in the
-- firmware; it cannot be read back afterwards.
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
  if not public.is_staff() then
    raise exception using message = 'NOT_STAFF', errcode = '42501';
  end if;

  select id into sid from public.schools where code = p_school_code;
  if sid is null then
    raise exception using message = 'SCHOOL_NOT_FOUND', errcode = '22023';
  end if;

  insert into public.devices (school_id, device_code, name, secret_hash)
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

create or replace function public.astro_rotate_device_secret(p_device_code text)
returns jsonb
language plpgsql security definer set search_path = public
as $$
declare
  sec text := encode(extensions.gen_random_bytes(24), 'hex');
  d public.devices;
begin
  if not public.is_staff() then
    raise exception using message = 'NOT_STAFF', errcode = '42501';
  end if;

  update public.devices
     set secret_hash = public.astro_sha256_hex(sec)
   where device_code = upper(btrim(p_device_code))
     and school_id = public.current_school_id()
  returning * into d;

  if d.id is null then
    raise exception using message = 'DEVICE_NOT_FOUND', errcode = '22023';
  end if;

  return jsonb_build_object('ok', true, 'device_code', d.device_code,
                            'device_secret', sec);
end $$;

revoke all on function public.astro_provision_device(text, text, text, text) from public;
revoke all on function public.astro_rotate_device_secret(text) from public;
grant execute on function public.astro_provision_device(text, text, text, text) to authenticated;
grant execute on function public.astro_rotate_device_secret(text) to authenticated;
