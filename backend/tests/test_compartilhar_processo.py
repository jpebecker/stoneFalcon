"""v8.3/07: compartilhar e parar de compartilhar um processo pela tela (a API que a tela chama)."""
import pytest
from sqlmodel import select

from app.audit import trilha
from app.observability import alertas
from app.seed.demo import semear
from app.tools import dados_ficticios, executor
from tests.conftest import como

V1 = "/api/v1"


@pytest.fixture(autouse=True)
def _limpo():
    dados_ficticios.zerar()
    executor.zerar_limites()


@pytest.fixture()
def demo(api, sessao):
    semear(sessao, alertas=False)
    return api


def _meu(api, perfil, nome):
    return next((p for p in api.get(f"{V1}/processos", headers=como(perfil)).json() if p["nome"] == nome), None)


def test_a_lista_de_areas_traz_as_seis(demo):
    areas = demo.get(f"{V1}/areas", headers=como("marina")).json()
    assert {a["id"] for a in areas} == {"atendimento", "risco", "pessoas", "logistica", "engenharia", "gestao"}
    assert all(a["nome"] for a in areas)


def test_marina_compartilha_com_risco_rafael_ve_e_ao_parar_deixa_de_ver(demo):
    nome = "Consulta ao FAQ de atendimento"
    p = _meu(demo, "marina", nome)
    assert p["compartilhado_com"] == [] and _meu(demo, "rafael", nome) is None       # antes: o Rafael não vê

    r = demo.post(f"{V1}/processos/{p['id']}/compartilhar", json={"areas": ["risco"]}, headers=como("marina"))
    assert r.status_code == 200 and r.json()["compartilhado_com"] == ["risco"] and r.json()["compartilhado_nomes"] == ["Prevenção a Fraudes"]
    do_rafael = _meu(demo, "rafael", nome)                                           # logo depois: vê, com o selo, e executa
    assert do_rafael and do_rafael["compartilhado_nomes"] == ["Prevenção a Fraudes"]
    d = demo.get(f"{V1}/processos/{p['id']}", headers=como("rafael")).json()
    assert d["pode_executar"] is True and d["pode_editar"] is False
    ex = demo.post(f"{V1}/processos/{p['id']}/executar", json={"entrada": {"assunto": "Estorno"}}, headers=como("rafael"))
    assert ex.status_code == 200      # a execução é aceita; o arquivo do FAQ não é da área de risco, então o bloco dele escala (veja abaixo)
    assert ex.json()["status"] == "escalada" and "faq-atendimento.csv" in str(ex.json()["passos"])

    r = demo.post(f"{V1}/processos/{p['id']}/compartilhar", json={"areas": []}, headers=como("marina"))   # parar de compartilhar
    assert r.status_code == 200 and r.json()["compartilhado_com"] == []
    assert _meu(demo, "rafael", nome) is None                                        # some da lista, do detalhe e da execução
    assert demo.get(f"{V1}/processos/{p['id']}", headers=como("rafael")).status_code == 403
    assert demo.post(f"{V1}/processos/{p['id']}/executar", json={"entrada": {"assunto": "Estorno"}}, headers=como("rafael")).status_code == 403


def test_a_mudanca_vai_para_a_trilha_com_as_areas(demo):
    p = _meu(demo, "marina", "Consulta ao FAQ de atendimento")
    demo.post(f"{V1}/processos/{p['id']}/compartilhar", json={"areas": ["risco", "pessoas"]}, headers=como("marina"))
    demo.post(f"{V1}/processos/{p['id']}/compartilhar", json={"areas": []}, headers=como("marina"))
    eventos = [e for e in demo.get(f"{V1}/processos/{p['id']}", headers=como("marina")).json()["historico"] if e["tipo"] == "processo_compartilhado"]
    assert sorted(tuple(e["dados"]["areas"]) for e in eventos) == [(), ("pessoas", "risco")]
    assert {e["ator"] for e in eventos} == {"marina"}


def test_so_quem_edita_compartilha_e_a_area_dona_nao_entra_na_lista(demo):
    p = _meu(demo, "marina", "Consulta ao FAQ de atendimento")
    assert demo.post(f"{V1}/processos/{p['id']}/compartilhar", json={"areas": ["risco"]}, headers=como("rafael")).status_code == 403
    assert demo.post(f"{V1}/processos/{p['id']}/compartilhar", json={"areas": ["atendimento", "risco"]}, headers=como("marina")).json()["compartilhado_com"] == ["risco"]
    assert demo.post(f"{V1}/processos/{p['id']}/compartilhar", json={"areas": ["inexistente"]}, headers=como("marina")).status_code == 422


def test_os_alertas_abertos_acompanham_o_compartilhamento_na_hora(demo, sessao):
    from app.seed import alertas_demo
    p = _meu(demo, "marina", "Consulta ao FAQ de atendimento")
    from app.processos import modelos as pm
    proc = sessao.get(pm.Processo, p["id"])
    alertas_demo._ligar_lento(sessao, proc)
    alertas.avaliar(sessao)
    chega = lambda perfil: any(a["processo_id"] == p["id"] for a in demo.get(f"{V1}/alertas", headers=como(perfil)).json())   # noqa: E731
    assert chega("marina") and not chega("rafael")
    demo.post(f"{V1}/processos/{p['id']}/compartilhar", json={"areas": ["risco"]}, headers=como("marina"))
    assert chega("rafael")                                                          # sem esperar a vigia de 60 s
    demo.post(f"{V1}/processos/{p['id']}/compartilhar", json={"areas": []}, headers=como("marina"))
    assert not chega("rafael")
    assert [e for e in trilha.listar(sessao, tipo="alerta_destinatarios_alterados", limite=20)]
