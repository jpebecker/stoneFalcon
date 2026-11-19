"""v8/06: agentes são trabalhadores (um passo de IA); fluxo de vários passos vira processo; "usado em processos"."""
import pytest

from app.agents import ciclo
from app.agents import modelos as am
from app.agents.blueprint import Blueprint
from app.core.identidade import PERSONAS
from app.processos.compilar import compilar, trabalhador
from app.processos.blueprint import ProcessoBlueprint
from app.seed.agentes_exemplo import DUVIDA_LOJISTA, TRIAGEM_CHARGEBACK
from app.tools import dados_ficticios, executor
from tests.conftest import como
from tests.test_processos import ENTRADA, agente_publicado, fluxo, trabalhador as bp_trabalhador

P = PERSONAS
V1 = "/api/v1"


@pytest.fixture(autouse=True)
def _limpo():
    dados_ficticios.zerar()
    executor.zerar_limites()


# ---------- criar, testar e publicar um trabalhador ----------
def test_trabalhador_criar_testar_publicar(api):
    bp = bp_trabalhador(ferramentas=("buscar_politica", "consultar_lojista")).model_dump()
    bp["campos"] = [{"id": "pergunta", "rotulo": "Pergunta", "tipo": "texto_longo", "exemplo": "", "ajuda": "", "opcoes": []}]
    t = api.post(f"{V1}/estudio/testar", json={"blueprint": bp, "entrada": {"pergunta": "Qual o prazo de estorno?"}}, headers=como("marina"))
    assert t.status_code == 200 and t.json()["status"] == "concluida"
    a = api.post(f"{V1}/agentes", json={"blueprint": bp}, headers=como("marina")).json()
    assert api.post(f"{V1}/agentes/{a['id']}/publicar", headers=como("marina")).json()["estado"] == "publicado"
    item = next(x for x in api.get(f"{V1}/agentes", headers=como("marina")).json() if x["id"] == a["id"])
    assert item["legado"] is False and item["processos"] == 0


def test_sugestao_traz_o_trabalhador_unico_e_se_o_fluxo_tem_varios_passos(api):
    s = api.post(f"{V1}/estudio/sugerir", headers=como("marina"), json={
        "descricao": "Quando um lojista pergunta algo no chamado, eu abro o cadastro dele, procuro a regra na política de "
                     "atendimento e escrevo a resposta com o tom certo. Levo uns 8 minutos por chamado."}).json()
    t = Blueprint.model_validate(s["trabalhador"])
    assert len(t.passos) == 1 and t.passos[0].tipo == "agente" and trabalhador(t) is not None
    assert {"consultar_lojista", "buscar_politica"} <= set(t.passos[0].ferramentas)   # as consultas do fluxo viram ferramentas dele
    assert t.campos == Blueprint.model_validate(s["blueprint"]).campos and t.minutos_manual == 8
    assert s["multipasso"] is True and len(s["blueprint"]["passos"]) > 2


def test_transformar_em_processo_cria_trabalhadores_rascunho_e_devolve_o_fluxo_de_blocos(api, sessao):
    fluxo_sugerido = DUVIDA_LOJISTA.model_dump()
    r = api.post(f"{V1}/estudio/em-processo", json={"blueprint": fluxo_sugerido}, headers=como("marina"))
    assert r.status_code == 200, r.text
    corpo = r.json()
    assert len(corpo["agentes"]) == 1                                            # um passo de IA = um trabalhador novo
    novo = ciclo.obter(sessao, corpo["agentes"][0]["id"])
    assert novo.estado == am.RASCUNHO and novo.dono == "marina"
    pbp = ProcessoBlueprint.model_validate(corpo["processo"])
    assert [b.tipo for b in pbp.blocos] == ["dados", "dados", "agente"] and pbp.roteiro_id == "marina"
    # o rascunho já abre no editor: valida e testa no sandbox (agente em rascunho serve para testar)
    assert api.post(f"{V1}/processos/validar", json={"blueprint": corpo["processo"]}, headers=como("marina")).json()["valido"] is True
    t = api.post(f"{V1}/processos/testar", json={"blueprint": corpo["processo"], "entrada": ENTRADA}, headers=como("marina")).json()
    assert t["status"] == "concluida"


