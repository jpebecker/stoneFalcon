"""Execuções de agentes: rodar (sandbox), acompanhar e decidir pendências humanas.

Na F4 a execução passa a ser pelo id do agente publicado; aqui o blueprint vem no pedido,
como no "Testar" do Estúdio.
"""
import json
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlmodel import Session, select

from .. import guardrails
from ..agents.blueprint import Blueprint
from ..core.db import sessao
from ..core.identidade import CRIADOR, GESTOR_IA, Persona, exigir, usuario_atual
from ..rotinas import marcar as marcar_rotina
from ..observability import avaliar_seguro
from ..runtime import modelos as m
from ..runtime import motor
from ..seed.agentes_exemplo import EXEMPLOS

rotas = APIRouter(prefix="/api/v1", tags=["execucoes"])


def _publico(exe: m.Execucao, mapa: dict | None = None) -> dict:
    d = exe.model_dump()
    d["custo_brl"] = round(exe.custo_usd * motor.precos.usd_para_brl(1.0), 4)
    if mapa:   # só na resposta a quem disparou: dados reais restaurados
        d["resultado_tela"] = guardrails.restaurar(exe.resultado or "", mapa)
        d["passos_tela"] = json.loads(guardrails.restaurar(json.dumps(exe.passos, ensure_ascii=False), mapa))
    return d


def _pode_ver(p: Persona, exe: m.Execucao) -> None:
    if not (p.id == exe.persona or p.area == exe.area or p.tem(GESTOR_IA)):
        raise HTTPException(status_code=403, detail="Você não tem acesso a esta execução.")


@rotas.get("/agentes-exemplo")
def agentes_exemplo(_p: Persona = Depends(usuario_atual)):
    return {k: bp.model_dump() for k, bp in EXEMPLOS.items()}


class PedidoExecucao(BaseModel):
    blueprint: Blueprint | None = None
    exemplo: str | None = None
    entrada: dict[str, Any] = Field(default_factory=dict)


@rotas.post("/execucoes")
def executar(pedido: PedidoExecucao, pessoa: Persona = Depends(usuario_atual), s: Session = Depends(sessao)):
    """Sandbox de rascunhos (como o "Testar" do Estúdio): só para criadores, sempre na área de quem
    chama e marcado como teste. Agentes publicados rodam por /agentes/{id}/executar, com governança."""
    exigir(pessoa, CRIADOR)
    bp = pedido.blueprint or EXEMPLOS.get(pedido.exemplo or "")
    if bp is None:
        raise HTTPException(status_code=422, detail="Envie um blueprint ou o nome de um agente de exemplo.")
    bp = bp.model_copy(update={"area": pessoa.area})
    faltando = [c for c in bp.ids_campos() if pedido.entrada.get(c) in (None, "")]
    if faltando:
        raise HTTPException(status_code=422, detail="Preencha: %s." % ", ".join(faltando))
    exe, mapa = motor.executar(s, pessoa, bp, pedido.entrada, agente_id="sandbox")
    return _publico(exe, mapa)


@rotas.get("/execucoes")
def listar(pendentes: bool = False, limite: int = 50, pessoa: Persona = Depends(usuario_atual),
           s: Session = Depends(sessao)):
    q = select(m.Execucao)
    if not pessoa.tem(GESTOR_IA):
        q = q.where((m.Execucao.persona == pessoa.id) | (m.Execucao.area == pessoa.area))
    if pendentes:
        q = q.where(m.Execucao.status == m.AGUARDANDO)
    itens = s.exec(q.order_by(m.Execucao.inicio.desc()).limit(min(max(limite, 1), 500))).all()
    return marcar_rotina(s, [_publico(e) for e in itens])


@rotas.get("/execucoes/{execucao_id}")
def detalhe(execucao_id: str, pessoa: Persona = Depends(usuario_atual), s: Session = Depends(sessao)):
    exe = s.get(m.Execucao, execucao_id)
    if exe is None:
        raise HTTPException(status_code=404, detail="Execução não encontrada.")
    _pode_ver(pessoa, exe)
    return marcar_rotina(s, [_publico(exe)])[0]


class PedidoDecisao(BaseModel):
    aprovar: bool


@rotas.post("/execucoes/{execucao_id}/decisao")
def decidir(execucao_id: str, pedido: PedidoDecisao, pessoa: Persona = Depends(usuario_atual),
            s: Session = Depends(sessao)):
    try:
        exe = motor.retomar(s, execucao_id, pessoa, pedido.aprovar)
    except motor.ErroRetomada as e:
        raise HTTPException(status_code=409, detail=str(e))
    avaliar_seguro(s)
    s.refresh(exe)
    return _publico(exe)
