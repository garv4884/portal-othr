-- Supabase schema for portal-othr
-- Run this once in Supabase SQL Editor.

create table if not exists public.ot_store (
  key text primary key,
  value jsonb
);

-- Grant API roles access required for anon/publishable key usage.
grant usage on schema public to anon, authenticated;
grant select, insert, update, delete on table public.ot_store to anon, authenticated;

-- Enforce RLS with explicit policies so access is predictable.
alter table public.ot_store enable row level security;

drop policy if exists ot_store_select_anon on public.ot_store;
create policy ot_store_select_anon
on public.ot_store
for select
to anon, authenticated
using (true);

drop policy if exists ot_store_insert_anon on public.ot_store;
create policy ot_store_insert_anon
on public.ot_store
for insert
to anon, authenticated
with check (true);

drop policy if exists ot_store_update_anon on public.ot_store;
create policy ot_store_update_anon
on public.ot_store
for update
to anon, authenticated
using (true)
with check (true);

drop policy if exists ot_store_delete_anon on public.ot_store;
create policy ot_store_delete_anon
on public.ot_store
for delete
to anon, authenticated
using (true);
