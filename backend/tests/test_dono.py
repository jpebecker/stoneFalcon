"""v8/03: ciclo de vida e runtime sem supor que o dono é um agente (o dono tem tipo e id; hoje só o agente existe)."""
from sqlalchemy import text
from sqlmodel import Session, select

from app.agents import ciclo
from app.agents import dono as d
from app.agents.blueprint import Blueprint
from app.audit import trilha
from app.core import db
from app.core.identidade import PERSONAS
from app.runtime import modelos as rm
from app.runtime import motor as rt
from tests.legado import DUVIDA_LOJISTA
import pytest

pytestmark = pytest.mark.usefixtures("legado")   # v7: usa fluxos de vários passos como dado de exemplo (veja o fixture)

P = PERSONAS


def _bp():
    return DUVIDA_LOJISTA


def test_o_ciclo_do_agente_e_um_ciclo_parametrizado_pelo_tipo(sessao):
    assert d.tipo(d.AGENTE).entidade is ciclo.m.Agente
    outro = ciclo.Ciclo(d.tipo(d.AGENTE))
    a = outro.criar(sessao, P["marina"], _bp())
    assert ciclo.obter(sessao, a.id).id == a.id            # as funções do módulo e a classe falam do mesmo agente
    outro.publicar(sessao, P["marina"], a.id)
    assert ciclo.obter(sessao, a.id).estado == "publicado"


def test_eventos_do_ciclo_carregam_o_tipo_do_dono(sessao):
    a = ciclo.criar(sessao, P["marina"], _bp())
    ciclo.publicar(sessao, P["marina"], a.id)
    eventos = trilha.listar(sessao, agente_id=a.id)
    assert {e.tipo for e in eventos} >= {"agente_criado", "agente_publicado"}
    assert all(e.dono_tipo == "agente" for e in eventos)


def test_execucao_grava_tipo_e_id_do_dono(sessao):
    a = ciclo.criar(sessao, P["marina"], _bp())
    ciclo.publicar(sessao, P["marina"], a.id)
    a, bp = ciclo.checar_execucao(sessao, P["marina"], a.id)
    entrada = {c: "L1001" if c == "lojista_id" else "Qual o prazo de estorno?" for c in bp.ids_campos()}
    exe, _ = rt.executar(sessao, P["marina"], bp, entrada, dono=d.Dono(d.AGENTE, a.id, a.versao_publicada))
    assert (exe.dono_tipo, exe.dono_id, exe.agente_id, exe.versao) == ("agente", a.id, a.id, 1)
    assert rt.dono_da(exe) == d.Dono("agente", a.id, 1)
    # o evento de fechamento da execução também diz de quem é
    ev = [e for e in trilha.listar(sessao, agente_id=a.id) if e.tipo.startswith("execucao_")]
    assert ev and all(e.dono_tipo == "agente" for e in ev)


def test_chamar_com_agente_id_continua_valendo(sessao):
    exe, _ = rt.executar(sessao, P["marina"], _bp().model_copy(update={"area": "atendimento"}),
                            {c.id: "L1001" if c.id == "lojista_id" else "Qual o prazo?" for c in _bp().campos}, agente_id="sandbox")
    assert (exe.dono_tipo, exe.dono_id, exe.agente_id) == ("agente", "sandbox", "sandbox")


def test_linha_antiga_sem_dono_le_como_agente():
    exe = rm.Execucao(id="x", agente_id="ag-1", persona="marina", inicio="2026-01-01T00:00:00", versao=2)
    assert rt.dono_da(exe) == d.Dono("agente", "ag-1", 2)


def test_blueprint_executavel_do_agente_e_o_proprio_blueprint(sessao):
    a = ciclo.criar(sessao, P["marina"], _bp())
    ciclo.publicar(sessao, P["marina"], a.id)
    _, bp = ciclo.checar_execucao(sessao, P["marina"], a.id)
    assert isinstance(bp, Blueprint) and bp.nome == a.nome


# ---------- banco da v7 abre na v8 ----------
def _como_na_v7(motor_):
    """Tira as colunas novas da v8, como se o banco tivesse sido criado pela v7."""
    with motor_.begin() as con:
        for tabela, coluna in (("execucao", "dono_tipo"), ("execucao", "dono_id"), ("auditoria", "dono_tipo")):
            con.execute(text('DROP INDEX IF EXISTS "ix_%s_%s"' % (tabela, coluna)))
            con.execute(text('ALTER TABLE "%s" DROP COLUMN "%s"' % (tabela, coluna)))


def test_banco_da_v7_ganha_as_colunas_novas_e_a_cadeia_continua_integra(motor):
    with Session(motor) as s:
        a = ciclo.criar(s, P["marina"], _bp())
        ciclo.publicar(s, P["marina"], a.id)
        a, bp = ciclo.checar_execucao(s, P["marina"], a.id)
        rt.executar(s, P["marina"], bp, {c: "L1001" if c == "lojista_id" else "Qual o prazo de estorno?" for c in bp.ids_campos()}, agente_id=a.id, versao=1)
    _como_na_v7(motor)
    feitas = db.acrescentar_colunas(motor)
    assert {"execucao.dono_tipo", "execucao.dono_id", "auditoria.dono_tipo"} <= set(feitas)
    assert db.acrescentar_colunas(motor) == []             # idempotente
    with Session(motor) as s:
        antigas = s.exec(select(rm.Execucao)).all()
        assert antigas and all(e.dono_tipo == "agente" for e in antigas)
        assert all(e.dono_tipo == "agente" for e in s.exec(select(trilha.EventoAuditoria)).all())
        assert trilha.verificar(s)["integra"] is True
