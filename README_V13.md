# Guia Orlando v13 — uso no celular e acompanhamento do dia

Esta versão parte da v12 e acrescenta a aba **📱 Meu guia**.

## Novidades
- Interface com botões maiores e espaçamento adaptado a telas estreitas.
- Próxima atração recomendada a partir das filas e das preferências configuradas na aba **Agora**.
- **Concluí**: registra a atração como realizada, define-a como referência de localização e recalcula a recomendação.
- **Pular agora**: exclui temporariamente a atração das recomendações; botão para recuperar todas as puladas.
- **Recalcular com filas atualizadas**: invalida o cache das filas atuais e recalcula a sugestão.
- Exportação/importação manual de progresso em JSON por parque, sem expor chaves de API.
- Leitura opcional de `THEMEPARKS_API_KEY` em Streamlit Secrets para publicação.

## Limites
- **Não utiliza GPS automático**: a localização continua sendo selecionada manualmente na aba Agora. Ao marcar uma atração como concluída, ela passa a ser a localização de referência.
- A atualização das filas ocorre por ação do usuário; não há monitoramento em segundo plano.
- O progresso é mantido na sessão Streamlit e pode ser perdido após reinício; exporte o JSON para recuperá-lo depois. Não há sincronização automática entre aparelhos.
- O cálculo é heurístico, não prevê com precisão o tempo de fila futuro e não realiza reservas de Lightning Lane ou Express.
- Serviços públicos de mapas e roteamento podem estar indisponíveis ou impor limites.

## Publicar
1. Envie os arquivos Python e `requirements.txt` ao GitHub, sem bancos SQLite, `.env` ou `secrets.toml`.
2. No Streamlit Community Cloud, selecione `app.py` e configure o segredo `THEMEPARKS_API_KEY`.
3. Abra a URL HTTPS no celular. A aba **Meu guia** foi desenhada para uso em telas pequenas.

## Executar localmente
```
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

## Testes
```
python -m unittest discover -s tests -v
```
