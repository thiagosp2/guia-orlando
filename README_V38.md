# Guia Orlando v38 — Mapa integrado

- Removida a seção **Simulação de roteiro do dia** da área Roteiro e mapa.
- Mapa único de atrações, coordenadas e rota de caminhada entre duas atrações selecionadas.
- Rótulos das áreas estimadas calculados pelo agrupamento das atrações que possuem nomes de área.
- Caminho desenhado somente quando o serviço de rotas retorna uma geometria real.
- Preservado o controle manual de Lightning Lane.
- Mantidos os demais recursos da v37.

Execução: `python -m pip install -r requirements.txt` e `python -m streamlit run app.py`.

Nota: os nomes de áreas dependem dos metadados disponíveis; coordenadas podem apontar para o centro das atrações, e não para as entradas.
