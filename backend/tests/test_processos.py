"""v8/04: aba Processos (tracer bullet): criar -> testar -> publicar -> executar, blocos de agente em sequência e em paralelo."""
import pytest

from app.agents import ciclo
from app.agents.blueprint import Blueprint
from app.core.identidade import PERSONAS
from app.tools import dados_ficticios, executor
from tests.conftest import como

P = PERSONAS


@pytest.fixture(autouse=True)
def _limpo():
    dados_ficticios.zerar()
    executor.zerar_limites()


def trabalhador(nome="Redator de respostas", ferramentas=("buscar_politica",), instrucao="Escreva a resposta em até 5 frases."):
    """Um agente trabalhador: um único passo de IA, reutilizável em blocos de processos."""
    return Blueprint.model_validate({
        "nome": nome, "objetivo": "Redigir respostas objetivas para lojistas.", "area": "atendimento",
        "instrucoes": "Tom cordial e direto.",
        "passos": [{"id": "trabalho", "titulo": nome, "tipo": "agente", "modelo": "rapido",
                    "ferramentas": list(ferramentas), "instrucao": instrucao}]})


def agente_publicado(sessao, pessoa="marina", **kw):
    a = ciclo.criar(sessao, P[pessoa], trabalhador(**kw))
    ciclo.publicar(sessao, P[pessoa], a.id)
    return a


def fluxo(*agentes):
    """Dois blocos de dados em paralelo -> um bloco por agente, em sequência."""
    blocos = [
        {"id": "cadastro", "tipo": "dados", "titulo": "Ler o cadastro do lojista", "ferramenta": "consultar_lojista",
         "entrada": {"lojista_id": "{{entrada.lojista_id}}"}},
        {"id": "politica", "tipo": "dados", "titulo": "Buscar a política", "ferramenta": "buscar_politica",
         "entrada": {"area": "atendimento", "consulta": "{{entrada.pergunta}}"}},
    ]
    anterior = ["cadastro", "politica"]
    for i, a in enumerate(agentes, 1):
        blocos.append({"id": "agente_%d" % i, "tipo": "agente", "titulo": "Agente %d" % i, "agente_id": a.id, "depende_de": anterior})
        anterior = ["agente_%d" % i]
    return {"nome": "Resposta a lojistas", "objetivo": "Responder dúvidas de lojistas com a política vigente.", "area": "atendimento",
            "campos": [{"id": "lojista_id", "rotulo": "Lojista", "tipo": "lojista"},
                       {"id": "pergunta", "rotulo": "Dúvida", "tipo": "texto_longo"}],
            "blocos": blocos, "minutos_manual": 8, "roteiro_id": "marina"}


ENTRADA = {"lojista_id": "L1001", "pergunta": "Qual o prazo de estorno no débito?"}


# ---------- o caminho feliz ----------
def test_criar_testar_publicar_e_executar(api, sessao):
    a = agente_publicado(sessao)
    corpo = fluxo(a)
    teste = api.post("/api/v1/processos/testar", json={"blueprint": corpo, "entrada": ENTRADA}, headers=como("marina"))
    assert teste.status_code == 200, teste.text
    t = teste.json()
    assert t["status"] == "concluida" and (t["dono_tipo"], t["dono_id"]) == ("processo", "sandbox")
    assert set(t["passos"]) == {"cadastro", "politica", "agente_1"}

    novo = api.post("/api/v1/processos", json={"blueprint": corpo, "nota": "primeira versão"}, headers=como("marina"))
    assert novo.status_code == 200, novo.text
    pid = novo.json()["id"]
    assert novo.json()["estado"] == "rascunho"
    assert api.post("/api/v1/processos/%s/publicar" % pid, headers=como("marina")).json()["estado"] == "publicado"

    r = api.post("/api/v1/processos/%s/executar" % pid, json={"entrada": ENTRADA}, headers=como("marina"))
    assert r.status_code == 200, r.text
    exe = r.json()
    assert exe["status"] == "concluida" and (exe["dono_tipo"], exe["dono_id"], exe["versao"]) == ("processo", pid, 1)
    # resultado aninhado: cada bloco com o seu registro, e o bloco do agente diz QUEM rodou
    bloco = exe["passos"]["agente_1"]
    assert bloco["bloco"] == "agente" and bloco["agente"] == {"id": a.id, "nome": a.nome, "versao": 1}
    assert exe["passos"]["cadastro"]["bloco"] == "dados"
    # custo e tempo somados no processo
    assert exe["custo_usd"] > 0 and exe["custo_usd"] == pytest.approx(sum(p["custo_usd"] for p in exe["passos"].values()))
    # a execução não vira "execução de agente"
    assert exe["agente_id"] is None
    assert api.get("/api/v1/processos/%s/execucoes" % pid, headers=como("marina")).json()[0]["id"] == exe["id"]


