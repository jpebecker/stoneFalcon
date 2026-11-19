"""Trilha de auditoria encadeada por hash (portada do v3, agora em banco).

Cada evento guarda o hash do anterior. Alterar ou apagar qualquer linha depois de
gravada quebra a cadeia, e `verificar` aponta onde. Em produção, os hashes de
fechamento de cada dia seriam publicados num cofre externo (WORM), para que nem
quem administra o banco consiga reescrever a história sem ser notado.

Tipos de evento cobrem o ciclo de vida exigido pelo desafio:
  criação → modificações → execuções → escaladas → deprecação
"""
import hashlib
import json
import uuid
from typing import Any

from sqlalchemy import JSON, Column
from sqlmodel import Field, Session, SQLModel, select

from ..core.db import trava as _trava
from ..core.relogio import agora

INICIO = "inicio"


class EventoAuditoria(SQLModel, table=True):
    __tablename__ = "auditoria"

    seq: int = Field(primary_key=True)
    id: str = Field(index=True, unique=True)
    tipo: str = Field(index=True)
    quando: str
    ator: str = Field(index=True)            # persona que causou o evento ("sistema" para automações)
    agente_id: str | None = Field(default=None, index=True)   # id do dono do evento (agente ou processo)
    dono_tipo: str = Field(default="agente", index=True)      # "agente" ou "processo"
    dados: dict = Field(default_factory=dict, sa_column=Column(JSON))
    hash_anterior: str
    hash: str


def _corpo(e: EventoAuditoria) -> dict:
    corpo = {"seq": e.seq, "id": e.id, "tipo": e.tipo, "quando": e.quando, "ator": e.ator,
             "agente_id": e.agente_id, "dados": e.dados, "hash_anterior": e.hash_anterior}
    if e.dono_tipo != "agente":   # só entra no hash quando não é agente: a cadeia gravada antes da v8 continua íntegra
        corpo["dono_tipo"] = e.dono_tipo
    return corpo


def calcular_hash(e: EventoAuditoria) -> str:
    bruto = json.dumps(_corpo(e), sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(bruto.encode("utf-8")).hexdigest()


def registrar(s: Session, tipo: str, ator: str, agente_id: str | None = None,
              dados: dict[str, Any] | None = None, quando: str | None = None, dono_tipo: str = "agente") -> EventoAuditoria:
    """Grava um evento no fim da cadeia. Os dados já devem chegar mascarados."""
    with _trava:
        ultimo = s.exec(select(EventoAuditoria).order_by(EventoAuditoria.seq.desc()).limit(1)).first()
        e = EventoAuditoria(
            seq=(ultimo.seq + 1) if ultimo else 1,
            id=uuid.uuid4().hex[:12],
            tipo=tipo,
            quando=quando or agora().isoformat(),
            ator=ator,
            agente_id=agente_id,
            dono_tipo=dono_tipo,
            dados=dados or {},
            hash_anterior=ultimo.hash if ultimo else INICIO,
            hash="",
        )
        e.hash = calcular_hash(e)
        s.add(e)
        s.commit()
        s.refresh(e)
        return e


def verificar(s: Session) -> dict:
    """Confere a cadeia inteira. Devolve {integra, quebra_em, total}."""
    anterior = INICIO
    total = 0
    for i, e in enumerate(s.exec(select(EventoAuditoria).order_by(EventoAuditoria.seq)), start=1):
        total = i
        if e.seq != i or e.hash_anterior != anterior or e.hash != calcular_hash(e):
            return {"integra": False, "quebra_em": e.seq, "total": None}
        anterior = e.hash
    return {"integra": True, "quebra_em": None, "total": total}


def listar(s: Session, agente_id: str | None = None, tipo: str | None = None, limite: int = 200,
           dono_tipo: str | None = None) -> list[EventoAuditoria]:
    q = select(EventoAuditoria)
    if agente_id:
        q = q.where(EventoAuditoria.agente_id == agente_id)
    if dono_tipo:
        q = q.where(EventoAuditoria.dono_tipo == dono_tipo)
    if tipo:
        q = q.where(EventoAuditoria.tipo == tipo)
    return list(s.exec(q.order_by(EventoAuditoria.seq.desc()).limit(limite)))
