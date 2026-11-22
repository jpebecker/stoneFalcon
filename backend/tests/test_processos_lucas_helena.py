"""v8.1/03 e 04: Lucas (Engenharia) e Helena (CoE de IA) também têm um processo próprio no estado inicial."""
import pytest
from sqlmodel import select

from app.agents import modelos as am
from app.audit import trilha
from app.audit.trilha import EventoAuditoria
from app.processos import modelos as pm
from app.roteiros.reinicio import reiniciar
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


def _processo(api, perfil, nome):
    return next(p for p in api.get(f"{V1}/processos", headers=como(perfil)).json() if p["nome"] == nome)


def _executar(api, perfil, nome, entrada):
    p = _processo(api, perfil, nome)
    return api.post(f"{V1}/processos/{p['id']}/executar", json={"entrada": entrada}, headers=como(perfil))


def test_os_dois_processos_nascem_publicados_com_dono_e_auditoria_integra(sessao, demo):
    for nome, dono, trabalhador in (("Triagem de incidente de sistema", "lucas", "Analista de incidentes"),
                                    ("Revisão mensal do custo de IA", "helena", "Analista de custo de IA")):
        p = sessao.exec(select(pm.Processo).where(pm.Processo.nome == nome)).one()
        assert p.estado == am.PUBLICADO and p.dono == dono
        a = sessao.exec(select(am.Agente).where(am.Agente.nome == trabalhador)).one()
        assert a.estado == am.PUBLICADO and a.dono == dono
        assert trilha.listar(sessao, agente_id=p.id, limite=50)      # passou pelo ciclo de vida real (há trilha)
    assert trilha.verificar(sessao)["integra"] is True


def test_lucas_roda_o_processo_e_so_abre_chamado_quando_o_sistema_esta_fora(api, sessao, demo):
    nome = "Triagem de incidente de sistema"
    ok = _executar(api, "lucas", nome, {"sistema": "Cadastro de lojistas"})
    assert ok.status_code == 200
    ok = ok.json()
    assert ok["status"] == "concluida" and not dados_ficticios.CHAMADOS
    assert "Nenhum incidente em curso" in ok["passos"]["analise"]["saida"]
    assert "1 incidente(s) anterior(es)" in ok["passos"]["analise"]["saida"]      # cita o número do registro
    assert ok["passos"]["chamado"]["status"] == "pulado"                          # a condição seguiu o ramo "não"

    executor.definir_falha(sessao, "consultar_lojista", "fora_do_ar", "lucas")
    fora = _executar(api, "lucas", nome, {"sistema": "Cadastro de lojistas"}).json()
    assert fora["status"] == "concluida" and "Incidente CRÍTICO" in fora["passos"]["analise"]["saida"]
    assert dados_ficticios.CHAMADOS[-1]["fila"] == "engenharia" and dados_ficticios.CHAMADOS[-1]["prioridade"] == "alta"


def test_helena_roda_a_revisao_de_custo_e_o_resultado_cita_os_numeros(api, demo):
    nome = "Revisão mensal do custo de IA"
    dentro = _executar(api, "helena", nome, {"orcamento_brl": "100"}).json()
    texto = dentro["passos"]["analise"]["saida"]
    assert dentro["status"] == "concluida" and "DENTRO DO ORÇAMENTO" in texto
    assert "R$ 60,30" in texto and "629 execuções" in texto                      # soma do resumo de Finanças
    acima = _executar(api, "helena", nome, {"orcamento_brl": "50"}).json()
    assert "ACIMA DO ORÇAMENTO" in acima["passos"]["analise"]["saida"]
    assert any(n["destino"] == "#coe-ia" for n in dados_ficticios.NOTIFICACOES)   # o aviso só sai quando passou do orçamento


def test_quem_nao_tem_a_area_e_barrado_e_auditado(api, sessao, demo):
    p = _processo(api, "lucas", "Triagem de incidente de sistema")
    r = api.post(f"{V1}/processos/{p['id']}/executar", json={"entrada": {"sistema": "Cadastro de lojistas"}}, headers=como("marina"))
    assert r.status_code == 403
    negadas = [e for e in sessao.exec(select(EventoAuditoria).where(EventoAuditoria.tipo == "execucao_negada")).all() if e.agente_id == p["id"]]
    assert negadas and negadas[-1].ator == "marina"
    # o nível também conta: o trabalhador de custo lê dado da gestão e a Marina não tem a área
    p2 = _processo(api, "helena", "Revisão mensal do custo de IA")
    assert api.post(f"{V1}/processos/{p2['id']}/executar", json={"entrada": {"orcamento_brl": "100"}}, headers=como("rafael")).status_code == 403


def test_aparecem_no_mapa_em_financas_e_com_historico_de_30_dias(api, sessao, demo):
    mapa = api.get(f"{V1}/mapa", headers=como("helena")).json()
    nomes = {n["rotulo"] for n in mapa["nos"] if n["tipo"] == "processo"}
    assert {"Triagem de incidente de sistema", "Revisão mensal do custo de IA"} <= nomes
    fin = api.get(f"{V1}/financas/resumo", headers=como("helena")).json()
    por = {x["nome"]: x for x in fin["por_agente"]}
    for nome in ("Triagem de incidente de sistema", "Revisão mensal do custo de IA"):
        assert por[nome]["tipo"] == "processo" and por[nome]["execucoes"] > 0 and por[nome]["orcamento_mensal_brl"] > 0
    from app.runtime import modelos as rm
    for nome in ("Triagem de incidente de sistema", "Revisão mensal do custo de IA"):
        pid = sessao.exec(select(pm.Processo).where(pm.Processo.nome == nome)).one().id
        feitas = [e for e in sessao.exec(select(rm.Execucao).where(rm.Execucao.dono_id == pid)).all() if e.demo]
        assert len({e.inicio[:10] for e in feitas}) >= 15                          # histórico sintético espalhado em ~30 dias


def test_reiniciar_a_demo_recria_os_dois(api, sessao, demo):
    reiniciar(sessao)
    from sqlmodel import Session
    from app.core import db
    with Session(db.motor()) as s:
        nomes = {p.nome for p in s.exec(select(pm.Processo)).all()}
    assert {"Triagem de incidente de sistema", "Revisão mensal do custo de IA"} <= nomes