def test_so_criador_transforma_em_processo(api):
    assert api.post(f"{V1}/estudio/em-processo", json={"blueprint": DUVIDA_LOJISTA.model_dump()}, headers=como("helena")).status_code == 403


# ---------- "usado em processos" ----------
def test_agente_mostra_em_quais_processos_trabalha_e_de_quem(api, sessao):
    a = agente_publicado(sessao)
    pid = api.post(f"{V1}/processos", json={"blueprint": fluxo(a)}, headers=como("marina")).json()["id"]
    d = api.get(f"{V1}/agentes/{a.id}", headers=como("marina")).json()
    assert d["usado_em"] == [{"id": pid, "nome": "Resposta a lojistas", "dono": "marina", "area": "atendimento", "estado": "rascunho",
                              "as_is": {"roteiro_id": "marina", "processo": "Resposta a dúvidas de lojistas", "persona": "marina"}}]
    lista = next(x for x in api.get(f"{V1}/agentes", headers=como("marina")).json() if x["id"] == a.id)
    assert lista["processos"] == 1


def test_pausar_trabalhador_avisa_os_processos_e_o_processo_mostra_o_alerta(api, sessao):
    a = agente_publicado(sessao)
    pid = api.post(f"{V1}/processos", json={"blueprint": fluxo(a)}, headers=como("marina")).json()["id"]
    api.post(f"{V1}/processos/{pid}/publicar", headers=como("marina"))
    r = api.post(f"{V1}/agentes/{a.id}/pausar", json={"motivo": "revisão de política"}, headers=como("lucas")).json()
    assert [p["id"] for p in r["processos_afetados"]] == [pid]
    p = api.get(f"{V1}/processos/{pid}", headers=como("marina")).json()
    assert p["alertas_agentes"] == [{"id": a.id, "nome": a.nome, "estado": "pausado", "motivo": "revisão de política"}]
    api.post(f"{V1}/agentes/{a.id}/retomar", headers=como("lucas"))
    assert api.get(f"{V1}/processos/{pid}", headers=como("marina")).json()["alertas_agentes"] == []
    dep = api.post(f"{V1}/agentes/{a.id}/depreciar", json={"motivo": "substituído"}, headers=como("marina")).json()
    assert [p["id"] for p in dep["processos_afetados"]] == [pid]
    assert api.get(f"{V1}/processos/{pid}", headers=como("marina")).json()["alertas_agentes"][0]["estado"] == "depreciado"


# ---------- agente antigo de vários passos: conversão ----------
def _equivalentes(s, legado: Blueprint, processo_id: str, pessoa) -> None:
    """Mesmas ferramentas, mesma ordem e paralelismo, mesmas aprovações."""
    from app.processos.tipo import ciclo as cp
    p = cp.obter(s, processo_id)
    novo = compilar(s, ProcessoBlueprint.model_validate(cp.versao(s, p.id, p.ultima_versao).blueprint), pessoa, "ultima")
    assert novo.niveis() == legado.niveis()                                                    # ordem e paralelismo
    assert {x.id: x.depende_de for x in novo.passos} == {x.id: x.depende_de for x in legado.passos}
    assert {x.id: x.tipo for x in novo.passos} == {x.id: x.tipo for x in legado.passos}        # aprovações e passos de IA no mesmo lugar
    for velho in legado.passos:
        n = novo.passo(velho.id)
        assert (n.ferramenta, n.entrada) == (velho.ferramenta, velho.entrada)
        assert set(n.ferramentas) == set(velho.ferramentas) and n.modelo == velho.modelo and n.instrucao == velho.instrucao
    assert novo.ferramentas_usadas() == legado.ferramentas_usadas()


