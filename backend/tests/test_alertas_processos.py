"""v8.1/05: os alertas entendem processos (falhando, lento, orçamento, sistema fora) e levam ao processo."""
import pytest
from sqlmodel import select

from app.agents import ciclo
from app.audit import trilha
from app.core.identidade import PERSONAS
from app.observability import alertas
from app.processos.blueprint import ProcessoBlueprint
from app.processos.tipo import ciclo as ciclo_processos
from app.runtime import modelos as rm
from app.agents.dono import PROCESSO, Dono
from app.runtime import motor
from app.seed import catalogo
from app.tools import dados_ficticios, executor
from tests.conftest import como

P = PERSONAS
V1 = "/api/v1"
ENTRADA = {"lojista_id": "L1001", "pergunta": "Em quanto tempo o estorno cai para o cliente?"}


@pytest.fixture(autouse=True)
def _limpo():
    dados_ficticios.zerar()
    executor.zerar_limites()


@pytest.fixture()
def processo(sessao):
    """O processo de dúvidas de lojistas da demo (trabalhador + blocos), publicado pelo ciclo real."""
    from app.seed.demo import criar_processo_demo
    return criar_processo_demo(sessao, "duvida")


def _executar(s, p, n, entrada=None):
    for _ in range(n):
        _p, bp = ciclo_processos.checar_execucao(s, P["marina"], p.id)
        motor.executar(s, P["marina"], bp, entrada or ENTRADA, dono=Dono(PROCESSO, p.id, p.versao_publicada))


def _orcamento(s, p, valor):
    """O gasto simulado é de centavos: grava o orçamento sem o arredondamento da tela para controlar a razão exata."""
    p.orcamento_mensal_brl = valor
    s.add(p)
    s.commit()


def _abertos(s):
    return list(s.exec(select(alertas.Alerta).where(alertas.Alerta.resolvido_em.is_(None))))


def _eventos(s, tipo):
    return trilha.listar(s, tipo=tipo, limite=500)


def test_processo_saudavel_nao_alerta(sessao, processo):
    _executar(sessao, processo, 4)
    alertas.avaliar(sessao)
    assert _abertos(sessao) == []


def test_processo_falhando_abre_e_fecha_sozinho(sessao, processo):
    _executar(sessao, processo, 3)
    executor.definir_falha(sessao, "consultar_lojista", "erro", "lucas")
    _executar(sessao, processo, 3)                       # 3 de 6 escaladas: 50% (>= 30%)
    alertas.avaliar(sessao)
    falhando = [a for a in _abertos(sessao) if a.regra == "processo_falhando"]
    assert len(falhando) == 1 and falhando[0].processo_id == processo.id and falhando[0].agente_id is None
    assert falhando[0].severidade == alertas.ATENCAO and falhando[0].destinatarios == ["marina"]
    assert "falhando" in falhando[0].titulo
    assert any(e.dados["alerta"] == falhando[0].id and e.dono_tipo == "processo" for e in _eventos(sessao, "alerta_aberto"))

    executor.definir_falha(sessao, "consultar_lojista", None, "lucas")
    _executar(sessao, processo, 8)                       # a janela das últimas 10 volta ao normal
    alertas.avaliar(sessao)
    assert [a for a in _abertos(sessao) if a.regra == "processo_falhando"] == []
    assert _eventos(sessao, "alerta_resolvido")


def test_orcamento_do_processo_a_80_abre_atencao_e_a_100_abre_critico_e_bloqueia(sessao, processo):
    _executar(sessao, processo, 2)
    from app.finance.resumo import gasto_no_mes
    gasto = gasto_no_mes(sessao, processo.id, "processo")
    assert gasto > 0
    _orcamento(sessao, processo, gasto / 0.85)                                                       # 85% usado
    alertas.avaliar(sessao)
    orc = [a for a in _abertos(sessao) if a.regra == "orcamento" and a.processo_id == processo.id]
    assert len(orc) == 1 and orc[0].severidade == alertas.ATENCAO and orc[0].destinatarios == ["marina"]

    _orcamento(sessao, processo, gasto)                                                              # 100%: corta
    alertas.avaliar(sessao)
    orc = [a for a in _abertos(sessao) if a.regra == "orcamento" and a.processo_id == processo.id]
    assert len(orc) == 1 and orc[0].severidade == alertas.CRITICO and "bloqueadas" in orc[0].detalhe
    with pytest.raises(ciclo.ErroCiclo) as e:
        ciclo_processos.checar_execucao(sessao, P["marina"], processo.id)
    assert e.value.status == 402


def test_sistema_fora_alerta_o_dono_do_processo_e_a_engenharia_sem_duplicar_por_trabalhador(sessao, processo):
    executor.definir_falha(sessao, "consultar_lojista", "fora_do_ar", "lucas")
    alertas.avaliar(sessao)
    sistema = [a for a in _abertos(sessao) if a.regra == "conector_fora" and a.conector == "consultar_lojista"]
    assert len(sistema) == 1                              # um alerta, não um por trabalhador
    a = sistema[0]
    assert a.processo_id == processo.id and a.agente_id is None
    assert "marina" in a.destinatarios and "lucas" in a.destinatarios
    alertas.avaliar(sessao)                               # reavaliar não duplica
    assert len([x for x in _abertos(sessao) if x.regra == "conector_fora" and x.conector == "consultar_lojista"]) == 1


def test_api_mostra_o_alerta_de_processo_e_a_saude_conta_na_nota(api, sessao, processo):
    antes = {x["agente"]["id"]: x for x in api.get(f"{V1}/saude/agentes", headers=como("marina")).json()}
    assert processo.id in antes and antes[processo.id]["agente"]["tipo"] == "processo"
    executor.definir_falha(sessao, "consultar_lojista", "fora_do_ar", "lucas")
    alertas.avaliar(sessao)
    lista = api.get(f"{V1}/alertas", headers=como("marina")).json()
    meu = next(a for a in lista if a["processo_id"] == processo.id)
    assert meu["agente_id"] is None and not meu["lido"]
    assert api.get(f"{V1}/notificacoes/contagem", headers=como("marina")).json()["nao_lidos"] >= 1
    depois = {x["agente"]["id"]: x for x in api.get(f"{V1}/saude/agentes", headers=como("marina")).json()}
    assert depois[processo.id]["score"]["nota"] < antes[processo.id]["score"]["nota"]
    assert depois[processo.id]["alertas"][0]["processo_id"] == processo.id
    detalhe = api.get(f"{V1}/saude/agentes/{processo.id}", headers=como("marina")).json()
    assert detalhe["agente"]["tipo"] == "processo" and detalhe["alertas"]
    assert api.get(f"{V1}/saude/agentes/{processo.id}", headers=como("rafael")).status_code in (200, 403)


def test_agente_que_roda_sozinho_continua_alertando_como_antes(sessao):
    """Um trabalhador fora de qualquer processo continua sendo avaliado pelo agente (o alerta de sistema vai a ele)."""
    from app.agents.blueprint import Blueprint
    bp = Blueprint.model_validate(catalogo.TRABALHADORES["duvida"].model_dump())
    a = ciclo.criar(sessao, P["marina"], bp)
    ciclo.publicar(sessao, P["marina"], a.id)
    executor.definir_falha(sessao, "consultar_lojista", "fora_do_ar", "lucas")
    alertas.avaliar(sessao)
    sistema = [x for x in _abertos(sessao) if x.regra == "conector_fora" and x.conector == "consultar_lojista"]
    assert [x.agente_id for x in sistema] == [a.id] and sistema[0].processo_id is None
