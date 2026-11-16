"""Banco de dados (SQLite no protótipo, Postgres em produção: só muda a URL)."""
import threading
from collections.abc import Iterator
from pathlib import Path

from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from . import config

_motor = None

# Escritas serializadas: passos paralelos de um agente gravam auditoria ao mesmo tempo,
# e o SQLite aceita um escritor por vez. (Em Postgres, a trava vira só proteção da sequência.)
trava = threading.RLock()


def criar_motor(url: str):
    if url.startswith("sqlite"):
        if url == "sqlite://":   # em memória (testes): uma conexão compartilhada
            return create_engine(url, connect_args={"check_same_thread": False}, poolclass=StaticPool)
        Path(url.removeprefix("sqlite:///")).parent.mkdir(parents=True, exist_ok=True)
        return create_engine(url, connect_args={"check_same_thread": False})
    return create_engine(url, pool_pre_ping=True)


def motor():
    global _motor
    if _motor is None:
        _motor = criar_motor(config.URL_BANCO)
    return _motor


def usar_motor(novo) -> None:
    """Troca o motor (usado pelos testes)."""
    global _motor
    _motor = novo


def criar_tabelas() -> None:
    from ..agents import modelos as _agentes  # noqa: F401
    from ..audit import trilha  # noqa: F401  (registra os modelos nas tabelas)
    from ..observability import alertas as _alertas  # noqa: F401
    from ..runtime import modelos  # noqa: F401
    from ..tools import executor  # noqa: F401
    SQLModel.metadata.create_all(motor())


def sessao() -> Iterator[Session]:
    """Dependência FastAPI: uma sessão por requisição."""
    with Session(motor()) as s:
        yield s