def test_lista_e_detalhe_mostram_dono_area_estado_versao_as_is_e_numeros(api, sessao):
    a = agente_publicado(sessao)
    pid = api.post("/api/v1/processos", json={"blueprint": fluxo(a)}, headers=como("marina")).json()["id"]
    api.post("/api/v1/processos/%s/publicar" % pid, headers=como("marina"))
    api.post("/api/v1/processos/%s/executar" % pid, json={"entrada": ENTRADA}, headers=como("marina"))
    item = next(x for x in api.get("/api/v1/processos", headers=como("marina")).json() if x["id"] == pid)
    assert (item["dono"], item["area"], item["estado"], item["versao_publicada"]) == ("marina", "atendimento", "publicado", 1)
    assert item["as_is"]["processo"] == "Resposta a dúvidas de lojistas" and item["execucoes"] == 1 and item["custo_brl"] > 0
    assert item["agentes"] == [a.id]
    d = api.get("/api/v1/processos/%s" % pid, headers=como("marina")).json()
    assert d["pode_editar"] and d["pode_executar"] and len(d["versoes"]) == 1
    assert {e["tipo"] for e in d["historico"]} >= {"processo_criado", "processo_publicado"}
    assert all(e["dono_tipo"] == "processo" for e in d["historico"])


def test_blocos_sem_dependencia_rodam_em_paralelo(api, sessao):
    a1, a2 = agente_publicado(sessao, nome="Redator A"), agente_publicado(sessao, nome="Redator B")
    corpo = fluxo()
    corpo["blocos"] = [
        {"id": "a", "tipo": "agente", "titulo": "Agente A", "agente_id": a1.id},
        {"id": "b", "tipo": "agente", "titulo": "Agente B", "agente_id": a2.id},
        {"id": "fim", "tipo": "aprovacao", "titulo": "Conferir", "depende_de": ["a", "b"]},
    ]
    corpo["campos"] = []
    v = api.post("/api/v1/processos/validar", json={"blueprint": corpo}, headers=como("marina")).json()
    assert v["valido"] and v["niveis"] == [["a", "b"], ["fim"]]
    t = api.post("/api/v1/processos/testar", json={"blueprint": corpo, "entrada": {}}, headers=como("marina")).json()
    # os dois agentes concluem; a aprovação humana pausa o fluxo no fim
    assert t["passos"]["a"]["status"] == t["passos"]["b"]["status"] == "concluido" and t["status"] == "aguardando_aprovacao"
    # o tempo estimado conta a camada paralela uma vez só (o mais lento), não a soma
    lentos = [t["passos"][x]["duracao_estimada_ms"] for x in ("a", "b")]
    assert t["duracao_estimada_ms"] < sum(lentos) or max(lentos) == 0


def test_dois_agentes_em_sequencia(api, sessao):
    a1, a2 = agente_publicado(sessao, nome="Redator A"), agente_publicado(sessao, nome="Revisor B")
    t = api.post("/api/v1/processos/testar", json={"blueprint": fluxo(a1, a2), "entrada": ENTRADA}, headers=como("marina")).json()
    assert t["status"] == "concluida" and t["passos"]["agente_2"]["agente"]["nome"] == "Revisor B"


def test_testar_rascunho_com_agente_ainda_nao_publicado_mas_nao_publica_o_processo(api, sessao):
    rascunho = ciclo.criar(sessao, P["marina"], trabalhador(nome="Rascunho"))
    corpo = fluxo(rascunho)
    t = api.post("/api/v1/processos/testar", json={"blueprint": corpo, "entrada": ENTRADA}, headers=como("marina"))
    assert t.status_code == 200 and t.json()["status"] == "concluida"
    pid = api.post("/api/v1/processos", json={"blueprint": corpo}, headers=como("marina")).json()["id"]
    r = api.post("/api/v1/processos/%s/publicar" % pid, headers=como("marina"))
    assert r.status_code == 422 and "Publique o agente" in r.json()["detail"]


# ---------- grafo inválido: mensagem em português ----------
def test_ciclo_e_referencia_solta_sao_recusados_em_portugues(api, sessao):
    a = agente_publicado(sessao)
    ciclico = fluxo(a)
    ciclico["blocos"][0]["depende_de"] = ["agente_1"]
    r = api.post("/api/v1/processos", json={"blueprint": ciclico}, headers=como("marina"))
    assert r.status_code == 422 and "formam um ciclo" in r.json()["detail"] and "Value error" not in r.json()["detail"]
    solto = fluxo(a)
    solto["blocos"][2]["depende_de"] = ["nao_existe"]
    r = api.post("/api/v1/processos", json={"blueprint": solto}, headers=como("marina"))
    assert r.status_code == 422 and "não existe" in r.json()["detail"]
    v = api.post("/api/v1/processos/validar", json={"blueprint": ciclico}, headers=como("marina")).json()
    assert v["valido"] is False and "ciclo" in v["erros"][0]


