# Guia Orlando v36 — Segunda opção por dia da semana

A segunda programação agora exige um dia da semana diferente da primeira para **cada parque**. O algoritmo busca a combinação alternativa de menor espera histórica normalizada, mantendo datas distintas entre parques. Trocar apenas a data por outra ocorrência do mesmo dia da semana não conta como alternativa.

Se não existir combinação completa com cobertura histórica para outros dias da semana, o aplicativo informa a limitação e não duplica o plano. O PDF permanece com as duas opções quando ambas existem. Os dados não são inventados.

## Executar
`python -m pip install -r requirements.txt`
`python -m streamlit run app.py`

A API remota e a interface precisam de validação no ambiente do usuário.
