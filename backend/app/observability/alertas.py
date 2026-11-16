"""Alertas automáticos ao responsável (owner) do agente.

O criador não configura nada: as regras são da plataforma. Cada regra abre um
alerta (uma vez, sem repetir enquanto o problema durar), avisa quem precisa
saber e fecha sozinha quando a condição some. Tudo vai para a trilha.

Regras:
  agente_falhando    — muitas execuções recentes escaladas ou com falha
  agente_lento       — latência recente bem acima da habitual do agente
  conector_fora      — sistema integrado com erro ou fora do ar
  conector_lento     — sistema integrado respondendo devagar
  orcamento          — gasto do mês passou de 80% (atenção) ou 100% (corte) do orçamento
"""
from __future__ import annotations

import uuid

from sqlalchemy import JSON, Column
from sqlmodel import Field, Session, SQLModel, select

from ..agents import modelos as am
from ..agents.blueprint import Blueprint
from ..audit import trilha
from ..core.db import trava
from ..core.identidade import ENGENHARIA_PLATAFORMA, GESTOR_IA, PERSONAS, Persona
from ..core.relogio import agora
from ..runtime import modelos as rm
from ..tools import executor
from ..tools.catalogo import CATALOGO
from . import metricas

# ---------- limiares (premissas da plataforma, ajustáveis pelo CoE) ----------
JANELA_EXECUCOES = 10          # últimas execuções avaliadas por agente
MIN_EXECUCOES = 3              # abaixo disso não há base para alertar
FALHA_ATENCAO = 0.30           # 30% escaladas/falhas -> atenção
FALHA_CRITICO = 0.60           # 60% -> crítico
LENTIDAO_FATOR = 2.0           # p95 recente > 2x a mediana histórica
JANELA_CONECTOR_H = 1          # janela das chamadas de ferramenta
ERRO_CONECTOR = 0.30           # 30% de erro de sistema numa janela com 3+ chamadas
LENTO_CONECTOR_FATOR = 4.0     # p95 > 4x a latência típica do conector
ORCAMENTO_ATENCAO = 0.80       # 80% do orçamento mensal gasto -> atenção (100% corta a execução)

ATENCAO, CRITICO = "atencao", "critico"


class Alerta(SQLModel, table=True):
    __tablename__ = "alerta"

    id: str = Field(primary_key=True)
    chave: str = Field(index=True)                  # regra:agente:conector (evita duplicar)
    regra: str
    severidade: str
    agente_id: str | None = Field(default=None, index=True)
    conector: str | None = None
    titulo: str
    detalhe: str
    destinatarios: list = Field(default_factory=list, sa_column=Column(JSON))
    lido_por: list = Field(default_factory=list, sa_column=Column(JSON))
    ocorrencias: int = 1
    aberto_em: str
    atualizado_em: str
    resolvido_em: str | None = Field(default=None, index=True)


# =============================================================
# Condições
# =============================================================
def _agentes_ativos(s: Session) -> list[tuple[am.Agente, Blueprint]]:
    saida = []
    for a in s.exec(select(am.Agente).where(am.Agente.estado.in_((am.PUBLICADO, am.PAUSADO)))):
        if a.versao_publicada is None:
            continue
        v = s.get(am.VersaoAgente, "%s-v%d" % (a.id, a.versao_publicada))
        saida.append((a, Blueprint.model_validate(v.blueprint)))
    return saida


def _condicoes_agente(s: Session, a: am.Agente) -> list[dict]:
    execs = [e for e in metricas.execucoes(s, a.id, horas=24 * 30) if e.status != rm.AGUARDANDO]
    recentes = execs[-JANELA_EXECUCOES:]
    achados = []
    if len(recentes) >= MIN_EXECUCOES:
        ruins = [e for e in recentes if e.status in (rm.ESCALADA, rm.FALHOU)]
        taxa = len(ruins) / len(recentes)
        if taxa >= FALHA_ATENCAO:
            motivo = ruins[-1].motivo or "sem motivo registrado"
            achados.append({"regra": "agente_falhando", "severidade": CRITICO if taxa >= FALHA_CRITICO else ATENCAO,
                            "conector": None, "titulo": "%s está falhando" % a.nome,
                            "detalhe": "%d de %d execuções recentes não concluíram (%.0f%%). Último motivo: %s"
                                       % (len(ruins), len(recentes), taxa * 100, motivo)})
    if a.orcamento_mensal_brl:
        from ..finance.resumo import gasto_no_mes
        gasto = gasto_no_mes(s, a.id)
        uso = gasto / a.orcamento_mensal_brl
        if uso >= ORCAMENTO_ATENCAO:
            achados.append({"regra": "orcamento", "severidade": CRITICO if uso >= 1 else ATENCAO, "conector": None,
                            "titulo": "%s %s o orçamento do mês" % (a.nome, "atingiu" if uso >= 1 else "está perto de atingir"),
                            "detalhe": "Gasto de R$ %.2f de R$ %.2f (%.0f%%).%s" % (
                                gasto, a.orcamento_mensal_brl, uso * 100,
                                " Novas execuções estão bloqueadas até o próximo mês ou até o orçamento ser revisto." if uso >= 1 else "")})
    antigas = execs[:-JANELA_EXECUCOES]
    if len(antigas) >= 5 and len(recentes) >= MIN_EXECUCOES:
        base = metricas.percentil([e.duracao_estimada_ms for e in antigas], 0.5)
        p95 = metricas.percentil([e.duracao_estimada_ms for e in recentes], 0.95)
        if base and p95 > LENTIDAO_FATOR * base:
            achados.append({"regra": "agente_lento", "severidade": ATENCAO, "conector": None,
                            "titulo": "%s está mais lento que o normal" % a.nome,
                            "detalhe": "Latência p95 recente de %.1f s contra %.1f s habituais."
                                       % (p95 / 1000, base / 1000)})
    return achados


