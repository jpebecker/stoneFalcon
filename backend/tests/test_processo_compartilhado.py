"""v8.3/05: um processo compartilhado entre duas áreas é a mesma coisa nas duas pontas. Caso de referência: "Registro de
incidente de sistema" (Thiago, Logística, compartilhado com a Engenharia, isto é, com o Lucas)."""
import pytest

from app.seed.demo import semear
from app.tools import dados_ficticios, executor
from tests.conftest import como

V1 = "/api/v1"
NOME = "Registro de incidente de sistema"
ENTRADA = {"sistema": "Cadastro de lojistas", "descricao": "Consultas com tempo esgotado.", "severidade": "alta"}


@pytest.fixture(autouse=True)
def _limpo():
    dados_ficticios.zerar()
    executor.zerar_limites()


@pytest.fixture()
def demo(api, sessao):
    semear(sessao, alertas=False)
    return api


def _processo(api, perfil):
    return next((p for p in api.get(f"{V1}/processos", headers=como(perfil)).json() if p["nome"] == NOME), None)


def _executar(api, perfil, pid):
    r = api.post(f"{V1}/processos/{pid}/executar", json={"entrada": ENTRADA}, headers=como(perfil))
    assert r.status_code == 200, r.text
    return r.json()


def test_lucas_lista_abre_e_executa_o_processo_compartilhado(demo):
    p = _processo(demo, "lucas")
    assert p and p["compartilhado_com"] == ["engenharia"]
    d = demo.get(f"{V1}/processos/{p['id']}", headers=como("lucas")).json()
    assert d["pode_executar"] is True and d["pode_editar"] is False
    assert _executar(demo, "lucas", p["id"])["status"] == "concluida"


def test_a_execucao_de_cada_lado_aparece_na_historia_do_outro(demo):
    p = _processo(demo, "thiago")
    do_lucas, do_thiago = _executar(demo, "lucas", p["id"]), _executar(demo, "thiago", p["id"])
    for perfil in ("thiago", "lucas"):                                    # o histórico do processo é o mesmo nas duas pontas
        quem = {e["id"]: e["persona"] for e in demo.get(f"{V1}/processos/{p['id']}/execucoes", headers=como(perfil)).json()}
        assert quem[do_lucas["id"]] == "lucas" and quem[do_thiago["id"]] == "thiago", perfil
    for perfil in ("thiago", "lucas"):                                    # e a lista de execuções (a do Início) também
        ids = {e["id"] for e in demo.get(f"{V1}/execucoes?limite=200", headers=como(perfil)).json()}
        assert {do_lucas["id"], do_thiago["id"]} <= ids, perfil
        for e in (do_lucas, do_thiago):                                   # e dá para abrir a execução do outro
            assert demo.get(f"{V1}/execucoes/{e['id']}", headers=como(perfil)).status_code == 200, perfil


def test_quem_nao_recebe_o_processo_nao_ve_nem_executa_nem_abre_as_execucoes(demo):
    p = _processo(demo, "thiago")
    exe = _executar(demo, "lucas", p["id"])
    assert _processo(demo, "marina") is None
    assert demo.get(f"{V1}/processos/{p['id']}", headers=como("marina")).status_code == 403
    assert demo.post(f"{V1}/processos/{p['id']}/executar", json={"entrada": ENTRADA}, headers=como("marina")).status_code == 403
    assert demo.get(f"{V1}/execucoes/{exe['id']}", headers=como("marina")).status_code == 403
    assert exe["id"] not in {e["id"] for e in demo.get(f"{V1}/execucoes?limite=200", headers=como("marina")).json()}
    assert demo.get(f"{V1}/processos/{p['id']}/execucoes", headers=como("marina")).status_code == 403


def test_o_outro_lado_executa_mas_nao_edita_nem_compartilha(demo):
    p = _processo(demo, "thiago")
    blueprint = demo.get(f"{V1}/processos/{p['id']}", headers=como("thiago")).json()["versoes"][0]["blueprint"]
    assert demo.put(f"{V1}/processos/{p['id']}", json={"blueprint": blueprint, "nota": "teste"}, headers=como("lucas")).status_code == 403
    assert demo.post(f"{V1}/processos/{p['id']}/compartilhar", json={"areas": []}, headers=como("lucas")).status_code == 403
    assert demo.put(f"{V1}/processos/{p['id']}", json={"blueprint": blueprint, "nota": "ok"}, headers=como("thiago")).status_code == 200


def test_o_resumo_diz_de_quem_e_e_com_quem_e_compartilhado(demo):
    for perfil in ("thiago", "lucas"):
        p = _processo(demo, perfil)
        assert (p["area"], p["area_nome"], p["dono_nome"]) == ("logistica", "Logística", "Thiago Moreira"), perfil
        assert p["compartilhado_nomes"] == ["Engenharia de Plataforma"], perfil
    outros = [x for x in demo.get(f"{V1}/processos", headers=como("lucas")).json() if x["nome"] != NOME]
    assert outros and all(x["compartilhado_nomes"] == [] for x in outros)           # só o compartilhado leva o selo


def test_a_trilha_guarda_o_compartilhamento_e_a_execucao_do_outro_lado(demo):
    p = _processo(demo, "thiago")
    _executar(demo, "lucas", p["id"])
    eventos = demo.get(f"{V1}/auditoria?agente_id={p['id']}&limite=500", headers=como("lucas")).json()["eventos"]
    tipos = {(e["tipo"], e["ator"]) for e in eventos}
    assert ("processo_compartilhado", "thiago") in tipos
    assert any(e["ator"] == "lucas" for e in eventos)                               # a execução do Lucas está na trilha do processo


def test_o_mapa_liga_as_duas_areas_pelo_processo(demo):
    p = _processo(demo, "thiago")
    mapa = demo.get(f"{V1}/mapa", headers=como("helena")).json()
    no = "processo:" + p["id"]
    ligacoes = {(l["de"], l["para"]): l for l in mapa["ligacoes"]}
    assert ("criador:thiago", no) in ligacoes and ("criador:lucas", no) in ligacoes
    assert ligacoes[("criador:lucas", no)].get("compartilhado") is True            # a ligação da outra área é marcada (tracejada na tela)
    assert not ligacoes[("criador:thiago", no)].get("compartilhado")
    # os processos que não são compartilhados não ganham ligação de outra área
    assert not [l for l in mapa["ligacoes"] if l.get("compartilhado") and l["para"] != no]
