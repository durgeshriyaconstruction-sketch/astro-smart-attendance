-- 0027_message_hard_delete.sql
-- Deleting a message really deletes it: the row is gone from `messages`, like
-- cutting a root, not hiding a branch. If the e-mail that announces it has not
-- been sent yet, that e-mail is withdrawn in the same breath, so a family never
-- receives a notice about a message the school already took back.
--
-- Whose delete does what:
--   staff/admin, any message in their school   -> hard delete
--   a parent, their own message to the school  -> hard delete
--   a parent, a message the school sent        -> hidden for that parent only
-- Nothing a parent does can erase the school's own record; nothing the school
-- does leaves a copy behind in the app.
--
-- E-mails that already went out are NOT deleted: the mail has left, and the
-- school must still be able to see what it sent and to whom.

create or replace function public.astro_delete_message(p_message_id uuid)
returns jsonb
language plpgsql
security definer
set search_path to 'public'
as $function$
declare
  m public.messages;
  n_emails integer := 0;
begin
  select * into m from public.messages where id = p_message_id for update;
  if m.id is null then
    return jsonb_build_object('ok', true, 'message_id', p_message_id,
                              'mode', 'already_gone', 'emails_withdrawn', 0);
  end if;

  -- School staff may erase any message in their school.
  if auth.uid() is null or (public.is_staff() and m.school_id = public.current_school_id()) then
    delete from public.alerts a
     where a.ref_kind = 'message' and a.ref_id = m.id
       and a.status in ('queued', 'failed', 'skipped');
    get diagnostics n_emails = row_count;
    delete from public.messages where id = m.id;
    return jsonb_build_object('ok', true, 'message_id', m.id, 'mode', 'deleted',
                              'emails_withdrawn', n_emails);
  end if;

  if not public.linked_student(m.student_id) then
    raise exception using message = 'NOT_ALLOWED', errcode = '42501';
  end if;

  -- A family may erase what they wrote themselves.
  if m.direction = 'from_student' and m.sender = auth.uid() then
    delete from public.alerts a
     where a.ref_kind = 'message' and a.ref_id = m.id
       and a.status in ('queued', 'failed', 'skipped');
    get diagnostics n_emails = row_count;
    delete from public.messages where id = m.id;
    return jsonb_build_object('ok', true, 'message_id', m.id, 'mode', 'deleted',
                              'emails_withdrawn', n_emails);
  end if;

  -- What the school sent stays on the school's side; it just leaves this
  -- family's view.
  update public.messages
     set student_hidden_at = coalesce(student_hidden_at, now())
   where id = m.id;
  return jsonb_build_object('ok', true, 'message_id', m.id, 'mode', 'hidden',
                            'emails_withdrawn', 0);
end
$function$;

comment on function public.astro_delete_message(uuid) is
  'Staff delete = row removed (and any unsent e-mail withdrawn). Parent delete of their own message = row removed; of a school message = hidden for that parent.';
