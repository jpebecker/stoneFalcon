"""Avaliações automáticas de um blueprint: risco, permissões e custo estimado.

O criador não preenche nada disso: a plataforma calcula a partir das ferramentas
que o agente usa. O nível de risco decide se a publicação precisa da revisão da
Segurança (F4) — é assim que a Engenharia governa o catálogo, não cada agente.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from ..core.identidade import Classificacao, Persona
from ..llm import precos, roteador
from ..tools.catalogo import CATALOGO
from ..tools.permissoes import avaliar
from .blueprint import Blueprint

BAIXO, MEDIO, ALTO = "baixo", "medio", "alto"


@dataclass
class Risco:
    nivel: str
    motivos: list[str] = field(default_factory=list)

    @property
    def exige_revisao(self) -> bool:
        return self.nivel == ALTO


def avaliar_risco(bp: Blueprint) -> Risco:
    motivos_alto, motivos_medio = [], []
    for fid in sorted(bp.ferramentas_usadas()):
        esp = CATALOGO[fid]
        if esp.classificacao >= Classificacao.RESTRITA:
            motivos_alto.append("usa \"%s\", que toca dados restritos" % esp.nome)
        elif esp.exige_aprovacao:
            motivos_alto.append("\"%s\" é uma ação sensível" % esp.nome)
        elif esp.acao == "escrita" and esp.classificacao >= Classificacao.CONFIDENCIAL:
            motivos_alto.append("\"%s\" altera dados confidenciais" % esp.nome)
        elif esp.classificacao >= Classificacao.CONFIDENCIAL:
            motivos_medio.append("lê dados confidenciais com \"%s\"" % esp.nome)
        elif esp.acao == "escrita":
            motivos_medio.append("age em outro sistema com \"%s\"" % esp.nome)
    if motivos_alto:
        return Risco(ALTO, motivos_alto + motivos_medio)
    if motivos_medio:
        return Risco(MEDIO, motivos_medio)
    return Risco(BAIXO, ["só lê informações internas ou públicas"])


def ferramentas_sem_permissao(pessoa: Persona, bp: Blueprint) -> dict[str, str]:
    """Ferramentas do agente que esta pessoa não pode usar -> motivo."""
    saida = {}
    for fid in sorted(bp.ferramentas_usadas()):
        v = avaliar(pessoa, CATALOGO[fid])
        if not v.permitido:
            saida[fid] = v.motivo
    return saida


# ---------- custo estimado por execução ----------
# Premissas de tamanho (tokens), a calibrar com as execuções reais registradas.
_SISTEMA = 450
_CONTEXTO_POR_DEPENDENCIA = 600
_POR_FERRAMENTA_DEFINIDA = 180
_RESULTADO_FERRAMENTA = 500
_SAIDA = 350


@dataclass
class Estimativa:
    custo_brl: float
    chamadas_modelo: int
    por_passo: dict[str, dict]


def estimar_custo(bp: Blueprint) -> Estimativa:
    total_usd, chamadas, por_passo = 0.0, 0, {}
    for p in bp.passos:
        if p.tipo != "agente":
            por_passo[p.id] = {"modelo": None, "custo_brl": 0.0}
            continue
        entrada = _SISTEMA + len(p.depende_de) * _CONTEXTO_POR_DEPENDENCIA + len(p.ferramentas) * _POR_FERRAMENTA_DEFINIDA
        decisao = roteador.decidir(p.modelo, p.instrucao, entrada)
        voltas = 2 if p.ferramentas else 1   # pede a ferramenta, depois conclui
        custo = 0.0
        for v in range(voltas):
            t_in = entrada + v * (_RESULTADO_FERRAMENTA + 120)
            custo += precos.custo_usd(decisao.chave_modelo, t_in, _SAIDA if v == voltas - 1 else 120)
        total_usd += custo
        chamadas += voltas
        por_passo[p.id] = {"modelo": decisao.nome_modelo, "custo_brl": round(precos.usd_para_brl(custo), 5)}
    return Estimativa(round(precos.usd_para_brl(total_usd), 5), chamadas, por_passo)


# ---------- duração estimada (caminho crítico) ----------
_VELOCIDADE = {"rapido": (180, 400), "forte": (70, 900)}   # tokens de saída/s, latência fixa ms (como o runtime)


def estimar_duracao_ms(bp: Blueprint) -> int:
    """Tempo do caminho crítico: passos da mesma camada rodam juntos, então cada camada custa o mais lento."""
    def duracao(p) -> int:
        if p.tipo == "ferramenta":
            return CATALOGO[p.ferramenta].latencia_ms
        if p.tipo == "aprovacao":
            return 0
        entrada = _SISTEMA + len(p.depende_de) * _CONTEXTO_POR_DEPENDENCIA + len(p.ferramentas) * _POR_FERRAMENTA_DEFINIDA
        chave = roteador.decidir(p.modelo, p.instrucao, entrada).chave_modelo
        vel, lat = _VELOCIDADE[chave]
        voltas = 2 if p.ferramentas else 1
        total = voltas * lat + int((_SAIDA + (120 if voltas == 2 else 0)) / vel * 1000)
        return total + max((CATALOGO[f].latencia_ms for f in p.ferramentas), default=0)
    return sum(max(duracao(bp.passo(pid)) for pid in camada) for camada in bp.niveis())
