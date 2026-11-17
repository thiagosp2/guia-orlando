# Guia Orlando v50 — Fundo cartográfico resiliente

Recupera a tentativa de carregar o OpenStreetMap diretamente no navegador quando o Python não consegue baixar os mosaicos por causa de proxy ou certificados. Mantém o mapa interativo sem Folium, as atrações, rótulos de áreas temáticas e rotas verificadas.

Os mosaicos do OpenStreetMap precisam de acesso à internet, pelo Python ou navegador. Se ambos forem bloqueados, o mapa apresenta uma base esquemática claramente identificada, nunca um quadrado branco.

Conserve os arquivos SQLite da instalação anterior.