def test_agente_inexistente_de_outra_area_ou_de_varios_passos(api, sessao):
    corpo = fluxo()
    corpo["blocos"] = [{"id": "x", "tipo": "agente", "titulo": "Agente", "agente_id": "fantasma-0000"}]
    assert "não existe" in api.post("/api/v1/processos", json={"blueprint": corpo}, headers=como("marina")).json()["detail"]
    risco = ciclo.criar(sessao, P["rafael"], Blueprint.model_validate({
        **trabalhador(nome="Do risco", ferramentas=()).model_dump(), "area": "risco"}))
    corpo["blocos"][0]["agente_id"] = risco.id
    r = api.post("/api/v1/processos", json={"blueprint": corpo}, headers=como("marina"))
    assert r.status_code == 422 and "não tem acesso ao agente" in r.json()["detail"]
    from app.seed.agentes_exemplo import DUVIDA_LOJISTA
    legado = ciclo.criar(sessao, P["marina"], DUVIDA_LOJISTA)
    corpo["blocos"][0]["agente_id"] = legado.id
    r = api.post("/api/v1/processos", json={"blueprint": corpo}, headers=como("marina"))
    assert r.status_code == 422 and "vários passos" in r.json()["detail"]
    lista = api.get("/api/v1/processos/agentes-disponiveis", headers=como("marina")).json()
    assert next(x for x in lista if x["id"] == legado.id)["trabalhador"] is False


# ---------- permissões ----------
def test_so_criadores_da_area_editam_e_a_api_confere(api, sessao):
    a = agente_publicado(sessao)
    corpo = fluxo(a)
    assert api.post("/api/v1/processos", json={"blueprint": corpo}, headers=como("helena")).status_code == 403
    assert api.post("/api/v1/processos", json={"blueprint": corpo}, headers=como("lucas")).status_code == 403
    pid = api.post("/api/v1/processos", json={"blueprint": corpo}, headers=como("marina")).json()["id"]
    assert api.put("/api/v1/processos/%s" % pid, json={"blueprint": corpo}, headers=como("rafael")).status_code == 403
    assert api.post("/api/v1/processos/%s/publicar" % pid, headers=como("rafael")).status_code == 403
    assert api.post("/api/v1/processos/testar", json={"blueprint": corpo, "entrada": ENTRADA}, headers=como("helena")).status_code == 403


def test_todos_veem_a_aba_mas_so_os_processos_que_podem(api, sessao):
    a = agente_publicado(sessao)
    pid = api.post("/api/v1/processos", json={"blueprint": fluxo(a)}, headers=como("marina")).json()["id"]
    for quem in ("marina", "rafael", "carla", "thiago", "lucas", "helena"):
        assert "processos" in api.get("/api/v1/eu", headers=como(quem)).json()["abas"]
    ids = lambda quem: {x["id"] for x in api.get("/api/v1/processos", headers=como(quem)).json()}   # noqa: E731
    assert pid in ids("marina") and pid in ids("helena") and pid in ids("lucas")
    assert pid not in ids("carla")
    assert api.get("/api/v1/processos/%s" % pid, headers=como("carla")).status_code == 403


def test_executar_exige_publicado_e_area_com_acesso(api, sessao):
    a = agente_publicado(sessao)
    pid = api.post("/api/v1/processos", json={"blueprint": fluxo(a)}, headers=como("marina")).json()["id"]
    r = api.post("/api/v1/processos/%s/executar" % pid, json={"entrada": ENTRADA}, headers=como("marina"))
    assert r.status_code == 409 and "ainda não foi publicado" in r.json()["detail"]
    api.post("/api/v1/processos/%s/publicar" % pid, headers=como("marina"))
    assert api.post("/api/v1/processos/%s/executar" % pid, json={"entrada": ENTRADA}, headers=como("thiago")).status_code == 403
    faltando = api.post("/api/v1/processos/%s/executar" % pid, json={"entrada": {}}, headers=como("marina"))
    assert faltando.status_code == 422 and "Preencha" in faltando.json()["detail"]


