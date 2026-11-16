"""Métricas de saúde calculadas a partir do que a plataforma já registra.

- Execuções (tabela execucao): sucesso, escaladas, latência, custo por agente.
- Chamadas de ferramenta (eventos da trilha): erro e latência por conector, de
  TODOS os agentes, inclusive testes no sandbox.
Nada aqui depende do criador instrumentar o agente: a observabilidade é nativa.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import timedelta
from statistics import median

from sqlmodel import Session, select

from ..audit.trilha import EventoAuditoria
from ..core.relogio import agora
from ..llm import precos
from ..runtime import modelos as rm

EVENTOS_FERRAMENTA = ("ferramenta_executada", "ferramenta_erro")
ERROS_DE_SISTEMA = {"falha", "sistema", "limite"}   # erros que indicam sistema doente (não entrada inválida)


def percentil(valores: list[float], p: float) -> float:
    if not valores:
        return 0.0
    v = sorted(valores)
    k = (len(v) - 1) * p
    i = int(k)
    return v[i] if i + 1 >= len(v) else v[i] + (v[i + 1] - v[i]) * (k - i)


def _desde(horas: float) -> str:
    return (agora() - timedelta(hours=horas)).isoformat()


def execucoes(s: Session, agente_id: str | None = None, horas: float = 24 * 7) -> list[rm.Execucao]:
    q = select(rm.Execucao).where(rm.Execucao.inicio >= _desde(horas))
    if agente_id:
        q = q.where(rm.Execucao.agente_id == agente_id)
    return list(s.exec(q.order_by(rm.Execucao.inicio)))


def resumo_execucoes(execs: list[rm.Execucao]) -> dict:
    fechadas = [e for e in execs if e.status != rm.AGUARDANDO]
    n = len(fechadas)
    ok = sum(1 for e in fechadas if e.status == rm.CONCLUIDA)
    lat = [e.duracao_estimada_ms for e in fechadas]
    custo = sum(e.custo_usd for e in execs)
    return {
        "execucoes": len(execs),
        "concluidas": ok,
        "escaladas": sum(1 for e in fechadas if e.status == rm.ESCALADA),
        "falhas": sum(1 for e in fechadas if e.status == rm.FALHOU),
        "aguardando": sum(1 for e in execs if e.status == rm.AGUARDANDO),
        "taxa_sucesso": round(ok / n, 4) if n else None,
        "latencia_p50_ms": int(percentil(lat, 0.5)),
        "latencia_p95_ms": int(percentil(lat, 0.95)),
        "custo_brl": round(precos.usd_para_brl(custo), 4),
        "custo_medio_brl": round(precos.usd_para_brl(custo / len(execs)), 5) if execs else 0.0,
    }


def por_dia(execs: list[rm.Execucao]) -> list[dict]:
    dias: dict[str, dict] = {}
    for e in execs:
        d = dias.setdefault(e.inicio[:10], {"dia": e.inicio[:10], "execucoes": 0, "concluidas": 0, "escaladas": 0, "custo_brl": 0.0})
        d["execucoes"] += 1
        d["concluidas"] += e.status == rm.CONCLUIDA
        d["escaladas"] += e.status == rm.ESCALADA
        d["custo_brl"] = round(d["custo_brl"] + precos.usd_para_brl(e.custo_usd), 4)
    return [dias[k] for k in sorted(dias)]


def chamadas_ferramentas(s: Session, horas: float = 24) -> dict[str, dict]:
    """Por conector: chamadas, erros de sistema, taxa de erro e latência, na janela."""
    eventos = s.exec(select(EventoAuditoria).where(EventoAuditoria.tipo.in_(EVENTOS_FERRAMENTA))
                     .where(EventoAuditoria.quando >= _desde(horas)).order_by(EventoAuditoria.seq)).all()
    por: dict[str, dict] = defaultdict(lambda: {"chamadas": 0, "erros": 0, "latencias": [], "ultimo_erro": None,
                                                "agentes": set()})
    for e in eventos:
        c = por[e.dados.get("conector")]
        c["chamadas"] += 1
        c["latencias"].append(e.dados.get("latencia_ms") or 0)
        if e.agente_id:
            c["agentes"].add(e.agente_id)
        if e.tipo == "ferramenta_erro" and e.dados.get("tipo_erro") in ERROS_DE_SISTEMA:
            c["erros"] += 1
            c["ultimo_erro"] = {"quando": e.quando, "erro": e.dados.get("erro")}
    saida = {}
    for cid, c in por.items():
        saida[cid] = {"chamadas": c["chamadas"], "erros": c["erros"],
                      "taxa_erro": round(c["erros"] / c["chamadas"], 4) if c["chamadas"] else 0.0,
                      "latencia_p50_ms": int(median(c["latencias"])) if c["latencias"] else 0,
                      "latencia_p95_ms": int(percentil(c["latencias"], 0.95)),
                      "ultimo_erro": c["ultimo_erro"], "agentes": sorted(c["agentes"])}
    return saida
