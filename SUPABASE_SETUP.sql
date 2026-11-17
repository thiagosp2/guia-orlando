-- Execute no SQL Editor do seu projeto Supabase.
-- Uma linha JSON por usuário, apenas parâmetros de pesquisa.
create table if not exists public.user_search_params (
  user_id uuid primary key references auth.users(id) on delete cascade,
  params jsonb not null default '{}'::jsonb,
  updated_at timestamptz not null default now()
);
alter table public.user_search_params enable row level security;
revoke all on public.user_search_params from anon;
grant select, insert, update, delete on public.user_search_params to authenticated;

drop policy if exists "read own params" on public.user_search_params;
create policy "read own params" on public.user_search_params
  for select to authenticated using ((select auth.uid()) = user_id);
drop policy if exists "insert own params" on public.user_search_params;
create policy "insert own params" on public.user_search_params
  for insert to authenticated with check ((select auth.uid()) = user_id);
drop policy if exists "update own params" on public.user_search_params;
create policy "update own params" on public.user_search_params
  for update to authenticated using ((select auth.uid()) = user_id)
  with check ((select auth.uid()) = user_id);
drop policy if exists "delete own params" on public.user_search_params;
create policy "delete own params" on public.user_search_params
  for delete to authenticated using ((select auth.uid()) = user_id);
