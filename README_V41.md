# Guia Orlando v41 — Mapa sempre visível e deslocamentos explícitos

## Correções
- Mapa de atrações e áreas renderizado com Folium/OpenStreetMap, sem token Mapbox ou dependência do estilo Carto GL.
- Marcadores e nomes das áreas aparecem antes de clicar em **Calcular rota de caminhada**.
- Após clicar, a rota real de pedestres é sobreposta apenas se Valhalla devolver geometria válida. Sem rota, não se desenha linha reta fictícia.
- Pontos com coordenadas inválidas/NaN são descartados.
- A cobertura de pares de caminhada no planejamento aumentou de até 12 para até 48 por parque, com cache em walking_routes.sqlite3.
- O editor do roteiro mostra **Não verificada** no lugar de NaN para caminhadas sem rota confirmada.
- As áreas são estimadas por palavras-chave nos nomes das atrações, não são polígonos oficiais. Atrações sem área reconhecida não recebem rótulo temático.

## Limitações
- Rotas entre atrações só são conhecidas se o serviço público Valhalla responder e o par for consultado; pares não consultados permanecem sem medição.
- Os mapas base dependem de acesso de rede a tiles do OpenStreetMap; firewalls podem bloquear ruas e imagens, mesmo que os pontos/áreas estejam disponíveis.
- 48 consultas por parque podem aumentar a primeira execução; as rotas válidas ficam em cache SQLite.

## Instalação
`python -m pip install -r requirements.txt`

`python -m streamlit run app.py`

Não substitua os arquivos `.sqlite3` da instalação anterior se quiser preservar o cache local.
