"""v8/09 (contrato): agente novo = UM trabalhador; agente de vários passos só existe em banco antigo (roda, é só leitura e converte);
um banco da v7 abre na v8 sem erros.

Estes testes NÃO usam o fixture `legado`: eles provam a regra que o fixture desliga.
"""
import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.agents import ciclo
from app.agents import modelos as am
from app.agents.ciclo import ErroCiclo
from app.audit import trilha
from app.core import db
from app.core.identidade import PERSONAS as P
from app.seed.agentes_exemplo import DUVIDA_LOJISTA, TRIAGEM_CHARGEBACK
from tests.conftest import como

V1 = "/api/v1"
FIXTURE_V7 = Path(__file__).parent / "fixtures" / "banco_v7.db"


# ---------- a regra: mais de um passo é rejeitado, em português, apontando para Processos ----------
def test_agente_de_varios_passos_e_rejeitado_ao_salvar(sessao):
    assert len(DUVIDA_LOJISTA.passos) > 1
    with pytest.raises(ErroCiclo) as e:
        ciclo.criar(sessao, P["marina"], DUVIDA_LOJISTA)
    assert e.value.status == 422 and "Processos" in str(e.value) and "uma tarefa" in str(e.value)
    assert not sessao.exec(select(am.Agente)).all()


def test_a_api_nao_cria_nem_edita_agente_de_varios_passos(api):
    h = como("marina")
    r = api.post(f"{V1}/agentes", json={"blueprint": DUVIDA_LOJISTA.model_dump()}, headers=h)
    assert r.status_code == 422 and "Processos" in r.json()["detail"]
    um_passo = DUVIDA_LOJISTA.model_copy(update={"passos": DUVIDA_LOJISTA.passos[-1:]}).model_dump()
    um_passo["passos"][0]["depende_de"] = []
    ok = api.post(f"{V1}/agentes", json={"blueprint": um_passo}, headers=h)
    assert ok.status_code == 200, ok.text
    aid = ok.json()["id"]
    r = api.put(f"{V1}/agentes/{aid}", json={"blueprint": DUVIDA_LOJISTA.model_dump(), "nota": "voltou"}, headers=h)
    assert r.status_code == 422 and "Processos" in r.json()["detail"]


def test_o_estudio_so_salva_o_trabalhador_e_o_fluxo_vira_processo(api):
    texto = ("Quando um lojista pergunta algo no chamado, eu abro o cadastro dele, procuro a regra na política de atendimento "
             "e escrevo a resposta com o tom certo. Levo uns 8 minutos por chamado.")
    sug = api.post(f"{V1}/estudio/sugerir", json={"descricao": texto}, headers=como("marina")).json()
    assert api.post(f"{V1}/agentes", json={"blueprint": sug["blueprint"]}, headers=como("marina")).status_code == 422
    assert api.post(f"{V1}/agentes", json={"blueprint": sug["trabalhador"]}, headers=como("marina")).status_code == 200


# ---------- agente antigo que já está no banco: roda, é só leitura e converte ----------
@pytest.fixture()
def antigo(sessao):
    """Um agente de vários passos como os que bancos da v7 têm: gravado desligando a regra só durante a criação."""
    from app.agents.ciclo import TIPO_AGENTE
    original = TIPO_AGENTE.normalizar
    object.__setattr__(TIPO_AGENTE, "normalizar", None)
    try:
        a = ciclo.criar(sessao, P["marina"], DUVIDA_LOJISTA, "v7")
        ciclo.publicar(sessao, P["marina"], a.id)
    finally:
        object.__setattr__(TIPO_AGENTE, "normalizar", original)
    return a.id


def test_agente_antigo_roda_e_aparece_como_legado(api, antigo):
    h = como("marina")
    assert api.get(f"{V1}/agentes/{antigo}", headers=h).json()["legado"] is True
    exe = api.post(f"{V1}/agentes/{antigo}/executar", json={"entrada": {"lojista_id": "L1001", "pergunta": "Prazo do estorno?"}}, headers=h)
    assert exe.status_code == 200 and exe.json()["status"] == "concluida"
    assert any(x["legado"] for x in api.get(f"{V1}/agentes", headers=h).json())


