# Disney Guia Virtual v6 — sem Docker

## Melhorias
- Pesos: prioridade 40%, fila 35%, caminhada 15%, tendência 10%.
- Planejador com projeção **heurística** de fila até 90 minutos, com proteção de tempo para atrações imperdíveis. Não é previsão estatística nem garante atrações.
- Localização atual persistida no `st.session_state` por parque ao atualizar filas. Sem localização, caminhada desconhecida usa 12 min como aproximação, em vez de zero.
- Mapa PyDeck com marcadores pequenos (3–7 pixels), legenda por prioridade e tooltip com nome e coordenadas.
- Valhalla público via POST JSON, SSL truststore, cache SQLite.

## Executar
```powershell
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

## Limites
A projeção usa tendências observadas localmente e pode divergir das filas futuras. Caminhadas são estimativas até que rotas reais sejam calculadas e armazenadas. Rotas OSM podem não corresponder aos acessos reais das atrações.
