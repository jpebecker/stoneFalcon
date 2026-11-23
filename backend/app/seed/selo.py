"""Selo de versão do seed (v8.3): diz com que versão da demonstração este banco foi semeado.

O seed só roda em banco VAZIO. Um banco semeado por código antigo (antes dos alertas de demonstração, por exemplo) nunca
recebia o catálogo novo: as pessoas viam a plataforma sem alertas e a saída era "apague o arquivo". Agora o seed grava este
selo, e a partida (veja partida.py) refaz o estado inicial de um banco sem selo ou com selo mais antigo.

O selo guarda também COMO o banco foi semeado (`origem`): "demo" é a demonstração completa, com alertas; qualquer outro valor
é o id de um roteiro guiado, que começa SEM alertas de propósito (cada roteiro molda o seu ao vivo). A partida (v8.3.1) trata um
banco semeado por roteiro como um selo antigo: refaz a demonstração completa, senão os alertas nunca voltariam.

`VERSAO_SEMENTE` NÃO é a versão da plataforma: é o número do seed. Some 1 sempre que o catálogo da demonstração
(catalogo.py) ou os cenários de alerta (alertas_demo.py) mudarem de um jeito que um banco já semeado precisa receber.
"""
from sqlmodel import Field, Session, SQLModel

from ..core.relogio import agora

VERSAO_SEMENTE = 4      # 4 (8.3.1): mais um alerta não lido para Marina, Rafael e Carla (sistemas lentos)
CHAVE = "demo"
ORIGEM_DEMO = "demo"       # a demonstração completa; outro valor = id do roteiro guiado que reiniciou o banco


class SeloSemente(SQLModel, table=True):
    __tablename__ = "selo_semente"
    chave: str = Field(primary_key=True)
    versao: int
    gravado_em: str = ""
    origem: str = ORIGEM_DEMO   # bancos com selo da 8.3 (sem esta coluna) contam como a demonstração completa


def ler(s: Session) -> int | None:
    """A versão do seed gravada neste banco; `None` se nunca foi gravada (banco semeado por código anterior ao selo)."""
    selo = s.get(SeloSemente, CHAVE)
    return selo.versao if selo else None


def origem(s: Session) -> str | None:
    """Como o banco foi semeado: "demo" (completa) ou o id do roteiro guiado; `None` sem selo."""
    selo = s.get(SeloSemente, CHAVE)
    return (selo.origem or ORIGEM_DEMO) if selo else None


def gravar(s: Session, origem: str = ORIGEM_DEMO) -> None:
    s.merge(SeloSemente(chave=CHAVE, versao=VERSAO_SEMENTE, gravado_em=agora().isoformat(), origem=origem))
    s.commit()


def atualizado(s: Session) -> bool:
    """Um banco da demonstração completa com selo igual ou mais novo que o do código não é tocado (uma demonstração em andamento
    sobrevive ao reinício). Um banco semeado por roteiro guiado nunca conta como atual: ele não tem os alertas."""
    versao = ler(s)
    return versao is not None and versao >= VERSAO_SEMENTE and origem(s) == ORIGEM_DEMO
