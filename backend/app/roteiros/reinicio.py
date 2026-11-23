"""Reinício da demonstração: volta ao estado inicial, geral ou o exato de um roteiro."""
from sqlmodel import Session, SQLModel, select

from ..processos import modelos as pm
from ..processos.blueprint import Bloco, ProcessoBlueprint
from ..processos.tipo import ciclo as ciclo_processos
from ..core import db
from .. import rotinas
from ..llm import balanceador
from ..core.identidade import PERSONAS
from ..plugins import servico as plugins
from ..runtime import motor
from ..seed.demo import semear
from ..tools import dados_ficticios, executor
from .catalogo import ROTEIROS


def _versao_em_revisao(s: Session) -> None:
    """Lucas: uma nova versão do processo de triagem (aviso por Slack) esperando a revisão de segurança."""
    rafael = PERSONAS["rafael"]
    processo = s.exec(select(pm.Processo).where(pm.Processo.nome == "Triagem de chargebacks")).first()
    if processo is None:
        return
    atual = ProcessoBlueprint.model_validate(ciclo_processos.versao(s, processo.id, processo.ultima_versao).blueprint)
    aviso = Bloco(id="aviso_slack", tipo="saida", titulo="Avisar o canal #time-risco no Slack", depende_de=["retencao"], ferramenta="enviar_notificacao",
                  entrada={"canal": "slack", "destino": "#time-risco", "mensagem": "Caso de {{passos.cadastro.saida.nome}} encaminhado: {{passos.analise.saida}}"})
    ciclo_processos.editar(s, rafael, processo.id, atual.model_copy(update={"blocos": [*atual.blocos, aviso]}),
                           "Passei a avisar o canal #time-risco no Slack quando o caso é encaminhado.")
    ciclo_processos.publicar(s, rafael, processo.id)   # risco alto: vai para a revisão da Segurança


def _pitch(s: Session) -> None:
    """Pitch v7: os plugins que o agente da planilha usa (Google Sheets e Slack) já estão integrados pelo Thiago,
    para a demonstração seguir direto ao ponto. Planilha local, agenda, balanceador e relógio nascem como no início."""
    for plugin in ("sheets", "slack"):
        plugins.integrar(s, PERSONAS["thiago"], plugin, "Preparado antes do pitch.")


PREPARAR = {"versao_em_revisao": _versao_em_revisao, "pitch": _pitch}


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
    balanceador.zerar()   # desfaz a queda simulada de provedor e a carga de teste
    rotinas.zerar()       # o relógio das rotinas volta ao normal (as agendas somem com o banco)
    with Session(db.motor()) as nova:
        semear(nova, sem=roteiro.sem if roteiro else frozenset(), alertas=roteiro is None, origem=roteiro.id if roteiro else None)
        if roteiro and roteiro.preparar:
            PREPARAR[roteiro.preparar](nova)
    return {"ok": True, "roteiro": roteiro.id if roteiro else None}
