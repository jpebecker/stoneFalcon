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


# estados de um pedido "Crie o seu plugin" (v8/12 e 13)
INT_AGUARDA_ANALISTA = "aguardando_analista"
INT_AGUARDA_SEGURANCA = "aguardando_seguranca"
INT_APROVADO = "aprovado"            # decidido, ainda sem publicar (a publicação é imediata na prática)
INT_PUBLICADO = "publicado"
INT_RECUSADO = "recusado"
INT_REMOVIDO = "removido"


class PedidoPluginInterno(SQLModel, table=True):
    """Pedido "Crie o seu plugin": a pessoa descreve uma ferramenta de mercado e a plataforma rascunha a especificação interna."""
    __tablename__ = "plugin_interno_pedido"

    id: str = Field(primary_key=True)
    solicitante: str = Field(index=True)
    area: str
    ferramenta_mercado: str                         # só para o analista saber do que se trata; não vai para o plugin
    descricao_publica: str                          # o texto público colado (limitado)
    finalidade: str
    areas: list = Field(default_factory=list, sa_column=Column(JSON))
    classificacao: int = 1
    spec: dict = Field(default_factory=dict, sa_column=Column(JSON))        # a especificação editada e enviada
    estado: str = Field(default=INT_AGUARDA_ANALISTA, index=True)
    plugin_id: str | None = None                    # id do plugin interno publicado (v8/13)
    decisao_analista: dict | None = Field(default=None, sa_column=Column(JSON))     # {por, aprovar, parecer, quando}
    decisao_seguranca: dict | None = Field(default=None, sa_column=Column(JSON))
    criado_em: str
    atualizado_em: str
