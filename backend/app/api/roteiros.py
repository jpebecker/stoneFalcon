"""Roteiros guiados, valor medido e Perguntas da Ferramenta.

Cada pessoa só enxerga o próprio roteiro; a Helena (CoE de IA) vê todos. A troca de perfil dos passos de quatro olhos
continua: quem participa de algum passo do roteiro também consegue carregá-lo (a barra do roteiro precisa dele)."""
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from ..agents import ciclo
from ..agents import modelos as am
from ..core.db import sessao
from ..core import config
from ..core.identidade import GESTOR_IA, PERSONAS, Persona, exigir_aba, usuario_atual
from ..roteiros import medicao, perguntas
from ..roteiros.catalogo import ROTEIROS
from ..roteiros.reinicio import reiniciar

rotas = APIRouter(prefix="/api/v1", tags=["roteiros"])


def _roteiro(roteiro_id: str):
    r = ROTEIROS.get(roteiro_id)
    if r is None:
        raise HTTPException(status_code=404, detail="Roteiro não encontrado.")
    return r


def _participa(pessoa: Persona, r) -> bool:
    return pessoa.id == r.persona or any(p.perfil == pessoa.id for p in r.passos)


def _acessivel(pessoa: Persona, roteiro_id: str):
    """Roteiro que a pessoa pode abrir: o dono, quem participa de algum passo e a Helena. Os demais: 403."""
    r = _roteiro(roteiro_id)
    if not (pessoa.tem(GESTOR_IA) or _participa(pessoa, r)):
        raise HTTPException(status_code=403, detail="Este roteiro é de outra pessoa.")
    return r


@rotas.get("/roteiros")
def listar(pessoa: Persona = Depends(usuario_atual)):
    """Só o roteiro do próprio perfil; a Helena vê todos."""
    return [{"id": r.id, "persona": r.persona, "titulo": r.titulo, "processo": r.processo, "resumo": r.resumo,
             "duracao_min": r.duracao_min, "passos": len(r.passos), "apresentacao": r.apresentacao}
            for r in ROTEIROS.values() if pessoa.tem(GESTOR_IA) or (r.persona == pessoa.id and not r.apresentacao)]


@rotas.get("/roteiros/consolidado")
def consolidado(_p: Persona = Depends(usuario_atual), s: Session = Depends(sessao)):
    return medicao.consolidado(s)


@rotas.get("/roteiros/{roteiro_id}")
def detalhe(roteiro_id: str, pessoa: Persona = Depends(usuario_atual)):
    r = _acessivel(pessoa, roteiro_id)
    d = r.publico()
    d["persona_dados"] = PERSONAS[r.persona].publico()
    return d


@rotas.post("/roteiros/{roteiro_id}/reiniciar")
def reiniciar_roteiro(roteiro_id: str, pessoa: Persona = Depends(usuario_atual), s: Session = Depends(sessao)):
    """Deixa a plataforma no estado exato de que o roteiro precisa. Apaga o banco: no modo demonstração (padrão do
    protótipo) qualquer perfil pode, porque o roteiro troca de perfil sozinho; com STONEFALCON_DEMO=0 só o CoE."""
    _acessivel(pessoa, roteiro_id)
    if not (config.MODO_DEMO or pessoa.tem(GESTOR_IA)):
        raise HTTPException(status_code=403, detail="Reiniciar apaga os dados, inclusive a auditoria: só o CoE de IA pode fora do modo demonstração.")
    return reiniciar(s, roteiro_id)


@rotas.get("/roteiros/{roteiro_id}/resultado")
def resultado(roteiro_id: str, agente_id: str | None = None, pessoa: Persona = Depends(usuario_atual),
              s: Session = Depends(sessao)):
    roteiro = _acessivel(pessoa, roteiro_id)
    if agente_id:   # o cartão mostra nome, custo e status do agente: só de quem pode ver aquele agente
        agente = s.get(am.Agente, agente_id)
        if agente is None or not ciclo.pode_ver(pessoa, agente):
            raise HTTPException(status_code=403, detail="Você não tem acesso a este agente.")
    return medicao.resultado(s, roteiro, agente_id)


@rotas.get("/perguntas")
def perguntas_da_ferramenta(persona: str | None = None, tema: str | None = None, pessoa: Persona = Depends(usuario_atual)):
    exigir_aba(pessoa, "perguntas")
    return {"temas": perguntas.TEMAS, "perguntas": perguntas.listar(persona, tema)}
