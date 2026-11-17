# Guia Orlando v18 — histórico automático sem escolher arquivos

Na aba **Feriados e lotação**, a aplicação consulta automaticamente as fontes públicas Wambles/Queue-Times e TouringPlans (quatro parques Disney). Não é necessário clicar para importar nem escolher parques ou arquivos.

- O cache da consulta dura 24 horas por instância Streamlit; o botão **Atualizar fontes agora** força uma nova tentativa.
- A coleta é limitada a 12 CSVs do projeto Wambles e 6 por parque TouringPlans para reduzir o consumo de rede e o tempo de inicialização. Não representa uma varredura completa de todos os arquivos disponíveis.
- Falhas e arquivos incompatíveis são relatados na seção **Transparência**. Se não houver dados históricos de filas anunciadas em minutos, a previsão não é fabricada.
- Não há necessidade de pagar ThemeParks.wiki para esse histórico. As fontes podem alterar estrutura, disponibilidade ou licenças; confira as condições de cada uma antes de redistribuir dados.
- A importação automática roda no código da página Streamlit e pode aumentar o tempo da primeira abertura, pois o Streamlit executa o conteúdo das abas mesmo que outra aba esteja selecionada.

Instalação: `python -m pip install -r requirements.txt` e `python -m streamlit run app.py`.
