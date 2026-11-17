# Guia Orlando v44 — Mapa com fundo cartográfico

- Removidas as abas **Previsão de filas** e **Feriados e lotação** da área Explorar dados.
- O mapa usa mosaicos cartográficos OpenStreetMap baixados pelo Python e incorporados ao SVG; não requer Folium, JavaScript externo ou CDN no navegador.
- Os mosaicos são armazenados localmente em `.map_tiles` por até sete dias para acelerar próximas visualizações. São consultados apenas os mosaicos necessários ao parque exibido.
- Se a rede bloquear o servidor de mosaicos, o mapa mostra um **fundo esquemático claramente identificado**, com atrações e áreas; não simula ruas reais.
- A rota de caminhada continua aparecendo somente após o botão e apenas quando confirmada pelo serviço de roteamento.
- O fundo cartográfico é fornecido por © OpenStreetMap contributors; requer acesso HTTPS do Python a `tile.openstreetmap.org` na primeira consulta.
- Preserva as demais funcionalidades, bancos SQLite e planejador v43.

Instalação: `python -m pip install -r requirements.txt` e `python -m streamlit run app.py`.
