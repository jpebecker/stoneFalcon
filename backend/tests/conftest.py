import os

# Nada de chave nem internet nos testes: sempre modo simulado, banco em memória.
os.environ["MODO_SIMULADO"] = "1"
os.environ.pop("ANTHROPIC_API_KEY", None)
os.environ["STONEFALCON_DB"] = "sqlite://"
os.environ["STONEFALCON_SEMEAR"] = "0"
os.environ["STONEFALCON_VIGIA"] = "0"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlmodel import Session, SQLModel  # noqa: E402

from app.core import db  # noqa: E402


@pytest.fixture()
def motor():
    m = db.criar_motor("sqlite://")
    db.usar_motor(m)
    db.criar_tabelas()
    yield m
    SQLModel.metadata.drop_all(m)


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
