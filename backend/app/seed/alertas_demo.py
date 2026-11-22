"""Alertas de demonstração (v8.1): cada persona entra na demo com UM alerta ligado ao seu papel.

NENHUM alerta é inserido direto. O que se molda é o ESTADO que as regras reais leem (o estado de sistemas integrados, o
histórico sintético de execuções e o orçamento de um processo) e depois roda `alertas.avaliar`, a mesma função que a vigia de
60 segundos usa. Por isso os alertas abrem, atualizam e fecham sozinhos como qualquer outro, e aparecem na trilha. Cada
cenário toca só o que é da persona (um sistema que só o processo dela usa, ou o histórico e o orçamento do processo dela),
para nenhum alerta cair em quem não tem nada com ele:

  Marina  — o processo de dúvidas mais lento que o normal (as últimas execuções demoraram bem mais que a mediana)
  Rafael  — a triagem de chargebacks falhando (4 das últimas 10 execuções escaladas: o agente não concluiu)
  Carla   — orçamento do processo de férias a ≈ 88%
  Thiago  — o estoque lento: só o processo de trocas consulta o estoque do modelo
  Lucas   — "Listar transações do lojista" fora do ar: nenhum processo usa, então o alerta é só da Engenharia, e a triagem
            de incidentes do Lucas (que lê o estado dos sistemas) continua de pé para ele triar esse incidente
  Helena  — orçamento do processo de revisão de custo a ≈ 88% (e vê todos os alertas da empresa)

O estado inicial (`moldar`) e o passo "veja e trate o seu alerta" de cada roteiro guiado (`moldar_persona`) contam a MESMA
história: o roteiro começa limpo (veja `roteiros/reinicio.py`) e o passo molda só o cenário da persona do roteiro.
A moldagem é do sistema (ator "sistema" na trilha), não de uma pessoa.
"""
from __future__ import annotations

import uuid
from datetime import timedelta

from sqlmodel import Session, select

from ..agents.blueprint import Blueprint
from ..agents.governanca import estimar_custo
from ..audit import trilha
from ..core.relogio import agora
from ..finance.resumo import gasto_no_mes
from ..observability import alertas
from ..processos import modelos as pm
from ..runtime import modelos as rm
from ..tools import executor
from . import catalogo, historico
from .historico import _passos

USO_DO_ORCAMENTO = 0.88      # entre 80% (atenção) e 100% (corte)
ESCALADAS_NA_JANELA = 4      # de 10: 40% (>= 30% abre "falhando", < 60% fica em atenção)
FATOR_LENTO = 3.0            # as execuções recentes demoram 3x: o p95 passa de 2x a mediana histórica
SISTEMA_LENTO_THIAGO = "consultar_estoque"   # só o processo de trocas usa
SISTEMA_FORA_LUCAS = "listar_transacoes"     # nenhum processo usa: alerta só da Engenharia
MOLDAGEM = "cenário de demonstração"


def _processo(s: Session, chave: str) -> pm.Processo | None:
    return s.exec(select(pm.Processo).where(pm.Processo.nome == catalogo.NOME_PROCESSO[chave])).first()


def _janela(s: Session, p: pm.Processo) -> list[rm.Execucao]:
    """As últimas execuções que a regra avalia (mais recente primeiro)."""
    return s.exec(select(rm.Execucao).where(rm.Execucao.dono_tipo == "processo").where(rm.Execucao.dono_id == p.id)
                  .where(rm.Execucao.status != rm.AGUARDANDO)
                  .order_by(rm.Execucao.inicio.desc()).limit(alertas.JANELA_EXECUCOES)).all()


def _com_historico(s: Session, p: pm.Processo) -> None:
    """O processo criado ao vivo num roteiro ainda não tem histórico: gera o sintético dele (marcado como demonstração), o
    mesmo do estado inicial, para a regra ter sobre o que se apoiar."""
    tem = s.exec(select(rm.Execucao.id).where(rm.Execucao.dono_tipo == "processo").where(rm.Execucao.dono_id == p.id)
                 .where(rm.Execucao.demo == True)).first()  # noqa: E712
    if tem is None:
        historico.gerar(s, apenas={p.id})


