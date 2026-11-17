"""Roteiros guiados, valor medido e perguntas da banca."""
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from ..agents import ciclo
from ..agents import modelos as am
from ..core.db import sessao
from ..core import config
from ..core.identidade import GESTOR_IA, PERSONAS, Persona, usuario_atual
from ..roteiros import medicao, perguntas
from ..roteiros.catalogo import ROTEIROS
from ..roteiros.reinicio import reiniciar

rotas = APIRouter(prefix="/api/v1", tags=["roteiros"])


def _roteiro(roteiro_id: str):
    r = ROTEIROS.get(roteiro_id)
    if r is None:
        raise HTTPException(status_code=404, detail="Roteiro não encontrado.")
    return r


@rotas.get("/roteiros")
def listar(_p: Persona = Depends(usuario_atual)):
    return [{"id": r.id, "persona": r.persona, "titulo": r.titulo, "processo": r.processo, "resumo": r.resumo,
             "duracao_min": r.duracao_min, "passos": len(r.passos)} for r in ROTEIROS.values()]


@rotas.get("/roteiros/consolidado")
def consolidado(_p: Persona = Depends(usuario_atual), s: Session = Depends(sessao)):
    return medicao.consolidado(s)


@rotas.get("/roteiros/{roteiro_id}")
def detalhe(roteiro_id: str, _p: Persona = Depends(usuario_atual)):
    r = _roteiro(roteiro_id)
    d = r.publico()
    d["persona_dados"] = PERSONAS[r.persona].publico()
    return d


@rotas.post("/roteiros/{roteiro_id}/reiniciar")
def reiniciar_roteiro(roteiro_id: str, pessoa: Persona = Depends(usuario_atual), s: Session = Depends(sessao)):
    """Deixa a plataforma no estado exato de que o roteiro precisa. Apaga o banco: no modo demonstração (padrão do
    protótipo) qualquer perfil pode, porque o roteiro troca de perfil sozinho; com STONEFALCON_DEMO=0 só o CoE."""
    _roteiro(roteiro_id)
    if not (config.MODO_DEMO or pessoa.tem(GESTOR_IA)):
        raise HTTPException(status_code=403, detail="Reiniciar apaga os dados, inclusive a auditoria: só o CoE de IA pode fora do modo demonstração.")
    return reiniciar(s, roteiro_id)


@rotas.get("/roteiros/{roteiro_id}/resultado")
def resultado(roteiro_id: str, agente_id: str | None = None, pessoa: Persona = Depends(usuario_atual),
              s: Session = Depends(sessao)):
    if agente_id:   # o cartão mostra nome, custo e status do agente: só de quem pode ver aquele agente
        agente = s.get(am.Agente, agente_id)
        if agente is None or not ciclo.pode_ver(pessoa, agente):
            raise HTTPException(status_code=403, detail="Você não tem acesso a este agente.")
    return medicao.resultado(s, _roteiro(roteiro_id), agente_id)


@rotas.get("/perguntas")
def perguntas_banca(persona: str | None = None, tema: str | None = None, _p: Persona = Depends(usuario_atual)):
    return {"temas": perguntas.TEMAS, "perguntas": perguntas.listar(persona, tema)}
