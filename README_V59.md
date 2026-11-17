# Guia Orlando v59

- Chave ThemeParks.wiki gerenciada exclusivamente pelo servidor via `THEMEPARKS_API_KEY` em Streamlit Cloud → App settings → Secrets. Não há campo de chave para visitantes. Não inclua tokens no GitHub.
- O seletor de parque foi movido para o início de **Meu dia no parque**.
- **Filas e oportunidades** agora consulta os dados históricos reais do parque selecionado, aproveita o cache compartilhado e calcula as métricas por atração para parques com cobertura histórica. Os avisos mostram dias, atrações e falhas. Sem amostras suficientes, as métricas permanecem indisponíveis, sem números fabricados.
- Para trocar a chave já exposta em mensagens, revogue-a no provedor e configure a nova nos Secrets.
- As consultas de até 30 dias podem demorar na primeira execução de cada parque; o cache e o estado da sessão reduzem consultas posteriores.

## Publicação
Atualize o repositório GitHub com os arquivos desta versão, preservando a configuração do Supabase no Streamlit Cloud. Em **Settings → Secrets**, configure `THEMEPARKS_API_KEY` e as variáveis `SUPABASE_URL` e `SUPABASE_ANON_KEY`. Não suba arquivos `.streamlit/secrets.toml` ou bancos `.sqlite3`.
