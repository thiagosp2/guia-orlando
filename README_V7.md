# Disney Guia Virtual v7 — Planejamento de melhores dias

Nova aba **📅 Melhores dias** para comparar filas históricas dos quatro parques e recomendar uma data distinta para cada parque dentro da viagem.

## Como funciona
- Consulta histórico de 7 a 21 dias recentes por parque, sujeito à janela de acesso da chave ThemeParks.wiki e limites da API.
- Amostra filas standby às 10h–18h (horário de Orlando). Calcula a mediana das filas disponíveis por hora e a média dessas medianas por dia; exclui estados fechados e registros antigos.
- Agrega as médias por dia da semana, mostra quantidade de dias observados e cobertura de atrações.
- Se houver atrações imperdíveis previamente selecionadas para o parque, incorpora suas filas à comparação (peso ajustável, padrão 40%).
- Otimiza a atribuição de um dia distinto para cada parque, comparando valores normalizados por parque.
- Exporta a recomendação em CSV.

## Limitações importantes
- Os resultados são **comparações históricas**, não previsão de lotação para datas futuras.
- O padrão semanal pode mudar em Thanksgiving, feriados, eventos especiais e horários extraordinários.
- Com 7 dias históricos pode existir apenas 1 observação por dia da semana; use 14 ou 21 dias para melhorar a amostra, dentro do plano disponível.
- Não integra clima, preços, disponibilidade de ingressos, eventos especiais, horários reais futuros ou Lightning Lane.
- O histórico pode gerar muitas consultas (até 84); respostas são armazenadas em cache por 30 minutos. Respeite os limites da API.
- Para prioridades de outro parque, selecione esse parque na barra lateral, marque as imperdíveis e depois volte à aba Melhores dias.

## Instalação
```powershell
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

O projeto preserva as funcionalidades da v6, o roteamento público via Valhalla e a correção de SSL com truststore.
