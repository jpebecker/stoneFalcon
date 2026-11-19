"""v8/05: paleta de blocos de baixo código: dados, agente, ação de plugin, aprovação, condição e aviso/resposta final."""
import pytest

from app.core.identidade import PERSONAS
from app.runtime import regras
from app.tools import dados_ficticios, executor
from tests.conftest import como
from tests.test_processos import agente_publicado, fluxo  # noqa: F401  (ajudantes da v8/04)

P = PERSONAS


@pytest.fixture(autouse=True)
def _limpo():
    dados_ficticios.zerar()
    executor.zerar_limites()


def processo(marina_api, corpo):
    r = marina_api.post("/api/v1/processos", json={"blueprint": corpo}, headers=como("marina"))
    assert r.status_code == 200, r.text
    pid = r.json()["id"]
    p = marina_api.post("/api/v1/processos/%s/publicar" % pid, headers=como("marina"))
    assert p.status_code == 200, p.text
    return pid


def base(blocos, campos=None):
    return {"nome": "Fluxo de teste", "objetivo": "Testar os blocos da paleta.", "area": "atendimento", "minutos_manual": 5,
            "campos": campos if campos is not None else [{"id": "lojista_id", "rotulo": "Lojista", "tipo": "lojista"}],
            "blocos": blocos}


CADASTRO = {"id": "cadastro", "tipo": "dados", "titulo": "Ler o cadastro", "ferramenta": "consultar_lojista",
            "entrada": {"lojista_id": "{{entrada.lojista_id}}"}}


def rodar(api, pid, lojista="L1001"):
    r = api.post("/api/v1/processos/%s/executar" % pid, json={"entrada": {"lojista_id": lojista}}, headers=como("marina"))
    assert r.status_code == 200, r.text
    return r.json()


# ---------- cada tipo de bloco ----------
def test_bloco_de_dados_alimenta_a_resposta_final_por_referencia(api):
    corpo = base([CADASTRO, {"id": "fim", "tipo": "saida", "titulo": "Resposta", "depende_de": ["cadastro"],
                             "texto": "Plano do lojista: {{passos.cadastro.saida.plano}}"}])
    exe = rodar(api, processo(api, corpo))
    assert exe["status"] == "concluida" and exe["resultado"] == "Plano do lojista: Essencial"
    assert exe["passos"]["cadastro"]["bloco"] == "dados" and exe["passos"]["fim"]["bloco"] == "saida"


def test_bloco_de_acao_do_plugin_escreve_num_sistema(api):
    corpo = base([CADASTRO, {"id": "chamado", "tipo": "plugin", "titulo": "Abrir chamado", "ferramenta": "abrir_chamado",
                             "depende_de": ["cadastro"], "entrada": {"fila": "logistica", "titulo": "Troca de maquininha",
                                                                      "descricao": "Plano {{passos.cadastro.saida.plano}}"}}])
    exe = rodar(api, processo(api, corpo))
    assert exe["status"] == "concluida" and exe["passos"]["chamado"]["bloco"] == "plugin"
    assert dados_ficticios.CHAMADOS and dados_ficticios.CHAMADOS[-1]["descricao"] == "Plano Essencial"


def test_aviso_por_ferramenta_e_aprovacao_humana(api):
    corpo = base([CADASTRO, {"id": "ok", "tipo": "aprovacao", "titulo": "Conferir o cadastro", "depende_de": ["cadastro"]},
                  {"id": "aviso", "tipo": "saida", "titulo": "Avisar o time", "depende_de": ["ok"], "ferramenta": "enviar_notificacao",
                   "entrada": {"canal": "slack", "destino": "#time-atendimento", "mensagem": "Cadastro de {{passos.cadastro.saida.nome}} conferido."}}])
    pid = processo(api, corpo)
    exe = rodar(api, pid)
    assert exe["status"] == "aguardando_aprovacao" and exe["pendencia"]["passo"] == "ok" and not dados_ficticios.NOTIFICACOES
    dec = api.post("/api/v1/execucoes/%s/decisao" % exe["id"], json={"aprovar": True}, headers=como("marina")).json()
    assert dec["status"] == "concluida" and dados_ficticios.NOTIFICACOES[-1]["mensagem"].startswith("Cadastro de ")


def test_dois_agentes_e_um_bloco_de_dados_no_mesmo_fluxo(api, sessao):
    a = agente_publicado(sessao)
    corpo = fluxo(a)
    pid = processo(api, corpo)
    exe = api.post("/api/v1/processos/%s/executar" % pid, json={"entrada": {"lojista_id": "L1001", "pergunta": "Prazo?"}},
                   headers=como("marina")).json()
    assert exe["status"] == "concluida" and exe["passos"]["agente_1"]["bloco"] == "agente"


