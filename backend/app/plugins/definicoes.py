"""Os 9 plugins da vitrine (os 8 da v6 e o Google Sheets da v7) e as ferramentas que cada um traz.

Importado SÓ por `tools/catalogo.py` (no fim dele), que registra as ferramentas no catálogo com a marca `plugin=<id>`:
elas existem sempre, mas só valem enquanto o plugin está integrado (`tools/permissoes.py` confere). Quem quiser os
plugins usa `plugins/catalogo.py`.
"""
from __future__ import annotations

import re

from ..core.identidade import Classificacao
from ..tools import dados_ficticios as fx
from ..tools.catalogo import TODAS, Contexto, ErroFerramenta, Especificacao
from . import planilhas
from . import sistemas as sx


# =============================================================
# Implementações (sistemas de mentira)
# =============================================================
def _chamado_zendesk(id_: str) -> dict:
    c = next((x for x in sx.ZENDESK if x["id"] == (id_ or "").strip().upper()), None)
    if c is None:
        raise ErroFerramenta("Chamado %s não encontrado no Zendesk. Use: %s." % (id_, ", ".join(x["id"] for x in sx.ZENDESK)))
    return c


def _zendesk_ler(e: dict, _c: Contexto) -> dict:
    c = _chamado_zendesk(e["chamado_id"])
    return {"chamado_id": c["id"], "assunto": c["assunto"], "solicitante": c["solicitante"], "lojista_id": c["lojista_id"],
            "prioridade": c["prioridade"], "status": c["status"], "mensagem": c["texto"], "respostas": len(c["respostas"])}


def _zendesk_responder(e: dict, c: Contexto) -> dict:
    with sx.trava:   # id + gravação atômicos
        ch = _chamado_zendesk(e["chamado_id"])
        ch["respostas"].append({"autor": c.persona_id, "agente_id": c.agente_id, "texto": e["resposta"]})
        ch["status"] = "respondido"
        return {"chamado_id": ch["id"], "status": "respondido", "respostas": len(ch["respostas"])}


def _salesforce_conta(e: dict, _c: Contexto) -> dict:
    lid = (e["lojista_id"] or "").strip().upper()
    conta = sx.CONTAS_SALESFORCE.get(lid)
    if conta is None:
        raise ErroFerramenta("Conta do lojista %s não encontrada no Salesforce." % e["lojista_id"])
    return dict(conta, lojista_id=lid, interacoes=sum(1 for i in sx.SALESFORCE_INTERACOES if i["lojista_id"] == lid))


def _salesforce_interacao(e: dict, c: Contexto) -> dict:
    with sx.trava:   # id + gravação atômicos
        lid = (e["lojista_id"] or "").strip().upper()
        if lid not in sx.CONTAS_SALESFORCE:
            raise ErroFerramenta("Conta do lojista %s não encontrada no Salesforce." % e["lojista_id"])
        i = {"id": sx.novo_id("INT", sx.SALESFORCE_INTERACOES), "lojista_id": lid, "resumo": e["resumo"], "por": c.persona_id,
             "agente_id": c.agente_id}
        sx.SALESFORCE_INTERACOES.append(i)
        return {"interacao_id": i["id"], "status": "registrada"}


def _slack_enviar(e: dict, c: Contexto) -> dict:
    with sx.trava:   # id + gravação atômicos
        m = {"id": sx.novo_id("SL", sx.SLACK), "canal": e["canal"], "mensagem": e["mensagem"], "enviado_por": c.persona_id,
             "agente_id": c.agente_id, "execucao_id": c.execucao_id}
        sx.SLACK.append(m)
        return {"mensagem_id": m["id"], "canal": m["canal"], "status": "publicada (simulado)"}


def _jira_abrir(e: dict, c: Contexto) -> dict:
    with sx.trava:   # id + gravação atômicos
        n = 1 + sum(1 for i in sx.JIRA if i["projeto"] == e["projeto"]) + (100 if e["projeto"] == "LOG" else 211)
        item = {"id": "%s-%d" % (e["projeto"], n), "projeto": e["projeto"], "titulo": e["titulo"], "descricao": e["descricao"],
                "status": "A fazer", "criado_por": c.persona_id, "agente_id": c.agente_id}
        sx.JIRA.append(item)
        return {"item_id": item["id"], "status": "A fazer", "projeto": item["projeto"]}


def _jira_status(e: dict, _c: Contexto) -> dict:
    item = next((i for i in sx.JIRA if i["id"] == (e["item_id"] or "").strip().upper()), None)
    if item is None:
        raise ErroFerramenta("Item %s não encontrado no Jira." % e["item_id"])
    return {"item_id": item["id"], "titulo": item["titulo"], "status": item["status"]}


def _tokens(t: str) -> set[str]:
    return {w for w in re.findall(r"\w+", t.lower()) if len(w) > 3}


def _drive_buscar(e: dict, _c: Contexto) -> dict:
    q = _tokens(e["consulta"])
    achados = sorted(((len(q & _tokens(d["titulo"] + " " + d["resumo"])), d) for d in sx.DOCUMENTOS_DRIVE), key=lambda x: -x[0])
    return {"documentos": [{"id": d["id"], "titulo": d["titulo"], "pasta": d["pasta"], "resumo": d["resumo"]}
                           for n, d in achados if n > 0][:3]}


