# Guia Orlando v52 — Motor compartilhado de comparação histórica

- `decision_engine.py` centraliza a agregação de filas históricas por hora, data e dia da semana.
- Planejar viagem já utilizava `day_metric` e `weekday_baselines`; o ranking e a Análise integrada agora usam essas mesmas funções via motor compartilhado.
- Análise integrada mostra um ranking geral com mesma janela horária do ranking semanal, além do detalhamento original por atração.
- Melhores dias permite selecionar atrações por parque (sem seleção = todas), usando a mesma regra do planejamento.
- Exige pelo menos 3 datas por dia da semana para o indicador comparativo.
- Parâmetros de seleção do ranking são persistidos, não os resultados.

**Limitação importante:** O Planejar viagem ainda escolhe as datas com base em médias históricas por dia da semana e otimiza a ordem das atrações *depois*. Portanto, as opções não são uma comparação exaustiva de todos os roteiros possíveis por data, nem previsão de filas futuras. A janela do planejamento é configurável; para comparação direta, use 10h–18h e as mesmas atrações/datas históricas.

Copie os bancos SQLite existentes para a pasta extraída, com o aplicativo fechado.