# ---------- condição: ramos "sim" e "não" ----------
def condicional():
    return base([
        CADASTRO,
        {"id": "plano", "tipo": "condicao", "titulo": "O plano é Pro?", "depende_de": ["cadastro"],
         "regra": {"fonte": "passos.cadastro.saida.plano", "operador": "igual", "valor": "Pro"}},
        {"id": "pro", "tipo": "saida", "titulo": "Aviso do plano Pro", "depende_de": ["plano"], "ramo": {"condicao": "plano", "valor": "sim"},
         "ferramenta": "enviar_notificacao",
         "entrada": {"canal": "slack", "destino": "#time-atendimento", "mensagem": "Lojista Pro: {{passos.cadastro.saida.nome}}"}},
        {"id": "essencial", "tipo": "saida", "titulo": "Resposta do plano Essencial", "depende_de": ["plano"],
         "ramo": {"condicao": "plano", "valor": "nao"}, "texto": "Plano Essencial: {{passos.cadastro.saida.nome}}"},
    ])


def test_condicao_roda_so_o_ramo_escolhido_e_o_outro_aparece_como_pulado(api):
    pid = processo(api, condicional())
    pro = rodar(api, pid, "L1002")              # Pro: segue o "sim"
    assert pro["status"] == "concluida" and pro["passos"]["plano"]["saida"] == {"resultado": "sim"}
    assert pro["passos"]["pro"]["status"] == "concluido" and pro["passos"]["essencial"]["status"] == "pulado"
    assert len(dados_ficticios.NOTIFICACOES) == 1
    ess = rodar(api, pid, "L1001")              # Essencial: segue o "não"; o aviso do Slack não dispara
    assert ess["passos"]["pro"]["status"] == "pulado" and ess["passos"]["essencial"]["status"] == "concluido"
    assert len(dados_ficticios.NOTIFICACOES) == 1
    assert ess["resultado"] == "Plano Essencial: Padaria Pão Dourado"   # só o ramo tomado entra no resultado


def test_bloco_depois_dos_dois_ramos_roda_se_um_deles_rodou(api):
    corpo = condicional()
    corpo["blocos"].append({"id": "fim", "tipo": "saida", "titulo": "Fechamento", "depende_de": ["pro", "essencial"], "texto": "Atendimento concluído."})
    pid = processo(api, corpo)
    assert rodar(api, pid, "L1001")["passos"]["fim"]["status"] == "concluido"


def test_regra_sem_valor_para_comparar_escala_em_vez_de_adivinhar(api):
    corpo = base([CADASTRO, {"id": "c", "tipo": "condicao", "titulo": "Verificar", "depende_de": ["cadastro"],
                             "regra": {"fonte": "passos.cadastro.saida.nao_existe", "operador": "igual", "valor": "x"}}])
    exe = rodar(api, processo(api, corpo))
    assert exe["status"] == "escalada" and "Não consegui avaliar a regra" in exe["motivo"]


@pytest.mark.parametrize("operador,valor,esperado,resultado", [
    ("igual", "Pro", "pro", True), ("igual", "Pro", "Basico", False), ("igual", 46, "46", True),
    ("contem", "Maquininha Pro de São Paulo", "são paulo", True), ("contem", {"a": "texto"}, "texto", True), ("contem", "abc", "x", False),
    ("maior", 46, "10", True), ("maior", 9, "10", False), ("maior", "1.250,50", "1000", True),
])
def test_operadores_da_regra(operador, valor, esperado, resultado):
    assert regras.avaliar(operador, valor, esperado) is resultado


def test_maior_que_com_texto_nao_numerico_e_erro_claro():
    with pytest.raises(regras.ErroRegra, match="não é um número"):
        regras.avaliar("maior", "muitos", "10")


# ---------- validação por bloco e permissões ----------
def validar(api, corpo, quem="marina"):
    return api.post("/api/v1/processos/validar", json={"blueprint": corpo}, headers=como(quem)).json()


def test_bloco_incompleto_aparece_destacado_sem_esconder_os_outros(api):
    corpo = base([CADASTRO,
                  {"id": "a", "tipo": "agente", "titulo": "Agente sem escolha", "depende_de": ["cadastro"]},
                  {"id": "d", "tipo": "dados", "titulo": "Estoque", "ferramenta": "consultar_estoque", "depende_de": ["cadastro"], "entrada": {}}])
    v = validar(api, corpo)
    assert v["valido"] is False
    assert v["blocos"]["a"] == ["Escolha o agente."]
    assert any("Falta preencher" in x for x in v["blocos"]["d"])
    assert "cadastro" not in v["blocos"]


