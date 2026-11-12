-- 0034_claim_lease.sql
-- The mail sender holds a lease on a row while Brevo is answering. Staleness
-- must therefore be measured from the moment the row was CLAIMED, not from the
-- moment it was queued: a mail queued yesterday and claimed a minute ago is not
-- stale, and releasing it would send it twice.
--
-- Applied to the live project on 2026-11-12.

alter table public.alerts add column if not exists claimed_at timestamptz;

create or replace function public.astro_release_stale_sending(p_minutes integer default 15)
returns jsonb
language plpgsql
security definer
set search_path = public
as $$
declare n integer;
begin
  -- claimed_at is when the sender took the row; created_at is when the mail was
  -- queued, which can be days earlier. Releasing on created_at would hand an
  -- in-flight message back to the queue and send it twice.
  update public.alerts
     set status = 'queued', claimed_at = null,
         last_error = coalesce(last_error, 'stale_claim_released')
   where status = 'sending'
     and coalesce(claimed_at, created_at) < now() - make_interval(mins => greatest(coalesce(p_minutes, 15), 1));
  get diagnostics n = row_count;
  return jsonb_build_object('ok', true, 'released', n);
end $$;

create or replace function public.astro_claim_emails(p_limit integer default 20)
returns setof public.alerts
language plpgsql
security definer
set search_path = public
as $$
begin
  -- a send that died mid-flight (function timeout, crash) must not sit in
  -- 'sending' forever; 5 minutes is far longer than a Brevo round trip
  perform public.astro_release_stale_sending(5);

  update public.alerts a
     set status = 'failed', last_error = coalesce(a.last_error, 'max_attempts_reached')
   where a.status = 'queued' and a.attempts >= 6;

  return query
  update public.alerts a
     set status = 'sending', claimed_at = now(), attempts = a.attempts + 1
   where a.id in (
     select q.id from public.alerts q
      where q.status = 'queued' and q.channel = 'email'
        and q.to_email is not null and q.attempts < 6
      order by q.created_at
      limit greatest(coalesce(p_limit, 20), 1)
      for update skip locked)
  returning a.id, a.school_id, a.student_id, a.to_email, a.subject, a.body,
            a.kind, a.ref_kind, a.ref_id, a.attempts;
end $$;

revoke execute on function public.astro_claim_emails(integer) from public, anon, authenticated;
revoke execute on function public.astro_release_stale_sending(integer) from public, anon, authenticated;
