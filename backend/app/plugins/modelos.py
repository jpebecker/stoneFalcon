"""Tabelas do marketplace: o que está integrado e os pedidos de integração (os sensíveis passam pelo Lucas)."""
from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel

# estados de um pedido
PENDENTE = "pendente"         # plugin confidencial/restrito: espera o parecer da Segurança
APROVADO = "aprovado"
RECUSADO = "recusado"
REGISTRADO = "registrado"     # quem não cria nem governa só registra o desejo; ninguém precisa decidir


class IntegracaoPlugin(SQLModel, table=True):
    __tablename__ = "plugin_integracao"

    plugin_id: str = Field(primary_key=True)
    integrado_por: str
    area: str
    quando: str
    origem: str = "direta"        # "direta" (público/interno) ou "pedido:<id>" (aprovado pela Segurança)


class PedidoPlugin(SQLModel, table=True):
    __tablename__ = "plugin_pedido"

    id: str = Field(primary_key=True)
    plugin_id: str = Field(index=True)
    solicitante: str = Field(index=True)
    area: str
    motivo: str = ""
    estado: str = Field(default=PENDENTE, index=True)
    revisor: str | None = None
    parecer: str | None = None
    criado_em: str
    decidido_em: str | None = None


class ArquivoPlugin(SQLModel, table=True):
    """Arquivo do plugin Arquivos e Planilhas (o REAL): CSV ou XLSX enviado por uma pessoa, guardado como colunas e linhas."""
    __tablename__ = "plugin_arquivo"

    id: str = Field(primary_key=True)
    nome: str = Field(index=True)
    formato: str                                   # "csv" | "xlsx"
    classificacao: int = 1                         # Classificacao: 0 pública ... 3 restrita
    areas: list = Field(default_factory=list, sa_column=Column(JSON))     # áreas que podem usar ("*" = todas)
    dono: str = Field(index=True)                  # quem enviou
    area_dono: str = ""
    colunas: list = Field(default_factory=list, sa_column=Column(JSON))
    linhas: list = Field(default_factory=list, sa_column=Column(JSON))    # lista de {coluna: valor}
    tamanho_bytes: int = 0
    versao: int = 1                                # sobe a cada mudança de conteúdo
    criado_em: str
    atualizado_em: str
    atualizado_por: str
    demo: bool = False                             # arquivo do estado inicial da demo
