"""v8.1/09: os seis roteiros ganham o passo "veja e trate o seu alerta" e passam de ponta a ponta no modo simulado."""
import pytest
from sqlmodel import Session

from app.core import db
from app.observability import alertas
from app.roteiros.catalogo import ROTEIROS
from app.seed.demo import criar_processo_demo
from app.tools import dados_ficticios, executor
from tests.conftest import como

V1 = "/api/v1"
SEIS = {"marina": "duvida", "rafael": "triagem", "carla": "ferias", "thiago": "troca", "lucas": None, "helena": "custo_ia"}
ENTRADA = {"marina": {"lojista_id": "L1001", "pergunta": "Em quanto tempo o estorno cai para o cliente?"},
           "carla": {"colaborador_id": "C501", "pergunta": "Quantos dias de férias eu tenho?"}}


@pytest.fixture(autouse=True)
def _limpo():
    dados_ficticios.zerar()
    executor.zerar_limites()


@pytest.mark.parametrize("persona", list(SEIS))
def test_o_roteiro_tem_o_passo_de_alerta_da_propria_persona(persona):
    passo = next(p for p in ROTEIROS[persona].passos if p.id == "alerta")
    assert passo.perfil == persona and passo.rota == "/alertas"
    assert ROTEIROS[persona].passos.index(passo) < len(ROTEIROS[persona].passos) - 1 or persona == "lucas"


@pytest.mark.parametrize("persona", [p for p in SEIS if p != "lucas"])
def test_o_passo_prepara_o_cenario_e_a_persona_trata_o_alerta(api, persona):
    chave = SEIS[persona]
    assert api.post(f"{V1}/roteiros/{persona}/reiniciar", headers=como("helena")).status_code == 200
    with Session(db.motor()) as s:
        assert alertas.avaliar(s)["abertos"] == []                                  # o roteiro começa limpo
        if persona != "helena":                                                      # o processo que a persona cria ao vivo
            criar_processo_demo(s, chave)
    if persona == "carla":                                                           # o gasto do mês vem de uma execução de verdade
        pid = next(p["id"] for p in api.get(f"{V1}/processos", headers=como("carla")).json() if p["nome"] == "Orientação de férias")
        assert api.post(f"{V1}/processos/{pid}/executar", json={"entrada": ENTRADA["carla"]}, headers=como("carla")).status_code == 200
    r = api.post(f"{V1}/roteiros/{persona}/alerta", headers=como(persona))
    assert r.status_code == 200, r.text
    assert api.post(f"{V1}/roteiros/{persona}/alerta", headers=como(persona)).json()["abertos"] == []   # repetir não duplica
    meus = [a for a in api.get(f"{V1}/alertas", headers=como(persona)).json() if a["acao"]]
    assert meus and api.get(f"{V1}/notificacoes/contagem", headers=como(persona)).json()["nao_lidos"] >= 1
    a = meus[0]
    corpo = {"valor_brl": 500.0} if a["acao"]["pede"] == "valor_brl" else {}
    ok = api.post(f"{V1}/alertas/{a['id']}/acao", json=corpo, headers=como(persona))
    assert ok.status_code == 200, ok.text
    assert ok.json()["alerta"]["tratando_por"] == persona                           # a ação assumiu o alerta
    if a["acao"]["pede"] == "valor_brl":                                             # orçamento revisto: o alerta fecha sozinho
        assert next(x for x in api.get(f"{V1}/alertas", params={"abertos": False}, headers=como(persona)).json() if x["id"] == a["id"])["resolvido_em"]


def test_lucas_trata_o_alerta_da_falha_que_ele_mesmo_simulou(api, sessao):
    assert api.post(f"{V1}/roteiros/lucas/reiniciar", headers=como("lucas")).status_code == 200
    r = api.post(f"{V1}/ferramentas/consultar_lojista/falha", json={"falha": "fora_do_ar"}, headers=como("lucas"))
    assert r.status_code == 200, r.text
    a = next(x for x in api.get(f"{V1}/alertas", headers=como("lucas")).json() if x["regra"] == "conector_fora")
    assert a["acao"]["id"] == "abrir_sistema"
    assert api.post(f"{V1}/alertas/{a['id']}/assumir", json={"nota": "Normalizando o cadastro."}, headers=como("lucas")).status_code == 200
    assert api.post(f"{V1}/ferramentas/consultar_lojista/falha", json={"falha": None}, headers=como("lucas")).status_code == 200
    depois = next(x for x in api.get(f"{V1}/alertas", params={"abertos": False}, headers=como("lucas")).json() if x["id"] == a["id"])
    assert depois["resolvido_em"] and depois["tratando_por"] == "lucas"
