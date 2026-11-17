# v26 — Correção da previsão por dia da semana

A previsão remota da ThemeParks.wiki agora aceita até 30 dias na função `period_waits(..., max_days=30)`. A consulta de histórico por período mantém seu limite de 7 dias (padrão da função). Respostas HTTP 403 para datas fora do plano continuam sendo exibidas como avisos, sem descartar os demais dias carregados.
