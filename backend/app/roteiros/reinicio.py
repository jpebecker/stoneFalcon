"""Reinício da demonstração: volta ao estado inicial, geral ou o exato de um roteiro."""
from sqlmodel import Session, SQLModel, select

from ..agents import ciclo
from ..agents import modelos as am
from ..agents.blueprint import Blueprint
from ..core import db
from ..core.identidade import PERSONAS
from ..plugins import servico as plugins
from ..runtime import motor
from ..seed.demo import semear
from ..tools import dados_ficticios, executor
from .catalogo import ROTEIROS


def _versao_em_revisao(s: Session) -> None:
    """Lucas: uma nova versão da triagem (aviso por Slack) esperando a revisão de segurança."""
    rafael = PERSONAS["rafael"]
    agente = s.exec(select(am.Agente).where(am.Agente.nome == "Triagem de chargebacks")).first()
    if agente is None:
        return
    atual = Blueprint.model_validate(ciclo.versao(s, agente.id, agente.ultima_versao).blueprint)
    passos = []
    for p in atual.passos:
        if p.id == "acao":
            p = p.model_copy(update={
                "ferramentas": sorted(set(p.ferramentas) | {"enviar_notificacao"}),
                "instrucao": p.instrucao + " Avise o canal #time-risco no Slack com o resumo do caso."})
        passos.append(p)
    ciclo.editar(s, rafael, agente.id, atual.model_copy(update={"passos": passos}),
                 "Passei a avisar o canal #time-risco no Slack quando o caso é encaminhado.")
    ciclo.publicar(s, rafael, agente.id)   # risco alto: vai para a revisão da Segurança


PREPARAR = {"versao_em_revisao": _versao_em_revisao}


def reiniciar(s: Session | None = None, roteiro_id: str | None = None) -> dict:
    """Apaga tudo e recria o estado inicial. Com `roteiro_id`, deixa o estado exato daquele roteiro."""
    roteiro = ROTEIROS.get(roteiro_id) if roteiro_id else None
    if s is not None:
        s.close()
    with db.trava:
        SQLModel.metadata.drop_all(db.motor())
        db.criar_tabelas()
    dados_ficticios.zerar()
    plugins.zerar()
    executor.zerar_limites()
    motor.zerar_pendentes()
    with Session(db.motor()) as nova:
        semear(nova, sem=roteiro.sem if roteiro else frozenset())
        if roteiro and roteiro.preparar:
            PREPARAR[roteiro.preparar](nova)
    return {"ok": True, "roteiro": roteiro.id if roteiro else None}
