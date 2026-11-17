# Guia Orlando v17 — histórico gratuito Disney

Nova seção na aba **🇺🇸 Feriados e lotação**:

- **Importar histórico Disney (2015–2026)**: consulta o diretório público `csv/` de `chadwambles/wdw-wait-times-analysis` no GitHub, descobre CSVs e importa apenas os que têm **datas e filas anunciadas em minutos**. Se a estrutura não for compatível, explica a rejeição; não converte índices de lotação em minutos.
- **Importar atrações TouringPlans**: consulta o repositório público de cada parque Disney e baixa até 12 arquivos CSV de atrações. Médias dessas atrações **não representam necessariamente a média do parque**.
- Integra os dados ao comparativo histórico de Thanksgiving já existente na v16, com precedência para observações diárias Wambles/Queue-Times quando houver sobreposição.
- Exibe cobertura, erros e atribuição das fontes.

## Limitações

A integração online não foi executada neste ambiente sem acesso de rede ao GitHub. Os arquivos e formatos podem mudar, e alguns repositórios podem não disponibilizar CSVs adequados. Os downloads acontecem no computador/servidor onde o Streamlit roda. No Streamlit Community Cloud, dados mantidos em memória podem desaparecer quando a instância reiniciar.

A comparação de feriados só prevê numericamente quando existem **dois anos comparáveis**, dias normais de referência e dados recentes. Não há preenchimento fictício. Dados TouringPlans são de atrações selecionadas; o projeto Wambles publica séries históricas e análises derivadas do Queue-Times. Confira os termos de reutilização e atribua ambas as fontes.

## Instalação

`python -m pip install -r requirements.txt`

`python -m streamlit run app.py`

Fontes:
- https://github.com/chadwambles/wdw-wait-times-analysis
- https://touringplans.com/blog/disney-world-wait-times-available-for-data-science-and-machine-learning/
- https://github.com/TouringPlans/DisneyAnimalKingdomWaitTimes
