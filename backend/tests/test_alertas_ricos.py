"""v8.3/03: cada persona abre os Alertas e o sino e encontra uma mistura crível: não lido, lido, em tratamento e resolvido,
tudo produzido pelas regras reais (o seed molda o estado, roda as regras e usa as mesmas funções da tela)."""
import pytest
from sqlmodel import select

from app.audit import trilha
from app.core.identidade import PERSONAS
from app.observability import alertas
from app.seed import selo
from app.seed.demo import semear
from app.tools import dados_ficticios, executor
from tests.conftest import como

V1 = "/api/v1"


@pytest.fixture(autouse=True)
def _limpo():
    dados_ficticios.zerar()
    executor.zerar_limites()


def _todos(s):
    return list(s.exec(select(alertas.Alerta)))


def _abertos_de(s, perfil):
    return alertas.visiveis(s, PERSONAS[perfil])


def _nao_lido(a, perfil):
    return perfil not in (a.lido_por or [])


def test_cada_persona_tem_nao_lido_lido_em_tratamento_e_resolvido(sessao):
    semear(sessao)
    for perfil, persona in PERSONAS.items():
        abertos = _abertos_de(sessao, perfil)
        todos = alertas.visiveis(sessao, persona, so_abertos=False)
        assert any(_nao_lido(a, perfil) for a in abertos), (perfil, "não lido")
        assert any(not _nao_lido(a, perfil) and not a.tratando_por for a in abertos), (perfil, "lido")
        assert any(a.tratando_por and a.tratando_nota for a in abertos), (perfil, "em tratamento")
        assert any(a.resolvido_em for a in todos), (perfil, "resolvido")


def test_o_que_a_pessoa_assumiu_e_dela_e_ela_ja_leu(sessao):
    """As funções são as da tela: quem assume já leu, e a nota fica guardada."""
    semear(sessao)
    for perfil in ("marina", "rafael", "carla", "thiago", "lucas", "helena"):
        meus = [a for a in _abertos_de(sessao, perfil) if a.tratando_por == perfil]
        assert meus, perfil
        assert all(perfil in a.lido_por and a.tratando_nota and a.tratando_desde for a in meus), perfil


def test_nenhum_alerta_e_inserido_direto_aberto_e_resolvido_tem_trilha_do_sistema(sessao):
    semear(sessao)
    todos = _todos(sessao)
    abertos = {e.dados["alerta"]: e for e in trilha.listar(sessao, tipo="alerta_aberto", limite=2000)}
    resolvidos = {e.dados["alerta"]: e for e in trilha.listar(sessao, tipo="alerta_resolvido", limite=2000)}
    assert todos and {a.id for a in todos} <= set(abertos)
    assert all(e.ator == "sistema" for e in abertos.values())
    fechados = [a for a in todos if a.resolvido_em]
    assert len(fechados) >= 5 and {a.id for a in fechados} == set(resolvidos)
    assert all(e.ator == "sistema" for e in resolvidos.values())
    assumidos = trilha.listar(sessao, tipo="alerta_assumido", limite=2000)
    assert len(assumidos) >= 6 and all(e.ator in PERSONAS for e in assumidos)   # quem assume é uma pessoa, não o sistema
    assert trilha.verificar(sessao)["integra"] is True


def test_o_sino_conta_so_os_nao_lidos_e_a_pagina_traz_abertos_e_historico(api, sessao):
    semear(sessao)
    for perfil in PERSONAS:
        h = como(perfil)
        abertos = api.get(f"{V1}/alertas", headers=h).json()
        assert api.get(f"{V1}/notificacoes/contagem", headers=h).json()["nao_lidos"] == sum(1 for a in abertos if not a["lido"]), perfil
        assert any(a["tratando_por"] and not a["resolvido_em"] for a in abertos), perfil     # filtro "Em tratamento"
        todos = api.get(f"{V1}/alertas", params={"abertos": "false"}, headers=h).json()        # filtro "Todos"
        assert len(todos) > len(abertos) and any(a["resolvido_em"] for a in todos), perfil


def test_quem_esta_tratando_aparece_para_quem_tambem_recebe_o_alerta(api, sessao):
    """O estoque lento chega ao Thiago e ao Lucas; o que o Lucas leu continua novo para o Thiago."""
    semear(sessao)
    estoque = next(a for a in api.get(f"{V1}/alertas", headers=como("thiago")).json() if a["conector"] == "consultar_estoque")
    do_lucas = next(a for a in api.get(f"{V1}/alertas", headers=como("lucas")).json() if a["id"] == estoque["id"])
    assert estoque["lido"] is False and do_lucas["lido"] is True


def test_duas_rodadas_da_vigia_mantem_a_mistura(sessao):
    semear(sessao)

    def foto():
        return sorted((a.id, a.resolvido_em is None, a.tratando_por, tuple(a.lido_por or [])) for a in _todos(sessao))
    antes = foto()
    for _ in range(2):
        r = alertas.avaliar(sessao)
        assert r["abertos"] == [] and r["resolvidos"] == []
    assert foto() == antes


def test_o_seed_subiu_de_versao_para_os_bancos_antigos_receberem_a_mistura():
    assert selo.VERSAO_SEMENTE >= 2
