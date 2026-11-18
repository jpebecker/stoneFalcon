"""Gestão financeira a partir das execuções registradas: custo, economia do roteador,
retorno por agente, orçamento mensal e os 5 indicadores da banca.

Regra de valor (premissa a validar num piloto): só execuções CONCLUÍDAS geram ganho.
Escaladas e falhas não contam, porque um humano fez o trabalho.
  ganho = concluídas × (minutos da tarefa manual − revisão humana) / 60 × custo-hora × aproveitamento
"""
from __future__ import annotations

from collections import defaultdict
from datetime import timedelta

from sqlmodel import Session, select

from ..agents import modelos as am
from ..audit.trilha import EventoAuditoria
from ..core.identidade import GESTOR_IA, Persona
from ..core.relogio import agora
from ..llm import precos, registro
from ..observability import metricas
from ..runtime import modelos as rm
from .calculadora import projetar
from .premissas import Premissas


def _ficha_modelo(chave: str) -> dict:
    """Linha de "gasto por modelo". Chaves de execuções antigas que saíram do registro aparecem como estão."""
    if not registro.existe(chave):
        return {"chave": chave, "modelo": chave, "provedor": "outro", "provedor_nome": "Outro", "simulado": True,
                "chamadas": 0, "custo_brl": 0.0}
    m = registro.obter(chave)
    return {"chave": m.chave, "modelo": m.nome, "provedor": m.provedor, "provedor_nome": registro.PROVEDORES[m.provedor].nome,
            "simulado": not registro.roda_de_verdade(m.chave), "chamadas": 0, "custo_brl": 0.0}


def brl(usd: float) -> float:
    return precos.usd_para_brl(usd)


def inicio_do_mes() -> str:
    return agora().replace(day=1, hour=0, minute=0, second=0).isoformat()


def gasto_no_mes(s: Session, agente_id: str) -> float:
    execs = s.exec(select(rm.Execucao).where(rm.Execucao.agente_id == agente_id)
                   .where(rm.Execucao.inicio >= inicio_do_mes())).all()
    return round(brl(sum(e.custo_usd for e in execs)), 4)


def _agentes_visiveis(s: Session, p: Persona) -> dict[str, am.Agente]:
    from ..agents import ciclo
    return {a.id: a for a in s.exec(select(am.Agente)) if ciclo.pode_ver(p, a)}


def _minutos(s: Session, a: am.Agente) -> float:
    n = a.versao_publicada or a.ultima_versao
    v = s.get(am.VersaoAgente, "%s-v%d" % (a.id, n))
    return float((v.blueprint if v else {}).get("minutos_manual", 0))


def resumo(s: Session, p: Persona, dias: int = 30, premissas: Premissas | None = None) -> dict:
    pr = premissas or Premissas()
    agentes = _agentes_visiveis(s, p)
    execs = [e for e in metricas.execucoes(s, horas=24 * dias) if e.agente_id in agentes]
    por_agente: dict[str, dict] = {}
    por_area: dict[str, dict] = defaultdict(lambda: {"execucoes": 0, "custo_brl": 0.0, "ganho_brl": 0.0})
    por_modelo: dict[str, dict] = {}
    custo = tudo_forte = ganho = 0.0
    for a in agentes.values():
        minutos = _minutos(s, a)
        meus = [e for e in execs if e.agente_id == a.id]
        concl = [e for e in meus if e.status == rm.CONCLUIDA]
        c = brl(sum(e.custo_usd for e in meus))
        g = len(concl) * max(minutos - pr.minutos_revisao_humana, 0) / 60 * pr.custo_hora * pr.aproveitamento
        mes = gasto_no_mes(s, a.id)
        por_agente[a.id] = {
            "id": a.id, "nome": a.nome, "area": a.area, "estado": a.estado, "minutos_manual": minutos,
            "execucoes": len(meus), "concluidas": len(concl), "custo_brl": round(c, 4), "ganho_brl": round(g, 2),
            "horas_liberadas": round(len(concl) * max(minutos - pr.minutos_revisao_humana, 0) / 60, 1),
            "roi": round((g - c) / c, 2) if c else None,
            "custo_medio_brl": round(c / len(meus), 5) if meus else 0.0,
            "orcamento_mensal_brl": a.orcamento_mensal_brl, "gasto_mes_brl": mes,
            "uso_orcamento": round(mes / a.orcamento_mensal_brl, 4) if a.orcamento_mensal_brl else None,
        }
        ar = por_area[a.area]
        ar["execucoes"] += len(meus)
        ar["custo_brl"] = round(ar["custo_brl"] + c, 4)
        ar["ganho_brl"] = round(ar["ganho_brl"] + g, 2)
        custo += c
        ganho += g
    for e in execs:
        tudo_forte += brl(e.custo_tudo_forte_usd)
        for chave, v in (e.por_modelo or {}).items():
            pm = por_modelo.setdefault(chave, _ficha_modelo(chave))
            pm["chamadas"] += v.get("chamadas", 0)
            pm["custo_brl"] = round(pm["custo_brl"] + brl(v.get("custo_usd", 0.0)), 4)
    dias_serie: dict[str, dict] = {}
    for e in execs:
        d = dias_serie.setdefault(e.inicio[:10], {"dia": e.inicio[:10], "execucoes": 0, "custo_brl": 0.0})
        d["execucoes"] += 1
        d["custo_brl"] = round(d["custo_brl"] + brl(e.custo_usd), 4)
        for chave, v in (e.por_modelo or {}).items():   # uma coluna "<chave>_brl" por modelo usado
            d[chave + "_brl"] = round(d.get(chave + "_brl", 0.0) + brl(v.get("custo_usd", 0.0)), 4)
    return {
        "dias": dias,
        "tem_demo": any(e.demo for e in execs),
        "execucoes": len(execs),
        "custo_brl": round(custo, 2),
        "custo_sem_roteador_brl": round(tudo_forte, 2),
        "economia_roteador_pct": round(1 - custo / tudo_forte, 4) if tudo_forte else None,
        "ganho_brl": round(ganho, 2),
        "roi_variavel": round((ganho - custo) / custo, 2) if custo else None,
        "por_agente": sorted(por_agente.values(), key=lambda x: -x["ganho_brl"]),
        "por_area": [{"area": k, **v} for k, v in sorted(por_area.items())],
        "por_modelo": sorted(por_modelo.values(), key=lambda x: x["modelo"]),
        "por_dia": [dias_serie[k] for k in sorted(dias_serie)],
        "premissas": pr.model_dump(),
    }


