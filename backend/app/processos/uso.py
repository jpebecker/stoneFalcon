"""Quem usa quem: em que processos um agente trabalhador está, e quais agentes de um processo não estão em dia."""
from __future__ import annotations

from sqlmodel import Session, select

from ..agents import modelos as am
from ..roteiros.catalogo import ROTEIROS
from . import modelos as pm
from .blueprint import ProcessoBlueprint


def _blueprint(s: Session, p: pm.Processo) -> ProcessoBlueprint | None:
    v = s.get(pm.VersaoProcesso, "%s-v%d" % (p.id, p.versao_publicada or p.ultima_versao))
    return ProcessoBlueprint.model_validate(v.blueprint) if v else None


def usado_em(s: Session, agente_id: str) -> list[dict]:
    """Processos (não depreciados) que têm um bloco com este agente: nome, dono, área e o processo AS IS que realizam."""
    saida = []
    for p in s.exec(select(pm.Processo).order_by(pm.Processo.nome)):
        if p.estado == am.DEPRECIADO:
            continue
        bp = _blueprint(s, p)
        if bp is None or agente_id not in bp.agentes_usados():
            continue
        r = ROTEIROS.get(p.roteiro_id or "")
        saida.append({"id": p.id, "nome": p.nome, "dono": p.dono, "area": p.area, "estado": p.estado,
                      "as_is": {"roteiro_id": r.id, "processo": r.processo, "persona": r.persona} if r else None})
    return saida


def agentes_com_problema(s: Session, p: pm.Processo) -> list[dict]:
    """Agentes do processo que estão pausados, depreciados ou ainda não publicados: o processo escala nesses blocos."""
    bp = _blueprint(s, p)
    if bp is None:
        return []
    problemas = []
    for aid in bp.agentes_usados():
        a = s.get(am.Agente, aid)
        if a is None:
            problemas.append({"id": aid, "nome": aid, "estado": "removido", "motivo": "O agente não existe mais."})
        elif a.estado in (am.PAUSADO, am.DEPRECIADO) or (a.versao_publicada is None and p.versao_publicada is not None):
            problemas.append({"id": a.id, "nome": a.nome, "estado": a.estado, "motivo": a.motivo_estado})
    return problemas
