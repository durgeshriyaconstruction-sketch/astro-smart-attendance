-- 0021 live updates: the web app subscribes to these tables instead of polling.
-- Row-level security still applies to realtime, so each user only receives rows they may read.
do $$
declare t text;
begin
  foreach t in array array['attendance','notices','messages','leave_requests','school_holidays','devices','device_commands','schools','students']
  loop
    if not exists (select 1 from pg_publication_tables where pubname = 'supabase_realtime' and schemaname = 'public' and tablename = t) then
      execute format('alter publication supabase_realtime add table public.%I', t);
    end if;
  end loop;
end $$;
-- deletes must carry the old row so a deleted notice / message disappears from open screens
alter table public.notices replica identity full;
alter table public.messages replica identity full;
alter table public.school_holidays replica identity full;
alter table public.attendance replica identity full;
