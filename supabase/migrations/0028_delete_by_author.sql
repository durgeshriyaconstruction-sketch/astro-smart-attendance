-- 0028_delete_by_author.sql
-- Only the person who wrote a message can delete it. Everyone else can read it
-- and nothing more:
--
--   staff/admin, a message the school wrote   -> row erased (+ unsent e-mail withdrawn)
--   a family,  a message the family wrote     -> row erased, for both sides
--   anyone else                                -> refused, nothing changes
--
-- The previous version let a family hide a school message from their own view.
-- That is gone: a school message stays visible to the family until the school
-- itself deletes it. `messages.student_hidden_at` is left in place (an old row
-- may still carry it) but nothing sets it any more.

create or replace function public.astro_delete_message(p_message_id uuid)
returns jsonb
language plpgsql
security definer
set search_path to 'public'
as $function$
declare
  m public.messages;
  n_emails integer := 0;
  wrote_it boolean;
begin
  select * into m from public.messages where id = p_message_id for update;
  if m.id is null then
    return jsonb_build_object('ok', true, 'message_id', p_message_id,
                              'mode', 'already_gone', 'emails_withdrawn', 0);
  end if;

  -- "Who messaged it" — the school's own messages, or literally this sender.
  wrote_it := (m.direction = 'to_student' and public.is_staff()
               and m.school_id = public.current_school_id())
           or (m.direction = 'from_student' and m.sender = auth.uid());

  if not wrote_it then
    -- A family may not touch a school message; staff may not erase what a
    -- family wrote. Say so plainly instead of doing something half-way.
    raise exception using
      message = 'NOT_YOUR_MESSAGE: only the sender can delete a message',
      errcode = '42501';
  end if;

  -- The root, not the branch: the row goes, and any e-mail still waiting to
  -- announce it is withdrawn with it. E-mail already delivered stays in the
  -- outbox as a record of what left the building.
  delete from public.alerts a
   where a.ref_kind = 'message' and a.ref_id = m.id
     and a.status in ('queued', 'failed', 'skipped');
  get diagnostics n_emails = row_count;

  delete from public.messages where id = m.id;

  return jsonb_build_object('ok', true, 'message_id', m.id, 'mode', 'deleted',
                            'emails_withdrawn', n_emails);
end
$function$;

comment on function public.astro_delete_message(uuid) is
  'Delete is erase and only the author may do it: the school erases messages it wrote, a family erases messages it wrote, the row is removed and any unsent e-mail for it is withdrawn. Anyone else is refused (NOT_YOUR_MESSAGE).';
