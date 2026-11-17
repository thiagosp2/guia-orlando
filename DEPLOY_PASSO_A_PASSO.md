# Publicar Guia Orlando no Streamlit Community Cloud

## 1. Antes de publicar
- Use um repositório **público** no GitHub somente se o código e as fontes puderem ser divulgados. Não inclua credenciais, dados pessoais ou bancos SQLite locais.
- Este pacote isola os parâmetros de pesquisa **por sessão**; no modo público, não persiste preferências após fechar a sessão. O cache histórico e de rotas contém somente dados públicos e é compartilhado entre usuários.
- Em hospedagem gratuita, o disco pode ser reiniciado, apagando caches SQLite. O aplicativo deverá reconstruí-los.
- O roteamento Valhalla e os mapas OSM dependem de serviços públicos externos; disponibilidade e limites não são garantidos.

## 2. GitHub
1. Crie uma conta em https://github.com se necessário.
2. Crie um repositório, por exemplo `guia-orlando`, com visibilidade adequada.
3. Faça upload do **conteúdo desta pasta** (app.py na raiz, não uma pasta acima).
4. Verifique se `requirements.txt`, `app.py`, `saved_views.py` e `.streamlit/config.toml` estão presentes.
5. Não envie arquivos `.sqlite3`, `.env`, `secrets.toml` ou chaves.

## 3. Streamlit Cloud
1. Acesse https://share.streamlit.io e entre com GitHub.
2. Clique em **Create app** / **New app** e selecione o repositório e a branch principal.
3. Main file path: `app.py`.
4. Escolha um subdomínio disponível e clique em Deploy.
5. Aguarde a instalação de `requirements.txt` e a inicialização.
6. Copie o link HTTPS e teste em celular e computador.

## 4. Teste no celular
- Abra o link no Chrome/Android e Safari/iPhone; confira menus, filtros, tabelas (rolagem horizontal), mapa (gestos de zoom), roteiro e PDF.
- No navegador móvel, use a opção Adicionar à Tela de Início para um atalho. Isso **não** transforma o site em aplicativo nativo.
- Compare resultados e carregamento no desktop.

## 5. Atualizar o aplicativo
- Altere arquivos no repositório GitHub. O Streamlit Cloud normalmente faz o redeploy automaticamente.
- Veja logs em Manage app quando houver erro.

## 6. Antes de divulgar amplamente
- Teste múltiplos visitantes simultâneos e sessões isoladas.
- Monitore latência, limites e disponibilidade das APIs públicas.
- Verifique termos de uso e atribuição dos mapas/serviços.
- Se precisar persistir preferências por pessoa entre dispositivos, implemente autenticação e armazenamento individualizado em banco gerenciado (não SQLite global).
- Para produção com alto tráfego, considere infraestrutura paga, cache compartilhado e roteador próprio/contratado.

## 7. API key opcional
- Em App settings → Secrets, se necessário, configure `THEMEPARKS_API_KEY = "SUA_CHAVE"`. Nunca envie a chave para o GitHub.
- Se o app usar a chave do servidor, todas as consultas poderão consumir a mesma cota. Avalie limites antes de divulgar.
