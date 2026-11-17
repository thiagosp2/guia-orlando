# Guia Orlando v22 — Oportunidades na aba Agora

A ordenação da aba **Agora** passa a favorecer atrações cuja fila atual está significativamente abaixo de sua própria média histórica. Ex.: TRON com média observada de 40 minutos e fila atual de 20 minutos recebe um bônus de oportunidade, sem substituir as restrições de fila, a precedência das atrações imperdíveis e os fatores de caminhada.

## Histórico e limitações

O cálculo usa exclusivamente amostras reais persistidas em `wait_history.sqlite3`, registradas durante o uso do aplicativo. Considera os últimos 30 dias e exige pelo menos 6 observações distribuídas por 2 datas diferentes. Prefere observações no mesmo horário local (±90 minutos), mas utiliza todas as horas se não houver cobertura suficiente. A tabela informa a base utilizada. O pico P90 é o percentil 90, não o máximo absoluto. Quando não há histórico suficiente, a ordem anterior é preservada.

**Importante:** a v22 não importa automaticamente o histórico remoto da aba "Histórico por data e período" para a base local. Para ter comparações imediatamente com dados de anos anteriores, será necessário integrar e persistir uma fonte histórica externa compatível. Sem isso, a função amadurece conforme o aplicativo é usado em diferentes dias.

## Instalação

Mantenha as dependências da versão anterior e execute `streamlit run app.py` no diretório do projeto.
