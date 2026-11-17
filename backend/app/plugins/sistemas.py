"""Sistemas externos de MENTIRA (Zendesk, Slack, Jira...). Nada aqui é dado real, nem integração real.

Cada plugin traz ferramentas que leem ou escrevem nestes sistemas. O estado mutável (respostas dadas, mensagens
enviadas, itens abertos) alimenta a "janela" simulada da página do plugin: o que os agentes fizeram aparece lá.
"""
import threading

from ..tools import dados_ficticios as fx

trava = threading.RLock()   # quem gera o id e grava na lista segura a trava do começo ao fim

# ---- Zendesk: fila de chamados de atendimento
CHAMADOS_ZENDESK_INICIAIS = [
    {"id": "Z-4812", "assunto": "Dúvida sobre prazo de estorno", "solicitante": "Padaria Pão Dourado", "lojista_id": "L1001",
     "prioridade": "normal", "texto": "Fiz um estorno de uma venda no débito ontem e a cliente ainda não viu o dinheiro. Em quanto tempo cai?"},
    {"id": "Z-4813", "assunto": "Maquininha não liga", "solicitante": "Ótica Visão Clara", "lojista_id": "L1002",
     "prioridade": "alta", "texto": "A Maquininha Pro parou de ligar hoje cedo, mesmo carregada. A tela ficou preta. Preciso de uma troca."},
    {"id": "Z-4814", "assunto": "Pedido de bobinas", "solicitante": "Pet Shop Amigo Fiel", "lojista_id": "L1004",
     "prioridade": "baixa", "texto": "Acabou a bobina da maquininha. Como solicito mais?"},
]
ZENDESK: list[dict] = []
# ---- Slack: mensagens enviadas pelos agentes
CANAIS_SLACK = ["#logistica", "#time-risco", "#atendimento", "#engenharia", "#geral"]
SLACK: list[dict] = []
# ---- Jira: itens de trabalho
ITENS_JIRA_INICIAIS = [
    {"id": "LOG-101", "projeto": "LOG", "titulo": "Reposição de Maquininha Smart no CD de São Paulo", "status": "Em andamento", "descricao": "Estoque abaixo de 10 unidades."},
    {"id": "ENG-212", "projeto": "ENG", "titulo": "Migrar o conector de cadastro para a nova API", "status": "A fazer", "descricao": "Janela de manutenção a combinar."},
    {"id": "LOG-102", "projeto": "LOG", "titulo": "Revisar o prazo de envio do CD de Florianópolis", "status": "Concluído", "descricao": "Prazo caiu de 3 para 2 dias."},
]
JIRA: list[dict] = []
SERVICENOW: list[dict] = []
SALESFORCE_INTERACOES: list[dict] = []
DOCUMENTOS_DRIVE = [
    {"id": "DOC-01", "titulo": "Política de estorno e contestação", "pasta": "Atendimento", "resumo": "Estornos no débito caem em até 2 dias úteis; no crédito, na próxima fatura."},
    {"id": "DOC-02", "titulo": "Política de troca de maquininha", "pasta": "Logística", "resumo": "Troca por defeito em até 3 dias úteis, com chamado na fila de logística."},
    {"id": "DOC-03", "titulo": "Guia de férias e benefícios", "pasta": "Pessoas", "resumo": "Férias podem ser divididas em até 3 períodos; um deles com pelo menos 14 dias."},
    {"id": "DOC-04", "titulo": "Procedimento de retenção preventiva de repasse", "pasta": "Risco", "resumo": "Só com confirmação de um analista humano e parecer registrado."},
]
CONTAS_SALESFORCE = {
    "L1001": {"conta": "Padaria Pão Dourado", "gerente": "Equipe Varejo Sul", "saude": "verde", "ultimo_contato": "2026-10-28", "potencial_mensal": 41_000},
    "L1002": {"conta": "Ótica Visão Clara", "gerente": "Equipe Varejo Sul", "saude": "verde", "ultimo_contato": "2026-11-05", "potencial_mensal": 98_000},
    "L1003": {"conta": "Eletrônicos Relâmpago", "gerente": "Equipe Grandes Contas", "saude": "vermelho", "ultimo_contato": "2026-11-12", "potencial_mensal": 240_000},
    "L1004": {"conta": "Pet Shop Amigo Fiel", "gerente": "Equipe Varejo Sul", "saude": "amarelo", "ultimo_contato": "2026-09-30", "potencial_mensal": 60_000},
}
ALERTAS_DATADOG = {
    "cadastro-lojistas": {"servico": "cadastro-lojistas", "monitor": "Latência p95 do cadastro", "status": "OK", "valor": "180 ms"},
    "api-repasses": {"servico": "api-repasses", "monitor": "Taxa de erro da API de repasses", "status": "Alerta", "valor": "2,4% (limite 1%)"},
    "estoque-logistica": {"servico": "estoque-logistica", "monitor": "Fila de reposição", "status": "OK", "valor": "12 itens"},
}


def zerar() -> None:
    with trava:
        ZENDESK.clear(); ZENDESK.extend(dict(c, status="aberto", respostas=[]) for c in CHAMADOS_ZENDESK_INICIAIS)
        SLACK.clear()
        JIRA.clear(); JIRA.extend(dict(i) for i in ITENS_JIRA_INICIAIS)
        SERVICENOW.clear()
        SALESFORCE_INTERACOES.clear()


zerar()


def novo_id(prefixo: str, lista: list, base: int = 0) -> str:
    """Chame com `trava` já segura até o append: senão duas chamadas simultâneas ganham o mesmo id."""
    with trava:
        return "%s-%04d" % (prefixo, len(lista) + 1 + base)


def lojista_de(chamado: dict) -> dict | None:
    return fx.LOJISTAS.get(chamado.get("lojista_id", ""))