def test_agente_antigo_aparece_como_legado_e_converte_em_processo_equivalente(api, sessao):
    a = ciclo.criar(sessao, P["marina"], DUVIDA_LOJISTA)
    ciclo.publicar(sessao, P["marina"], a.id)
    item = next(x for x in api.get(f"{V1}/agentes", headers=como("marina")).json() if x["id"] == a.id)
    assert item["legado"] is True
    r = api.post(f"{V1}/agentes/{a.id}/converter-em-processo", headers=como("marina"))
    assert r.status_code == 200, r.text
    corpo = r.json()
    assert corpo["processo"]["estado"] == "publicado" and corpo["processo"]["roteiro_id"] == "marina"   # risco baixo: já no ar
    assert [t["estado"] for t in corpo["agentes"]] == ["publicado"] and corpo["agentes"][0]["nome"].startswith(DUVIDA_LOJISTA.nome)
    _equivalentes(sessao, DUVIDA_LOJISTA.model_copy(update={"area": "atendimento"}), corpo["processo"]["id"], P["marina"])
    assert ciclo.obter(sessao, a.id).estado == am.PUBLICADO                                              # o antigo fica até a v8/09
    exe = api.post(f"{V1}/processos/{corpo['processo']['id']}/executar", json={"entrada": ENTRADA}, headers=como("marina")).json()
    assert exe["status"] == "concluida" and exe["passos"]["resposta"]["agente"]["id"] == corpo["agentes"][0]["id"]
    assert next(x for x in api.get(f"{V1}/agentes", headers=como("marina")).json() if x["id"] == corpo["agentes"][0]["id"])["processos"] == 1


def test_conversao_de_agente_de_risco_alto_mantem_a_aprovacao_e_a_revisao(api, sessao):
    a = ciclo.criar(sessao, P["rafael"], TRIAGEM_CHARGEBACK)
    ciclo.publicar(sessao, P["rafael"], a.id)
    ciclo.revisar(sessao, P["lucas"], a.id, True, "Confirmação humana obrigatória. Aprovado.")
    r = api.post(f"{V1}/agentes/{a.id}/converter-em-processo", headers=como("rafael"))
    assert r.status_code == 200, r.text
    corpo = r.json()
    assert len(corpo["agentes"]) == 2                                              # análise e ação: dois trabalhadores
    assert {t["nome"].split(" — ")[1] for t in corpo["agentes"]} == {"Avaliar o risco do caso", "Encaminhar o caso"}
    assert sorted(t["estado"] for t in corpo["agentes"]) == ["em_revisao", "publicado"]   # a ação (retenção de repasse) espera a Segurança
    assert corpo["processo"]["estado"] == "rascunho"                                  # sem todos os agentes no ar, o processo espera
    _equivalentes(sessao, TRIAGEM_CHARGEBACK, corpo["processo"]["id"], P["rafael"])
    # a Segurança aprova o trabalhador e o criador publica o processo (que também passa pela revisão: risco alto)
    acao = next(t for t in corpo["agentes"] if t["estado"] == "em_revisao")
    assert api.post(f"{V1}/agentes/{acao['id']}/revisao", json={"aprovar": True, "parecer": "ok"}, headers=como("lucas")).status_code == 200
    assert api.post(f"{V1}/processos/{corpo['processo']['id']}/publicar", headers=como("rafael")).json()["estado"] == "em_revisao"


def test_conversao_exige_criador_da_area_e_so_vale_para_agente_de_varios_passos(api, sessao):
    a = ciclo.criar(sessao, P["marina"], DUVIDA_LOJISTA)
    assert api.post(f"{V1}/agentes/{a.id}/converter-em-processo", headers=como("helena")).status_code == 403
    assert api.post(f"{V1}/agentes/{a.id}/converter-em-processo", headers=como("rafael")).status_code == 403
    t = agente_publicado(sessao)
    r = api.post(f"{V1}/agentes/{t.id}/converter-em-processo", headers=como("marina"))
    assert r.status_code == 409 and "já é um trabalhador" in r.json()["detail"]
