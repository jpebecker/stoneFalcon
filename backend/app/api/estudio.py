"""Estúdio: criar agente a partir de uma descrição, ajustar, validar e testar no sandbox."""
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, ValidationError
from sqlmodel import Session

from ..agents.blueprint import Blueprint
from ..agents.governanca import avaliar_risco, estimar_custo, ferramentas_sem_permissao
from ..audit import trilha
from ..core.db import sessao
from ..core.identidade import CRIADOR, Persona, exigir, usuario_atual
from ..runtime import motor
from ..studio import sugestao
from ..studio.modelos_prontos import PADROES
from .execucoes import _publico as execucao_publica

rotas = APIRouter(prefix="/api/v1/estudio", tags=["estudio"])


@rotas.get("/padroes")
def padroes(_p: Persona = Depends(usuario_atual)):
    return [{"id": p["id"], "titulo": p["titulo"], "area": p["area"], "exemplo": p["exemplos"][0]} for p in PADROES]


class PedidoSugestao(BaseModel):
    descricao: str = Field(min_length=15, max_length=3000)


@rotas.post("/sugerir")
def sugerir(pedido: PedidoSugestao, pessoa: Persona = Depends(usuario_atual), s: Session = Depends(sessao)):
    exigir(pessoa, CRIADOR)
    sug = sugestao.sugerir(pessoa, pedido.descricao)
    trilha.registrar(s, "estudio_sugestao", pessoa.id, dados={
        "origem": sug.origem, "nome": sug.blueprint.nome, "risco": sug.risco.nivel,
        "removidas": sorted(sug.removidas), "custo_sugestao_brl": sug.custo_sugestao_brl})
    return sug.publico()


class PedidoBlueprint(BaseModel):
    blueprint: dict[str, Any]


@rotas.post("/validar")
def validar(pedido: PedidoBlueprint, pessoa: Persona = Depends(usuario_atual)):
    """Checagem ao vivo enquanto a pessoa edita o canvas."""
    try:
        bp = Blueprint.model_validate(pedido.blueprint)
    except ValidationError as e:
        return {"valido": False, "erros": [err["msg"].removeprefix("Value error, ") for err in e.errors()]}
    est = estimar_custo(bp)
    risco = avaliar_risco(bp)
    return {
        "valido": True, "erros": [], "niveis": bp.niveis(),
        "sem_permissao": ferramentas_sem_permissao(pessoa, bp),
        "risco": {"nivel": risco.nivel, "motivos": risco.motivos, "exige_revisao_seguranca": risco.exige_revisao},
        "estimativa": {"custo_por_execucao_brl": est.custo_brl, "chamadas_modelo": est.chamadas_modelo,
                       "por_passo": est.por_passo},
        "explicacao": sugestao.explicar(bp, est),
    }


class PedidoTeste(BaseModel):
    blueprint: Blueprint
    entrada: dict[str, Any] = Field(default_factory=dict)


@rotas.post("/testar")
def testar(pedido: PedidoTeste, pessoa: Persona = Depends(usuario_atual), s: Session = Depends(sessao)):
    """Sandbox: roda o rascunho com as permissões de quem está criando."""
    exigir(pessoa, CRIADOR)
    bp = pedido.blueprint.model_copy(update={"area": pessoa.area})
    faltando = [c for c in bp.campos_entrada if pedido.entrada.get(c) in (None, "")]
    if faltando:
        raise HTTPException(status_code=422, detail="Preencha: %s." % ", ".join(faltando))
    exe, mapa = motor.executar(s, pessoa, bp, pedido.entrada, agente_id="sandbox")
    return execucao_publica(exe, mapa)
