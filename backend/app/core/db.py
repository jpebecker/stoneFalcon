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
    from ..plugins import modelos as _plugins  # noqa: F401
    from ..processos import modelos as _processos  # noqa: F401
    from ..rotinas import modelos as _rotinas  # noqa: F401
    from ..runtime import modelos  # noqa: F401
    from ..tools import executor  # noqa: F401
    SQLModel.metadata.create_all(motor())
    acrescentar_colunas(motor())


def acrescentar_colunas(m) -> list[str]:
    """Bancos de versões anteriores: o `create_all` cria tabelas que faltam, mas não acrescenta colunas novas em
    tabelas que já existem. Aqui só se ACRESCENTA (nunca remove nem altera), com o valor padrão do modelo,
    para que um banco da v7 abra na v8 sem migração manual. Devolve as colunas acrescentadas ("tabela.coluna")."""
    from sqlalchemy import inspect, text
    insp = inspect(m)
    feitas: list[str] = []
    for tabela in SQLModel.metadata.sorted_tables:
        if not insp.has_table(tabela.name):
            continue
        existentes = {c["name"] for c in insp.get_columns(tabela.name)}
        for col in tabela.columns:
            if col.name in existentes:
                continue
            tipo = col.type.compile(dialect=m.dialect)
            padrao = ""
            if col.default is not None and getattr(col.default, "is_scalar", False):
                v = col.default.arg
                padrao = " DEFAULT %s" % ("'%s'" % str(v).replace("'", "''") if isinstance(v, str) else int(v) if isinstance(v, bool) else v)
            elif not col.nullable:
                padrao = " DEFAULT ''" if "CHAR" in tipo.upper() or "TEXT" in tipo.upper() else " DEFAULT 0"
            with m.begin() as con:
                con.execute(text('ALTER TABLE "%s" ADD COLUMN "%s" %s%s' % (tabela.name, col.name, tipo, padrao)))
                if col.index:
                    con.execute(text('CREATE INDEX IF NOT EXISTS "ix_%s_%s" ON "%s" ("%s")' % (tabela.name, col.name, tabela.name, col.name)))
            feitas.append("%s.%s" % (tabela.name, col.name))
    return feitas


def sessao() -> Iterator[Session]:
    """Dependência FastAPI: uma sessão por requisição."""
    with Session(motor()) as s:
        yield s
