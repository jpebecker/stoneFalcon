"""Selo de versão do seed (v8.3): diz com que versão da demonstração este banco foi semeado.

O seed só roda em banco VAZIO. Um banco semeado por código antigo (antes dos alertas de demonstração, por exemplo) nunca
recebia o catálogo novo: as pessoas viam a plataforma sem alertas e a saída era "apague o arquivo". Agora o seed grava este
selo, e a partida (veja partida.py) refaz o estado inicial de um banco sem selo ou com selo mais antigo.

`VERSAO_SEMENTE` NÃO é a versão da plataforma: é o número do seed. Some 1 sempre que o catálogo da demonstração
(catalogo.py) ou os cenários de alerta (alertas_demo.py) mudarem de um jeito que um banco já semeado precisa receber.
"""
from sqlmodel import Field, Session, SQLModel

from ..core.relogio import agora

VERSAO_SEMENTE = 2
CHAVE = "demo"


class SeloSemente(SQLModel, table=True):
    __tablename__ = "selo_semente"
    chave: str = Field(primary_key=True)
    versao: int
    gravado_em: str = ""


def ler(s: Session) -> int | None:
    """A versão do seed gravada neste banco; `None` se nunca foi gravada (banco semeado por código anterior ao selo)."""
    selo = s.get(SeloSemente, CHAVE)
    return selo.versao if selo else None


def gravar(s: Session) -> None:
    s.merge(SeloSemente(chave=CHAVE, versao=VERSAO_SEMENTE, gravado_em=agora().isoformat()))
    s.commit()


def atualizado(s: Session) -> bool:
    """Um banco com selo igual ou mais novo que o do código não é tocado (uma demonstração em andamento sobrevive ao reinício)."""
    versao = ler(s)
    return versao is not None and versao >= VERSAO_SEMENTE
