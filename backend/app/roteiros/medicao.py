"""Valor medido de cada roteiro: AS IS × TO BE nos 5 critérios da banca.

Cada número diz de onde vem:
  - "medido": tempo e custo da execução real do agente no roteiro (no modo simulado, o tempo é o caminho
    crítico das latências típicas e os tokens são estimados com a mesma régua do modo real);
  - "estimado": ainda sem execução, calculado do desenho do agente;
  - "premissa": valores a validar num piloto (custo da hora, conferência humana, retrabalho);
  - "hipótese": o AS IS, até medirmos o processo com a área.
"""
from __future__ import annotations

from sqlmodel import Session, select

from ..agents import ciclo
from ..agents import modelos as am
from ..agents.blueprint import Blueprint
from ..agents.governanca import estimar_custo, estimar_duracao_ms
from ..finance.premissas import Premissas
from ..llm import precos
from ..processos import modelos as pm
from ..processos.blueprint import ProcessoBlueprint
from ..processos.compilar import compilar
from ..runtime import modelos as rm
from ..seed.agentes_exemplo import DUVIDA_LOJISTA, TRIAGEM_CHARGEBACK
from ..studio.modelos_prontos import por_id
from ..studio.sugestao import blueprint_planilha
from .catalogo import ROTEIROS, Roteiro

PROCESSOS = ("marina", "rafael", "carla", "thiago")      # os quatro processos do consolidado da Helena
COM_TAREFA = PROCESSOS + ("pitch",)               # roteiros com cartão AS IS × TO BE


def _padrao(roteiro_id: str) -> Blueprint:
    return {"marina": DUVIDA_LOJISTA, "rafael": TRIAGEM_CHARGEBACK,
            "carla": Blueprint.model_validate(por_id("ferias_colaborador")["blueprint"]),
            "thiago": Blueprint.model_validate(por_id("troca_maquininha_estoque")["blueprint"]),
            "pitch": Blueprint.model_validate(blueprint_planilha("local:pedidos-troca"))}[roteiro_id]


def _agente(s: Session, r: Roteiro, dono_id: str | None) -> am.Agente | pm.Processo | None:
    """O dono do cartão: o PROCESSO ligado ao roteiro (v8) ou, no pitch, o agente de vários passos que ele cria."""
    if dono_id:
        return s.get(pm.Processo, dono_id) or s.get(am.Agente, dono_id)
    if r.id != "pitch":
        return s.exec(select(pm.Processo).where(pm.Processo.roteiro_id == r.id).where(pm.Processo.estado != am.DEPRECIADO)
                      .order_by(pm.Processo.criado_em.desc())).first()
    if not r.agente_nome:
        return None
    return s.exec(select(am.Agente).where(am.Agente.nome == r.agente_nome).order_by(am.Agente.criado_em.desc())).first()


def _execucoes_do(dono) -> tuple:
    """Filtro das execuções de um agente ou de um processo."""
    if isinstance(dono, pm.Processo):
        return (rm.Execucao.dono_tipo == "processo", rm.Execucao.dono_id == dono.id)
    return (rm.Execucao.agente_id == dono.id,)


def _ultima_execucao(s: Session, dono) -> rm.Execucao | None:
    execs = s.exec(select(rm.Execucao).where(*_execucoes_do(dono)).where(rm.Execucao.demo == False)  # noqa: E712
                   .order_by(rm.Execucao.inicio.desc())).all()
    boas = [e for e in execs if e.status in (rm.CONCLUIDA, rm.AGUARDANDO)]
    return (boas or execs or [None])[0]


def _linha(criterio: str, unidade: str, as_is, to_be, origem_as_is: str, origem_to_be: str, melhor: str = "menor") -> dict:
    delta = None
    if isinstance(as_is, (int, float)) and isinstance(to_be, (int, float)) and as_is:
        delta = round((to_be - as_is) / as_is, 4)
    return {"criterio": criterio, "unidade": unidade, "as_is": as_is, "to_be": to_be, "delta_pct": delta,
            "origem_as_is": origem_as_is, "origem_to_be": origem_to_be, "melhor": melhor}


