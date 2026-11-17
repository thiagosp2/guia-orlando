# Guia Orlando v33 — duas opções de dia/parque

Baseada na v32, preservando a otimização da exploração de dados e a correção SQLite.

Em **Planejar viagem**, após gerar o roteiro, são apresentadas duas alternativas completas de datas/parques, classificadas pela menor espera histórica normalizada das atrações escolhidas. Cada alternativa respeita a exigência de datas distintas por parque. A seleção de uma opção atualiza o roteiro de atrações e a exportação PDF/CSV. Se não houver dados para duas alternativas, a interface informa a limitação sem inventar dados.

Os horários de atrações são calculados separadamente para cada alternativa, com a mesma cobertura mínima e os mesmos filtros da versão anterior.

Executar: `python -m pip install -r requirements.txt` e `python -m streamlit run app.py`.