def _sheets_ler(e: dict, _c: Contexto) -> dict:
    try:
        return planilhas.ler(e["fonte"])
    except planilhas.ErroPlanilha as erro:
        raise ErroFerramenta(str(erro))


def _servicenow_abrir(e: dict, c: Contexto) -> dict:
    with sx.trava:   # id + gravação atômicos
        i = {"id": "INC%07d" % (10001 + len(sx.SERVICENOW)), "titulo": e["titulo"], "descricao": e["descricao"],
             "urgencia": e.get("urgencia", "media"), "aberto_por": c.persona_id, "agente_id": c.agente_id, "estado": "Novo"}
        sx.SERVICENOW.append(i)
        return {"incidente_id": i["id"], "estado": "Novo", "urgencia": i["urgencia"]}


def _sap_saldo(e: dict, _c: Contexto) -> dict:
    col = fx.COLABORADORES.get((e["colaborador_id"] or "").strip().upper())
    if col is None:
        raise ErroFerramenta("Colaborador %s não encontrado no SAP SuccessFactors." % e["colaborador_id"])
    return {"colaborador_id": col["id"], "nome": col["nome"], "saldo_ferias_dias": col["saldo_ferias_dias"],
            "admissao": col["admissao"]}


def _datadog_alerta(e: dict, _c: Contexto) -> dict:
    a = sx.ALERTAS_DATADOG.get(e["servico"])
    if a is None:
        raise ErroFerramenta("Serviço %s sem monitor. Use: %s." % (e["servico"], ", ".join(sx.ALERTAS_DATADOG)))
    return dict(a)


# =============================================================
# Ferramentas que cada plugin traz (mesmo contrato do catálogo)
# =============================================================
_I, _C = Classificacao.INTERNA, Classificacao.CONFIDENCIAL


def _f(plugin: str, id_: str, nome: str, descricao: str, classif, areas, acao: str, parametros: dict, obrigatorios: tuple,
       executar, latencia: int) -> Especificacao:
    # mesma regra do catálogo da plataforma: escrita em dado confidencial ou restrito só com confirmação humana
    return Especificacao(id_, nome, descricao, "plugins", classif, areas, acao, parametros, obrigatorios, executar,
                         exige_aprovacao=acao == "escrita" and classif >= Classificacao.CONFIDENCIAL,
                         limite_por_minuto=10 if acao == "escrita" else 30,
                         latencia_ms=latencia, plugin=plugin)