def test_referencia_a_bloco_que_nao_vem_antes_e_apontada(api):
    corpo = base([CADASTRO, {"id": "x", "tipo": "saida", "titulo": "Resposta", "texto": "{{passos.cadastro.saida.plano}}"},
                  {"id": "y", "tipo": "saida", "titulo": "Outra", "depende_de": ["cadastro"], "texto": "{{entrada.nao_existe}}"}])
    v = validar(api, corpo)
    assert "não vem antes" in v["blocos"]["x"][0] and "não existe" in v["blocos"]["y"][0]


def test_ferramenta_que_o_criador_nao_pode_usar_mostra_o_motivo(api):
    corpo = base([{"id": "t", "tipo": "dados", "titulo": "Transações", "ferramenta": "listar_transacoes",
                   "entrada": {"lojista_id": "{{entrada.lojista_id}}"}}])
    v = validar(api, corpo)
    assert v["valido"] is True and "listar_transacoes" in v["sem_permissao"]
    assert any("não está autorizada" in x or "nível de acesso" in x for x in v["blocos"]["t"])
    assert validar(api, corpo, "rafael")["blocos"] == {}                      # quem pode usar não vê problema
    cat = {f["id"]: f for f in api.get("/api/v1/ferramentas", headers=como("marina")).json()["ferramentas"]}
    assert cat["listar_transacoes"]["disponivel_para_mim"] is False and cat["listar_transacoes"]["motivo"]
    assert cat["consultar_lojista"]["campos_saida"]["plano"] == "Plano"


def test_bloco_de_dados_so_aceita_ferramenta_de_leitura(api):
    corpo = base([{"id": "d", "tipo": "dados", "titulo": "Abrir", "ferramenta": "abrir_chamado",
                   "entrada": {"fila": "ti", "titulo": "x", "descricao": "y"}}])
    v = validar(api, corpo)
    assert v["valido"] is False and "só lê" in v["erros"][0] and "só lê" in v["blocos"]["d"][0]


def test_nao_publica_enquanto_algum_bloco_estiver_incompleto(api):
    corpo = base([CADASTRO, {"id": "d", "tipo": "dados", "titulo": "Estoque", "ferramenta": "consultar_estoque", "depende_de": ["cadastro"], "entrada": {}}])
    pid = api.post("/api/v1/processos", json={"blueprint": corpo}, headers=como("marina")).json()["id"]     # rascunho salva
    r = api.post("/api/v1/processos/%s/publicar" % pid, headers=como("marina"))
    assert r.status_code == 422 and "não está pronto" in r.json()["detail"] and "Falta preencher" in r.json()["detail"]


def test_risco_e_estimativa_acompanham_os_blocos(api, sessao):
    a = agente_publicado(sessao)
    leve = base([CADASTRO])
    v1 = validar(api, leve)
    assert v1["risco"]["nivel"] == "baixo" and v1["estimativa"]["custo_por_execucao_brl"] == 0
    com_agente = base([CADASTRO, {"id": "a", "tipo": "agente", "titulo": "Redator", "agente_id": a.id, "depende_de": ["cadastro"]},
                       {"id": "chamado", "tipo": "plugin", "titulo": "Abrir chamado", "ferramenta": "abrir_chamado", "depende_de": ["a"],
                        "entrada": {"fila": "ti", "titulo": "x", "descricao": "{{passos.a.saida}}"}}])
    v2 = validar(api, com_agente)
    assert v2["risco"]["nivel"] == "medio" and v2["estimativa"]["custo_por_execucao_brl"] > 0 and v2["estimativa"]["duracao_ms"] > 0
    assert v2["estimativa"]["chamadas_modelo"] >= 1


def test_condicao_pede_regra_e_tipos_invalidos_sao_recusados(api):
    sem_regra = base([CADASTRO, {"id": "c", "tipo": "condicao", "titulo": "Verificar", "depende_de": ["cadastro"]}])
    v = validar(api, sem_regra)
    assert v["valido"] is False and v["blocos"]["c"] == ["Escolha o que a condição verifica."]
    ramo_solto = base([CADASTRO, {"id": "s", "tipo": "aprovacao", "titulo": "Conferir", "depende_de": ["cadastro"], "ramo": {"condicao": "cadastro", "valor": "sim"}}])
    assert "condição que não existe" in validar(api, ramo_solto)["erros"][0]
