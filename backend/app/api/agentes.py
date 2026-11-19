"""Agentes: criar, versionar, publicar (com revisão), operar e executar."""
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlmodel import Session, select

from ..agents import ciclo
from ..agents import modelos as m
from ..agents.blueprint import Blueprint
from ..agents.diff import comparar
from ..audit import trilha
from ..core.db import sessao
from ..core.identidade import GESTOR_IA, REVISOR_SEGURANCA, Persona, usuario_atual
from ..observability import avaliar_seguro
from ..plugins import servico as plugins
from ..runtime import motor
from ..runtime.modelos import Execucao
from ..rotinas import marcar as marcar_rotina
from .execucoes import _publico as execucao_publica

rotas = APIRouter(prefix="/api/v1", tags=["agentes"])

_EVENTOS_CICLO = {"agente_criado", "agente_modificado", "agente_enviado_revisao", "revisao_aprovada",
                  "revisao_rejeitada", "agente_publicado", "agente_pausado", "agente_retomado",
                  "agente_depreciado", "agente_compartilhado", "execucao_escalada", "execucao_negada"}


def _dump(s: Session, obj) -> dict:
    s.refresh(obj)   # o commit da auditoria expira o objeto
    return obj.model_dump()


def _erro(e: ciclo.ErroCiclo):
    raise HTTPException(status_code=e.status, detail=str(e))


def _resumo(a: m.Agente, s: Session) -> dict:
    d = a.model_dump()
    execs = s.exec(select(Execucao).where(Execucao.agente_id == a.id)).all()
    d["execucoes"] = len(execs)
    d["escaladas"] = sum(1 for e in execs if e.status == "escalada")
    d["custo_brl"] = round(sum(e.custo_usd for e in execs) * motor.precos.usd_para_brl(1.0), 4)
    d["plugins_indisponiveis"] = plugins.plugins_indisponiveis(s, a)   # depende de plugin removido: sinalizado, não silencioso
    return d


def _ver(p: Persona, a: m.Agente) -> None:
    if not ciclo.pode_ver(p, a):
        raise HTTPException(status_code=403, detail="Você não tem acesso a este agente.")


@rotas.get("/agentes")
def listar(pessoa: Persona = Depends(usuario_atual), s: Session = Depends(sessao)):
    todos = s.exec(select(m.Agente).order_by(m.Agente.atualizado_em.desc())).all()
    return [_resumo(a, s) for a in todos if ciclo.pode_ver(pessoa, a)]


class PedidoAgente(BaseModel):
    blueprint: Blueprint
    nota: str = Field(default="", max_length=500)


@rotas.post("/agentes")
def criar(pedido: PedidoAgente, pessoa: Persona = Depends(usuario_atual), s: Session = Depends(sessao)):
    try:
        return _dump(s, ciclo.criar(s, pessoa, pedido.blueprint, pedido.nota))
    except ciclo.ErroCiclo as e:
        _erro(e)


@rotas.get("/agentes/{agente_id}")
def detalhe(agente_id: str, pessoa: Persona = Depends(usuario_atual), s: Session = Depends(sessao)):
    try:
        a = ciclo.obter(s, agente_id)
    except ciclo.ErroCiclo as e:
        _erro(e)
    _ver(pessoa, a)
    d = _resumo(a, s)
    d["versoes"] = [v.model_dump() for v in ciclo.versoes(s, a.id)]
    d["pode_executar"] = ciclo.pode_executar(pessoa, a)
    eventos = [e for e in trilha.listar(s, agente_id=a.id, limite=300) if e.tipo in _EVENTOS_CICLO]
    d["historico"] = [e.model_dump() for e in eventos]
    return d


@rotas.put("/agentes/{agente_id}")
def editar(agente_id: str, pedido: PedidoAgente, pessoa: Persona = Depends(usuario_atual), s: Session = Depends(sessao)):
    try:
        return _dump(s, ciclo.editar(s, pessoa, agente_id, pedido.blueprint, pedido.nota))
    except ciclo.ErroCiclo as e:
        _erro(e)


@rotas.get("/agentes/{agente_id}/diff")
def diff(agente_id: str, de: int, para: int, pessoa: Persona = Depends(usuario_atual), s: Session = Depends(sessao)):
    try:
        a = ciclo.obter(s, agente_id)
        _ver(pessoa, a)
        antes = ciclo.versao(s, agente_id, de).blueprint if de > 0 else None
        return comparar(antes, ciclo.versao(s, agente_id, para).blueprint)
    except ciclo.ErroCiclo as e:
        _erro(e)


@rotas.post("/agentes/{agente_id}/publicar")
def publicar(agente_id: str, pessoa: Persona = Depends(usuario_atual), s: Session = Depends(sessao)):
    try:
        return _dump(s, ciclo.publicar(s, pessoa, agente_id))
    except ciclo.ErroCiclo as e:
        _erro(e)


class PedidoRevisao(BaseModel):
    aprovar: bool
    parecer: str = Field(default="", max_length=1500)


