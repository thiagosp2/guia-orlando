# Guia Orlando v25 — Previsão com histórico remoto ThemeParks.wiki

Na seção Previsão de filas, os melhores horários passam a utilizar **exclusivamente** os registros históricos consultados diretamente na API ThemeParks.wiki. O banco SQLite local não alimenta mais essa seção.

Clique em **Consultar histórico ThemeParks.wiki** e escolha janela de 7 ou 30 dias. A consulta busca um dia por chamada para o parque inteiro e amostra o horário local de 08h a 22h em passos de 30 minutos. Somente valores com estado OPERATING e atualizados em até 90 minutos entram no cálculo. O filtro de feriados/outliers do `weekday_optimizer.py` permanece.

**Restrições importantes:** sem chave a API permite somente 7 dias, com chave gratuita 30 dias; períodos mais longos são pagos. Como a análise exige 3 datas distintas para o mesmo dia da semana e horário, uma janela de 7 dias geralmente **não** permite recomendar horários; 30 dias pode permitir. Falhas 403 e 429 são apresentadas sem fabricar valores. Consultas são armazenadas no cache Streamlit por 30 minutos, não no banco local.

Atribuição: Powered by ThemeParks.wiki — https://www.themeparks.wiki/
