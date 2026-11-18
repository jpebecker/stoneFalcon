"""Histórico SINTÉTICO de execuções (30 dias) para os painéis da demonstração.

Não é medição: é um cenário gerado, marcado com demo=True e sinalizado nas telas.
Os valores seguem o comportamento do runtime: custo pela estimativa do agente
(mesmo roteador), duração típica por passo, ~90% concluídas e um dia ruim na
triagem (sistema de chargebacks instável) para o painel de saúde ter história.
"""
import random
import uuid
from datetime import timedelta

from sqlmodel import Session, select

from ..agents import modelos as am
from ..agents.blueprint import Blueprint
from ..agents.governanca import estimar_custo
from ..audit import trilha
from ..core.db import trava
from ..core.identidade import PERSONAS
from ..core.relogio import agora
from ..llm import precos, registro
from ..runtime import modelos as rm

# Parte das execuções do histórico roda em outros provedores (todos simulados), para os gráficos de Finanças
# não nascerem só com o Claude. Cada nível troca por um modelo de capacidade parecida de outro provedor.
FRACAO_OUTROS_PROVEDORES = 0.35
EQUIVALENTES = {
    "rapido": ["gemini-flash-lite", "gpt-luna", "deepseek-flash", "grok-43"],
    "forte": ["gemini-carbon", "gpt-sol", "deepseek-pro", "grok-47"],
}


def _tokens_do_custo(chave: str, custo_usd: float) -> tuple[int, int]:
    """Tokens coerentes com o custo e a tabela do modelo (metade do gasto em entrada, metade em saída)."""
    m = registro.obter(chave)
    return int(custo_usd * 0.5 / m.preco_entrada * 1_000_000), int(custo_usd * 0.5 / m.preco_saida * 1_000_000)


VOLUME_DIA = {"atendimento": 22, "risco": 9, "pessoas": 12, "logistica": 10}   # execuções por dia útil


def gerar(s: Session, dias: int = 30, semente: int = 7) -> int:
    rnd = random.Random(semente)
    hoje = agora()
    criadas = []
    agentes = s.exec(select(am.Agente).where(am.Agente.estado == am.PUBLICADO)).all()
    for a in agentes:
        v = s.get(am.VersaoAgente, "%s-v%d" % (a.id, a.versao_publicada))
        bp = Blueprint.model_validate(v.blueprint)
        est = estimar_custo(bp)
        pessoas = [p.id for p in PERSONAS.values() if p.area == a.area] or [a.dono]
        modelos_usados = [x["modelo_chave"] for x in est.por_passo.values() if x.get("modelo_chave")]
        chave = "forte" if "forte" in modelos_usados else "rapido"
        for d in range(dias, 0, -1):
            dia = hoje - timedelta(days=d)
            if dia.weekday() >= 5:
                continue
            ruim = a.area == "risco" and d in (6, 7)
            for _ in range(max(1, int(VOLUME_DIA.get(a.area, 8) * rnd.uniform(0.7, 1.3)))):
                inicio = dia.replace(hour=rnd.randint(8, 18), minute=rnd.randint(0, 59), second=rnd.randint(0, 59))
                sorteio = rnd.random()
                if ruim and sorteio < 0.45:
                    status, motivo = rm.ESCALADA, "Levantar contestações da semana: O sistema respondeu com erro 500."
                elif sorteio < 0.06 and d > 3:   # últimos dias saudáveis: a demo começa sem alerta
                    status, motivo = rm.ESCALADA, "O agente não concluiu em 6 tentativas."
                else:
                    status, motivo = rm.CONCLUIDA, None
                custo_brl = est.custo_brl * rnd.uniform(0.75, 1.3) * (0.4 if status == rm.ESCALADA else 1)
                custo_usd = custo_brl / precos.usd_para_brl(1.0)
                fator_forte = 1.0 if chave == "forte" and len(set(modelos_usados)) == 1 else rnd.uniform(3.5, 6.0)
                usado, tudo_forte_usd = chave, custo_usd * fator_forte   # a referência "tudo no forte" não muda
                if rnd.random() < FRACAO_OUTROS_PROVEDORES:   # outro provedor: o custo muda pela razão das tabelas
                    usado = rnd.choice(EQUIVALENTES[chave])
                    custo_usd *= registro.obter(usado).peso / registro.obter(chave).peso
                t_in, t_out = _tokens_do_custo(usado, custo_usd)
                criadas.append(rm.Execucao(
                    id=uuid.uuid4().hex[:12], agente_id=a.id, versao=a.versao_publicada, agente_nome=a.nome, area=a.area,
                    persona=rnd.choice(pessoas), status=status, motivo=motivo, entrada={}, blueprint=bp.model_dump(),
                    passos={}, resultado=None if status != rm.CONCLUIDA else "(histórico de demonstração)",
                    chamadas_modelo=est.chamadas_modelo, custo_usd=round(custo_usd, 8),
                    custo_tudo_forte_usd=round(tudo_forte_usd, 8),
                    tokens_entrada=t_in, tokens_saida=t_out,
                    por_modelo={usado: {"chamadas": est.chamadas_modelo, "custo_usd": round(custo_usd, 8),
                                        "tokens_entrada": t_in, "tokens_saida": t_out}},
                    duracao_estimada_ms=int(rnd.uniform(2500, 9000) * (2.5 if ruim else 1)),
                    simulado=True, demo=True, inicio=inicio.isoformat(), fim=inicio.isoformat()))
    with trava:
        for e in criadas:
            s.add(e)
        s.commit()
    trilha.registrar(s, "historico_demo_gerado", "sistema", dados={"execucoes": len(criadas), "dias": dias})
    return len(criadas)


def apagar(s: Session) -> int:
    with trava:
        itens = s.exec(select(rm.Execucao).where(rm.Execucao.demo == True)).all()  # noqa: E712
        for e in itens:
            s.delete(e)
        s.commit()
    trilha.registrar(s, "historico_demo_apagado", "sistema", dados={"execucoes": len(itens)})
    return len(itens)
