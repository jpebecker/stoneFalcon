"""Estado inicial da demo: agentes trabalhadores e processos já publicados, passando pelo ciclo de vida real.

Roda uma vez, quando o banco está vazio (desligue com STONEFALCON_SEMEAR=0).
Tudo passa pelas mesmas funções que a tela usa, então a auditoria já nasce íntegra.

v8: cada agente de vários passos da v7 virou um trabalhador (um passo de IA) mais um processo de blocos que o usa
(definições em catalogo.py, a fonte única).
"""
from sqlmodel import Session, select

from ..agents import ciclo
from ..agents import modelos as m
from ..core.identidade import PERSONAS
from ..processos.blueprint import ProcessoBlueprint
from ..processos.tipo import ciclo as ciclo_processos
from . import arquivos_demo, historico
from .catalogo import CHAVES, DEMOS, ROTEIRO, TRABALHADORES, processo


def criar_processo_demo(s: Session, chave: str):
    """Cria e publica o trabalhador e o processo de `chave` (revisão da Segurança incluída quando o risco é alto)."""
    demo = DEMOS[chave]
    criador, lucas, helena = PERSONAS[demo.persona], PERSONAS["lucas"], PERSONAS["helena"]
    trabalhador = ciclo.criar(s, criador, TRABALHADORES[chave], demo.nota)
    ciclo.publicar(s, criador, trabalhador.id)
    p = ciclo_processos.criar(s, criador, ProcessoBlueprint.model_validate(processo(chave, trabalhador.id)), demo.nota)
    p = ciclo_processos.publicar(s, criador, p.id)   # risco alto: vai para a revisão da Segurança
    if p.estado == m.EM_REVISAO:
        ciclo_processos.revisar(s, lucas, p.id, True, demo.parecer or "Aprovado.")
    ciclo_processos.definir_orcamento(s, helena, p.id, demo.orcamento)
    return p


def semear(s: Session, sem: frozenset[str] | set[str] = frozenset()) -> bool:
    """Estado inicial da demo. `sem` tira os processos (e o trabalhador de cada um) que um roteiro faz a persona criar ao vivo
    ("duvida", "triagem", "ferias", "troca"), para o roteiro começar do zero daquele fluxo."""
    if s.exec(select(m.Agente).limit(1)).first():
        return False
    arquivos_demo.preparar(s)      # o plugin e os arquivos primeiro: os processos de Lucas e Helena já leem arquivos
    for chave in CHAVES:
        if chave not in sem:
            criar_processo_demo(s, chave)
    arquivos_demo.semear(s)
    historico.gerar(s)
    return True


__all__ = ["semear", "criar_processo_demo", "ROTEIRO"]