def _falhando(s: Session, p: pm.Processo) -> None:
    """Molda 4 das últimas 10 execuções SINTÉTICAS do processo como escaladas, pelo motivo que o histórico já usa. As execuções
    reais da pessoa (fora do histórico) nunca são tocadas."""
    _com_historico(s, p)
    if "processo_falhando" in alertas.regras_que_valem(s, p, "processo"):
        return
    demo = [e for e in _janela(s, p) if e.demo]
    if len(demo) < alertas.MIN_EXECUCOES:
        return
    motivo = "O agente não concluiu em 6 tentativas."
    for e in demo[1::2][:ESCALADAS_NA_JANELA]:
        bp = Blueprint.model_validate(e.blueprint)
        e.status, e.motivo, e.resultado = rm.ESCALADA, motivo, None
        e.custo_usd = round(e.custo_usd * 0.4, 8)
        e.custo_tudo_forte_usd = round(e.custo_tudo_forte_usd * 0.4, 8)
        e.por_modelo = {k: {**v, "custo_usd": round(v["custo_usd"] * 0.4, 8)} for k, v in (e.por_modelo or {}).items()}
        e.passos = _passos(bp, estimar_custo(bp), e.custo_usd, rm.ESCALADA, motivo)
        s.add(e)
    s.commit()


def _lento(s: Session, p: pm.Processo) -> None:
    """Molda as últimas execuções SINTÉTICAS do processo para demorarem FATOR_LENTO vezes mais (a regra compara o p95 recente
    com a mediana das antigas). As execuções reais da pessoa nunca são tocadas."""
    _com_historico(s, p)
    if "processo_lento" in alertas.regras_que_valem(s, p, "processo"):
        return
    for e in (e for e in _janela(s, p) if e.demo):
        e.duracao_estimada_ms = int(e.duracao_estimada_ms * FATOR_LENTO)
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


def _orcamento_a_88(s: Session, p: pm.Processo) -> None:
    if "orcamento" in alertas.regras_que_valem(s, p, "processo"):
        return
    _ao_menos_um_gasto_no_mes(s, p)
    gasto = gasto_no_mes(s, p.id, "processo")
    if gasto <= 0:
        return
    anterior = p.orcamento_mensal_brl
    p.orcamento_mensal_brl = round(gasto / USO_DO_ORCAMENTO, 4)   # a tela arredonda em centavos; o gasto simulado é de centavos
    p.atualizado_em = agora().isoformat()
    s.add(p)
    s.commit()
    trilha.registrar(s, "orcamento_definido", "sistema", p.id,
                     {"de": anterior, "para": p.orcamento_mensal_brl, "origem": MOLDAGEM}, dono_tipo="processo")


def _cenario(s: Session, persona: str) -> None:
    """Molda o cenário de `persona` (o mesmo no estado inicial e no passo do roteiro)."""
    if persona == "marina":
        p = _processo(s, "duvida")
        if p is not None:
            _lento(s, p)
    elif persona == "rafael":
        p = _processo(s, "triagem")
        if p is not None:
            _falhando(s, p)
    elif persona in ("carla", "helena"):
        p = _processo(s, "ferias" if persona == "carla" else "custo_ia")
        if p is not None:
            _orcamento_a_88(s, p)
    elif persona == "thiago":
        executor.definir_falha(s, SISTEMA_LENTO_THIAGO, "lento", "sistema")
    elif persona == "lucas":
        executor.definir_falha(s, SISTEMA_FORA_LUCAS, "fora_do_ar", "sistema")


def moldar_persona(s: Session, persona: str) -> dict:
    """O passo "veja e trate o seu alerta" de um roteiro guiado: molda SÓ o cenário da persona (o roteiro começa limpo) e roda
    as regras. É idempotente: repetir não molda de novo nem abre alerta novo."""
    _cenario(s, persona)
    return alertas.avaliar(s)


def moldar(s: Session) -> dict:
    """Deixa o estado inicial como o cenário descrito no topo e roda as regras. Devolve o que as regras abriram."""
    for persona in ("marina", "rafael", "carla", "thiago", "lucas", "helena"):
        _cenario(s, persona)
    return alertas.avaliar(s)
