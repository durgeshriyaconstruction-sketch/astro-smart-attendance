-- 0014: the outbox worker contract.
--
-- 0011/0012 built the queue; nothing could drain it yet. This adds the three
-- RPCs a dispatcher needs, so the worker never touches tables directly:
--
--   astro_claim_emails(n)          atomically take up to n queued emails
--                                  (status: queued -> sending, attempts+1)
--   astro_finish_email(id, ok, e)  sending -> sent | failed (+ error text)
--   astro_release_stale_sending()  sending -> queued for a worker that died
--
-- Claiming uses UPDATE ... WHERE id IN (SELECT ... FOR UPDATE SKIP LOCKED), so
-- two workers can run side by side without double-sending.
--
-- `sending` is added to alert_status_check. The old, never-written `alerts.error`
-- column is dropped: 0011 added `last_error`, which is the one the worker uses.

-- 1. statuses ---------------------------------------------------------------

alter table public.alerts drop constraint if exists alerts_status_check;
alter table public.alerts add constraint alerts_status_check
  check (status in ('queued', 'sending', 'sent', 'failed', 'skipped'));

create index if not exists alerts_queued_idx
  on public.alerts (created_at)
  where status = 'queued';

-- 2. drop the dead duplicate error column -----------------------------------

do $$
begin
  if exists (
    select 1 from information_schema.columns
    where table_schema = 'public' and table_name = 'alerts' and column_name = 'error'
  ) and not exists (select 1 from public.alerts where error is not null) then
    alter table public.alerts drop column error;
  end if;
end $$;

-- 3. claim ------------------------------------------------------------------

create or replace function public.astro_claim_emails(p_limit integer default 20)
returns table (
  id bigint,
  school_id uuid,
  student_id uuid,
  to_email text,
  subject text,
  body text,
  kind text,
  ref_kind text,
  ref_id uuid,
  attempts integer
)
language plpgsql
security definer
set search_path = public
as $$
begin
  -- give up on rows that have already burned every retry
  update public.alerts
     set status = 'failed', last_error = coalesce(last_error, 'max_attempts_reached')
   where status = 'queued' and attempts >= 6;

  return query
  update public.alerts a
     set status = 'sending', attempts = a.attempts + 1
   where a.id in (
     select q.id
       from public.alerts q
      where q.status = 'queued'
        and q.channel = 'email'
        and q.to_email is not null
        and q.attempts < 6
      order by q.created_at
      limit greatest(coalesce(p_limit, 20), 1)
      for update skip locked
   )
  returning a.id, a.school_id, a.student_id, a.to_email, a.subject, a.body,
            a.kind, a.ref_kind, a.ref_id, a.attempts;
end $$;

-- 4. finish -----------------------------------------------------------------

create or replace function public.astro_finish_email(p_id bigint, p_ok boolean, p_error text default null)
returns jsonb
language plpgsql
security definer
set search_path = public
as $$
declare a public.alerts;
begin
  update public.alerts
     set status     = case when p_ok then 'sent' else 'failed' end,
         sent_at    = case when p_ok then now() else sent_at end,
         last_error = case when p_ok then null else left(coalesce(p_error, 'unknown_error'), 500) end
   where id = p_id
  returning * into a;

  if a.id is null then
    return jsonb_build_object('ok', false, 'reason', 'ALERT_NOT_FOUND', 'id', p_id);
  end if;

  return jsonb_build_object(
    'ok', true,
    'id', a.id,
    'status', a.status,
    'attempts', a.attempts,
    'sent_at', a.sent_at,
    'last_error', a.last_error
  );
end $$;

-- 5. crash recovery ---------------------------------------------------------

create or replace function public.astro_release_stale_sending(p_minutes integer default 15)
returns jsonb
language plpgsql
security definer
set search_path = public
as $$
declare n integer;
begin
  update public.alerts
     set status = 'queued',
         last_error = coalesce(last_error, 'stale_claim_released')
   where status = 'sending'
     and created_at < now() - make_interval(mins => greatest(coalesce(p_minutes, 15), 1));
  get diagnostics n = row_count;
  return jsonb_build_object('ok', true, 'released', n);
end $$;

-- 6. grants: worker uses the secret key (service_role), nobody else ----------

revoke all on function public.astro_claim_emails(integer) from anon, authenticated, public;
revoke all on function public.astro_finish_email(bigint, boolean, text) from anon, authenticated, public;
revoke all on function public.astro_release_stale_sending(integer) from anon, authenticated, public;

grant execute on function public.astro_claim_emails(integer) to service_role;
grant execute on function public.astro_finish_email(bigint, boolean, text) to service_role;
grant execute on function public.astro_release_stale_sending(integer) to service_role;