# ---------- ciclo de vida compartilhado com os agentes ----------
def test_pausa_de_emergencia_e_deprecacao_do_processo(api, sessao):
    a = agente_publicado(sessao)
    pid = api.post("/api/v1/processos", json={"blueprint": fluxo(a)}, headers=como("marina")).json()["id"]
    api.post("/api/v1/processos/%s/publicar" % pid, headers=como("marina"))
    assert api.post("/api/v1/processos/%s/pausar" % pid, json={"motivo": "incidente"}, headers=como("lucas")).json()["estado"] == "pausado"
    r = api.post("/api/v1/processos/%s/executar" % pid, json={"entrada": ENTRADA}, headers=como("marina"))
    assert r.status_code == 409 and "pausado: incidente" in r.json()["detail"]
    assert api.post("/api/v1/processos/%s/retomar" % pid, headers=como("lucas")).json()["estado"] == "publicado"
    assert api.post("/api/v1/processos/%s/depreciar" % pid, json={"motivo": "substituído"}, headers=como("marina")).json()["estado"] == "depreciado"


def test_risco_alto_passa_pela_revisao_de_seguranca_com_quatro_olhos(api, sessao):
    risco = ciclo.criar(sessao, P["rafael"], Blueprint.model_validate({
        "nome": "Reter repasses", "objetivo": "Propor a retenção de repasses.", "area": "risco",
        "passos": [{"id": "t", "titulo": "Propor retenção", "tipo": "agente", "ferramentas": ["bloquear_repasse"],
                    "instrucao": "Proponha a retenção do repasse."}]}))
    ciclo.publicar(sessao, P["rafael"], risco.id)
    ciclo.revisar(sessao, P["lucas"], risco.id, True, "Confirmação humana obrigatória. Aprovado.")
    corpo = {"nome": "Triagem com retenção", "objetivo": "Tratar contestações e propor retenção.", "area": "risco",
             "campos": [], "blocos": [{"id": "r", "tipo": "agente", "titulo": "Reter", "agente_id": risco.id}]}
    pid = api.post("/api/v1/processos", json={"blueprint": corpo}, headers=como("rafael")).json()["id"]
    assert api.post("/api/v1/processos/%s/publicar" % pid, headers=como("rafael")).json()["estado"] == "em_revisao"
    fila = api.get("/api/v1/revisoes", headers=como("lucas")).json()
    assert any(i["tipo"] == "processo" and i["agente"]["id"] == pid for i in fila)
    assert api.post("/api/v1/processos/%s/revisao" % pid, json={"aprovar": True, "parecer": "ok"}, headers=como("rafael")).status_code == 403
    ok = api.post("/api/v1/processos/%s/revisao" % pid, json={"aprovar": True, "parecer": "Confirmação humana mantida."}, headers=como("lucas"))
    assert ok.status_code == 200 and ok.json()["estado"] == "publicado"


def test_nova_versao_gera_diff_em_linguagem_de_quem_revisa(api, sessao):
    a = agente_publicado(sessao)
    corpo = fluxo(a)
    pid = api.post("/api/v1/processos", json={"blueprint": corpo}, headers=como("marina")).json()["id"]
    api.post("/api/v1/processos/%s/publicar" % pid, headers=como("marina"))
    novo = fluxo(a)
    novo["blocos"][1]["titulo"] = "Consultar a política de atendimento"
    novo["blocos"].append({"id": "aprova", "tipo": "aprovacao", "titulo": "Conferir", "depende_de": ["agente_1"]})
    assert api.put("/api/v1/processos/%s" % pid, json={"blueprint": novo, "nota": "mais uma conferência"}, headers=como("marina")).json()["numero"] == 2
    d = api.get("/api/v1/processos/%s/diff?de=1&para=2" % pid, headers=como("marina")).json()
    assert {(m["tipo"], m["alvo"]) for m in d} >= {("adicionado", "bloco:aprova"), ("alterado", "bloco:politica")}


# ---------- agente pausado dentro do processo ----------
def test_agente_pausado_dentro_do_processo_escala_com_o_motivo(api, sessao):
    a = agente_publicado(sessao)
    pid = api.post("/api/v1/processos", json={"blueprint": fluxo(a)}, headers=como("marina")).json()["id"]
    api.post("/api/v1/processos/%s/publicar" % pid, headers=como("marina"))
    ciclo.pausar(sessao, P["lucas"], a.id, "revisão de política")
    exe = api.post("/api/v1/processos/%s/executar" % pid, json={"entrada": ENTRADA}, headers=como("marina")).json()
    assert exe["status"] == "escalada"
    assert "pausado: revisão de política" in exe["motivo"] and exe["passos"]["agente_1"]["status"] == "escalado"
    assert exe["passos"]["cadastro"]["status"] == "concluido"            # o que não dependia do agente já tinha rodado
    assert exe["custo_usd"] == 0                                         # nenhum modelo foi chamado
