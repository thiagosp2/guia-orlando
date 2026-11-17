# Guia Orlando v40 — Planejamento mais rápido

- Histórico dos 30 dias por parque coletado em até 3 requisições simultâneas.
- Cache persistente SQLite (`planner_history_cache.sqlite3`), por parque/data, validade de 30 dias; apenas respostas válidas são gravadas.
- Mudanças de atrações, datas de visita, intervalos e duração reaproveitam históricos já baixados.
- Tentativas com espera progressiva para HTTP 429 e falhas temporárias; erros são exibidos sem inventar filas.
- Rotas verificadas continuam reaproveitadas do SQLite `walking_routes.sqlite3` da v39.
- Painel de desempenho informa tempos por etapa, cache hits e chamadas reais.
- As duas opções de dias, itinerários por dia da semana, mapas e PDF são mantidos.

## Instalação
`pip install -r requirements.txt` e `python -m streamlit run app.py`.
Não substitua seus arquivos `.sqlite3` existentes se desejar preservar o histórico.

## Observação
Otimização incremental é feita reutilizando dados históricos e rotas; a classificação e a sequência do roteiro são recalculadas após clicar Gerar. Não existe processamento em segundo plano.
