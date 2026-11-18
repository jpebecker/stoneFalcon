import os

# Nada de chave nem internet nos testes: sempre modo simulado, banco em memória.
os.environ["MODO_SIMULADO"] = "1"
os.environ.pop("ANTHROPIC_API_KEY", None)
os.environ["STONEFALCON_DB"] = "sqlite://"
os.environ["STONEFALCON_SEMEAR"] = "0"
os.environ["STONEFALCON_VIGIA"] = "0"
os.environ["STONEFALCON_AGENDADOR"] = "0"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlmodel import Session, SQLModel  # noqa: E402

from app.core import db  # noqa: E402


@pytest.fixture(autouse=True)
def _balanceador_limpo():
    """Queda simulada de provedor é estado global: nenhum teste herda a do anterior (nem os que não usam o banco)."""
    from app.llm import balanceador
    balanceador.zerar()
    yield
    balanceador.zerar()


@pytest.fixture()
def motor():
    from app import rotinas
    from app.llm import balanceador
    from app.plugins import servico as plugins
    balanceador.zerar()
    rotinas.zerar()
    m = db.criar_motor("sqlite://")
    db.usar_motor(m)
    db.criar_tabelas()
    plugins.zerar()          # plugins integrados e sistemas externos simulados começam do zero em cada teste
    yield m
    SQLModel.metadata.drop_all(m)
    plugins.zerar()
    balanceador.zerar()
    rotinas.zerar()


@pytest.fixture()
def sessao(motor):
    with Session(motor) as s:
        yield s


@pytest.fixture()
def api(motor):
    from app.main import app
    with TestClient(app) as c:
        yield c


def como(pessoa: str) -> dict:
    return {"X-Usuario": pessoa}
