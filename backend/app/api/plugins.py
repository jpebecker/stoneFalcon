"""Marketplace de plugins homologados (simulado): vitrine, integração, pedidos e página consolidada."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlmodel import Session

from ..core.db import sessao
from ..core.identidade import Persona, exigir_aba, usuario_atual
from ..observability import avaliar_seguro
from ..plugins import servico
from ..plugins.servico import ErroPlugin

rotas = APIRouter(prefix="/api/v1/plugins", tags=["plugins"])


def _erro(e: ErroPlugin):
    raise HTTPException(status_code=e.status, detail=str(e))


@rotas.get("")
def listar(pessoa: Persona = Depends(usuario_atual), s: Session = Depends(sessao)):
    exigir_aba(pessoa, "plugins")
    return servico.listar(s, pessoa)


@rotas.get("/pedidos")
def pedidos(pessoa: Persona = Depends(usuario_atual), s: Session = Depends(sessao)):
    """Segurança: pedidos de integração esperando parecer (ao lado das revisões de agentes). Os demais: os próprios pedidos."""
    exigir_aba(pessoa, "plugins")
    return servico.fila_para(s, pessoa)


class PedidoDecisao(BaseModel):
    aprovar: bool
    parecer: str = Field(default="", max_length=1500)


@rotas.post("/pedidos/{pedido_id}/decisao")
def decidir(pedido_id: str, corpo: PedidoDecisao, pessoa: Persona = Depends(usuario_atual), s: Session = Depends(sessao)):
    try:
        r = servico.decidir(s, pessoa, pedido_id, corpo.aprovar, corpo.parecer)
    except ErroPlugin as e:
        _erro(e)
    avaliar_seguro(s)
    return r


class PedidoIntegracao(BaseModel):
    motivo: str = Field(default="", max_length=600)


@rotas.get("/{plugin_id}")
def detalhe(plugin_id: str, pessoa: Persona = Depends(usuario_atual), s: Session = Depends(sessao)):
    exigir_aba(pessoa, "plugins")
    try:
        return servico.publico(s, servico._plugin(plugin_id), pessoa)
    except ErroPlugin as e:
        _erro(e)


@rotas.post("/{plugin_id}/integrar")
def integrar(plugin_id: str, corpo: PedidoIntegracao | None = None, pessoa: Persona = Depends(usuario_atual),
             s: Session = Depends(sessao)):
    exigir_aba(pessoa, "plugins")
    try:
        r = servico.integrar(s, pessoa, plugin_id, (corpo.motivo if corpo else ""))
    except ErroPlugin as e:
        _erro(e)
    avaliar_seguro(s)
    return r


@rotas.post("/{plugin_id}/pedir")
def pedir(plugin_id: str, corpo: PedidoIntegracao | None = None, pessoa: Persona = Depends(usuario_atual),
          s: Session = Depends(sessao)):
    exigir_aba(pessoa, "plugins")
    try:
        return servico.pedir(s, pessoa, plugin_id, (corpo.motivo if corpo else ""))
    except ErroPlugin as e:
        _erro(e)


@rotas.delete("/{plugin_id}/integracao")
def remover(plugin_id: str, pessoa: Persona = Depends(usuario_atual), s: Session = Depends(sessao)):
    exigir_aba(pessoa, "plugins")
    try:
        r = servico.remover(s, pessoa, plugin_id)
    except ErroPlugin as e:
        _erro(e)
    avaliar_seguro(s)
    return r


@rotas.get("/{plugin_id}/consolidado")
def consolidado(plugin_id: str, pessoa: Persona = Depends(usuario_atual), s: Session = Depends(sessao)):
    exigir_aba(pessoa, "plugins")
    try:
        return servico.consolidado(s, pessoa, plugin_id)
    except ErroPlugin as e:
        _erro(e)
