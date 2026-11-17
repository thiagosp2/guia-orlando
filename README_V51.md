# v51 — Persistência de parâmetros (somente)

O aplicativo guarda automaticamente no SQLite `saved_views.sqlite3` os filtros e seleções das visões Planejar viagem, Meu dia no parque, Análise integrada e Melhores dias. Os parâmetros são restaurados na abertura seguinte. **Não são salvos** resultados de pesquisas, gráficos, respostas da API ou chave de API. Os bancos de histórico e rotas continuam independentes.

O botão `Limpar parâmetros salvos` fica na barra lateral. Para migrar, mantenha os bancos SQLite anteriores na pasta do app. O novo `saved_views.sqlite3` será criado automaticamente.
