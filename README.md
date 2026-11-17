# Disney Guia Virtual v4 — sem Docker

## Executar no Windows / VS Code

```powershell
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

Mantenha `app.py`, `core.py` e `routing.py` na mesma pasta.

## O que mudou

A URL do Valhalla já vem preenchida com `https://valhalla1.openstreetmap.de`, servidor público de demonstração. Não precisa instalar Docker nem configurar chave Valhalla. Na aba **Roteiro e mapa**, selecione duas atrações e clique em **Calcular rota de caminhada**.

O servidor público pode estar indisponível, limitar solicitações ou não possuir caminhos adequados dentro da Disney. Não use para consultar grandes matrizes de rotas automaticamente. O aplicativo mantém as demais funções mesmo se o roteamento falhar.

As rotas obtidas são guardadas em `walking_routes.sqlite3` por até 30 dias. O planejamento utiliza pares armazenados e, para os demais, estimativas aproximadas. Os pontos das atrações podem não coincidir com as entradas/saídas reais; confirme o trajeto no mapa oficial do parque.

## Histórico e autenticação

O histórico e a chave ThemeParks.wiki continuam disponíveis. Cole sua chave no campo lateral. O acesso ao histórico depende do plano e da disponibilidade da API.

## SSL corporativo

As consultas HTTPS da ThemeParks.wiki e do Valhalla utilizam `truststore` com certificados confiáveis do Windows. Não é necessário desativar a verificação TLS. Se sua rede exigir proxy, solicite configuração adequada à TI.

## Limites

O tempo de caminhada é distância roteada / velocidade escolhida. Não inclui tempo de saída da atração, filas, lotação ou fechamento de passagens.


## v7
Nova aba **Melhores dias**. Leia README_V7.md para metodologia, limitações e instruções.
