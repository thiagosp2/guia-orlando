# Guia Orlando v39 — Sequência otimizada por filas e caminhada

## Mudanças
- Duas opções de dias de parque preservadas da v38.
- Novo planejador de sequência (`optimize_ride_route`) utiliza busca por feixe (*beam search*) para encaixar o maior número de atrações e, entre sequências com igual cobertura, buscar menor tempo de término. Considera filas históricas por dia da semana e hora, caminhadas de pedestres confirmadas por Valhalla, duração média ajustável da atração e margem entre atrações.
- Coordenadas obtidas do catálogo ThemeParks.wiki; são usadas somente quando disponíveis.
- Até 12 pares de rota por parque (até 3 consultas concorrentes), compartilhados pelas duas opções. Os pares são priorizados por proximidade geográfica para evitar excesso de consultas; **não é uma matriz completa**.
- Se o servidor Valhalla não responder ou faltarem coordenadas, os trechos ficam **não verificados**. Nenhum tempo de caminhada é inventado. Nesses casos a sequência ainda pode ser calculada por filas e margem configurada, mas o tempo total é incompleto.
- Colunas `Caminhada (min)`, `Rota verificada`, `Duração atração (min)` na tabela e caminhada identificada no PDF.
- Controle para ativar/desativar consultas de caminhada, duração média da atração e margem configurável.

## Limitações importantes
- Duração média é uma hipótese definida pelo usuário, **não um dado medido** por atração.
- Horários de fila são estimativas históricas por hora, não previsões garantidas. O algoritmo não integra reservas de Lightning Lane, duração real específica, horários de shows ou fechamentos excepcionais.
- O tempo de rota depende do mapa OSM e do Valhalla, que podem não conter todos os caminhos internos do parque. O serviço público pode falhar ou limitar chamadas.
- Busca heurística, não garante ótimo global. Horários são recalculados para cada dia da semana das opções 1 e 2.
- O tempo total com trechos não verificados é incompleto; não interpretar como caminhada zero.

## Como executar
`python -m pip install -r requirements.txt`
`python -m streamlit run app.py`

## Testes
`python -m pytest -q`

Ao atualizar, não substitua os arquivos `.sqlite3` de sua instalação anterior.
