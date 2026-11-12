-- 0030_defer_rate_limited.sql
-- Hitting a provider's daily cap (Brevo free = 300/day) must not burn a mail's
-- retry budget. Without this, a busy day could claim rows, get 429s, count six
-- "failures" and park real parent e-mails as permanently failed.
--
-- astro_defer_email() puts a claimed row back in the queue unchanged: status
-- back to 'queued', attempts handed back, and the reason left in last_error so
-- the dashboard says why it is waiting instead of looking broken.

create or replace function public.astro_defer_email(
  p_id bigint,
  p_reason text default 'provider rate limit — will retry'
)
returns void
language plpgsql
security definer
set search_path to 'public'
as $function$
begin
  update public.alerts
     set status = 'queued',
         attempts = greatest(attempts - 1, 0),
         last_error = left(coalesce(p_reason, 'deferred'), 300)
   where id = p_id
     and status = 'sending';
end
$function$;

comment on function public.astro_defer_email(bigint, text) is
  'Returns a claimed e-mail to the queue without spending one of its six attempts — used when the provider is rate limited (429) rather than the address being bad.';
