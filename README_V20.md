# Guia Orlando v20 — lotação relativa e previsão de filas

A aba **Feriados e lotação** agora usa o modelo `crowd_model.py` e não inclui a auditoria v19.

- Reutiliza importação automática v18 (cache de 24h) e CSVs públicos Chart the Magic.
- Normaliza séries de filas por parque e ano para evitar comparar diretamente índices de lotação de escalas diferentes.
- Calcula efeitos relativos do feriado usando pelo menos dois anos históricos com observações reais.
- Usa mediana de filas recentes para converter o efeito relativo em minutos.
- Estima atrações individualmente quando há pelo menos cinco dias observados para cada uma.
- Não inventa dados ausentes; mostra insuficiência quando não existe amostra adequada.
- WDW Passport é uma referência metodológica, não importação automática: acesso programático e permissão de reutilização não confirmados.

**Importante:** o modelo ainda depende de cobertura histórica real. O índice de lotação não é uma medida de público e a faixa P20–P80 não é um intervalo de confiança. A projeção horária continua não calibrada para Thanksgiving.

Execução: `pip install -r requirements.txt` e `streamlit run app.py`.
