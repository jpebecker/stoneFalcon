"""Mapa de IA: só da Helena (aba "mapa", mesma lista de abas do back)."""
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from ..core.db import sessao
from ..core.identidade import Persona, exigir_aba, usuario_atual
from ..llm import registro
from ..mapa import grafo

rotas = APIRouter(prefix="/api/v1", tags=["mapa"])


@rotas.get("/mapa")
def mapa(dias: int = 7, area: str | None = None, provedor: str | None = None,
         pessoa: Persona = Depends(usuario_atual), s: Session = Depends(sessao)):
    """O grafo do período. `area` e `provedor` filtram (e se combinam)."""
    exigir_aba(pessoa, "mapa")
    if provedor and provedor not in registro.PROVEDORES:
        raise HTTPException(status_code=404, detail="Provedor desconhecido.")
    return grafo(s, min(max(dias, 1), 90), area or None, provedor or None)
