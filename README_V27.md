# Guia Orlando v27 — Comparação semanal de filas por horário

Na área **Previsão experimental de filas**, após consultar o histórico remoto da ThemeParks.wiki:

- Selecione as atrações na seleção já existente.
- Selecione quais dias da semana comparar (segunda a domingo).
- Escolha uma atração para o gráfico. Cada linha mostra um dia da semana, e o eixo horizontal exibe os horários.
- Veja a menor espera típica por dia e uma tabela consolidada de todas as atrações.
- Exporte os resultados em CSV.

A comparação usa exclusivamente as observações remotas já carregadas na v26, com os mesmos filtros de feriados e MAD, exigindo três datas válidas por dia da semana/atração/horário. Não inventa pontos ausentes. Em janela de 7 dias, geralmente não haverá amostras suficientes; recomenda-se 30 dias com chave gratuita.

## Validação
Arquivos Python compilados; testes específicos do otimizador de dias da semana executados. A API externa não foi consultada durante a validação.