@rotas.post("/agentes/{agente_id}/revisao")
def revisar(agente_id: str, pedido: PedidoRevisao, pessoa: Persona = Depends(usuario_atual), s: Session = Depends(sessao)):
    try:
        return _dump(s, ciclo.revisar(s, pessoa, agente_id, pedido.aprovar, pedido.parecer))
    except ciclo.ErroCiclo as e:
        _erro(e)


@rotas.get("/revisoes")
def revisoes(pessoa: Persona = Depends(usuario_atual), s: Session = Depends(sessao)):
    if not (pessoa.tem(REVISOR_SEGURANCA) or pessoa.tem(GESTOR_IA)):
        raise HTTPException(status_code=403, detail="Fila de revisão é da Segurança.")
    saida = []
    for a, v in ciclo.pendentes_revisao(s):
        anterior = ciclo.versao(s, a.id, a.versao_publicada).blueprint if a.versao_publicada else None
        saida.append({"tipo": "agente", "agente": a.model_dump(), "versao": v.model_dump(), "mudancas": comparar(anterior, v.blueprint)})
    from ..processos.diff import comparar as comparar_processo
    from ..processos.tipo import ciclo as ciclo_processos
    for p, v in ciclo_processos.pendentes_revisao(s):   # processos de risco alto esperam a mesma revisão
        anterior = ciclo_processos.versao(s, p.id, p.versao_publicada).blueprint if p.versao_publicada else None
        saida.append({"tipo": "processo", "agente": p.model_dump(), "versao": v.model_dump(), "mudancas": comparar_processo(anterior, v.blueprint)})
    return saida


class PedidoMotivo(BaseModel):
    motivo: str = Field(default="", max_length=500)


@rotas.post("/agentes/{agente_id}/pausar")
def pausar(agente_id: str, pedido: PedidoMotivo, pessoa: Persona = Depends(usuario_atual), s: Session = Depends(sessao)):
    try:
        a = ciclo.pausar(s, pessoa, agente_id, pedido.motivo)
        avaliar_seguro(s)
        return _dump(s, a)
    except ciclo.ErroCiclo as e:
        _erro(e)


@rotas.post("/agentes/{agente_id}/retomar")
def retomar(agente_id: str, pessoa: Persona = Depends(usuario_atual), s: Session = Depends(sessao)):
    try:
        a = ciclo.retomar(s, pessoa, agente_id)
        avaliar_seguro(s)
        return _dump(s, a)
    except ciclo.ErroCiclo as e:
        _erro(e)


@rotas.post("/agentes/{agente_id}/depreciar")
def depreciar(agente_id: str, pedido: PedidoMotivo, pessoa: Persona = Depends(usuario_atual), s: Session = Depends(sessao)):
    try:
        a = ciclo.depreciar(s, pessoa, agente_id, pedido.motivo)
        avaliar_seguro(s)
        return _dump(s, a)
    except ciclo.ErroCiclo as e:
        _erro(e)


class PedidoCompartilhar(BaseModel):
    areas: list[str]


@rotas.post("/agentes/{agente_id}/compartilhar")
def compartilhar(agente_id: str, pedido: PedidoCompartilhar, pessoa: Persona = Depends(usuario_atual),
                 s: Session = Depends(sessao)):
    try:
        return _dump(s, ciclo.compartilhar(s, pessoa, agente_id, pedido.areas))
    except ciclo.ErroCiclo as e:
        _erro(e)


class PedidoExecutar(BaseModel):
    entrada: dict[str, Any] = Field(default_factory=dict)


@rotas.post("/agentes/{agente_id}/executar")
def executar(agente_id: str, pedido: PedidoExecutar, pessoa: Persona = Depends(usuario_atual), s: Session = Depends(sessao)):
    try:
        a, bp = ciclo.checar_execucao(s, pessoa, agente_id)
    except ciclo.ErroCiclo as e:
        _erro(e)
    faltando = [c for c in bp.ids_campos() if pedido.entrada.get(c) in (None, "")]
    if faltando:
        raise HTTPException(status_code=422, detail="Preencha: %s." % ", ".join(faltando))
    exe, mapa = motor.executar(s, pessoa, bp, pedido.entrada, agente_id=a.id, versao=a.versao_publicada)
    avaliar_seguro(s)
    s.refresh(exe)
    return execucao_publica(exe, mapa)


@rotas.get("/agentes/{agente_id}/execucoes")
def execucoes(agente_id: str, limite: int = 50, pessoa: Persona = Depends(usuario_atual), s: Session = Depends(sessao)):
    try:
        a = ciclo.obter(s, agente_id)
    except ciclo.ErroCiclo as e:
        _erro(e)
    _ver(pessoa, a)
    itens = s.exec(select(Execucao).where(Execucao.agente_id == a.id).order_by(Execucao.inicio.desc())
                   .limit(min(max(limite, 1), 500))).all()
    return marcar_rotina(s, [execucao_publica(e) for e in itens])
