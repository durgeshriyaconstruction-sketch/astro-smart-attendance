-- 0026_leave_outbox_sync.sql
-- =====================================================================
-- Fix: a cancelled or deleted leave kept its "Leave approved" email.
--
-- astro_decide_leave() queues an email into `alerts` (ref_kind='leave',
-- ref_id=leave id). Nothing removed that row when the leave was later
-- cancelled, rejected after the fact, or deleted, so the parent received
-- "Leave approved" for a leave the school had already withdrawn. Verified:
-- two such orphaned rows existed in the live queue.
--
-- Notices and messages already have astro_outbox_sync(); leaves did not.
-- Same pattern: while the email is still queued, withdraw it.
-- (If the mail has already gone out, rewording it here would be a lie -
-- only unsent rows are touched.)
-- =====================================================================

begin;

create or replace function public.astro_leave_outbox_sync()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
  if tg_op = 'DELETE' then
    delete from public.alerts
     where ref_kind = 'leave' and ref_id = old.id and status = 'queued';
    return old;
  end if;
  if new.status in ('cancelled', 'rejected') then
    delete from public.alerts
     where ref_kind = 'leave' and ref_id = new.id and status = 'queued';
  end if;
  return new;
end
$$;

drop trigger if exists leave_requests_outbox on public.leave_requests;
create trigger leave_requests_outbox
  after update or delete on public.leave_requests
  for each row execute function public.astro_leave_outbox_sync();

revoke all on function public.astro_leave_outbox_sync() from public, anon, authenticated;
grant execute on function public.astro_leave_outbox_sync() to service_role;

commit;
