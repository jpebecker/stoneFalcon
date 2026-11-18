"""Mapa de IA: só da Helena (aba "mapa", mesma lista de abas do back)."""
from fastapi import APIRouter, Depends
from sqlmodel import Session

from ..core.db import sessao
from ..core.identidade import Persona, exigir_aba, usuario_atual
from ..mapa import grafo

rotas = APIRouter(prefix="/api/v1", tags=["mapa"])


@rotas.get("/mapa")
def mapa(dias: int = 7, pessoa: Persona = Depends(usuario_atual), s: Session = Depends(sessao)):
    exigir_aba(pessoa, "mapa")
    return grafo(s, min(max(dias, 1), 90))