def numeros(s: Session, r: Roteiro, agente_id: str | None = None) -> dict:
    """Tempo (min) e custo (R$) por tarefa do processo, com a origem de cada número."""
    pr = Premissas()
    agente = _agente(s, r, agente_id)
    bp = None
    if isinstance(agente, pm.Processo):
        v = s.get(pm.VersaoProcesso, "%s-v%d" % (agente.id, agente.versao_publicada or agente.ultima_versao))
        bp = compilar(s, ProcessoBlueprint.model_validate(v.blueprint), None, "ultima")
    elif agente:
        v = ciclo.versao(s, agente.id, agente.versao_publicada or agente.ultima_versao)
        bp = Blueprint.model_validate(v.blueprint)
    bp = bp or _padrao(r.id)
    exe = _ultima_execucao(s, agente) if agente else None
    todas = s.exec(select(rm.Execucao).where(*_execucoes_do(agente)).where(rm.Execucao.demo == False)  # noqa: E712
                   .where(rm.Execucao.status != rm.AGUARDANDO)).all() if agente else []
    escaladas = sum(1 for e in todas if e.status in (rm.ESCALADA, rm.FALHOU))
    if exe is not None and exe.duracao_estimada_ms:
        agente_min = exe.duracao_estimada_ms / 60_000
        custo_tokens = exe.custo_usd * precos.usd_para_brl(1.0)
        origem = "medido"
    else:
        agente_min = estimar_duracao_ms(bp) / 60_000
        custo_tokens = estimar_custo(bp).custo_brl
        origem = "estimado"
    conferencia = r.to_be["conferencia_min"]
    as_is_min = float(r.as_is["minutos"])
    return {"agente": agente, "execucao": exe, "origem": origem, "as_is_min": as_is_min, "agente_min": agente_min,
            "conferencia_min": conferencia, "to_be_min": agente_min + conferencia, "custo_tokens_brl": custo_tokens,
            "custo_hora": pr.custo_hora, "aproveitamento": pr.aproveitamento, "taxa_erro_manual": pr.taxa_erro_manual,
            "bp": bp, "execucoes": len(todas), "escaladas": escaladas}


def _indicadores_governanca(s: Session, r: Roteiro) -> list[dict]:
    """Roteiros sem tarefa para comparar (Lucas e Helena): o valor está em contagens medidas na própria plataforma."""
    from datetime import datetime

    from ..observability.alertas import Alerta
    publicados = (s.exec(select(am.Agente).where(am.Agente.estado == am.PUBLICADO)).all()
                  + s.exec(select(pm.Processo).where(pm.Processo.estado == am.PUBLICADO)).all())
    revisadas = [v for v in (s.exec(select(am.VersaoAgente)).all() + s.exec(select(pm.VersaoProcesso)).all()) if v.revisor and v.revisada_em]
    alertas = s.exec(select(Alerta)).all()
    if r.id == "lucas":
        tempos = [(datetime.fromisoformat(v.revisada_em) - datetime.fromisoformat(v.criada_em)).total_seconds() / 60 for v in revisadas]
        return [
            {"nome": "Agentes e processos publicados sem código novo", "valor": len(publicados), "unidade": "itens",
             "origem": "medido", "detalhe": "Cada um foi criado no Estúdio, sem fila de Engenharia."},
            {"nome": "Revisões de segurança feitas", "valor": len(revisadas), "unidade": "revisões",
             "origem": "medido", "detalhe": "Só os agentes e processos de risco alto passam pelos quatro olhos."},
            {"nome": "Tempo médio de revisão", "valor": round(sum(tempos) / len(tempos), 1) if tempos else None, "unidade": "min",
             "origem": "medido", "detalhe": "Entre o envio e o parecer; no AS IS, a fila leva semanas (hipótese)."},
            {"nome": "Incidentes detectados pelo alerta", "valor": len(alertas), "unidade": "alertas",
             "origem": "medido", "detalhe": "Abertos sozinhos quando um sistema ou agente degrada."},
        ]
    c = consolidado(s)["totais"]
    return [
        {"nome": "Redução de tempo (4 processos)", "valor": round((c["reducao_pct"] or 0) * 100), "unidade": "%",
         "origem": "estimado + hipótese", "detalhe": "AS IS é hipótese até um piloto com as áreas."},
        {"nome": "Ganho por tarefa de cada processo", "valor": c["ganho_por_rodada_brl"], "unidade": "R$",
         "origem": "premissa", "detalhe": "R$ 45/h e 50% do tempo liberado vira ganho (a validar)."},
        {"nome": "Agentes ativos", "valor": len(publicados), "unidade": "agentes", "origem": "medido", "detalhe": ""},
    ]


