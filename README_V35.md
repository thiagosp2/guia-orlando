# Guia Orlando v35 — cobertura histórica adaptativa

- O planejamento procura inicialmente duas programações completas com >=3 datas válidas por dia da semana/parque.
- Se não conseguir duas, tenta 2 datas e depois 1, sempre com observações reais.
- Caso a exclusão de feriados impeça o planejamento, tenta também as datas históricas de feriado, com aviso de risco.
- Exibe o nível de cobertura e propaga alertas para o PDF.
- Mantém duas opções automáticas quando os dados e as datas permitem; não fabrica resultados.
- Mantém os recursos de Explorar dados e as otimizações anteriores.

**Limitações:** horários individuais ainda podem não ser calculados quando o histórico da atração é insuficiente, especialmente em feriados. A API externa e o desempenho em Windows não foram validados neste ambiente.

Executar: `python -m streamlit run app.py`.
