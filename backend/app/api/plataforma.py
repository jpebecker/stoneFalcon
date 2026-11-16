"""Rotas de base da plataforma: saúde, identidade, auditoria e guardrails."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlmodel import Session

from .. import guardrails
from ..audit import trilha
from ..core import config
from ..core.db import sessao
from ..core.identidade import GESTOR_IA, PERSONAS, REVISOR_SEGURANCA, Persona, usuario_atual

rotas = APIRouter(prefix="/api/v1")


@rotas.get("/saude")
def saude():
    return {
        "ok": True,
        "versao": "4.0.0",
        "modo": "real" if config.modo_real() else "simulado",
        "modelos": {k: m["nome"] for k, m in config.MODELOS.items()},
        "cotacao_dolar": config.COTACAO_DOLAR,
    }


@rotas.get("/perfis")
def perfis():
    """Perfis de demonstração para o login simulado."""
    return [p.publico() for p in PERSONAS.values()]


@rotas.get("/eu")
def eu(pessoa: Persona = Depends(usuario_atual)):
    return pessoa.publico()


def _pode_ver_auditoria(p: Persona) -> None:
    if not (p.tem(GESTOR_IA) or p.tem(REVISOR_SEGURANCA)):
        raise HTTPException(status_code=403, detail="A auditoria completa é do CoE de IA e da Segurança.")


@rotas.get("/auditoria")
def auditoria(agente_id: str | None = None, tipo: str | None = None, limite: int = 200,
              pessoa: Persona = Depends(usuario_atual), s: Session = Depends(sessao)):
    _pode_ver_auditoria(pessoa)
    eventos = trilha.listar(s, agente_id=agente_id, tipo=tipo, limite=min(max(limite, 1), 1000))
    return {"eventos": [e.model_dump() for e in eventos], "cadeia": trilha.verificar(s)}


@rotas.get("/auditoria/verificar")
def auditoria_verificar(pessoa: Persona = Depends(usuario_atual), s: Session = Depends(sessao)):
    _pode_ver_auditoria(pessoa)
    return trilha.verificar(s)


class PedidoTexto(BaseModel):
    texto: str = Field(max_length=20_000)


@rotas.post("/guardrails/testar")
def guardrails_testar(pedido: PedidoTexto, pessoa: Persona = Depends(usuario_atual)):
    """Mostra o que sairia daqui para um modelo: só marcadores no lugar dos dados."""
    mascarado, _mapa, resumo = guardrails.mascarar(pedido.texto)
    return {"enviado_ao_modelo": mascarado, "mascarados": resumo}
