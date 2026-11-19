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


def _motor_de_teste(caminho):
    """Banco num arquivo temporário, com o pool normal: cada thread ganha a sua conexão, como em produção.
    (O SQLite em memória com StaticPool divide UMA conexão entre as threads; blocos paralelos de um processo
    consultavam o banco ao mesmo tempo e o sqlite3 falhava com "bad parameter or other API misuse".)"""
    from sqlalchemy import event
    m = db.criar_motor("sqlite:///" + caminho.as_posix())

    @event.listens_for(m, "connect")
    def _rapido(con, _):     # teste não precisa sobreviver a queda de energia: sem fsync
        cur = con.cursor()
        cur.execute("PRAGMA synchronous=OFF")
        cur.execute("PRAGMA journal_mode=MEMORY")
        cur.close()
    return m


@pytest.fixture()
def motor(tmp_path):
    from app import rotinas
    from app.llm import balanceador
    from app.plugins import servico as plugins
    balanceador.zerar()
    rotinas.zerar()
    m = _motor_de_teste(tmp_path / "teste.db")
    db.usar_motor(m)
    db.criar_tabelas()
    plugins.zerar()          # plugins integrados e sistemas externos simulados começam do zero em cada teste
    yield m
    SQLModel.metadata.drop_all(m)
    m.dispose()              # solta o arquivo (no Windows, arquivo aberto não sai da pasta temporária)
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
