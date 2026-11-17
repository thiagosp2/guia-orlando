# Guia Orlando v31 — correção database is locked

Corrige travamentos ao salvar filas atuais em wait_history.sqlite3.

- SQLite WAL e busy_timeout de 8 segundos para leitura e escrita concorrentes.
- Conexões curtas e commits explícitos via context manager.
- Persistência de filas é opcional: banco ocupado não derruba a tela de filas da ThemeParks.wiki.
- Leituras de tendências locais indisponíveis retornam vazio em vez de derrubar o aplicativo.
- Preserva os bancos de dados existentes no computador do usuário: não apagar os arquivos .sqlite3.
- O MVP29 e a v30 original não foram modificados.

## Instalação
Copie os arquivos do ZIP v31 para uma pasta de trabalho (ou substitua os arquivos .py da v30). Feche instâncias antigas do Streamlit antes de iniciar novamente. Mantenha seus arquivos .sqlite3 locais.