def test_agente_antigo_e_so_leitura_mas_converte_em_processo(api, antigo):
    h = como("marina")
    r = api.put(f"{V1}/agentes/{antigo}", json={"blueprint": DUVIDA_LOJISTA.model_dump(), "nota": "mexi"}, headers=h)
    assert r.status_code == 422 and "Processos" in r.json()["detail"]          # nova versão de vários passos: não
    c = api.post(f"{V1}/agentes/{antigo}/converter-em-processo", json={}, headers=h)
    assert c.status_code == 200, c.text
    corpo = c.json()
    assert corpo["processo"]["estado"] in ("publicado", "em_revisao") and corpo["agentes"]
    for t in corpo["agentes"]:          # os agentes trabalhadores nascem de um passo só
        assert api.get(f"{V1}/agentes/{t['id']}", headers=h).json()["legado"] is False


# ---------- um banco da v7 abre na v8 ----------
@pytest.fixture()
def banco_v7(tmp_path):
    copia = tmp_path / "banco_v7.db"
    shutil.copy(FIXTURE_V7, copia)
    anterior = db._motor
    m = db.criar_motor("sqlite:///" + str(copia).replace("\\", "/"))
    db.usar_motor(m)
    yield m
    m.dispose()
    db.usar_motor(anterior)


def test_banco_da_v7_abre_na_v8_sem_erros_e_continua_integro(banco_v7):
    from app.main import app
    db.criar_tabelas()                                   # o que o servidor faz ao subir: tabelas novas e colunas novas
    with TestClient(app) as c:
        h = como("helena")
        agentes = c.get(f"{V1}/agentes", headers=h).json()
        assert len(agentes) == 3 and sum(a["legado"] for a in agentes) == 3       # os três da v7 são fluxos de vários passos
        assert c.get(f"{V1}/processos", headers=h).json() == []
        for tela in ("/mapa", "/financas/resumo", "/financas/indicadores", "/saude", "/alertas", "/auditoria", "/execucoes", "/rotinas"):
            assert c.get(V1 + tela, headers=h).status_code == 200, tela
        assert c.get(f"{V1}/auditoria/verificar", headers=h).json()["integra"] is True
        # as execuções gravadas na v7 continuam abrindo (dono = agente, mesmo sem a coluna nova preenchida)
        execs = c.get(f"{V1}/execucoes", headers=h).json()
        assert execs and all(e.get("dono_tipo", "agente") == "agente" for e in execs)

        # o agente antigo roda e agenda rotina; o fluxo converte em processo; a cadeia segue íntegra
        duvida = next(a for a in agentes if a["nome"] == "Resposta a dúvidas de lojistas")
        r = c.post(f"{V1}/agentes/{duvida['id']}/executar", json={"entrada": {"lojista_id": "L1001", "pergunta": "Prazo do estorno?"}},
                   headers=como("marina"))
        assert r.status_code == 200 and r.json()["status"] == "concluida"
        rot = c.post(f"{V1}/agentes/{duvida['id']}/rotinas", headers=como("marina"),
                     json={"frequencia": "diaria", "hora": 9, "minuto": 0, "entrada": {"lojista_id": "L1001", "pergunta": "Prazo do estorno?"}})
        assert rot.status_code == 200 and rot.json()["dono_tipo"] == "agente"
        conv = c.post(f"{V1}/agentes/{duvida['id']}/converter-em-processo", json={}, headers=como("marina"))
        assert conv.status_code == 200, conv.text
        assert c.get(f"{V1}/auditoria/verificar", headers=h).json()["integra"] is True
    with Session(db.motor()) as s:
        assert trilha.verificar(s)["integra"] is True
