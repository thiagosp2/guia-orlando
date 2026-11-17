# Guia Orlando v16 — Comparação com feriados de anos anteriores

Na aba **Feriados e lotação**, carregue os CSVs diários do Chart the Magic e/ou importe um CSV de histórico de outros anos. O formato mínimo é `date,park,avg_posted_wait_min` (uma linha por parque e dia); também aceita o formato por atração com `ride` e `readings`.

O aplicativo compara **a fila anunciada observada** no mesmo deslocamento relativo ao Thanksgiving (por exemplo, Black Friday ou sábado após o feriado) com a mediana de dias equivalentes em semanas próximas **no mesmo ano**. O fator é a mediana das diferenças percentuais anuais. Só apresenta previsão se houver pelo menos **2 anos comparáveis**, **2 dias normais por ano** e **2 dias recentes de referência**. Sem isso, mostra observações disponíveis e informa que não há previsão fundamentada.

Os CSVs públicos do Chart the Magic começaram em junho de 2026, então **não incluem feriados de anos anteriores**. O usuário precisa importar um conjunto histórico legítimo para obter a comparação numérica. A fonte TouringPlans tem dados históricos de algumas atrações da Disney, mas não cobre todos os parques/atrações e requer tratamento de seu formato; não se deve inferir que a Universal tenha a mesma cobertura.

Os resultados são médias de filas **anunciadas**, não filas realmente enfrentadas. A faixa P20–P80 é dispersão de anos observados, não garantia nem intervalo de confiança. Verifique direitos de uso e atribuição de cada fonte externa antes de importar/publicar os dados.

Execução: `pip install -r requirements.txt` e `streamlit run app.py`.
