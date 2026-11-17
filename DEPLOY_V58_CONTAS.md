# Guia Orlando v58 — contas individuais e sincronização de pesquisas

## 1. Crie o projeto Supabase

1. Entre em https://supabase.com/dashboard e crie um projeto.
2. Em **SQL Editor**, cole e execute `SUPABASE_SETUP.sql`.
3. Em **Authentication → Providers → Email**, mantenha o provedor de e-mail habilitado. Recomenda-se confirmação por e-mail. Configure o serviço SMTP para produção; o envio padrão do Supabase pode ter limites severos.
4. Em **Project Settings → API** (ou **Connect**, conforme a interface), copie **Project URL** e **anon/publishable key**. **Nunca use `service_role` ou secret key no aplicativo.**
5. Em Authentication, configure URL do site e as URLs de redirecionamento conforme seu endereço Streamlit. Este aplicativo usa login por senha, sem callback OAuth.

## 2. Configure Streamlit Cloud

1. Publique os arquivos da v58 no GitHub, preservando `.streamlit/config.toml`, `app.py`, `cloud_accounts.py`, `saved_views.py`, `requirements.txt` e `SUPABASE_SETUP.sql`.
2. No painel do app Streamlit Cloud, abra **Settings → Secrets** e adicione:

```toml
SUPABASE_URL = "https://SEU-PROJETO.supabase.co"
SUPABASE_ANON_KEY = "SUA_CHAVE_PUBLICAVEL_OU_ANON"
```

3. Salve e reinicie o aplicativo, se necessário.
4. Abra o app, crie uma conta, confirme o e-mail (se solicitado), entre e selecione parques e datas.
5. Abra o mesmo app em outro dispositivo/navegador e entre com a mesma conta. Os parâmetros devem reaparecer.
6. Teste com uma **segunda conta diferente** e confirme que não vê os parâmetros da primeira.

## Segurança e limitações

- O Supabase aplica **Row Level Security (RLS)**: cada usuário só acessa sua linha.
- A chave pública é usada apenas com o JWT do usuário; não há `service_role` no app.
- Senhas não são salvas pelo app. Tokens ficam somente na sessão Streamlit do servidor, não no SQLite nem no GitHub.
- Ao sair, o app limpa o estado de sessão. A página precisa ser autenticada novamente após reinício da sessão.
- Não há login automático persistente entre fechamentos da sessão; **as preferências**, sim, são persistentes entre dispositivos.
- Os dados são salvos ao mudar filtros e no final da renderização; erros de rede são mostrados na tela.
- `saved_views.sqlite3` não é usado em modo público e não deve ser enviado ao GitHub.
- Cache de filas/rotas em SQLite no Streamlit Cloud pode ser efêmero e não é separado por conta. Não grave informações pessoais nesses caches.
- Confirme cotas, políticas de uso e condições do plano Supabase antes de abrir para grande público.
- A v58 não foi testada contra um projeto Supabase real: execute os testes acima antes de divulgar.
