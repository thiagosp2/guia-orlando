# Guia Orlando v43 — Mapa sem Folium

O mapa de atrações agora usa SVG nativo, incorporado ao Streamlit: não depende de Folium, streamlit-folium, CDN, tiles ou instalação de biblioteca de mapas. Mostra atrações e nomes de áreas imediatamente e o caminho calculado pelo Valhalla após o botão. O fundo é **esquemático, não cartográfico**: sem ruas, polígonos de áreas ou caminhos quando não houver rota verificada.

Instale: `python -m pip install -r requirements.txt` e execute `python -m streamlit run app.py`. Preserve os bancos SQLite ao migrar.
