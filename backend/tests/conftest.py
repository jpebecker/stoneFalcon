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


@pytest.fixture()
def legado():
    """Bancos da v7 têm agentes de vários passos; um agente novo só pode ter um (v8/09). Os testes que exercitam o ciclo de vida,
    a saúde, os plugins... com fluxos de vários passos como dado de exemplo pedem este fixture, que desliga só a regra do
    "uma tarefa só" (os testes da regra, em test_contrato_agentes.py, não o usam)."""
    from app.agents.ciclo import TIPO_AGENTE
    original = TIPO_AGENTE.normalizar
    object.__setattr__(TIPO_AGENTE, "normalizar", None)
    yield
    object.__setattr__(TIPO_AGENTE, "normalizar", original)
