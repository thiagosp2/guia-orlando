# Guia Orlando v14 — Previsão experimental e alertas

## Novidades

- Nova aba **📈 Previsão de filas**, com estimativas de 30, 60 e 120 minutos à frente.
- Estimativas baseadas exclusivamente nas observações locais de dias anteriores, no mesmo horário aproximado (±45 minutos), com maior peso para o mesmo dia da semana.
- Exige pelo menos **3 dias distintos** com dados para mostrar estimativa; caso contrário exibe **Sem dados**.
- Apresenta faixa de dispersão histórica e quantidade de dias amostrados, sem afirmar precisão garantida.
- Na aba **📱 Meu guia**, mostra a estimativa de 30 minutos para a próxima atração, quando disponível.
- Alertas de alterações de fila de pelo menos 20 minutos e de abertura/fechamento entre consultas feitas nesta sessão.
- Mantém os botões **Concluí**, **Pular agora**, **Recalcular com filas atualizadas**, mapas claros, horários regulares e melhores dias da v13.

## Limitações importantes

- **Não é um modelo de aprendizado de máquina treinado em dados históricos da API.** É uma estimativa por comparação de amostras locais anteriores.
- O SQLite local coleta dados apenas quando o aplicativo recebe consultas. Uma implantação recente provavelmente terá amostras insuficientes. O histórico local pode desaparecer em reinicializações do Streamlit Community Cloud.
- Alertas são exibidos somente quando o aplicativo é acessado/atualizado; **não são notificações automáticas em segundo plano**.
- O replanejamento acontece ao concluir/pular atrações ou atualizar as filas; não há atualização contínua em segundo plano nem GPS automático.
- Não integra reservas de Lightning Lane ou Express.

## Executar

```bash
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

## Publicar

Envie todos os arquivos `.py`, `requirements.txt`, a pasta `tests/` e opcionalmente os READMEs para o GitHub. Configure `THEMEPARKS_API_KEY` nos Secrets do Streamlit Cloud. **Não envie** arquivos `.sqlite3`, `.env`, `secrets.toml`, `__pycache__/` ou chaves.

## Testes

```bash
python -m unittest discover -s tests -v
```
