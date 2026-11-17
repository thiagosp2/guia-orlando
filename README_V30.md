# Guia Orlando v30 — quatro áreas e exploração histórica integrada

## Instalação

No terminal Windows, dentro da pasta do projeto:

```powershell
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

## Áreas principais

1. **Planejar viagem** — seleciona datas, parques e atrações; gera programação por parque, com edição de horário e ordem e exportação PDF/CSV. Para sugerir um dia da semana, exige três datas válidas após filtros; sem dados, avisa.
2. **Meu dia no parque** — filas ao vivo e oportunidades, acompanhamento das atrações planejadas para a data atual, mapas e roteamento opcional (Valhalla).
3. **Explorar dados** — subárea **Análise integrada** com histórico por data, por dia da semana, por horário e comparação entre datas específicas e referências típicas dos dias da semana. Inclui alternância **Histórico completo / filtrado**, contagens de amostras, CSV e subáreas avançadas legadas (Previsão, Histórico detalhado, Melhores dias, Feriados).
4. **Configurações e fontes** — explicação da fonte e metodologia, com ajustes técnicos e chave da API na barra lateral.

## Dados e cálculos

- Fonte das novas análises: **ThemeParks.wiki**, diretamente do endpoint histórico. A análise integrada não usa SQLite local.
- Média e mediana por atração/data; por dia da semana: primeiro agregar por data e depois pela semana para que cada data tenha o mesmo peso.
- Por horário: agrupar observações em intervalos de 60 minutos; mostrar a mediana de medianas diárias para o dia da semana escolhido. Exigir ao menos três datas no gráfico horário.
- **Filtrado:** exclui feriados/períodos especiais identificados e dias com mediana de fila anômala via MAD quando há seis ou mais datas do mesmo dia da semana. **Completo:** inclui datas atípicas, sinalizadas.
- Sem imputação ou estimativas inventadas. Dados ausentes aparecem como lacunas.
- Janela histórica ajustável de 1 a 365 dias na interface; datas fora do plano da API podem retornar HTTP 403. A extensão futura do histórico depende de autorização de acesso e termos da fonte. As consultas são feitas individualmente por data e são cacheadas por 30 minutos.

## Limitações conhecidas

- O algoritmo de roteiro usa os históricos da API para escolher dias e horários, mas não calcula um itinerário com deslocamentos reais e duração das atrações; a edição manual não valida conflitos.
- A seleção de atrações é compartilhada do planejamento para a análise por parque, mas alterações feitas diretamente em Explorar não modificam automaticamente o roteiro já gerado.
- A área de acompanhamento diário identifica a data atual e o parque selecionado, mas não persiste check-ins após reiniciar a sessão.
- Alguns módulos analíticos avançados legados permanecem separados em subtabs para não perder funcionalidades; a integração completa de suas métricas é uma melhoria futura.
- O PDF usa Python padrão, sem ReportLab. O adaptador `truststore` é opcional; quando instalado, usa o armazenamento de certificados do sistema, útil em redes corporativas.

## Verificações

Compilação Python e 38 testes automatizados aprovados no ambiente de desenvolvimento. Testes com a API real e inspeção visual do Streamlit não realizados neste ambiente.

**O MVP29 original não foi alterado.**
