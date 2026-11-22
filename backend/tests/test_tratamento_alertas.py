"""v8.1/07 e 08: assumir o alerta e a ação de tratamento de cada regra, por perfil."""
import pytest
from sqlmodel import select

from app.agents import modelos as am
from app.audit.trilha import EventoAuditoria
from app.observability import alertas
from app.processos import modelos as pm
from app.seed.demo import semear
from app.tools import dados_ficticios, executor
from tests.conftest import como

V1 = "/api/v1"


@pytest.fixture(autouse=True)
def _limpo():
    dados_ficticios.zerar()
    executor.zerar_limites()


@pytest.fixture()
def demo(sessao):
    semear(sessao)


def _meus(api, perfil, abertos=True):
    return api.get(f"{V1}/alertas", params={"abertos": abertos}, headers=como(perfil)).json()


def _alerta(api, perfil, regra, trecho=""):
    return next(a for a in _meus(api, perfil) if a["regra"] == regra and trecho.lower() in a["titulo"].lower())


def _eventos(s, tipo):
    return list(s.exec(select(EventoAuditoria).where(EventoAuditoria.tipo == tipo)).all())


# ---------------------------------------------------------------- 07: assumir
def test_assumir_mostra_em_tratamento_para_todos_os_destinatarios_com_nota_e_hora(api, demo):
    a = _alerta(api, "marina", "conector_lento", "Cadastro")
    assert a["tratando_por"] is None
    r = api.post(f"{V1}/alertas/{a['id']}/assumir", json={"nota": "Falei com a Engenharia, aguardando retorno."}, headers=como("marina"))
    assert r.status_code == 200, r.text
    assert r.json()["tratando_nome"] == "Marina Duarte" and r.json()["tratando_nota"].startswith("Falei") and r.json()["tratando_desde"]
    # a Engenharia também recebe este alerta de sistema e vê quem está tratando
    visto = next(x for x in _meus(api, "lucas") if x["id"] == a["id"])
    assert visto["tratando_por"] == "marina" and visto["tratando_nome"] == "Marina Duarte"
    # outro destinatário não toma o alerta de quem já assumiu
    assert api.post(f"{V1}/alertas/{a['id']}/assumir", json={}, headers=como("lucas")).status_code == 409


def test_so_destinatario_ou_a_helena_assume(api, demo):
    carla = _alerta(api, "carla", "orcamento")
    assert api.post(f"{V1}/alertas/{carla['id']}/assumir", json={}, headers=como("rafael")).status_code == 404
    assert api.post(f"{V1}/alertas/{carla['id']}/assumir", json={}, headers=como("lucas")).status_code == 404
    assert api.post(f"{V1}/alertas/{carla['id']}/assumir", json={"nota": "Vou conversar com a Carla."}, headers=como("helena")).status_code == 200


def test_devolver_e_a_auditoria_registra_quem_quando_e_a_nota(api, sessao, demo):
    a = _alerta(api, "rafael", "processo_falhando")
    api.post(f"{V1}/alertas/{a['id']}/assumir", json={"nota": "Olhando o sistema de contestações."}, headers=como("rafael"))
    assert api.post(f"{V1}/alertas/{a['id']}/devolver", headers=como("helena")).status_code == 200      # a Helena pode devolver
    assert api.post(f"{V1}/alertas/{a['id']}/devolver", headers=como("rafael")).status_code == 409      # já devolvido
    assert next(x for x in _meus(api, "rafael") if x["id"] == a["id"])["tratando_por"] is None
    ass = [e for e in _eventos(sessao, "alerta_assumido") if e.dados["alerta"] == a["id"]]
    assert ass and ass[0].ator == "rafael" and ass[0].dados["nota"].startswith("Olhando") and ass[0].quando and ass[0].dono_tipo == "processo"
    dev = [e for e in _eventos(sessao, "alerta_devolvido") if e.dados["alerta"] == a["id"]]
    assert dev and dev[0].ator == "helena" and dev[0].dados["tratando_antes"] == "rafael"


def test_alerta_resolvido_sozinho_guarda_quem_estava_tratando(api, sessao, demo):
    a = _alerta(api, "thiago", "conector_lento", "estoque")
    api.post(f"{V1}/alertas/{a['id']}/assumir", json={"nota": "Pedi a normalização."}, headers=como("thiago"))
    executor.definir_falha(sessao, "consultar_estoque", None, "lucas")
    alertas.avaliar(sessao)
    antigo = next(x for x in _meus(api, "thiago", abertos=False) if x["id"] == a["id"])
    assert antigo["resolvido_em"] and antigo["tratando_por"] == "thiago" and antigo["tratando_nota"] == "Pedi a normalização."
    assert api.post(f"{V1}/alertas/{a['id']}/assumir", json={}, headers=como("thiago")).status_code == 409   # já resolvido
    resolvido = [e for e in _eventos(sessao, "alerta_resolvido") if e.dados["alerta"] == a["id"]]
    assert resolvido and resolvido[0].dados["tratando_por"] == "thiago"


def test_saude_mostra_o_estado_em_tratamento(api, demo):
    a = _alerta(api, "rafael", "processo_falhando")
    api.post(f"{V1}/alertas/{a['id']}/assumir", json={"nota": "x"}, headers=como("rafael"))
    cartao = next(x for x in api.get(f"{V1}/saude/agentes", headers=como("rafael")).json() if x["agente"]["id"] == a["processo_id"])
    assert cartao["alertas"][0]["tratando_nome"] == "Rafael Lima"


