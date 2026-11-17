# Guia Orlando v12 — Correção de Melhores dias

O endpoint de horários não oferece necessariamente datas históricas. A v11 descartava o histórico de filas caso não encontrasse horário publicado. Agora, a seção usa o horário oficial quando disponível e, na ausência dele, usa 10h–18h (horário de Orlando) como janela aproximada, sinalizando a quantidade de dias afetados. Não inclui automaticamente dados de horários noturnos ou eventos especiais.

O filtro de horário regular continua aplicado ao planejamento diário. Na análise histórica, sem agenda histórica, não é possível garantir que todas as amostras estejam dentro do horário regular; a limitação é informada.
