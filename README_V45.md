# Guia Orlando v45 — Explorar dados com SQLite compartilhado

As três abas de Explorar dados (Análise integrada, Histórico detalhado e Melhores dias) passam a utilizar `planner_history_cache.sqlite3`, o mesmo cache persistente do Planejar viagem. A coleta consulta primeiro o SQLite e busca somente dias ausentes ou expirados. Respostas válidas são persistidas; falhas não são gravadas. Concorrência limitada a 3 consultas, com retry controlado para erros transitórios.

O cache é por identificador do parque e data; expira após 30 dias, conforme a implementação existente. `wait_history.sqlite3` permanece destinado aos dados de filas de outras funções e `walking_routes.sqlite3` às rotas. O cache histórico compartilhado fica em `planner_history_cache.sqlite3`. Preserve esse arquivo nas atualizações.

A interface exibe quantos dias foram reutilizados e quantas consultas à API foram feitas.
