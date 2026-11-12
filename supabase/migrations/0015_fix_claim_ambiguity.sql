-- 0015: fix a name collision in the outbox claim RPC.
--
-- astro_claim_emails() is declared RETURNS TABLE (… attempts integer …), so
-- `attempts` is both an OUT parameter and a column of public.alerts. The body
-- from 0014 referenced it unqualified in two places and Postgres rejected the
-- statement at first call with 42702 (column reference "attempts" is ambiguous).
-- Every column reference in the body is now table-qualified.

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
  update public.alerts a
     set status = 'failed',
         last_error = coalesce(a.last_error, 'max_attempts_reached')
   where a.status = 'queued' and a.attempts >= 6;

  return query
  update public.alerts a
     set status = 'sending',
         attempts = a.attempts + 1
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

revoke all on function public.astro_claim_emails(integer) from anon, authenticated, public;
grant execute on function public.astro_claim_emails(integer) to service_role;
