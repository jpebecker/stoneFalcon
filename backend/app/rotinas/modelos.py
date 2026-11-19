"""Tabelas das rotinas. São tabelas NOVAS (create_all as cria): bancos de versões anteriores continuam valendo."""
from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel


class Rotina(SQLModel, table=True):
    """Agenda de um agente ou processo publicado, com uma entrada fixa. Roda em nome de quem agendou."""
    __tablename__ = "rotina"

    id: str = Field(primary_key=True)
    agente_id: str = Field(index=True)          # id do agente OU do processo (veja dono_tipo); o nome da coluna vem da v7
    dono_tipo: str = Field(default="agente", index=True)   # "agente" | "processo" (linhas antigas = agente)
    dono: str                                   # quem agendou: a execução usa as permissões dele
    frequencia: str                             # "diaria" | "semanal"
    dia_semana: int | None = None               # 0 = segunda ... 6 = domingo (só na semanal)
    hora: int = 9
    minuto: int = 0
    entrada: dict = Field(default_factory=dict, sa_column=Column(JSON))   # entrada fixa (sem dado pessoal)
    ativa: bool = True
    proxima_em: str | None = None               # ISO, no relógio das rotinas
    ultima_em: str | None = None
    ultima_execucao_id: str | None = None
    ultimo_resultado: str | None = None         # status da última execução ou o motivo de ter sido pulada
    criada_em: str


class RotinaExecucao(SQLModel, table=True):
    """Liga uma execução à rotina que a disparou (o selo "rotina" em Execuções e no Mapa de IA)."""
    __tablename__ = "rotina_execucao"

    execucao_id: str = Field(primary_key=True)
    rotina_id: str = Field(index=True)
    origem: str = "agenda"                      # "agenda" (disparou sozinha) | "manual" (Rodar agora)
