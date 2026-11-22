"""Alertas de demonstração (v8.1): cada persona entra na demo com pelo menos um alerta ligado ao seu papel.

NENHUM alerta é inserido direto. O que se molda é o ESTADO que as regras reais leem (o estado de sistemas integrados, o
histórico sintético de execuções e o orçamento de um processo) e depois roda `alertas.avaliar`, a mesma função que a vigia de
60 segundos usa. Por isso os alertas abrem, atualizam e fecham sozinhos como qualquer outro, e aparecem na trilha.

  Marina  — "Cadastro de lojistas" lento: o processo de dúvidas depende dele
  Rafael  — a triagem de chargebacks falhando (4 das últimas 10 execuções escaladas)
  Carla   — orçamento do processo de férias a ≈ 88%
  Thiago  — o estoque lento: o processo de trocas consulta o estoque do modelo
  Lucas   — o estado dos sistemas fora do ar: o processo de incidentes depende dele
  Helena  — orçamento do processo de revisão de custo a ≈ 88% (e vê todos os alertas da empresa)

Os roteiros guiados NÃO usam este cenário: cada um começa limpo (veja `roteiros/reinicio.py`).
"""
from __future__ import annotations

import uuid
from datetime import timedelta

from sqlmodel import Session, select

from ..agents.governanca import estimar_custo
from ..audit import trilha
from ..core.identidade import PERSONAS
from ..core.relogio import agora
from ..finance.resumo import gasto_no_mes
from ..observability import alertas
from ..processos import modelos as pm
from ..runtime import modelos as rm
from ..tools import executor
from . import catalogo
from .historico import _passos

USO_DO_ORCAMENTO = 0.88      # entre 80% (atenção) e 100% (corte)
ESCALADAS_NA_JANELA = 4      # de 10: 40% (>= 30% abre "falhando", < 60% fica em atenção)


def _processo(s: Session, chave: str) -> pm.Processo | None:
    return s.exec(select(pm.Processo).where(pm.Processo.nome == catalogo.NOME_PROCESSO[chave])).first()


def _falhando(s: Session, p: pm.Processo) -> None:
    """Molda as últimas 10 execuções do processo: 4 escaladas, espalhadas, pelo mesmo motivo que o histórico já usa."""
    execs = s.exec(select(rm.Execucao).where(rm.Execucao.dono_tipo == "processo").where(rm.Execucao.dono_id == p.id)
                   .order_by(rm.Execucao.inicio.desc()).limit(alertas.JANELA_EXECUCOES)).all()
    if len(execs) < alertas.MIN_EXECUCOES:
        return
    motivo = "Levantar contestações da semana: O sistema respondeu com erro 500."
    from ..agents.blueprint import Blueprint
    for i in range(ESCALADAS_NA_JANELA):
        e = execs[min(i * 2 + 1, len(execs) - 1)]
        bp = Blueprint.model_validate(e.blueprint)
        e.status, e.motivo, e.resultado = rm.ESCALADA, motivo, None
        e.custo_usd = round(e.custo_usd * 0.4, 8)
        e.passos = _passos(bp, estimar_custo(bp), e.custo_usd, rm.ESCALADA, motivo)
        s.add(e)
    s.commit()


def _ao_menos_um_gasto_no_mes(s: Session, p: pm.Processo) -> None:
    """No primeiro dia do mês o histórico (que termina ontem) ainda não gastou nada: repete a execução sintética mais recente
    do processo, agora, para a razão do orçamento ter sobre o que se apoiar."""
    if gasto_no_mes(s, p.id, "processo") > 0:
        return
    ultima = s.exec(select(rm.Execucao).where(rm.Execucao.dono_tipo == "processo").where(rm.Execucao.dono_id == p.id)
                    .where(rm.Execucao.demo == True).order_by(rm.Execucao.inicio.desc())).first()  # noqa: E712
    if ultima is None:
        return
    quando = (agora() - timedelta(minutes=5)).isoformat()
    s.add(rm.Execucao(**{**ultima.model_dump(), "id": uuid.uuid4().hex[:12], "inicio": quando, "fim": quando}))
    s.commit()


def _orcamento_a_88(s: Session, p: pm.Processo, quem: str) -> None:
    _ao_menos_um_gasto_no_mes(s, p)
    gasto = gasto_no_mes(s, p.id, "processo")
    if gasto <= 0:
        return
    anterior = p.orcamento_mensal_brl
    p.orcamento_mensal_brl = round(gasto / USO_DO_ORCAMENTO, 4)   # a tela arredonda em centavos; o gasto simulado é de centavos
    p.atualizado_em = agora().isoformat()
    s.add(p)
    s.commit()
    trilha.registrar(s, "orcamento_definido", quem, p.id, {"de": anterior, "para": p.orcamento_mensal_brl}, dono_tipo="processo")


def moldar(s: Session) -> dict:
    """Deixa o estado inicial como o cenário descrito no topo e roda as regras. Devolve o que as regras abriram."""
    executor.definir_falha(s, "consultar_lojista", "lento", "sistema")           # Marina
    executor.definir_falha(s, "consultar_estoque", "lento", "sistema")           # Thiago
    executor.definir_falha(s, "consultar_estado_sistemas", "fora_do_ar", "sistema")   # Lucas
    triagem = _processo(s, "triagem")
    if triagem is not None:                                                      # Rafael
        _falhando(s, triagem)
    ferias = _processo(s, "ferias")
    if ferias is not None:                                                       # Carla
        _orcamento_a_88(s, ferias, PERSONAS["helena"].id)
    custo = _processo(s, "custo_ia")
    if custo is not None:                                                        # Helena
        _orcamento_a_88(s, custo, PERSONAS["helena"].id)
    return alertas.avaliar(s)
