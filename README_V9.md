# v9 — Somente horário regular dos parques

- Na simulação diária, consulta `/entity/{id}/schedule`, seleciona apenas `type=OPERATING` da data atual no fuso de Orlando e restringe o roteiro à interseção com o horário informado.
- Não utiliza `EXTRA_HOURS`, festas noturnas nem After Hours para estender o roteiro.
- Se não houver horário regular publicado, não gera roteiro para evitar recomendações fora de horário.
- Em **Melhores dias**, amostra somente horas dentro do horário `OPERATING` das datas históricas quando o serviço as disponibilizar. Datas sem horários publicados ficam sem pontuação.
- Horários da ThemeParks.wiki podem não refletir alterações de última hora. Confira o calendário oficial da Disney.
- Atrações individuais podem ter horários próprios e encerrar antes do parque. A versão não valida esses horários individuais.