EXECUCOES_POR_MES = {"semanal": 52 / 12, "diaria": 365 / 12}     # premissa: a rotina roda em todas as semanas e dias


def _rotina(s: Session, agente: am.Agente | None, ganho_por_tarefa: float) -> dict | None:
    """A rotina semanal conta no ganho: cada disparo sozinho é uma tarefa feita sem ninguém iniciar (premissa a validar)."""
    if agente is None:
        return None
    from ..rotinas import descricao
    from ..rotinas.modelos import Rotina, RotinaExecucao
    rotinas = s.exec(select(Rotina).where(Rotina.agente_id == agente.id)).all()
    if not rotinas:
        return None
    ativas = [r for r in rotinas if r.ativa]
    feitas = s.exec(select(RotinaExecucao).where(RotinaExecucao.rotina_id.in_([r.id for r in rotinas]))).all()
    por_mes = sum(EXECUCOES_POR_MES[r.frequencia] for r in ativas)
    return {"agendas": [descricao(r) for r in ativas], "execucoes_feitas": len(feitas), "execucoes_por_mes": round(por_mes, 1),
            "ganho_mensal_brl": round(ganho_por_tarefa * por_mes, 2),
            "origem": "premissa (a rotina roda em todas as semanas; cada disparo vale uma tarefa sem ninguém iniciar)"}


