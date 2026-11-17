# Guia Orlando v28 — Roteiro Planejado

A guia **Meu guia** foi substituída por **Roteiro Planejado**.

1. Informe o período da viagem e escolha parques.
2. Selecione explicitamente as atrações de cada parque.
3. Escolha a janela horária e a margem entre atrações.
4. Clique em **Gerar roteiro com histórico de 30 dias**. A aplicação consulta `/entity/{id}/history` da ThemeParks.wiki para os 30 dias anteriores, com cache de 30 minutos, sem usar o banco local.
5. Compara médias diárias apenas das atrações selecionadas, descarta feriados americanos conhecidos e dias anômalos via MAD; distribui parques em datas distintas, minimizando a espera relativa por parque.
6. Para cada parque/dia escolhido, estima a mediana de fila por atração/hora do mesmo dia da semana, usando pelo menos 3 datas independentes, e organiza horários sem sobreposição aproximada. Atrações sem evidência são sinalizadas, não recebem estimativa fabricada.
7. Exporte PDF e CSV da programação.

## Limitações

- Histórico gratuito: 30 dias com chave aceita; alguns dias podem retornar 403 ou 429.
- Só quatro a cinco amostras por dia da semana na janela de 30 dias. Excluir feriados e outliers pode inviabilizar previsões para algumas atrações.
- Sem cálculo real de percurso, duração das atrações, ingressos, calendário de funcionamento ou Lightning Lane. Horários são recomendações de início aproximadas.
- A programação para Thanksgiving e eventos especiais pode divergir fortemente da mediana histórica dos dias comuns.
- O app requer `reportlab>=4.0` para PDF.
