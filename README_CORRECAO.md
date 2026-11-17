# Correção da coluna Caminhada estimada — v8

- Ao atualizar filas, preserva metadados de coordenadas já obtidos quando a consulta de metadados falha temporariamente.
- Usa coordenadas fornecidas diretamente na resposta de filas, quando disponíveis.
- Se a localização ou as coordenadas estiverem ausentes, mostra célula vazia, **não 12 minutos**.
- Para o índice de recomendação e o planejador, uma penalidade neutra interna de 12 min continua sendo utilizada quando a distância é desconhecida. Essa penalidade não é uma distância medida.
- Mantém Valhalla e as rotas reais previamente calculadas.

Execute `python -m streamlit run app.py`.
