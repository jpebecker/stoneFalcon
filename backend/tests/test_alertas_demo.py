"""v8.1/06: cada persona entra na demo com pelo menos um alerta aberto pelas regras reais."""
import pytest
from sqlmodel import Session, select

from app.audit import trilha
from app.core import db
from app.core.identidade import PERSONAS
from app.observability import alertas
from app.roteiros.reinicio import reiniciar
from app.runtime import modelos as rm
from app.seed.demo import semear
from app.tools import dados_ficticios, executor
from tests.conftest import como

V1 = "/api/v1"

# o que cada persona deve ver (regra, parte do título): coerente com o próprio perfil
ESPERADO = {
    "marina": ("processo_lento", "Resposta a dúvidas de lojistas"),
    "rafael": ("processo_falhando", "Triagem de chargebacks"),
    "carla": ("orcamento", "Orientação de férias"),
    "thiago": ("conector_lento", "estoque"),
    "lucas": ("conector_fora", "transações"),
    "helena": ("orcamento", "Revisão mensal do custo de IA"),
}


@pytest.fixture(autouse=True)
def _limpo():
    dados_ficticios.zerar()
    executor.zerar_limites()


def _nao_lidos(s, perfil):
    return [a for a in alertas.visiveis(s, PERSONAS[perfil]) if PERSONAS[perfil].id not in (a.lido_por or [])]


def _abertos(s):
    return list(s.exec(select(alertas.Alerta).where(alertas.Alerta.resolvido_em.is_(None))))


def test_cada_persona_entra_com_um_alerta_nao_lido_coerente_com_o_perfil(sessao):
    semear(sessao)
    for perfil, (regra, trecho) in ESPERADO.items():
        meus = _nao_lidos(sessao, perfil)
        assert any(a.regra == regra and trecho.lower() in a.titulo.lower() for a in meus), (perfil, [(a.regra, a.titulo) for a in meus])


def test_nenhum_alerta_e_inserido_direto_todos_nascem_da_avaliacao(sessao):
    semear(sessao)
    abertos = _abertos(sessao)
    assert abertos
    eventos = {e.dados["alerta"]: e for e in trilha.listar(sessao, tipo="alerta_aberto", limite=500)}
    assert {a.id for a in abertos} <= set(eventos) and all(e.ator == "sistema" for e in eventos.values())
    assert alertas.avaliar(sessao)["abertos"] == []                      # a mesma regra, sobre o mesmo estado: nada novo
    # desfeito o estado, as regras fecham o que abriram (nada ficou "chumbado")
    for cid in ("consultar_estoque", "listar_transacoes"):
        executor.definir_falha(sessao, cid, None, "lucas")
    fechados = alertas.avaliar(sessao)["resolvidos"]
    assert {a.id for a in abertos if a.regra.startswith("conector_")} <= set(fechados)


def test_historico_e_marcado_como_demonstracao(sessao):
    semear(sessao)
    execs = sessao.exec(select(rm.Execucao)).all()
    assert execs and all(e.demo and e.simulado for e in execs)
    assert [e for e in execs if e.status == rm.ESCALADA]                 # a triagem falhando é histórico sintético moldado


def test_reiniciar_a_demo_volta_ao_mesmo_conjunto_de_alertas(sessao):
    semear(sessao)
    antes = sorted((a.regra, a.titulo, a.severidade) for a in _abertos(sessao))
    reiniciar(sessao)
    with Session(db.motor()) as s:
        depois = sorted((a.regra, a.titulo, a.severidade) for a in _abertos(s))
    assert antes == depois and antes


def test_iniciar_um_roteiro_guiado_comeca_sem_alertas(api, sessao):
    semear(sessao)
    assert _abertos(sessao)
    for roteiro in ("lucas", "marina", "helena"):
        assert api.post(f"{V1}/roteiros/{roteiro}/reiniciar", headers=como("helena")).status_code == 200
        with Session(db.motor()) as s:
            assert _abertos(s) == [], roteiro
        assert api.get(f"{V1}/notificacoes/contagem", headers=como("lucas")).json()["nao_lidos"] == 0


def test_api_do_sino_mostra_os_alertas_de_cada_persona(api, sessao):
    semear(sessao)
    for perfil in ESPERADO:
        assert api.get(f"{V1}/notificacoes/contagem", headers=como(perfil)).json()["nao_lidos"] >= 1, perfil


def test_cada_cenario_toca_so_a_propria_persona(sessao):
    """Ninguém recebe alerta de cenário de outra persona (a Helena vê todos, a Engenharia recebe os de sistema)."""
    semear(sessao)
    for perfil, (regra, trecho) in ESPERADO.items():
        if perfil in ("helena", "lucas"):
            continue
        meus = [(a.regra, a.titulo) for a in alertas.visiveis(sessao, PERSONAS[perfil])]
        assert len(meus) == 1 and meus[0][0] == regra and trecho.lower() in meus[0][1].lower(), (perfil, meus)


def test_o_processo_do_lucas_segue_de_pe_para_triar_o_incidente(api, sessao):
    semear(sessao)
    pid = next(p["id"] for p in api.get(f"{V1}/processos", headers=como("lucas")).json() if p["nome"] == "Triagem de incidente de sistema")
    r = api.post(f"{V1}/processos/{pid}/executar", json={"entrada": {"sistema": "Transações e contestações"}}, headers=como("lucas"))
    assert r.status_code == 200, r.text
    assert "CRÍTICO" in str(r.json())


def test_a_moldagem_do_orcamento_e_do_sistema_nao_de_uma_pessoa(sessao):
    semear(sessao)
    moldados = [e for e in trilha.listar(sessao, tipo="orcamento_definido", limite=500) if (e.dados or {}).get("origem")]
    assert moldados and all(e.ator == "sistema" for e in moldados)