# ---------------------------------------------------------------- 08: ação por regra
def _acao(api, perfil, alerta, **corpo):
    return api.post(f"{V1}/alertas/{alerta['id']}/acao", json=corpo, headers=como(perfil))


def test_cada_persona_tem_uma_acao_para_o_alerta_semeado_em_poucos_cliques(api, demo):
    esperado = {"marina": ("conector_lento", "abrir_sistema"), "rafael": ("processo_falhando", "pausar"),
                "carla": ("orcamento", "revisar_orcamento"), "thiago": ("conector_lento", "abrir_sistema"),
                "lucas": ("conector_fora", "abrir_sistema"), "helena": ("orcamento", "revisar_orcamento")}
    for perfil, (regra, acao) in esperado.items():
        a = next(x for x in _meus(api, perfil) if x["regra"] == regra and x["acao"] and x["acao"]["id"] == acao)
        assert a["acao"]["rotulo"], perfil


def test_pausar_pelo_alerta_usa_a_pausa_de_emergencia_e_assume_o_alerta(api, sessao, demo):
    a = _alerta(api, "rafael", "processo_falhando")
    assert a["acao"]["id"] == "pausar" and a["acao"]["rotulo"] == "Pausar o processo"
    r = _acao(api, "rafael", a, motivo="Contestações com erro 500 no sistema.")
    assert r.status_code == 200, r.text
    p = sessao.get(pm.Processo, a["processo_id"])
    assert p.estado == am.PAUSADO and p.motivo_estado == "Contestações com erro 500 no sistema."
    depois = r.json()["alerta"]
    assert depois["tratando_por"] == "rafael" and depois["acao"] is None            # já pausado: sem botão
    assert [e for e in _eventos(sessao, "alerta_acao") if e.dados["acao"] == "pausar"]
    assert [e for e in _eventos(sessao, "processo_pausado")]                                 # a mesma trilha da tela de pausa


def test_revisar_o_orcamento_pelo_alerta_fecha_o_alerta_quando_a_condicao_some(api, sessao, demo):
    a = _alerta(api, "carla", "orcamento")
    assert api.post(f"{V1}/alertas/{a['id']}/acao", json={}, headers=como("carla")).status_code == 422     # precisa do valor
    processo = sessao.get(pm.Processo, a["processo_id"])
    r = _acao(api, "carla", a, valor_brl=500.0)
    assert r.status_code == 200, r.text
    sessao.refresh(processo)
    assert processo.orcamento_mensal_brl == 500.0
    todos = _meus(api, "carla", abertos=False)
    fechado = next(x for x in todos if x["id"] == a["id"])
    assert fechado["resolvido_em"] and fechado["tratando_por"] == "carla"             # fechou sozinho e guardou quem tratou


def test_abrir_o_sistema_leva_para_a_saude_e_assume(api, sessao, demo):
    a = _alerta(api, "marina", "conector_lento", "Cadastro")
    r = _acao(api, "marina", a)
    assert r.status_code == 200 and r.json()["rota"] == "/saude" and r.json()["alerta"]["tratando_por"] == "marina"


def test_quem_nao_pode_nao_ve_o_botao_e_a_api_recusa(api, sessao, demo):
    # sistema fora no cadastro: o dono pausa; a Engenharia abre o sistema em Saúde
    executor.definir_falha(sessao, "consultar_lojista", "fora_do_ar", "lucas")
    alertas.avaliar(sessao)
    da_marina = _alerta(api, "marina", "conector_fora", "cadastro")
    da_engenharia = next(x for x in _meus(api, "lucas") if x["id"] == da_marina["id"])
    assert da_marina["acao"]["id"] == "pausar" and da_engenharia["acao"]["id"] == "abrir_sistema"
    # orçamento: o botão é de quem pode revisá-lo (o dono ou o CoE de IA)
    carla = _alerta(api, "carla", "orcamento")
    como_helena = next(x for x in _meus(api, "helena") if x["id"] == carla["id"])
    assert como_helena["acao"]["id"] == "revisar_orcamento"
    assert api.post(f"{V1}/alertas/{carla['id']}/acao", json={"valor_brl": 5}, headers=como("rafael")).status_code == 404
    # quem não pode operar o processo recebe 403 mesmo sabendo o id
    sem_acao = [x for x in _meus(api, "helena") if x["acao"] is None]
    assert all(not x.get("resolvido_em") for x in sem_acao)


def test_restaurar_o_provedor_e_so_da_helena(api, sessao, demo):
    assert api.post(f"{V1}/balanceador/provedores/anthropic/falha", json={"fora": True}, headers=como("helena")).status_code == 200
    a = next(x for x in _meus(api, "helena") if x["regra"] == "provedor_fora")
    assert a["acao"]["id"] == "restaurar_provedor"
    assert next(x for x in _meus(api, "lucas") if x["id"] == a["id"])["acao"] is None            # a Engenharia só vê
    r = _acao(api, "helena", a)
    assert r.status_code == 200
    assert next(x for x in _meus(api, "helena", abertos=False) if x["id"] == a["id"])["resolvido_em"]
