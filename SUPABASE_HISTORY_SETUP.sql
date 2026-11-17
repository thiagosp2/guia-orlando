-- Execute no SQL Editor do mesmo projeto Supabase usado para autenticação.
create table if not exists public.shared_history_cache (
  park text not null,
  day date not null,
  payload jsonb not null,
  saved_at bigint not null,
  primary key (park, day)
);
create index if not exists shared_history_saved_at_idx
  on public.shared_history_cache (saved_at);
alter table public.shared_history_cache enable row level security;
-- Sem políticas para anon/authenticated: acesso somente pelo backend com service_role.
revoke all on public.shared_history_cache from anon, authenticated;
