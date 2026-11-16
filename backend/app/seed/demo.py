"""Estado inicial da demo: agentes já publicados, passando pelo ciclo de vida real.

Roda uma vez, quando o banco está vazio (desligue com STONEFALCON_SEMEAR=0).
Tudo passa pelas mesmas funções que a tela usa, então a auditoria já nasce íntegra.
"""
from sqlmodel import Session, select

from ..agents import ciclo
from ..agents import modelos as m
from ..core.identidade import PERSONAS
from ..studio.modelos_prontos import por_id
from ..agents.blueprint import Blueprint
from . import historico
from .agentes_exemplo import DUVIDA_LOJISTA, TRIAGEM_CHARGEBACK


def semear(s: Session) -> bool:
    if s.exec(select(m.Agente).limit(1)).first():
        return False
    marina, rafael, carla, lucas = (PERSONAS[x] for x in ("marina", "rafael", "carla", "lucas"))

    a = ciclo.criar(s, marina, DUVIDA_LOJISTA, "Primeira versão, a partir das perguntas mais comuns da fila.")
    ciclo.publicar(s, marina, a.id)

    t = ciclo.criar(s, rafael, TRIAGEM_CHARGEBACK, "Triagem diária de contestações.")
    ciclo.publicar(s, rafael, t.id)   # risco alto: vai para revisão
    ciclo.revisar(s, lucas, t.id, True, "Retenção de repasse protegida por confirmação humana; acesso restrito à área de risco. Aprovado.")

    ferias = Blueprint.model_validate(por_id("ferias_colaborador")["blueprint"])
    f = ciclo.criar(s, carla, ferias, "Dúvidas de férias e benefícios.")
    ciclo.publicar(s, carla, f.id)
    for agente, orcamento in ((a, 120.0), (t, 300.0), (f, 80.0)):
        ciclo.definir_orcamento(s, PERSONAS["helena"], agente.id, orcamento)
    historico.gerar(s)
    return True
