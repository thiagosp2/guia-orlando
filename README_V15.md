# Guia Orlando v15 — Feriados e lotação (gratuito)

## Novo
- Aba **🇺🇸 Feriados e lotação** com datas da viagem, alertas de Thanksgiving/Black Friday e Natal.
- Importação de CSVs diários públicos do Chart the Magic (CC BY 4.0) por upload ou download direto.
- Referência por parque/atração baseada em medianas diárias, com percentis e cobertura observada.
- Exportação CSV da comparação.

## Limitação importante
**Não há previsão numérica corrigida para Thanksgiving sem histórico comparável do feriado.** O campo `Estimativa feriado (min)` permanece vazio de propósito. A fila base é histórica, não é fila prevista no feriado. Os dados públicos começam em junho de 2026; o feriado de 2026 ainda não ocorreu na data de criação deste MVP.

Os CSVs podem ser baixados em https://chartthemagic.com/open-data/ (atribuição obrigatória: Chart the Magic, CC BY 4.0). A aplicação não envia a chave ThemeParks.wiki para o Chart the Magic.

## Execução
`python -m pip install -r requirements.txt`

`python -m streamlit run app.py`

Em ambiente corporativo, o download automático pode falhar por bloqueios de rede. Baixe os arquivos pelo navegador e use a opção de upload.
