"""Do agente de vários passos (formato antigo) ao processo: os passos viram blocos e cada passo de IA vira um agente trabalhador.

  passo "ferramenta" (só lê)    -> bloco "dados"
  passo "ferramenta" (escreve)  -> bloco "plugin" (ação)
  passo "agente"                -> bloco "agente" + um agente trabalhador novo (rascunho, do criador)
  passo "aprovacao"             -> bloco "aprovacao"

Os ids dos passos viram ids dos blocos e as dependências ficam iguais: mesma ordem, mesmo paralelismo, mesmas aprovações,
mesmas ferramentas. As referências (`{{entrada.x}}`, `{{passos.ID.saida}}`) continuam valendo sem mudar nada.
"""
from __future__ import annotations

from sqlmodel import Session

from ..agents import ciclo
from ..agents import modelos as am
from ..agents.blueprint import Blueprint, Passo
from ..agents.ciclo import ErroCiclo
from ..core.identidade import Persona
from ..roteiros.catalogo import ROTEIROS
from ..tools.catalogo import CATALOGO
from .blueprint import Bloco, ProcessoBlueprint
from .compilar import trabalhador


def eh_trabalhador(bp: Blueprint) -> bool:
    return trabalhador(bp) is not None


def trabalhador_do_fluxo(bp: Blueprint) -> Blueprint:
    """Resume um fluxo de vários passos num ÚNICO agente trabalhador: o trabalhador LÊ e raciocina (as ferramentas de leitura dos
    passos viram ferramentas dele) e as instruções dos passos de IA viram o que ele deve fazer. Quem AGE em outro sistema (abrir
    chamado, avisar, reter repasse) é o processo, onde a aprovação humana fica à vista: veja `acoes_do_fluxo`."""
    ferramentas: list[str] = []
    for f in _ferramentas_do_fluxo(bp):
        if CATALOGO[f].acao == "leitura" and f not in ferramentas:
            ferramentas.append(f)
    instrucoes = [p.instrucao.strip() for p in bp.passos if p.tipo == "agente" and p.instrucao.strip()]
    modelos = {p.modelo for p in bp.passos if p.tipo == "agente"}
    modelo = modelos.pop() if len(modelos) == 1 else "auto"
    if instrucoes:
        instrucao = " ".join(instrucoes)
        if any(p.tipo == "ferramenta" for p in bp.passos):
            instrucao = "Consulte as informações de que precisar com as ferramentas liberadas. " + instrucao
    else:
        instrucao = bp.objetivo
    return Blueprint(
        nome=bp.nome, objetivo=bp.objetivo, area=bp.area, instrucoes=bp.instrucoes, campos=list(bp.campos),
        passos=[Passo(id="trabalho", titulo=bp.nome[:120], tipo="agente", modelo=modelo, ferramentas=ferramentas,
                      instrucao=instrucao, max_iteracoes=max((p.max_iteracoes for p in bp.passos if p.tipo == "agente"), default=6))],
        limites=bp.limites, minutos_manual=bp.minutos_manual)


def _ferramentas_do_fluxo(bp: Blueprint) -> list[str]:
    return [f for p in bp.passos for f in ([p.ferramenta] if p.ferramenta else []) + list(p.ferramentas)]


def acoes_do_fluxo(bp: Blueprint) -> list[str]:
    """Nomes das ações em outros sistemas que o fluxo faz: ficam de fora do agente e entram como blocos do processo."""
    return sorted({CATALOGO[f].nome for f in _ferramentas_do_fluxo(bp) if CATALOGO[f].acao != "leitura"})


def eh_multipasso(bp: Blueprint) -> bool:
    """Um fluxo "claramente de vários passos": mais de dois passos, aprovação humana ou mais de um passo de IA."""
    return len(bp.passos) > 2 or any(p.tipo == "aprovacao" for p in bp.passos) or sum(p.tipo == "agente" for p in bp.passos) > 1


def roteiro_do_agente(nome: str) -> str | None:
    return next((r.id for r in ROTEIROS.values() if not r.apresentacao and r.agente_nome == nome), None)


def _trabalhador_do_passo(bp: Blueprint, p: Passo, area: str) -> Blueprint:
    nome = ("%s — %s" % (bp.nome, p.titulo))[:80]
    return Blueprint(
        nome=nome, objetivo=("%s. %s" % (p.titulo, bp.objetivo))[:600], area=area, instrucoes=bp.instrucoes, campos=[],
        passos=[Passo(id="trabalho", titulo=p.titulo, tipo="agente", modelo=p.modelo, ferramentas=list(p.ferramentas),
                      instrucao=p.instrucao, max_iteracoes=p.max_iteracoes)],
        limites=bp.limites, minutos_manual=0)


def converter_fluxo(s: Session, pessoa: Persona, bp: Blueprint, roteiro_id: str | None = None,
                    nota: str = "Criado ao transformar um fluxo em processo.") -> tuple[ProcessoBlueprint, list[am.Agente]]:
    """Cria os agentes trabalhadores (rascunhos do criador) e devolve o fluxo de blocos que os usa (ainda não salvo)."""
    agentes: list[am.Agente] = []
    blocos: list[Bloco] = []
    for p in bp.passos:
        base = dict(id=p.id, titulo=p.titulo, depende_de=list(p.depende_de))
        if p.tipo == "ferramenta":
            leitura = CATALOGO[p.ferramenta].acao == "leitura"
            blocos.append(Bloco(tipo="dados" if leitura else "plugin", ferramenta=p.ferramenta, entrada=dict(p.entrada), **base))
        elif p.tipo == "aprovacao":
            blocos.append(Bloco(tipo="aprovacao", **base))
        elif p.tipo == "agente":
            a = ciclo.criar(s, pessoa, _trabalhador_do_passo(bp, p, pessoa.area), nota)
            agentes.append(a)
            blocos.append(Bloco(tipo="agente", agente_id=a.id, **base))
        else:
            raise ErroCiclo("O passo “%s” não tem equivalente em blocos." % p.titulo, 422)
    pbp = ProcessoBlueprint(nome=bp.nome, objetivo=bp.objetivo, area=pessoa.area, campos=list(bp.campos), blocos=blocos,
                            limites=bp.limites, minutos_manual=bp.minutos_manual, roteiro_id=roteiro_id)
    return pbp, agentes
