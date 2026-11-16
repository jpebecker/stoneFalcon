"""Registro persistido de cada execução de agente."""
from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel

# status de uma execução
EM_ANDAMENTO = "em_andamento"
CONCLUIDA = "concluida"
AGUARDANDO = "aguardando_aprovacao"
ESCALADA = "escalada"        # o agente desistiu de forma segura e passou para um humano
FALHOU = "falhou"            # erro de plataforma (não deveria acontecer)
NEGADA = "negada"


class Execucao(SQLModel, table=True):
    __tablename__ = "execucao"

    id: str = Field(primary_key=True)
    agente_id: str | None = Field(default=None, index=True)
    versao: int | None = None
    agente_nome: str = ""
    area: str = ""
    persona: str = Field(index=True)
    status: str = Field(default=EM_ANDAMENTO, index=True)
    motivo: str | None = None                       # por que escalou / falhou / está parada
    entrada: dict = Field(default_factory=dict, sa_column=Column(JSON))     # já mascarada
    blueprint: dict = Field(default_factory=dict, sa_column=Column(JSON))   # retrato do agente executado
    passos: dict = Field(default_factory=dict, sa_column=Column(JSON))      # id -> registro do passo
    pendencia: dict | None = Field(default=None, sa_column=Column(JSON))    # ação esperando humano
    resultado: str | None = None                    # texto final (mascarado)
    chamadas_modelo: int = 0
    tokens_entrada: int = 0
    tokens_saida: int = 0
    tokens_cache: int = 0
    custo_usd: float = 0.0
    custo_tudo_forte_usd: float = 0.0               # mesmo consumo, tudo no modelo forte (sem roteador)
    por_modelo: dict = Field(default_factory=dict, sa_column=Column(JSON))   # chave_modelo -> chamadas, custo, tokens
    demo: bool = Field(default=False, index=True)   # histórico sintético da demonstração
    duracao_ms: int = 0                             # relógio de parede
    duracao_estimada_ms: int = 0                    # soma do caminho crítico (paralelos contam uma vez)
    simulado: bool = False
    inicio: str = Field(index=True)
    fim: str | None = None
