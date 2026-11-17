# Guia Orlando v49 — mapa interativo sem Folium

O mapa da aba Meu dia no parque agora permite ampliar e reduzir pelos botões + e −, usar a roda do mouse, arrastar para navegar, dar duplo clique para ampliar e restaurar o enquadramento pelo botão ⤢. Os gestos funcionam dentro do componente HTML do Streamlit, sem bibliotecas adicionais, Folium ou CDN. As atrações, áreas e rota permanecem sobre a base cartográfica OpenStreetMap (quando os mosaicos estiverem acessíveis). Quando a rede bloquear os mosaicos, continua existindo o fundo esquemático.

O mapa mantém o limite de ampliação em 12 vezes sobre os mosaicos inicialmente carregados. Para maiores detalhes em zoom alto seria necessário buscar mosaicos de resolução superior. O funcionamento real do navegador e da rede do usuário não foi validado neste ambiente.

Instalação: `python -m pip install -r requirements.txt` e `python -m streamlit run app.py`. Preserve seus arquivos SQLite da versão anterior.
