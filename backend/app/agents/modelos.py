"""Agente e suas versões (persistidos).

Ciclo de vida do agente:
    rascunho -> (em_revisao) -> publicado <-> pausado -> depreciado
Cada alteração gera uma versão nova; a versão publicada nunca é editada.
Execuções guardam o número da versão que rodou.
"""
from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel

# estados do agente
RASCUNHO = "rascunho"
EM_REVISAO = "em_revisao"
PUBLICADO = "publicado"
PAUSADO = "pausado"
DEPRECIADO = "depreciado"

# estados de uma versão
V_RASCUNHO = "rascunho"
V_EM_REVISAO = "em_revisao"
V_REJEITADA = "rejeitada"
V_PUBLICADA = "publicada"
V_SUBSTITUIDA = "substituida"


class Agente(SQLModel, table=True):
    __tablename__ = "agente"

    id: str = Field(primary_key=True)
    nome: str
    area: str = Field(index=True)
    dono: str = Field(index=True)
    estado: str = Field(default=RASCUNHO, index=True)
    versao_publicada: int | None = None
    ultima_versao: int = 1
    risco: str = "baixo"
    compartilhado_com: list = Field(default_factory=list, sa_column=Column(JSON))   # áreas extras que podem executar
    motivo_estado: str | None = None
    orcamento_mensal_brl: float = 100.0         # corte automático: ao atingir, o agente para de executar no mês
    criado_em: str
    atualizado_em: str


class VersaoAgente(SQLModel, table=True):
    __tablename__ = "agente_versao"

    id: str = Field(primary_key=True)          # "<agente>-v<n>"
    agente_id: str = Field(index=True)
    numero: int
    estado: str = Field(default=V_RASCUNHO)
    blueprint: dict = Field(default_factory=dict, sa_column=Column(JSON))
    nota: str = ""                             # o que mudou, nas palavras de quem editou
    autor: str
    criada_em: str
    risco: str = "baixo"
    revisor: str | None = None
    parecer: str | None = None
    revisada_em: str | None = None
    publicada_em: str | None = None
