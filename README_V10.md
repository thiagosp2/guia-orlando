# Guia Orlando v10 — Disney + Universal

Inclui Universal Studios Florida, Islands of Adventure e Epic Universe nos módulos de filas ao vivo, atrações prioritárias, roteiro, histórico e Melhores dias. Os IDs dos três parques são descobertos em `/v1/destinations`, evitando IDs inventados. Se a API estiver inacessível, a Universal não aparece até a conexão ser restaurada.

Os horários seguem a configuração existente de horário regular ou extra. Eventos pagos e benefícios exclusivos não são automaticamente considerados. Para a Universal, Lightning Lane não se aplica: os produtos de acesso expresso são diferentes (Universal Express), não integrados a este MVP.

Execute `python -m pip install -r requirements.txt` e `python -m streamlit run app.py`.

**Atenção:** o Valhalla público pode não rotear caminhos privados internos. O histórico disponível depende do plano da API. A Universal pode ter campos e disponibilidade diferentes da Disney. A integração remota não foi testada neste ambiente sem acesso externo.
