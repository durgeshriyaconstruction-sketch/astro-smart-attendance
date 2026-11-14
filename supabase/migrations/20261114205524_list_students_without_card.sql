-- ============================================================================
-- 20261114205524_list_students_without_card.sql
-- Applied to the live project (nrjchonjlncamfyzmfye) on 14 Nov 2026 at
-- 20:55 UTC via the Supabase migration API. This file is the copy of record.
--
-- astro_list_students: send a student to the device even when no RFID card has
-- been assigned yet.
--
-- WHAT WAS WRONG
--   The card lookup used an INNER "join lateral", so a student created on the
--   website without a card was silently dropped from the list the gate terminal
--   receives. The only symptom was a child present on the website and missing on
--   the device, with nothing logged anywhere.
--
-- WHY THIS IS SAFE
--   The firmware already expects cardless students - main.cpp carries the
--   comment "Support students added remotely on the website even before an RFID
--   card is assigned", invents a stable local placeholder via
--   generateUniqueRfid() ("A5" + 6 hex chars) and stores the cloud student_id,
--   so the placeholder does not change on the next pull and no duplicate is
--   created. Pushing that placeholder back is also safe: astro_create_student
--   upserts on (school_id, roll_no) and explicitly refuses to reassign a card
--   that already belongs to a different student.
--
--   rfid_uid is coalesced to '' rather than JSON null so the firmware's
--   jsonStr() fallback path is unambiguous.
--
-- VERIFIED AFTER APPLYING (read-only, nothing written)
--   * the definition contains "left join lateral" and no inner join remains
--   * anon and authenticated can still execute it
--   * with a synthetic cardless student added to the pool, the old inner join
--     returned 17 rows and the new left join returns 18
--
-- Idempotent: safe to re-run.
-- ============================================================================

create or replace function public.astro_list_students(
  "device_code" text default null,
  "device_secret" text default null
) returns jsonb
language plpgsql security definer set search_path = public as $$
declare
  d public.devices;
begin
  d := public.astro_fw_auth("device_code", "device_secret");
  return coalesce((
    select jsonb_agg(jsonb_build_object(
             'student_id', st.id::text, 'rfid_uid', coalesce(c.card_uid, ''),
             'name', st.full_name, 'roll', coalesce(st.roll_no, ''),
             'class_name', cl.name, 'section', cl.section,
             'fingerprint_id', st.fingerprint_id
           ) order by st.roll_no nulls last, st.full_name)
      from public.students st
      left join lateral (
        select rc.card_uid from public.rfid_cards rc
         where rc.student_id = st.id and rc.active
         order by rc.assigned_at desc limit 1
      ) c on true
      left join public.classes cl on cl.id = st.class_id
     where st.school_id = d.school_id and st.active
  ), '[]'::jsonb);
end $$;

revoke all on function public.astro_list_students(text, text) from public;
grant execute on function public.astro_list_students(text, text) to anon, authenticated;