FERRAMENTAS: list[Especificacao] = [
    _f("zendesk", "zendesk_ler_chamado", "Ler chamado (Zendesk)",
       "Lê um chamado da fila do Zendesk: assunto, solicitante, prioridade, status e a mensagem do lojista.",
       _I, ("atendimento",), "leitura", {"chamado_id": {"type": "string", "description": "Código do chamado, por exemplo Z-4812."}},
       ("chamado_id",), _zendesk_ler, 260),
    _f("zendesk", "zendesk_responder_chamado", "Responder chamado (Zendesk)",
       "Publica a resposta ao lojista num chamado do Zendesk e marca o chamado como respondido.",
       _I, ("atendimento",), "escrita",
       {"chamado_id": {"type": "string", "description": "Código do chamado, por exemplo Z-4812."},
        "resposta": {"type": "string", "description": "Texto da resposta ao lojista."}},
       ("chamado_id", "resposta"), _zendesk_responder, 300),
    _f("salesforce", "salesforce_consultar_conta", "Consultar conta do lojista (Salesforce)",
       "Consulta a conta do lojista no CRM: gerente, saúde da conta, último contato e potencial mensal.",
       _C, ("atendimento", "risco"), "leitura", {"lojista_id": {"type": "string", "description": "Código do lojista, por exemplo L1001."}},
       ("lojista_id",), _salesforce_conta, 340),
    _f("salesforce", "salesforce_registrar_interacao", "Registrar interação (Salesforce)",
       "Registra no CRM um resumo da interação com o lojista.",
       _C, ("atendimento", "risco"), "escrita",
       {"lojista_id": {"type": "string", "description": "Código do lojista, por exemplo L1001."},
        "resumo": {"type": "string", "description": "O que foi tratado com o lojista."}},
       ("lojista_id", "resumo"), _salesforce_interacao, 380),
    _f("slack", "slack_enviar_mensagem", "Enviar mensagem em canal (Slack)",
       "Publica uma mensagem curta num canal do Slack (por exemplo #logistica) para avisar um time.",
       _I, (TODAS,), "escrita",
       {"canal": {"type": "string", "enum": sx.CANAIS_SLACK, "description": "Canal de destino."},
        "mensagem": {"type": "string", "description": "Mensagem curta, com o que o time precisa saber."}},
       ("canal", "mensagem"), _slack_enviar, 150),
    _f("jira", "jira_abrir_item", "Abrir item (Jira)",
       "Abre um item de trabalho no quadro do Jira (projeto LOG ou ENG).",
       _I, ("engenharia", "logistica"), "escrita",
       {"projeto": {"type": "string", "enum": ["LOG", "ENG"], "description": "Projeto do quadro."},
        "titulo": {"type": "string", "description": "Resumo em uma linha."},
        "descricao": {"type": "string", "description": "Detalhes do item."}},
       ("projeto", "titulo", "descricao"), _jira_abrir, 280),
    _f("jira", "jira_consultar_status", "Consultar status do item (Jira)",
       "Consulta o status de um item do quadro do Jira.",
       _I, ("engenharia", "logistica"), "leitura", {"item_id": {"type": "string", "description": "Código do item, por exemplo LOG-101."}},
       ("item_id",), _jira_status, 220),
    _f("drive", "drive_buscar_documento", "Buscar documento de política (Google Drive)",
       "Procura nos documentos de política do Drive os mais próximos da consulta.",
       _I, (TODAS,), "leitura", {"consulta": {"type": "string", "description": "O que procurar, em linguagem natural."}},
       ("consulta",), _drive_buscar, 200),
    _f("sheets", "sheets_ler_planilha", "Ler planilha (Google Sheets)",
       "Lê as linhas de uma planilha do Google Sheets (publicada na web) ou da planilha fictícia local. Devolve as colunas, "
       "as linhas e a primeira linha pendente. Só leitura.",
       _I, ("logistica",), "leitura",
       {"fonte": {"type": "string", "description": "Endereço da planilha (https://docs.google.com/spreadsheets/...) "
                                                   "ou local:pedidos-troca para a planilha fictícia."}},
       ("fonte",), _sheets_ler, 650),
    _f("servicenow", "servicenow_abrir_incidente", "Abrir incidente (ServiceNow)",
       "Abre um incidente de TI no ServiceNow.",
       _I, ("engenharia",), "escrita",
       {"titulo": {"type": "string", "description": "Resumo em uma linha."},
        "descricao": {"type": "string", "description": "Detalhes do incidente."},
        "urgencia": {"type": "string", "enum": ["baixa", "media", "alta"]}},
       ("titulo", "descricao"), _servicenow_abrir, 320),
    _f("sap", "sap_consultar_saldo_ferias", "Consultar saldo de férias (SAP SuccessFactors)",
       "Consulta no sistema de RH o saldo de férias de um colaborador.",
       _C, ("pessoas",), "leitura", {"colaborador_id": {"type": "string", "description": "Matrícula, por exemplo C501."}},
       ("colaborador_id",), _sap_saldo, 420),
    _f("datadog", "datadog_consultar_alerta", "Consultar alerta de sistema (Datadog)",
       "Consulta o monitor de um serviço no Datadog: status e valor atual.",
       _I, ("engenharia",), "leitura",
       {"servico": {"type": "string", "enum": sorted(sx.ALERTAS_DATADOG), "description": "Serviço monitorado."}},
       ("servico",), _datadog_alerta, 180),
]

# Metadados de vitrine (a classificação e as áreas valem para o plugin inteiro: vêm das ferramentas dele)
VITRINE = [
    {"id": "zendesk", "nome": "Zendesk", "categoria": "helpdesk", "categoria_nome": "Helpdesk", "janela": True,
     "descricao": "Fila de chamados de atendimento: lê o chamado do lojista e publica a resposta."},
    {"id": "salesforce", "nome": "Salesforce", "categoria": "crm", "categoria_nome": "CRM", "janela": False,
     "descricao": "Conta do lojista no CRM: saúde da conta, gerente e histórico de interações."},
    {"id": "slack", "nome": "Slack", "categoria": "chat", "categoria_nome": "Chat corporativo", "janela": True,
     "descricao": "Avisa um canal do time quando um agente termina uma tarefa."},
    {"id": "jira", "nome": "Jira", "categoria": "trabalho", "categoria_nome": "Gestão de trabalho", "janela": True,
     "descricao": "Quadro de itens de trabalho: abre itens e consulta o andamento."},
    {"id": "drive", "nome": "Google Drive", "categoria": "documentos", "categoria_nome": "Documentos", "janela": False,
     "descricao": "Busca nos documentos de política da empresa."},
    {"id": "sheets", "nome": "Google Sheets", "categoria": "planilhas", "categoria_nome": "Planilhas", "janela": False,
     "descricao": "Lê planilhas (só leitura): publicadas na web no Google Sheets ou a planilha fictícia local, para ensaio sem internet."},
    {"id": "servicenow", "nome": "ServiceNow", "categoria": "ti", "categoria_nome": "Chamados de TI", "janela": False,
     "descricao": "Abre incidentes de TI para a Engenharia tratar."},
    {"id": "sap", "nome": "SAP SuccessFactors", "categoria": "rh", "categoria_nome": "RH", "janela": False,
     "descricao": "Sistema de RH: saldo de férias do colaborador (dado confidencial)."},
    {"id": "datadog", "nome": "Datadog", "categoria": "observabilidade", "categoria_nome": "Observabilidade", "janela": False,
     "descricao": "Monitores de serviços: consulta o alerta e o valor atual."},
]
