# Guia Orlando v32 — Explorar dados mais rápido

- Consultas históricas paralelas limitadas a 3 conexões para reduzir a espera.
- Normalização e identificação de dias atípicos executadas apenas após uma nova coleta.
- Alterar atrações, métricas, filtros, datas e dia da semana reutiliza os dados já carregados.
- Erros por data continuam visíveis; nenhum valor é inventado.
- Preserva v29, v30 e v31; v32 é uma pasta independente.

## Como executar
`python -m pip install -r requirements.txt`
`python -m streamlit run app.py`

## Observação
A velocidade real depende da API, rede e proxy corporativo. Um erro 429 pode indicar que o limite de consultas foi atingido; nesse caso reduza a janela histórica.
