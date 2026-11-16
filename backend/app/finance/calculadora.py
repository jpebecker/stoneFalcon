"""Calculadora de investimento e retorno: fluxo de caixa mensal, VPL, TIR e payback."""
from __future__ import annotations

from .premissas import Premissas


def projetar(p: Premissas) -> dict:
    meses = []
    acumulado = -p.investimento_total
    taxa_mensal = (1 + p.taxa_desconto_anual) ** (1 / 12) - 1
    vpl = -p.investimento_total
    fluxos = [-p.investimento_total]
    payback = None
    for mes in range(1, p.meses + 1):
        adocao = p.adocao_alvo * min(1.0, mes / p.meses_rampa)
        ativos = p.usuarios * adocao
        execucoes = ativos * p.tarefas_por_usuario_dia * p.dias_uteis
        custo_tokens = execucoes * p.custo_por_execucao
        beneficio = execucoes * p.ganho_por_tarefa
        fluxo = beneficio - custo_tokens - p.custo_fixo_mensal
        acumulado += fluxo
        vpl += fluxo / (1 + taxa_mensal) ** mes
        fluxos.append(fluxo)
        if payback is None and acumulado >= 0:
            payback = mes
        meses.append({"mes": mes, "usuarios_ativos": round(ativos), "execucoes": round(execucoes),
                      "horas_liberadas": round(execucoes * max(p.minutos_por_tarefa - p.minutos_revisao_humana, 0) / 60),
                      "custo_tokens": round(custo_tokens, 2), "custo_fixo": round(p.custo_fixo_mensal, 2),
                      "beneficio": round(beneficio, 2), "fluxo": round(fluxo, 2), "acumulado": round(acumulado, 2)})
    tir_mensal = tir(fluxos)
    custo_total = p.investimento_total + sum(m["custo_tokens"] + m["custo_fixo"] for m in meses)
    beneficio_total = sum(m["beneficio"] for m in meses)
    return {
        "meses": meses,
        "investimento_total": round(p.investimento_total, 2),
        "custo_fixo_mensal": round(p.custo_fixo_mensal, 2),
        "ganho_por_tarefa": round(p.ganho_por_tarefa, 4),
        "payback_mes": payback,
        "vpl": round(vpl, 2),
        "tir_anual": round((1 + tir_mensal) ** 12 - 1, 4) if tir_mensal is not None else None,
        "roi": round((beneficio_total - custo_total) / custo_total, 4) if custo_total else None,
        "beneficio_total": round(beneficio_total, 2),
        "custo_total": round(custo_total, 2),
        "tokens_participacao": round(sum(m["custo_tokens"] for m in meses) / custo_total, 4) if custo_total else 0.0,
    }


def tir(fluxos: list[float], baixo: float = -0.99, alto: float = 10.0) -> float | None:
    """TIR por bisseção (taxa por período). None se não houver troca de sinal."""
    def vpl(taxa):
        return sum(f / (1 + taxa) ** i for i, f in enumerate(fluxos))
    if vpl(baixo) * vpl(alto) > 0:
        return None
    for _ in range(200):
        meio = (baixo + alto) / 2
        if vpl(baixo) * vpl(meio) <= 0:
            alto = meio
        else:
            baixo = meio
    return (baixo + alto) / 2


def ponto_de_equilibrio(p: Premissas) -> float | None:
    """Execuções por mês para cobrir só o custo fixo (sem recuperar o investimento)."""
    margem = p.ganho_por_tarefa - p.custo_por_execucao
    return round(p.custo_fixo_mensal / margem) if margem > 0 else None
