# Guia Orlando v42 — Rotas sob demanda

- Removido o limite fixo de 48 pares por parque.
- Para cada opção de roteiro, a sequência é calculada e os pares consecutivos ainda não verificados são consultados em paralelo (até 3 chamadas).
- Após incorporar as rotas válidas, a sequência é recalculada; novas transições necessárias são verificadas progressivamente.
- Os resultados válidos são persistidos em `walking_routes.sqlite3` pela camada `routing.py`, e compartilhados entre as duas opções de roteiro.
- Falhas de rota não são tratadas como zero minuto e não são consultadas repetidamente na mesma execução.
- A busca é limitada pelo número finito de pares direcionais possíveis das atrações selecionadas, e não por um número arbitrário.
- Tempos de caminhada não verificados continuam assinalados como tal.

## Instalação

```bash
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

Para preservar o histórico, copie seus bancos `wait_history.sqlite3` e `walking_routes.sqlite3` para a nova pasta, com o aplicativo desligado. Não substitua os bancos existentes por arquivos vazios.

## Validação

`python -m pytest -q`: 56 testes aprovados. `python -m compileall -q .`: aprovado.

Não houve teste de ponta a ponta com a API externa ou o navegador.
