"""Processo e suas versões (persistidos). Mesmo ciclo de vida do agente: rascunho -> revisão -> publicado <-> pausado -> depreciado."""
from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel

from ..agents.modelos import RASCUNHO, V_RASCUNHO


class Processo(SQLModel, table=True):
    __tablename__ = "processo"

    id: str = Field(primary_key=True)
    nome: str
    area: str = Field(index=True)
    dono: str = Field(index=True)
    estado: str = Field(default=RASCUNHO, index=True)
    versao_publicada: int | None = None
    ultima_versao: int = 1
    risco: str = "baixo"
    compartilhado_com: list = Field(default_factory=list, sa_column=Column(JSON))
    motivo_estado: str | None = None
    orcamento_mensal_brl: float = 200.0
    roteiro_id: str | None = Field(default=None, index=True)   # roteiro guiado cujo processo AS IS -> TO BE este fluxo realiza
    criado_em: str
    atualizado_em: str


class VersaoProcesso(SQLModel, table=True):
    __tablename__ = "processo_versao"

    id: str = Field(primary_key=True)          # "<processo>-v<n>"
    processo_id: str = Field(index=True)
    numero: int
    estado: str = Field(default=V_RASCUNHO)
    blueprint: dict = Field(default_factory=dict, sa_column=Column(JSON))
    nota: str = ""
    autor: str
    criada_em: str
    risco: str = "baixo"
    revisor: str | None = None
    parecer: str | None = None
    revisada_em: str | None = None
    publicada_em: str | None = None
