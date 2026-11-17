# Guia Orlando v11 — Mapas claros

- Os dois mapas de **Roteiro e mapa** usam um mapa-base claro CARTO Positron com dados OpenStreetMap, sem token Mapbox.
- O mapa de rotas mostra o trajeto azul, origem verde e destino vermelho.
- O mapa de atrações usa zoom mais próximo, marcadores pequenos e tooltip com nome e coordenadas.
- É necessário acesso à internet para carregar os mosaicos/estilo do mapa. Se a rede corporativa bloquear basemaps.cartocdn.com, o fundo pode continuar indisponível; libere esse domínio na rede ou use outro provedor autorizado.
- Os nomes das áreas temáticas (ex. Tomorrowland, Hogsmeade) só aparecerão se estiverem mapeados e rotulados na cartografia. Não são inventados pelo aplicativo.

Instale `requirements.txt` e execute `python -m streamlit run app.py`.
