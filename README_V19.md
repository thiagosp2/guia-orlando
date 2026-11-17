# Guia Orlando v19 — Auditoria de cobertura de feriados

## Objetivo
Diagnosticar se os históricos gratuitos realmente permitem comparar Thanksgiving de 2023, 2024 e 2025 antes de emitir previsões.

## Mudanças
- Auditoria automática por fonte, parque e ano, usando dados já importados pela v18.
- Verificação da presença de Thanksgiving e de pelo menos dois dias normais de referência.
- Contagem de atrações e observações no feriado.
- Exportação CSV do diagnóstico.
- Explicação dos limites de Wambles/Queue-Times, TouringPlans e Chart the Magic.
- Sem inventar minutos nem declarar uma previsão confiável a partir de índice de lotação.

## Limitações
Não foram verificados downloads externos nesta execução (acesso HTTPS indisponível no ambiente de teste).
A auditoria testa cobertura mínima, não estabilidade de composição das atrações nem acurácia da previsão.
Para gerar uma previsão com confiança, ainda precisamos validar fontes históricas com séries de minutos comparáveis.
