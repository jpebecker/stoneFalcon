"""Quem vê uma execução: quem disparou, a área dela, o CoE de IA e (v8.3) as áreas com quem o processo dono foi compartilhado.

As rotas só orquestram; a regra de visibilidade mora aqui, para a lista e o detalhe usarem a mesma.
"""
from __future__ import annotations

from sqlmodel import Session, select

from ..agents.ciclo import compartilhado_com_area
from ..agents.dono import PROCESSO
from ..core.identidade import GESTOR_IA, Persona
from ..processos import modelos as pm
from . import modelos as m


def processos_compartilhados_com(s: Session, area: str) -> list[str]:
    """Os ids dos processos que outras áreas compartilham com `area`."""
    return [x.id for x in s.exec(select(pm.Processo)) if compartilhado_com_area(x, area)]


def _recebe_o_processo(s: Session, p: Persona, exe: m.Execucao) -> bool:
    """A execução é de um processo compartilhado com a área de `p` (as duas áreas veem a mesma história do processo)."""
    if exe.dono_tipo != PROCESSO or not exe.dono_id:
        return False
    proc = s.get(pm.Processo, exe.dono_id)
    return proc is not None and compartilhado_com_area(proc, p.area)


def pode_ver(s: Session, p: Persona, exe: m.Execucao) -> bool:
    return p.id == exe.persona or p.area == exe.area or p.tem(GESTOR_IA) or _recebe_o_processo(s, p, exe)


def filtro(s: Session, p: Persona):
    """A condição SQL das execuções que `p` vê, ou None quando vê todas (CoE de IA)."""
    if p.tem(GESTOR_IA):
        return None
    return ((m.Execucao.persona == p.id) | (m.Execucao.area == p.area)
            | ((m.Execucao.dono_tipo == PROCESSO) & m.Execucao.dono_id.in_(processos_compartilhados_com(s, p.area))))
