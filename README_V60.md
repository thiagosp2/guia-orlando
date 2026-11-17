# v60 — Histórico compartilhado persistente no Supabase

Fluxo: SQLite local (cache rápido) → Supabase PostgreSQL (persistência entre reinícios) → API ThemeParks.wiki (apenas ausentes/expirados). Resultados válidos obtidos na API são gravados em SQLite e Supabase. O cache tem TTL de 30 dias. Falhas de rede não são armazenadas como dados históricos.

## Configuração
1. Execute `SUPABASE_HISTORY_SETUP.sql` no SQL Editor do seu projeto Supabase.
2. No Streamlit Community Cloud → App settings → Secrets, mantenha `SUPABASE_URL`, `SUPABASE_ANON_KEY` e acrescente `SUPABASE_SERVICE_ROLE_KEY` com a chave **service_role** obtida nas configurações de API do projeto.
3. Nunca envie `SUPABASE_SERVICE_ROLE_KEY` ao GitHub, ao navegador ou ao suporte. Essa chave ignora RLS; use-a exclusivamente nos Secrets do servidor. Se vazou, revogue-a.
4. Atualize os arquivos do repositório com a v60 e reinicie o app.
5. Faça uma consulta histórica, verifique registros em `shared_history_cache`, reinicie a aplicação e consulte novamente: o cache deve ser recuperado do Supabase.

A conta do usuário continua usando a chave pública e RLS em `user_search_params`. A tabela de histórico é compartilhada, não contém preferências pessoais. A funcionalidade pode operar com SQLite/API quando o segredo do Supabase não estiver configurado, mas nesse caso a persistência entre reinicializações não estará ativa. A primeira carga pode ser lenta e o plano Supabase tem cotas de armazenamento e requisições.
