# Guia Orlando v47 — ranking semanal por parque

A aba **Explorar dados > Melhores dias** agora apresenta exclusivamente o ranking de segunda a domingo para cada parque, ordenado pela menor média histórica de fila.

- Período histórico selecionável, com padrão dos 30 dias completos anteriores.
- Consulta primeiro `planner_history_cache.sqlite3` e busca apenas datas ausentes ou expiradas na API.
- Exibe dias sem dados como não classificados, sem inventar médias.
- Média por dia histórico na janela 10h–18h (Orlando), depois média por dia da semana.
- O limite de acesso histórico da API pode impedir períodos mais antigos.
- Outras áreas preservadas.

Mantenha os bancos SQLite da versão anterior ao migrar.
