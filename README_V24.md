# Guia Orlando v24 — Melhor horário por dia da semana

A aba **Previsão experimental de filas** agora permite escolher segunda a domingo, atrações e intervalo horário. Calcula a mediana por hora a partir de datas históricas distintas e destaca o horário de menor espera típica para cada atração. Exclui feriados federais dos EUA, janelas de Thanksgiving, Natal, Ano Novo e 4 de julho, e aplica filtro robusto MAD a dias anômalos e observações de atrações. Exige pelo menos três dias por horário; não inventa valores faltantes.

**Limitação importante:** usa a base local SQLite, cuja cobertura depende da coleta realizada enquanto o app está ativo. Não detecta automaticamente todos os eventos especiais e não incorpora o histórico remoto da aba de histórico. O filtro de outliers pode ser pouco efetivo em amostras pequenas.
