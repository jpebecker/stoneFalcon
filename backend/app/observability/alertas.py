"""Alertas automáticos ao responsável (owner) do agente ou do processo.

O criador não configura nada: as regras são da plataforma. Cada regra abre um
alerta (uma vez, sem repetir enquanto o problema durar), avisa quem precisa
saber e fecha sozinha quando a condição some. Tudo vai para a trilha.

Regras:
  agente_falhando    — muitas execuções recentes escaladas ou com falha
  agente_lento       — latência recente bem acima da habitual do agente
  conector_fora      — sistema integrado com erro ou fora do ar
  conector_lento     — sistema integrado respondendo devagar
  orcamento          — gasto do mês passou de 80% (atenção) ou 100% (corte) do orçamento
  provedor_fora      — provedor de IA indisponível (queda simulada pelo CoE; o balanceador delega)

v8.1: as mesmas regras valem para PROCESSOS publicados ou pausados (agente_falhando/agente_lento viram processo_falhando/
processo_lento, e `orcamento` e `conector_*` ganham o processo como dono). O alerta de processo vai ao dono do processo, aos criadores das áreas com quem ele é compartilhado (v8.3) e, no caso de
sistema, à Engenharia e leva a "Abrir o processo". Alerta de sistema vale UMA vez por processo (não por trabalhador):
os agentes trabalhadores de um processo não abrem alerta de SISTEMA por conta própria (quem abre é o processo). Falhando, lento e
orçamento seguem por agente, mas as execuções de um processo são do processo, então o trabalhador só alerta pelo que rodar
sozinho. Os agentes que rodam sozinhos continuam como estavam.
"""
from __future__ import annotations

import uuid

from sqlalchemy import JSON, Column
from sqlmodel import Field, Session, SQLModel, select

from ..agents import modelos as am
from ..agents.blueprint import Blueprint
from ..agents.ciclo import ErroCiclo
from ..audit import trilha
from ..core.db import trava
from ..core.identidade import CRIADOR, ENGENHARIA_PLATAFORMA, GESTOR_IA, PERSONAS, Persona
from ..core.relogio import agora
from ..llm import balanceador, registro
from ..processos import modelos as pm
from ..processos.blueprint import ProcessoBlueprint
from ..processos.compilar import compilar
from ..runtime import modelos as rm
from ..tools import executor
from ..tools.catalogo import disponiveis
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
    processo_id: str | None = Field(default=None, index=True)   # v8.1: o alerta é de um processo (agente_id fica vazio)
    conector: str | None = None
    titulo: str
    detalhe: str
    destinatarios: list = Field(default_factory=list, sa_column=Column(JSON))
    lido_por: list = Field(default_factory=list, sa_column=Column(JSON))
    ocorrencias: int = 1
    aberto_em: str
    atualizado_em: str
    resolvido_em: str | None = Field(default=None, index=True)
    tratando_por: str | None = Field(default=None, index=True)   # v8.1: quem assumiu o alerta (fica depois de resolvido)
    tratando_nota: str | None = None
    tratando_desde: str | None = None


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


def _processos_ativos(s: Session) -> list[tuple[pm.Processo, Blueprint]]:
    """Processos publicados ou pausados, com o fluxo publicado já compilado (os agentes de cada bloco resolvidos)."""
    saida = []
    for p in s.exec(select(pm.Processo).where(pm.Processo.estado.in_((am.PUBLICADO, am.PAUSADO)))):
        if p.versao_publicada is None:
            continue
        v = s.get(pm.VersaoProcesso, "%s-v%d" % (p.id, p.versao_publicada))
        if v is None:   # versão publicada sumiu do banco: o alerta não pode quebrar a avaliação dos outros
            continue
        try:
            saida.append((p, compilar(s, ProcessoBlueprint.model_validate(v.blueprint), None, "publicada")))
        except ErroCiclo:   # bloco com agente que não existe mais: o ciclo de vida já avisa; o alerta não pode quebrar
            continue
    return saida


def _agentes_de_processo(processos: list[tuple[pm.Processo, Blueprint]]) -> set[str]:
    """Os agentes trabalhadores que estão num processo ativo: quem alerta por eles é o processo."""
    return {p.agente_ref["id"] for _p, bp in processos for p in bp.passos if p.agente_ref}


