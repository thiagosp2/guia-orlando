# Guia Orlando v54 — diagnóstico e refinamento de rotas

- Aumenta de 3 para 12 as rodadas máximas de refinamento das rotas sob demanda. O processo termina antes quando não há novas conexões a consultar.
- Mostra os trechos sem rota verificada por opção de roteiro, evitando acumular o total de outras opções.
- Mostra causas de falha do roteador e pares sem coordenadas para facilitar o diagnóstico de bloqueios SSL, HTTP, indisponibilidade ou dados ausentes.
- Não estima nem inventa tempo de caminhada para trechos sem rota verificada.
- O serviço público Valhalla continua externo e pode estar indisponível; aumentar rodadas não resolve falhas de rede.

Instalação: extrair em pasta nova, copiar os bancos SQLite da versão anterior com o aplicativo desligado. Manter as dependências existentes.
