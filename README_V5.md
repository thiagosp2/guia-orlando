# Disney Guia Virtual v5 — prioridades protegidas

Execute `python -m pip install -r requirements.txt` e `python -m streamlit run app.py`.

- Pesos normalizados: prioridade **40%**, fila **35%**, caminhada **15%**, tendência observada **10%**.
- Três níveis: **imperdível**, **desejada** e **opcional**.
- Imperdíveis têm precedência rígida na classificação e não são removidas pelo filtro de fila máxima. Atrações fechadas ou sem fila conhecida não podem ser agendadas.
- O planejador alerta sobre imperdíveis não encaixadas; não promete que todas serão realizadas.
- Tempos de fila são fotografias do momento, não previsões. Roteamento público Valhalla via POST + truststore, com cache SQLite e estimativa alternativa.
- O planejamento ainda é heurístico e não incorpora automaticamente janelas de Lightning Lane.