def _condicoes_dono(s: Session, d, tipo: str) -> list[dict]:
    """Falhando, lento e orçamento de um agente (que roda sozinho) ou de um processo (`tipo`)."""
    from ..finance.resumo import gasto_no_mes
    execs = [e for e in metricas.execucoes(s, d.id, horas=24 * 30, tipo=tipo) if e.status != rm.AGUARDANDO]
    recentes = execs[-JANELA_EXECUCOES:]
    achados = []
    if len(recentes) >= MIN_EXECUCOES:
        ruins = [e for e in recentes if e.status in (rm.ESCALADA, rm.FALHOU)]
        taxa = len(ruins) / len(recentes)
        if taxa >= FALHA_ATENCAO:
            motivo = ruins[-1].motivo or "sem motivo registrado"
            achados.append({"regra": tipo + "_falhando", "severidade": CRITICO if taxa >= FALHA_CRITICO else ATENCAO,
                            "conector": None, "titulo": "%s está falhando" % d.nome,
                            "detalhe": "%d de %d execuções recentes não concluíram (%.0f%%). Último motivo: %s"
                                       % (len(ruins), len(recentes), taxa * 100, motivo)})
    if d.orcamento_mensal_brl:
        gasto = gasto_no_mes(s, d.id, tipo)
        uso = gasto / d.orcamento_mensal_brl
        if uso >= ORCAMENTO_ATENCAO:
            achados.append({"regra": "orcamento", "severidade": CRITICO if uso >= 1 else ATENCAO, "conector": None,
                            "titulo": "%s %s o orçamento do mês" % (d.nome, "atingiu" if uso >= 1 else "está perto de atingir"),
                            "detalhe": "Gasto de R$ %.2f de R$ %.2f (%.0f%%).%s" % (
                                gasto, d.orcamento_mensal_brl, uso * 100,
                                " Novas execuções estão bloqueadas até o próximo mês ou até o orçamento ser revisto." if uso >= 1 else "")})
    antigas = execs[:-JANELA_EXECUCOES]
    if len(antigas) >= 5 and len(recentes) >= MIN_EXECUCOES:
        base = metricas.percentil([e.duracao_estimada_ms for e in antigas], 0.5)
        p95 = metricas.percentil([e.duracao_estimada_ms for e in recentes], 0.95)
        if base and p95 > LENTIDAO_FATOR * base:
            achados.append({"regra": tipo + "_lento", "severidade": ATENCAO, "conector": None,
                            "titulo": "%s está mais lento que o normal" % d.nome,
                            "detalhe": "Latência p95 recente de %.1f s contra %.1f s habituais."
                                       % (p95 / 1000, base / 1000)})
    return achados


def _condicoes_agente(s: Session, a: am.Agente) -> list[dict]:
    return _condicoes_dono(s, a, "agente")


def regras_que_valem(s: Session, d, tipo: str) -> set[str]:
    """As regras de falhando, lento e orçamento que valem agora para `d` (sem abrir alerta): o cenário da demo usa para não
    moldar de novo o que já está moldado."""
    return {c["regra"] for c in _condicoes_dono(s, d, tipo)}


def _condicoes_conectores(s: Session) -> dict[str, dict]:
    uso = metricas.chamadas_ferramentas(s, horas=JANELA_CONECTOR_H)
    achados = {}
    for cid, esp in disponiveis().items():
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


def destinatarios_do_processo(p: pm.Processo) -> list[str]:
    """Quem responde por um processo: o dono e, v8.3, os criadores de cada área com quem ele é compartilhado (elas dependem
    dele, então ouvem dos problemas dele). Sem repetir ninguém."""
    areas = set(p.compartilhado_com or [])
    return sorted({p.dono} | {x.id for x in PERSONAS.values() if x.area in areas and x.tem(CRIADOR)})


def _abrir_ou_atualizar(s: Session, abertos: dict[str, Alerta], chave: str, dados: dict, agente_id: str | None,
                        destinatarios: list[str], vistos: set[str], processo_id: str | None = None) -> None:
    vistos.add(chave)
    agora_iso = agora().isoformat()
    a = abertos.get(chave)
    if a:
        novos = sorted(set(destinatarios))
        if novos != sorted(a.destinatarios or []):   # o processo passou a ser (ou deixou de ser) compartilhado com outra área
            trilha.registrar(s, "alerta_destinatarios_alterados", "sistema", agente_id or processo_id,
                             {"alerta": a.id, "de": sorted(a.destinatarios or []), "para": novos},
                             dono_tipo="processo" if processo_id else "agente")
            a.destinatarios, a.atualizado_em = novos, agora_iso
            s.add(a)
        if a.detalhe != dados["detalhe"] or a.severidade != dados["severidade"]:
            a.detalhe, a.severidade, a.atualizado_em = dados["detalhe"], dados["severidade"], agora_iso
            a.ocorrencias += 1
            s.add(a)
        return
    a = Alerta(id=uuid.uuid4().hex[:12], chave=chave, regra=dados["regra"], severidade=dados["severidade"],
               agente_id=agente_id, processo_id=processo_id, conector=dados.get("conector"), titulo=dados["titulo"], detalhe=dados["detalhe"],
               destinatarios=sorted(set(destinatarios)), lido_por=[], aberto_em=agora_iso, atualizado_em=agora_iso)
    s.add(a)
    abertos[chave] = a
    trilha.registrar(s, "alerta_aberto", "sistema", agente_id or processo_id, {
        "alerta": a.id, "regra": a.regra, "severidade": a.severidade, "conector": a.conector,
        "destinatarios": a.destinatarios, "titulo": a.titulo}, dono_tipo="processo" if processo_id else "agente")


