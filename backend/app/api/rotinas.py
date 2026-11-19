"""Tarefas de rotina: agenda de agentes publicados, "Rodar agora" e o relógio acelerado da demonstração."""
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlmodel import Session

from .. import rotinas
from ..core import config
from ..core.db import sessao
from ..core.identidade import CRIADOR, GESTOR_IA, Persona, usuario_atual
from ..rotinas import ErroRotina
from .execucoes import _publico

rotas = APIRouter(prefix="/api/v1", tags=["rotinas"])


def _erro(e: ErroRotina):
    raise HTTPException(status_code=e.status, detail=str(e))


class PedidoRotina(BaseModel):
    frequencia: str = Field(default="semanal", max_length=10)
    dia_semana: int | None = Field(default=None, ge=0, le=6)
    hora: int = Field(default=9, ge=0, le=23)
    minuto: int = Field(default=0, ge=0, le=59)
    entrada: dict[str, Any] = Field(default_factory=dict)


@rotas.post("/agentes/{agente_id}/rotinas")
def criar(agente_id: str, pedido: PedidoRotina, pessoa: Persona = Depends(usuario_atual), s: Session = Depends(sessao)):
    try:
        r = rotinas.criar(s, pessoa, agente_id, pedido.frequencia, pedido.dia_semana, pedido.hora, pedido.minuto, pedido.entrada)
    except ErroRotina as e:
        _erro(e)
    return rotinas.publica(s, r)


@rotas.post("/processos/{processo_id}/rotinas")
def criar_do_processo(processo_id: str, pedido: PedidoRotina, pessoa: Persona = Depends(usuario_atual), s: Session = Depends(sessao)):
    try:
        r = rotinas.criar(s, pessoa, processo_id, pedido.frequencia, pedido.dia_semana, pedido.hora, pedido.minuto, pedido.entrada,
                          tipo="processo")
    except ErroRotina as e:
        _erro(e)
    return rotinas.publica(s, r)


@rotas.get("/processos/{processo_id}/rotinas")
def do_processo(processo_id: str, pessoa: Persona = Depends(usuario_atual), s: Session = Depends(sessao)):
    return rotinas.listar(s, pessoa, processo_id)


@rotas.get("/agentes/{agente_id}/rotinas")
def do_agente(agente_id: str, pessoa: Persona = Depends(usuario_atual), s: Session = Depends(sessao)):
    return rotinas.listar(s, pessoa, agente_id)


@rotas.get("/rotinas")
def todas(pessoa: Persona = Depends(usuario_atual), s: Session = Depends(sessao)):
    return rotinas.listar(s, pessoa)


@rotas.get("/rotinas/relogio")
def relogio(pessoa: Persona = Depends(usuario_atual)):
    return _relogio(pessoa)


def pode_mexer_no_relogio(p: Persona) -> bool:
    return p.tem(GESTOR_IA) or p.tem(CRIADOR)


def _relogio(pessoa: Persona) -> dict:
    return {"agora": rotinas.relogio.agora().isoformat(), "fator": rotinas.relogio.fator, "demo": config.MODO_DEMO,
            "pode_mexer": config.MODO_DEMO and pode_mexer_no_relogio(pessoa)}


class PedidoRelogio(BaseModel):
    avancar_horas: float | None = Field(default=None, ge=0, le=24 * 31)
    fator: float | None = Field(default=None, ge=0, le=100_000)
    zerar: bool = False


@rotas.post("/rotinas/relogio")
def mexer_no_relogio(pedido: PedidoRelogio, pessoa: Persona = Depends(usuario_atual), s: Session = Depends(sessao)):
    """Relógio acelerado da demonstração: avança no tempo e já dispara o que venceu (sem esperar a segunda-feira).
    Mexe na agenda de todo mundo: só o CoE de IA e os criadores (quem agenda rotinas)."""
    if not config.MODO_DEMO:
        raise HTTPException(status_code=403, detail="O relógio acelerado só existe no modo demonstração.")
    if not pode_mexer_no_relogio(pessoa):
        raise HTTPException(status_code=403, detail="Só o CoE de IA e os criadores mexem no relógio da demonstração.")
    if pedido.zerar:
        rotinas.relogio.zerar()
    if pedido.fator is not None:
        rotinas.relogio.acelerar(pedido.fator)
    if pedido.avancar_horas:
        from datetime import timedelta
        rotinas.relogio.avancar(timedelta(hours=pedido.avancar_horas))
    return {**_relogio(pessoa), "disparadas": rotinas.tick(s)}


@rotas.post("/rotinas/{rotina_id}/pausar")
def pausar(rotina_id: str, pessoa: Persona = Depends(usuario_atual), s: Session = Depends(sessao)):
    try:
        return rotinas.publica(s, rotinas.pausar(s, pessoa, rotina_id))
    except ErroRotina as e:
        _erro(e)


@rotas.post("/rotinas/{rotina_id}/retomar")
def retomar(rotina_id: str, pessoa: Persona = Depends(usuario_atual), s: Session = Depends(sessao)):
    try:
        return rotinas.publica(s, rotinas.retomar(s, pessoa, rotina_id))
    except ErroRotina as e:
        _erro(e)


@rotas.delete("/rotinas/{rotina_id}")
def remover(rotina_id: str, pessoa: Persona = Depends(usuario_atual), s: Session = Depends(sessao)):
    try:
        rotinas.remover(s, pessoa, rotina_id)
    except ErroRotina as e:
        _erro(e)
    return {"ok": True}


@rotas.post("/rotinas/{rotina_id}/rodar")
def rodar(rotina_id: str, pessoa: Persona = Depends(usuario_atual), s: Session = Depends(sessao)):
    """"Rodar agora": a mesma execução que a agenda faria, marcada como rotina."""
    try:
        r = rotinas.rodar_agora(s, pessoa, rotina_id)
    except ErroRotina as e:
        _erro(e)
    if r["execucao"]:
        from ..runtime import modelos as rm
        exe = s.get(rm.Execucao, r["execucao"])
        r["execucao_detalhe"] = rotinas.marcar(s, [_publico(exe)])[0]
    return r
