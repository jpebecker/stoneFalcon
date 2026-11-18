"""StoneFalcon v7: plataforma agêntica institucional (protótipo acadêmico UFSC / StoneLab).

    uv run uvicorn app.main:app --reload --port 8765
Se frontend/dist existir (npm run build), o app inteiro abre em http://localhost:8765.
"""
import asyncio
import os
from contextlib import asynccontextmanager

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from .api.agentes import rotas as rotas_agentes
from .api.balanceador import rotas as rotas_balanceador
from .api.cadastros import rotas as rotas_cadastros
from .api.extensao import rotas as rotas_extensao
from .api.mapa import rotas as rotas_mapa
from .api.estudio import rotas as rotas_estudio
from .api.execucoes import rotas as rotas_execucoes
from .api.ferramentas import rotas as rotas_ferramentas
from .api.financas import rotas as rotas_financas
from .api.plataforma import rotas as rotas_plataforma
from .api.plugins import rotas as rotas_plugins
from .api.roteiros import rotas as rotas_roteiros
from .api.saude import rotas as rotas_saude
from .core import config
from .core import db
from .core.versao import VERSAO
from .core.db import criar_tabelas


@asynccontextmanager
async def ciclo(_app: FastAPI):
    criar_tabelas()
    from sqlmodel import Session as _Sessao

    from .plugins import servico as _plugins
    with _Sessao(db.motor()) as _s:
        _plugins.sincronizar(_s)   # plugins integrados que ficaram gravados no banco voltam ao catálogo
    if os.environ.get("STONEFALCON_SEMEAR", "1") != "0":
        from sqlmodel import Session

        from .seed.demo import semear
        with Session(db.motor()) as s:
            semear(s)
    tarefa = asyncio.create_task(_vigiar()) if os.environ.get("STONEFALCON_VIGIA", "1") != "0" else None
    yield
    if tarefa:
        tarefa.cancel()


async def _vigiar():
    """Reavalia alertas a cada minuto, mesmo sem ninguém usando a plataforma."""
    from sqlmodel import Session

    from .observability import avaliar_seguro

    def rodada():
        with Session(db.motor()) as s:
            avaliar_seguro(s)
    while True:
        await asyncio.sleep(60)
        await asyncio.to_thread(rodada)


app = FastAPI(
    title="StoneFalcon",
    version=VERSAO,
    description="Fábrica governada de agentes de IA. Protótipo acadêmico; não é um produto oficial da Stone.",
    lifespan=ciclo,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.ORIGENS_CORS,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(rotas_plataforma)
app.include_router(rotas_cadastros)
app.include_router(rotas_extensao)
app.include_router(rotas_ferramentas)
app.include_router(rotas_execucoes)
app.include_router(rotas_estudio)
app.include_router(rotas_agentes)
app.include_router(rotas_saude)
app.include_router(rotas_financas)
app.include_router(rotas_roteiros)
app.include_router(rotas_plugins)
app.include_router(rotas_balanceador)
app.include_router(rotas_mapa)


# ---------- página de demonstração para a extensão (helpdesk fictício) ----------
_ESTATICO = Path(__file__).resolve().parent / "static"


@app.get("/demo/helpdesk", include_in_schema=False)
def helpdesk():
    return FileResponse(_ESTATICO / "helpdesk.html")


# ---------- fotos das personas (avatares), servidas pela própria plataforma ----------
app.mount("/avatares", StaticFiles(directory=_ESTATICO / "avatares"), name="avatares")


# ---------- front compilado (frontend/dist), servido pelo mesmo endereço ----------
# Em desenvolvimento o Vite (porta 5173) cuida disso; para a demo, um endereço só.
_DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"
if _DIST.is_dir():
    app.mount("/assets", StaticFiles(directory=_DIST / "assets"), name="assets")

    @app.get("/{caminho:path}", include_in_schema=False)
    def spa(caminho: str):
        if caminho.startswith("api/"):
            raise HTTPException(status_code=404)
        arquivo = (_DIST / caminho).resolve()
        if caminho and arquivo.is_file() and _DIST in arquivo.parents:
            return FileResponse(arquivo)
        return FileResponse(_DIST / "index.html")   # rotas do React (ex.: /agentes/x)
