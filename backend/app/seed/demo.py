"""Estado inicial da demo: agentes trabalhadores e processos já publicados, passando pelo ciclo de vida real.

Roda uma vez, quando o banco está vazio (desligue com STONEFALCON_SEMEAR=0).
Tudo passa pelas mesmas funções que a tela usa, então a auditoria já nasce íntegra.

v8: cada agente de vários passos da v7 virou um trabalhador (um passo de IA) mais um processo de blocos que o usa
(definições em processos_demo.py).
"""
from sqlmodel import Session, select

from ..agents import ciclo
from ..agents import modelos as m
from ..core.identidade import PERSONAS
from ..processos.blueprint import ProcessoBlueprint
from ..processos.tipo import ciclo as ciclo_processos
from . import arquivos_demo, historico
from .processos_demo import CHAVES, ROTEIRO, TRABALHADORES, processo

# quem cria cada um, o orçamento mensal do processo e o parecer da Segurança (só o que passa pela revisão de risco alto)
_CRIADOR = {"duvida": "marina", "triagem": "rafael", "ferias": "carla", "troca": "thiago"}
_ORCAMENTO = {"duvida": 120.0, "triagem": 300.0, "ferias": 80.0, "troca": 100.0}
_PARECER = {"triagem": "Retenção de repasse protegida por confirmação humana; acesso restrito à área de risco. Aprovado."}
_NOTA = {"duvida": "Primeira versão, a partir das perguntas mais comuns da fila.", "triagem": "Triagem diária de contestações.",
         "ferias": "Dúvidas de férias e benefícios.", "troca": "Troca de maquininha com cadastro, regra e estoque em paralelo."}


def criar_processo_demo(s: Session, chave: str):
    """Cria e publica o trabalhador e o processo de `chave` (revisão da Segurança incluída quando o risco é alto)."""
    criador, lucas, helena = PERSONAS[_CRIADOR[chave]], PERSONAS["lucas"], PERSONAS["helena"]
    trabalhador = ciclo.criar(s, criador, TRABALHADORES[chave], _NOTA[chave])
    ciclo.publicar(s, criador, trabalhador.id)
    p = ciclo_processos.criar(s, criador, ProcessoBlueprint.model_validate(processo(chave, trabalhador.id)), _NOTA[chave])
    p = ciclo_processos.publicar(s, criador, p.id)   # risco alto: vai para a revisão da Segurança
    if p.estado == m.EM_REVISAO:
        ciclo_processos.revisar(s, lucas, p.id, True, _PARECER[chave])
    ciclo_processos.definir_orcamento(s, helena, p.id, _ORCAMENTO[chave])
    return p


def semear(s: Session, sem: frozenset[str] | set[str] = frozenset()) -> bool:
    """Estado inicial da demo. `sem` tira os processos (e o trabalhador de cada um) que um roteiro faz a persona criar ao vivo
    ("duvida", "triagem", "ferias", "troca"), para o roteiro começar do zero daquele fluxo."""
    if s.exec(select(m.Agente).limit(1)).first():
        return False
    for chave in CHAVES:
        if chave not in sem:
            criar_processo_demo(s, chave)
    arquivos_demo.semear(s)
    historico.gerar(s)
    return True


__all__ = ["semear", "criar_processo_demo", "ROTEIRO"]
