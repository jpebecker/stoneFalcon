"""Tabelas do marketplace: o que está integrado e os pedidos de integração (os sensíveis passam pelo Lucas)."""
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