def avaliar(s: Session) -> dict:
    """Roda todas as regras. Devolve {abertos, resolvidos} desta rodada."""
    with trava:
        abertos = {a.chave: a for a in s.exec(select(Alerta).where(Alerta.resolvido_em.is_(None)))
                   if not a.regra.startswith("plugin_")}   # alertas do marketplace têm ciclo próprio
        antes = set(abertos)
        vistos: set[str] = set()
        ativos = _agentes_ativos(s)
        processos = _processos_ativos(s)
        trabalhadores = _agentes_de_processo(processos)

        for a, _bp in ativos:
            for c in _condicoes_agente(s, a):
                _abrir_ou_atualizar(s, abertos, "%s:%s:" % (c["regra"], a.id), c, a.id, [a.dono], vistos)
        for p, _bp in processos:
            for c in _condicoes_dono(s, p, "processo"):
                _abrir_ou_atualizar(s, abertos, "%s:%s:" % (c["regra"], p.id), c, None, destinatarios_do_processo(p), vistos, processo_id=p.id)

        for cid, c in _condicoes_conectores(s).items():
            c = dict(c, conector=cid)
            dep_processos = [p for p, bp in processos if cid in bp.ferramentas_usadas()]
            dependentes = [(a, bp) for a, bp in ativos if cid in bp.ferramentas_usadas() and a.id not in trabalhadores]
            for p in dep_processos:   # uma vez por processo, não por trabalhador
                _abrir_ou_atualizar(s, abertos, "%s:%s:%s" % (c["regra"], p.id, cid), c, None,
                                    destinatarios_do_processo(p) + _engenharia(), vistos, processo_id=p.id)
            for a, _bp in dependentes:
                _abrir_ou_atualizar(s, abertos, "%s:%s:%s" % (c["regra"], a.id, cid), c, a.id,
                                    [a.dono] + _engenharia(), vistos)
            if not dependentes and not dep_processos:
                _abrir_ou_atualizar(s, abertos, "%s::%s" % (c["regra"], cid), c, None, _engenharia(), vistos)

        for pid in sorted(balanceador.fora_do_ar()):   # queda de provedor de IA (simulada pelo CoE)
            nome = registro.PROVEDORES[pid].nome
            _abrir_ou_atualizar(s, abertos, "provedor_fora::" + pid, {
                "regra": "provedor_fora", "severidade": ATENCAO, "titulo": "Provedor de IA indisponível: %s" % nome,
                "detalhe": "%s está fora do ar (queda simulada). Os passos automáticos estão sendo delegados a outro provedor "
                           "capaz; os passos com modelo fixado desse provedor continuam nele." % nome},
                None, [p.id for p in PERSONAS.values() if p.tem(GESTOR_IA)] + _engenharia(), vistos)

        resolvidos = []
        for chave in antes - vistos:
            a = abertos[chave]
            a.resolvido_em = a.atualizado_em = agora().isoformat()
            s.add(a)
            resolvidos.append(a.id)
            trilha.registrar(s, "alerta_resolvido", "sistema", a.agente_id or a.processo_id, {"alerta": a.id, "regra": a.regra, "tratando_por": a.tratando_por},
                             dono_tipo="processo" if a.processo_id else "agente")
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


def marcar_lido(s: Session, al: Alerta, p: Persona) -> Alerta:
    """"Marcar como lido" para `p` (a tela e a demonstração usam esta mesma função; não mexe no estado do alerta)."""
    if p.id not in (al.lido_por or []):
        al.lido_por = sorted(set(al.lido_por or []) | {p.id})
        s.add(al)
        s.commit()
    return al


def score(taxa_sucesso: float | None, alertas_abertos: list[Alerta]) -> dict:
    """0 a 100. Começa pela taxa de sucesso e perde pontos por alerta aberto."""
    nota = 100.0 if taxa_sucesso is None else 40 + 60 * taxa_sucesso
    for al in alertas_abertos:
        nota -= 25 if al.severidade == CRITICO else 10
    nota = max(0, min(100, round(nota)))
    return {"nota": nota, "status": "saudavel" if nota >= 80 else "atencao" if nota >= 50 else "critico"}