def resultado(s: Session, r: Roteiro, agente_id: str | None = None) -> dict:
    if r.id not in COM_TAREFA:
        return {"roteiro": r.id, "titulo": r.titulo, "processo": r.processo, "agente": None, "execucao": None,
                "origem": "medido", "linhas": [], "ganho_por_tarefa_brl": 0.0, "aviso": None,
                "indicadores": _indicadores_governanca(s, r)}
    n = numeros(s, r, agente_id)
    exe = n["execucao"]
    custo_hora = n["custo_hora"]
    as_is_custo = n["as_is_min"] / 60 * custo_hora
    to_be_custo = n["custo_tokens_brl"] + n["conferencia_min"] / 60 * custo_hora
    ganho = max(n["as_is_min"] - n["to_be_min"], 0) / 60 * custo_hora * n["aproveitamento"]
    origem_tempo = ("medido (agente) + hipótese (conferência humana)" if n["origem"] == "medido"
                    else "estimado (agente) + hipótese (conferência humana)")
    linhas = []
    if r.as_is["minutos"]:
        linhas = [
            _linha("Tempo por tarefa", "min", round(n["as_is_min"], 2), round(n["to_be_min"], 2), "hipótese", origem_tempo),
            _linha("Custo por tarefa", "R$", round(as_is_custo, 2), round(to_be_custo, 2),
                   "premissa (R$ %.0f/h × tempo AS IS)" % custo_hora,
                   "%s (tokens) + premissa (conferência)" % n["origem"]),
            _linha("Produtividade", "tarefas/hora", round(60 / n["as_is_min"], 1), round(60 / n["to_be_min"], 1),
                   "hipótese", origem_tempo, "maior"),
            _linha("Erros", "% (retrabalho × escalada)", round(n["taxa_erro_manual"] * 100, 1),
                   round(n["escaladas"] / n["execucoes"] * 100, 1) if n["execucoes"] else None,
                   "premissa (retrabalho manual a validar)",
                   ("medido em %d execução(ões): %d escalada(s) para humano%s" % (
                       n["execucoes"], n["escaladas"], "; amostra pequena, não é taxa" if n["execucoes"] < 30 else ""))
                   if n["execucoes"] else "sem execução ainda"),
            _linha("ROI", "R$ por R$ 1 em tokens", None,
                   round(ganho / n["custo_tokens_brl"]) if n["custo_tokens_brl"] else None, "—",
                   "premissa (%.0f%% do tempo liberado vira ganho) ÷ tokens" % (n["aproveitamento"] * 100), "maior"),
        ]
    return {
        "roteiro": r.id, "titulo": r.titulo, "processo": r.processo,
        "agente": {"id": n["agente"].id, "nome": n["agente"].nome, "estado": n["agente"].estado,
                   "tipo": "processo" if isinstance(n["agente"], pm.Processo) else "agente"} if n["agente"] else None,
        "execucao": ({"id": exe.id, "status": exe.status, "custo_brl": round(exe.custo_usd * precos.usd_para_brl(1.0), 4),
                      "duracao_min": round(n["agente_min"], 3), "simulado": exe.simulado} if exe else None),
        "origem": n["origem"], "linhas": linhas, "ganho_por_tarefa_brl": round(ganho, 2), "indicadores": [],
        "rotina": _rotina(s, n["agente"] if isinstance(n["agente"], am.Agente) else None, ganho),
        "aviso": ("Números medidos no modo simulado: o tempo é o caminho crítico das latências típicas e os tokens são estimados."
                  if (exe is not None and exe.simulado) else None),
    }


def consolidado(s: Session) -> dict:
    """AS IS × TO BE dos quatro processos, para a Helena."""
    pr = Premissas()
    processos = []
    for rid in PROCESSOS:
        r = ROTEIROS[rid]
        n = numeros(s, r)
        ganho = max(n["as_is_min"] - n["to_be_min"], 0) / 60 * n["custo_hora"] * n["aproveitamento"]
        processos.append({
            "roteiro": rid, "persona": r.persona, "processo": r.processo,
            "as_is_min": round(n["as_is_min"], 2), "to_be_min": round(n["to_be_min"], 2),
            "reducao_pct": round(1 - n["to_be_min"] / n["as_is_min"], 4) if n["as_is_min"] else None,
            "custo_tokens_brl": round(n["custo_tokens_brl"], 4), "ganho_por_tarefa_brl": round(ganho, 2),
            "origem_to_be": n["origem"], "origem_as_is": "hipótese",
            "calculadora": {"minutos_por_tarefa": n["as_is_min"], "minutos_revisao_humana": n["conferencia_min"],
                            "custo_por_execucao": round(n["custo_tokens_brl"], 4)},
        })
    total_as_is = sum(p["as_is_min"] for p in processos)
    total_to_be = sum(p["to_be_min"] for p in processos)
    return {"processos": processos,
            "totais": {"as_is_min": round(total_as_is, 1), "to_be_min": round(total_to_be, 1),
                       "reducao_pct": round(1 - total_to_be / total_as_is, 4) if total_as_is else None,
                       "ganho_por_rodada_brl": round(sum(p["ganho_por_tarefa_brl"] for p in processos), 2)},
            "premissas": {"custo_hora": pr.custo_hora, "aproveitamento": pr.aproveitamento,
                          "taxa_erro_manual": pr.taxa_erro_manual}}