def indicadores(s: Session, p: Persona, dias: int = 30) -> dict:
    """Os 5 critérios de avaliação: tempo, custo operacional, produtividade, erros e ROI."""
    pr = Premissas()
    r = resumo(s, p, dias, pr)
    agentes = _agentes_visiveis(s, p)
    execs = [e for e in metricas.execucoes(s, horas=24 * dias) if e.agente_id in agentes and e.status != rm.AGUARDANDO]
    concl = [e for e in execs if e.status == rm.CONCLUIDA]
    minutos = {aid: _minutos(s, a) for aid, a in agentes.items()}
    tempo_manual = (sum(minutos[e.agente_id] for e in concl) / len(concl)) if concl else 0.0
    # tempo com agente = execução + a conferência humana do resultado (premissa)
    tempo_agente_min = ((metricas.percentil([e.duracao_estimada_ms for e in concl], 0.5) / 60_000) + pr.minutos_revisao_humana)         if concl else 0.0
    custo_manual_op = tempo_manual / 60 * pr.custo_hora
    custo_agente_op = (r["custo_brl"] / len(execs)) if execs else 0.0
    ruins = sum(1 for e in execs if e.status in (rm.ESCALADA, rm.FALHOU))
    taxa_erro = ruins / len(execs) if execs else None
    eventos = s.exec(select(EventoAuditoria).where(EventoAuditoria.quando >= (agora() - timedelta(days=dias)).isoformat())
                     .where(EventoAuditoria.tipo.in_(("ferramenta_negada", "execucao_negada", "ferramenta_executada")))).all()
    bloqueios = sum(1 for e in eventos if e.tipo != "ferramenta_executada")
    mascarados = sum(sum(m.get("quantidade", 0) for m in (e.dados.get("mascarados") or [])) for e in eventos
                     if e.tipo == "ferramenta_executada")
    projecao = projetar(pr.model_copy(update={
        "minutos_por_tarefa": tempo_manual or pr.minutos_por_tarefa,
        "custo_por_execucao": custo_agente_op or pr.custo_por_execucao}))
    return {
        "dias": dias, "tem_demo": r["tem_demo"], "execucoes": len(execs),
        "tempo_execucao": {"manual_min": round(tempo_manual, 1), "agente_min": round(tempo_agente_min, 2),
                           "revisao_humana_min": pr.minutos_revisao_humana,
                           "reducao_pct": round(1 - tempo_agente_min / tempo_manual, 4) if tempo_manual else None},
        "custo_operacional": {"manual_brl": round(custo_manual_op, 2), "agente_brl": round(custo_agente_op, 4),
                              "economia_por_operacao_brl": round(custo_manual_op - custo_agente_op, 2),
                              "economia_roteador_pct": r["economia_roteador_pct"]},
        "produtividade": {"tarefas_concluidas": len(concl), "horas_liberadas": round(sum(max(minutos[e.agente_id] - pr.minutos_revisao_humana, 0) for e in concl) / 60, 1),
                          "agentes_ativos": sum(1 for a in agentes.values() if a.estado == am.PUBLICADO)},
        "taxa_erros": {"agente": round(taxa_erro, 4) if taxa_erro is not None else None, "manual_premissa": pr.taxa_erro_manual,
                       "escaladas_ou_falhas": ruins, "acessos_bloqueados": bloqueios, "dados_mascarados": mascarados},
        "roi": {"periodo_ganho_brl": r["ganho_brl"], "periodo_custo_brl": r["custo_brl"], "periodo_roi_variavel": r["roi_variavel"],
                "projecao_payback_mes": projecao["payback_mes"], "projecao_vpl": projecao["vpl"],
                "projecao_roi": projecao["roi"], "projecao_tir_anual": projecao["tir_anual"]},
        "premissas_usadas": {"custo_hora": pr.custo_hora, "aproveitamento": pr.aproveitamento,
                             "minutos_revisao_humana": pr.minutos_revisao_humana,
                             "taxa_erro_manual": pr.taxa_erro_manual},
    }


def pode_ver_tudo(p: Persona) -> bool:
    return p.tem(GESTOR_IA)
