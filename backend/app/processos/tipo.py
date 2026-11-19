"""O tipo PROCESSO do ciclo de vida: como se avalia, se compara e se executa o blueprint de um processo."""
from __future__ import annotations

from sqlmodel import Session

from ..agents import ciclo as ciclo_agentes
from ..agents import modelos as am
from ..agents.blueprint import Blueprint
from ..agents.ciclo import Ciclo, ErroCiclo
from ..agents.dono import PROCESSO, TipoDono, registrar_tipo
from ..agents.governanca import avaliar_risco, ferramentas_sem_permissao
from ..core.identidade import Persona
from . import modelos as pm
from .blueprint import ProcessoBlueprint
from .compilar import compilar
from .diff import comparar, ferramentas_novas


def _normalizar(s: Session, p: Persona, bp: ProcessoBlueprint) -> ProcessoBlueprint:
    bp = bp.model_copy(update={"area": p.area})
    compilar(s, bp, p, "ultima")   # agente que não existe ou de formato antigo: erro em português, já ao salvar
    for b in bp.blocos:
        if b.tipo == "agente":
            a = s.get(am.Agente, b.agente_id)
            if a is not None and not ciclo_agentes.pode_executar(p, a):
                raise ErroCiclo("A sua área não tem acesso ao agente “%s” (bloco “%s”)." % (a.nome, b.titulo), 422)
    return bp


def _antes_de_publicar(s: Session, bp: ProcessoBlueprint) -> None:
    """Um processo só vai ao ar quando os agentes que ele usa já foram publicados."""
    for b in bp.blocos:
        if b.tipo != "agente":
            continue
        a = s.get(am.Agente, b.agente_id)
        if a is None:
            raise ErroCiclo("O bloco “%s” usa um agente que não existe mais." % b.titulo, 422)
        if a.versao_publicada is None or a.estado == am.DEPRECIADO:
            raise ErroCiclo("Publique o agente “%s” antes de publicar o processo (bloco “%s”)." % (a.nome, b.titulo), 422)


def _executavel(s: Session, p: Persona, dono, bruto: dict) -> Blueprint:
    return compilar(s, ProcessoBlueprint.model_validate(bruto), p, "publicada")


TIPO_PROCESSO = registrar_tipo(TipoDono(
    nome=PROCESSO, entidade=pm.Processo, versao_cls=pm.VersaoProcesso, fk="processo_id", modelo=ProcessoBlueprint,
    slug_padrao="processo",
    risco=lambda s, bp: avaliar_risco(compilar(s, bp, None, "ultima")),
    sem_permissao=lambda s, p, bp: ferramentas_sem_permissao(p, compilar(s, bp, None, "ultima")),
    comparar=comparar, ferramentas_novas=ferramentas_novas, executavel=_executavel,
    normalizar=_normalizar, extras_criacao=lambda bp: {"roteiro_id": bp.roteiro_id},
    antes_de_publicar=_antes_de_publicar,
))

ciclo = Ciclo(TIPO_PROCESSO)
