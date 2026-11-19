"""Crie o seu plugin: rascunho da especificação, pedido e status. A decisão da analista de IA e da Segurança vem em v8/13."""
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlmodel import Session

from ..core.db import sessao
from ..core.identidade import Persona, exigir_aba, usuario_atual
from ..plugins import interno
from ..plugins.interno import ErroPedidoPlugin

rotas = APIRouter(prefix="/api/v1/plugins-internos", tags=["plugins-internos"])


def _erro(e: ErroPedidoPlugin):
    raise HTTPException(status_code=e.status, detail=str(e))


class PedidoRascunho(BaseModel):
    ferramenta_mercado: str = Field(max_length=120)
    descricao_publica: str = Field(max_length=interno.MAX_DESCRICAO + 500)
    finalidade: str = Field(max_length=800)
    areas: list[str] = Field(default_factory=list, max_length=20)
    classificacao: str = "interna"
    aceita_aviso_publico: bool = False


@rotas.get("/regras")
def regras(pessoa: Persona = Depends(usuario_atual)):
    exigir_aba(pessoa, "plugins")
    return {"pode_pedir": interno.pode_pedir(pessoa), "aviso_publico": interno.AVISO_PUBLICO, "max_descricao": interno.MAX_DESCRICAO,
            "min_descricao": interno.MIN_DESCRICAO, "max_ferramentas": interno.MAX_FERRAMENTAS}


@rotas.post("/rascunho")
def rascunho(pedido: PedidoRascunho, pessoa: Persona = Depends(usuario_atual), s: Session = Depends(sessao)):
    exigir_aba(pessoa, "plugins")
    try:
        return interno.rascunhar(s, pessoa, pedido.ferramenta_mercado, pedido.descricao_publica, pedido.finalidade, pedido.areas,
                                 pedido.classificacao, pedido.aceita_aviso_publico)
    except ErroPedidoPlugin as e:
        _erro(e)


class PedidoEnvio(PedidoRascunho):
    spec: dict[str, Any]


@rotas.post("")
def enviar(pedido: PedidoEnvio, pessoa: Persona = Depends(usuario_atual), s: Session = Depends(sessao)):
    exigir_aba(pessoa, "plugins")
    try:
        p = interno.solicitar(s, pessoa, pedido.ferramenta_mercado, pedido.descricao_publica, pedido.finalidade, pedido.areas,
                              pedido.classificacao, pedido.spec, pedido.aceita_aviso_publico)
    except ErroPedidoPlugin as e:
        _erro(e)
    return interno.publico(p, pessoa)


@rotas.get("")
def listar(pessoa: Persona = Depends(usuario_atual), s: Session = Depends(sessao)):
    exigir_aba(pessoa, "plugins")
    return [interno.publico(p, pessoa) for p in interno.listar(s, pessoa)]


class PedidoDecisao(BaseModel):
    aprovar: bool
    parecer: str = Field(default="", max_length=1500)


@rotas.post("/{pedido_id}/analista")
def decidir_analista(pedido_id: str, d: PedidoDecisao, pessoa: Persona = Depends(usuario_atual), s: Session = Depends(sessao)):
    """A analista de IA aprova ou recusa (com parecer). Dado confidencial ou restrito segue para a Segurança."""
    exigir_aba(pessoa, "plugins")
    try:
        p = interno.decidir_analista(s, pessoa, pedido_id, d.aprovar, d.parecer)
    except ErroPedidoPlugin as e:
        _erro(e)
    return interno.publico(p, pessoa)


@rotas.post("/{pedido_id}/seguranca")
def decidir_seguranca(pedido_id: str, d: PedidoDecisao, pessoa: Persona = Depends(usuario_atual), s: Session = Depends(sessao)):
    """A Segurança dá o aval final do dado sensível (quatro olhos: depois da analista, e nunca o próprio pedido)."""
    exigir_aba(pessoa, "plugins")
    try:
        p = interno.decidir_seguranca(s, pessoa, pedido_id, d.aprovar, d.parecer)
    except ErroPedidoPlugin as e:
        _erro(e)
    return interno.publico(p, pessoa)


@rotas.get("/{pedido_id}")
def detalhe(pedido_id: str, pessoa: Persona = Depends(usuario_atual), s: Session = Depends(sessao)):
    exigir_aba(pessoa, "plugins")
    try:
        return interno.publico(interno.obter(s, pessoa, pedido_id), pessoa)
    except ErroPedidoPlugin as e:
        _erro(e)