def _condicoes_conectores(s: Session) -> dict[str, dict]:
    uso = metricas.chamadas_ferramentas(s, horas=JANELA_CONECTOR_H)
    achados = {}
    for cid, esp in CATALOGO.items():
        est = executor.estado(s, cid)
        u = uso.get(cid, {})
        if est.falha in ("erro", "fora_do_ar") or (u.get("chamadas", 0) >= 3 and u.get("taxa_erro", 0) >= ERRO_CONECTOR):
            causa = {"erro": "respondendo com erro", "fora_do_ar": "fora do ar"}.get(est.falha) or \
                "com %.0f%% de erro na última hora" % (u["taxa_erro"] * 100)
            achados[cid] = {"regra": "conector_fora", "severidade": CRITICO,
                            "titulo": "Sistema integrado com problema: %s" % esp.nome,
                            "detalhe": "\"%s\" está %s. Agentes que dependem dele vão escalar para humanos até normalizar." % (esp.nome, causa)}
        elif est.falha == "lento" or (u.get("chamadas", 0) >= 3 and u.get("latencia_p95_ms", 0) > LENTO_CONECTOR_FATOR * esp.latencia_ms):
            achados[cid] = {"regra": "conector_lento", "severidade": ATENCAO,
                            "titulo": "Sistema integrado lento: %s" % esp.nome,
                            "detalhe": "\"%s\" está respondendo bem acima do tempo típico (%d ms). As execuções vão demorar mais."
                                       % (esp.nome, esp.latencia_ms)}
    return achados


# =============================================================
# Abertura, atualização e fechamento
# =============================================================
def _engenharia() -> list[str]:
    return [p.id for p in PERSONAS.values() if p.tem(ENGENHARIA_PLATAFORMA)]


def _abrir_ou_atualizar(s: Session, abertos: dict[str, Alerta], chave: str, dados: dict, agente_id: str | None,
                        destinatarios: list[str], vistos: set[str]) -> None:
    vistos.add(chave)
    agora_iso = agora().isoformat()
    a = abertos.get(chave)
    if a:
        if a.detalhe != dados["detalhe"] or a.severidade != dados["severidade"]:
            a.detalhe, a.severidade, a.atualizado_em = dados["detalhe"], dados["severidade"], agora_iso
            a.ocorrencias += 1
            s.add(a)
        return
    a = Alerta(id=uuid.uuid4().hex[:12], chave=chave, regra=dados["regra"], severidade=dados["severidade"],
               agente_id=agente_id, conector=dados.get("conector"), titulo=dados["titulo"], detalhe=dados["detalhe"],
               destinatarios=sorted(set(destinatarios)), lido_por=[], aberto_em=agora_iso, atualizado_em=agora_iso)
    s.add(a)
    abertos[chave] = a
    trilha.registrar(s, "alerta_aberto", "sistema", agente_id, {
        "alerta": a.id, "regra": a.regra, "severidade": a.severidade, "conector": a.conector,
        "destinatarios": a.destinatarios, "titulo": a.titulo})


def avaliar(s: Session) -> dict:
    """Roda todas as regras. Devolve {abertos, resolvidos} desta rodada."""
    with trava:
        abertos = {a.chave: a for a in s.exec(select(Alerta).where(Alerta.resolvido_em.is_(None)))}
        antes = set(abertos)
        vistos: set[str] = set()
        ativos = _agentes_ativos(s)

        for a, _bp in ativos:
            for c in _condicoes_agente(s, a):
                _abrir_ou_atualizar(s, abertos, "%s:%s:" % (c["regra"], a.id), c, a.id, [a.dono], vistos)

        for cid, c in _condicoes_conectores(s).items():
            c = dict(c, conector=cid)
            dependentes = [(a, bp) for a, bp in ativos if cid in bp.ferramentas_usadas()]
            for a, _bp in dependentes:
                _abrir_ou_atualizar(s, abertos, "%s:%s:%s" % (c["regra"], a.id, cid), c, a.id,
                                    [a.dono] + _engenharia(), vistos)
            if not dependentes:
                _abrir_ou_atualizar(s, abertos, "%s::%s" % (c["regra"], cid), c, None, _engenharia(), vistos)

        resolvidos = []
        for chave in antes - vistos:
            a = abertos[chave]
            a.resolvido_em = a.atualizado_em = agora().isoformat()
            s.add(a)
            resolvidos.append(a.id)
            trilha.registrar(s, "alerta_resolvido", "sistema", a.agente_id, {"alerta": a.id, "regra": a.regra})
        s.commit()
        return {"abertos": sorted(vistos - antes), "resolvidos": resolvidos}


# =============================================================
# Leitura
# =============================================================
def visiveis(s: Session, p: Persona, so_abertos: bool = True) -> list[Alerta]:
    q = select(Alerta)
    if so_abertos:
        q = q.where(Alerta.resolvido_em.is_(None))
    todos = s.exec(q.order_by(Alerta.atualizado_em.desc())).all()
    if p.tem(GESTOR_IA):
        return list(todos)
    return [a for a in todos if p.id in (a.destinatarios or [])]


def score(taxa_sucesso: float | None, alertas_abertos: list[Alerta]) -> dict:
    """0 a 100. Começa pela taxa de sucesso e perde pontos por alerta aberto."""
    nota = 100.0 if taxa_sucesso is None else 40 + 60 * taxa_sucesso
    for al in alertas_abertos:
        nota -= 25 if al.severidade == CRITICO else 10
    nota = max(0, min(100, round(nota)))
    return {"nota": nota, "status": "saudavel" if nota >= 80 else "atencao" if nota >= 50 else "critico"}
