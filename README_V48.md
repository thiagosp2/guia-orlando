# v48 — Análise integrada mais rápida

- Reaproveita SQLite, consulta apenas datas ausentes.
- Até seis requisições paralelas em vez de três; timeout 15 s por tentativa, uma repetição em falhas temporárias.
- Progresso das consultas pendentes.
- Processa apenas atrações selecionadas, sem recalcular ao mudar filtros de apresentação.
- Preserva os outros recursos e os arquivos SQLite existentes.
- Não inventa filas para dias sem histórico.
