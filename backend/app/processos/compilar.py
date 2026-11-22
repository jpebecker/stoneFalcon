"""Compila o processo (blocos) no grafo de passos que o runtime já executa.

  bloco "dados" / "plugin"  -> passo "ferramenta"
  bloco "agente"            -> passo "agente" com as instruções, ferramentas e modelo do agente trabalhador
  bloco "aprovacao"         -> passo "aprovacao"
  bloco "condicao"          -> passo "condicao" (ramos "sim" e "não" pulam o que não foi escolhido)
  bloco "saida"             -> passo "ferramenta" (aviso) ou "saida" (resposta final)

O agente do bloco é resolvido na hora: para rodar um processo publicado vale a versão PUBLICADA do agente; para testar um
rascunho vale a última versão (rascunho incluso). Se o agente não pode rodar (pausado, depreciado, sem acesso), o passo
nasce BLOQUEADO e o runtime escala com o motivo, em vez de falhar em silêncio.
"""
from __future__ import annotations

from sqlmodel import Session

from ..agents import ciclo
from ..agents import modelos as am
from ..agents.blueprint import Blueprint, Passo
from ..agents.ciclo import ErroCiclo
from ..core.identidade import Persona
from .blueprint import Bloco, ProcessoBlueprint


def trabalhador(bp: Blueprint) -> Passo | None:
    """O passo do agente trabalhador (um agente = um trabalhador de IA). Agentes de vários passos são o formato antigo."""
    return bp.passos[0] if len(bp.passos) == 1 and bp.passos[0].tipo == "agente" else None


def resolver_agente(s: Session, b: Bloco, pessoa: Persona | None, usar: str) -> tuple[am.Agente, Passo, int, str | None]:
    """(agente, passo trabalhador, versão usada, motivo do bloqueio ou None)."""
    a = s.get(am.Agente, b.agente_id)
    if a is None:
        raise ErroCiclo("O bloco “%s” usa um agente que não existe mais." % b.titulo, 422)
    bloqueio = None
    numero = a.ultima_versao
    if usar == "publicada":
        if a.versao_publicada is None:
            bloqueio = "O agente “%s” ainda não foi publicado." % a.nome
        else:
            numero = a.versao_publicada
        if a.estado == am.PAUSADO:
            bloqueio = "O agente “%s” está pausado%s." % (a.nome, ": " + a.motivo_estado if a.motivo_estado else "")
    if a.estado == am.DEPRECIADO:
        bloqueio = "O agente “%s” foi depreciado e não executa mais." % a.nome
    if bloqueio is None and pessoa is not None and not ciclo.pode_executar(pessoa, a):
        bloqueio = "A área %s não tem acesso ao agente “%s”." % (pessoa.area_nome, a.nome)
    v = s.get(am.VersaoAgente, "%s-v%d" % (a.id, numero))
    w = trabalhador(Blueprint.model_validate(v.blueprint))
    if w is None:
        raise ErroCiclo("O agente “%s” tem vários passos (formato antigo). Converta-o em processo antes de usá-lo como bloco." % a.nome, 422)
    return a, w, numero, bloqueio


def compilar(s: Session | None, pbp: ProcessoBlueprint, pessoa: Persona | None = None, usar: str = "ultima",
             trabalhadores: dict[str, Blueprint] | None = None) -> Blueprint:
    """`trabalhadores` ({agente_id: blueprint}) compila sem banco, com os agentes dados (estimativas do catálogo da demo)."""
    passos: list[Passo] = []
    for b in pbp.blocos:
        base = dict(id=b.id, titulo=b.titulo, depende_de=list(b.depende_de), bloco=b.tipo,
                    ramo=b.ramo.model_dump() if b.ramo else None)
        if b.tipo == "agente" and trabalhadores is not None:
            bpa = trabalhadores[b.agente_id]
            w = trabalhador(bpa)
            passos.append(Passo(tipo="agente", instrucao=w.instrucao, ferramentas=list(w.ferramentas), modelo=w.modelo,
                                max_iteracoes=w.max_iteracoes, agente_ref={"id": b.agente_id, "nome": bpa.nome, "versao": 1},
                                contexto_agente={"nome": bpa.nome, "objetivo": bpa.objetivo, "instrucoes": bpa.instrucoes}, **base))
        elif b.tipo == "agente":
            a, w, numero, bloqueio = resolver_agente(s, b, pessoa, usar)
            bpa = Blueprint.model_validate(s.get(am.VersaoAgente, "%s-v%d" % (a.id, numero)).blueprint)
            passos.append(Passo(tipo="agente", instrucao=w.instrucao, ferramentas=list(w.ferramentas), modelo=w.modelo,
                                max_iteracoes=w.max_iteracoes, bloqueio=bloqueio,
                                agente_ref={"id": a.id, "nome": a.nome, "versao": numero},
                                contexto_agente={"nome": a.nome, "objetivo": bpa.objetivo, "instrucoes": bpa.instrucoes},
                                **base))
        elif b.tipo in ("dados", "plugin") or (b.tipo == "saida" and b.ferramenta):
            passos.append(Passo(tipo="ferramenta", ferramenta=b.ferramenta, entrada=dict(b.entrada), **base))
        elif b.tipo == "aprovacao":
            passos.append(Passo(tipo="aprovacao", **base))
        elif b.tipo == "condicao":
            passos.append(Passo(tipo="condicao", regra=b.regra.model_dump(), **base))
        else:   # saida sem ferramenta: a resposta final
            passos.append(Passo(tipo="saida", texto=b.texto, **base))
    return Blueprint(nome=pbp.nome, objetivo=pbp.objetivo, area=pbp.area, campos=list(pbp.campos), passos=passos,
                     limites=pbp.limites, minutos_manual=pbp.minutos_manual)
