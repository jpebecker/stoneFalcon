"""F2: runtime de agentes (DAG paralelo, loop de raciocínio, limites, escalada, aprovação)."""
import json
import threading
import time

import pytest
from pydantic import ValidationError

from app.agents.blueprint import Blueprint
from app.audit import trilha
from app.core.identidade import PERSONAS
from app.llm.cliente import ChamadaFerramenta, RespostaLLM, simulador
from app.runtime import modelos as m
from app.runtime import motor
from tests.legado import DUVIDA_LOJISTA, TRIAGEM_CHARGEBACK
from app.tools import catalogo, dados_ficticios, executor
from tests.conftest import como


@pytest.fixture(autouse=True)
def _limpo():
    dados_ficticios.zerar()
    executor.zerar_limites()
    yield


def _rodar(s, pessoa, bp, entrada):
    return motor.executar(s, PERSONAS[pessoa], bp, entrada)


def _bp(passos, **kw):
    return Blueprint.model_validate({"nome": "Teste", "objetivo": "Testar o runtime", "area": "risco",
                                     "passos": passos, **kw})


# ---------- blueprint ----------
def test_niveis_do_dag_agrupam_passos_paralelos():
    assert TRIAGEM_CHARGEBACK.niveis() == [["cadastro", "contestacoes"], ["analise"], ["acao"]]


@pytest.mark.parametrize("passos,erro", [
    ([{"id": "a", "titulo": "A", "tipo": "agente", "instrucao": "x", "depende_de": ["b"]},
      {"id": "b", "titulo": "B", "tipo": "agente", "instrucao": "x", "depende_de": ["a"]}], "ciclo"),
    ([{"id": "a", "titulo": "A", "tipo": "ferramenta", "ferramenta": "apagar_tudo"}], "fora do catálogo"),
    ([{"id": "a", "titulo": "A", "tipo": "agente", "instrucao": "x", "depende_de": ["z"]}], "não existe"),
    ([{"id": "a", "titulo": "A", "tipo": "agente", "instrucao": ""}], "instrução"),
])
def test_blueprint_invalido_e_recusado(passos, erro):
    with pytest.raises(ValidationError, match=erro):
        _bp(passos)


# ---------- ponta a ponta (critério de pronto da F2) ----------
def test_agente_com_passos_paralelos_roda_ponta_a_ponta(sessao):
    exe, _ = _rodar(sessao, "marina", DUVIDA_LOJISTA, {"lojista_id": "L1001", "pergunta": "quanto tempo demora o estorno?"})
    assert exe.status == m.CONCLUIDA and exe.resultado
    assert {p["status"] for p in exe.passos.values()} == {"concluido"}
    assert exe.chamadas_modelo == 1 and exe.custo_usd > 0 and exe.simulado
    pol = exe.passos["politica"]["saida"]["resultados"][0]
    assert "estorno" in pol["pergunta"].lower()
    # paralelos contam uma vez no caminho crítico
    lat = {f: catalogo.CATALOGO[f].latencia_ms for f in ("consultar_lojista", "buscar_politica")}
    assert exe.duracao_estimada_ms < lat["consultar_lojista"] + lat["buscar_politica"] + exe.passos["resposta"]["duracao_estimada_ms"]
    assert trilha.listar(sessao, tipo="execucao_concluida")[0].dados["execucao"] == exe.id
    assert trilha.verificar(sessao)["integra"]


def test_passos_da_mesma_camada_rodam_ao_mesmo_tempo(sessao, monkeypatch):
    ativos, pico = [0], [0]
    trava = threading.Lock()
    original = catalogo.CATALOGO["consultar_lojista"].executar

    def lento(e, c):
        with trava:
            ativos[0] += 1
            pico[0] = max(pico[0], ativos[0])
        time.sleep(0.15)
        with trava:
            ativos[0] -= 1
        return original(e, c)

    esp = catalogo.CATALOGO["consultar_lojista"]
    monkeypatch.setitem(catalogo.CATALOGO, "consultar_lojista", esp.__class__(**{**esp.__dict__, "executar": lento}))
    bp = _bp([{"id": "a", "titulo": "A", "tipo": "ferramenta", "ferramenta": "consultar_lojista",
               "entrada": {"lojista_id": "L1001"}},
              {"id": "b", "titulo": "B", "tipo": "ferramenta", "ferramenta": "consultar_lojista",
               "entrada": {"lojista_id": "L1002"}}])
    exe, _ = _rodar(sessao, "rafael", bp, {})
    assert exe.status == m.CONCLUIDA and pico[0] == 2


# ---------- aprovação humana ----------
def test_acao_sensivel_pausa_e_retoma_com_aprovacao(sessao):
    exe, _ = _rodar(sessao, "rafael", TRIAGEM_CHARGEBACK, {"lojista_id": "L1003"})
    assert exe.status == m.AGUARDANDO and exe.pendencia["conector"] == "bloquear_repasse"
    assert not dados_ficticios.BLOQUEIOS and len(dados_ficticios.CHAMADOS) == 1   # o chamado já foi aberto
    with pytest.raises(motor.ErroRetomada, match="área"):
        motor.retomar(sessao, exe.id, PERSONAS["marina"], True)
    exe = motor.retomar(sessao, exe.id, PERSONAS["rafael"], True)
    assert exe.status == m.CONCLUIDA and len(dados_ficticios.BLOQUEIOS) == 1
    assert trilha.listar(sessao, tipo="aprovacao_concedida")
    with pytest.raises(motor.ErroRetomada):
        motor.retomar(sessao, exe.id, PERSONAS["rafael"], True)


def test_recusa_humana_encerra_sem_acao(sessao):
    exe, _ = _rodar(sessao, "rafael", TRIAGEM_CHARGEBACK, {"lojista_id": "L1003"})
    exe = motor.retomar(sessao, exe.id, PERSONAS["rafael"], False)
    assert exe.status == m.CONCLUIDA and not dados_ficticios.BLOQUEIOS and "recusada" in exe.resultado


def test_lojista_sem_risco_nao_propoe_bloqueio(sessao):
    exe, _ = _rodar(sessao, "rafael", TRIAGEM_CHARGEBACK, {"lojista_id": "L1001"})
    assert exe.status == m.CONCLUIDA and not dados_ficticios.BLOQUEIOS


def test_passo_de_aprovacao_explicito(sessao):
    bp = _bp([{"id": "ok", "titulo": "Gestor confere", "tipo": "aprovacao"},
              {"id": "c", "titulo": "Cadastro", "tipo": "ferramenta", "ferramenta": "consultar_lojista",
               "entrada": {"lojista_id": "L1001"}, "depende_de": ["ok"]}])
    exe, _ = _rodar(sessao, "rafael", bp, {})
    assert exe.status == m.AGUARDANDO and "c" not in exe.passos
    exe = motor.retomar(sessao, exe.id, PERSONAS["rafael"], True)
    assert exe.status == m.CONCLUIDA and exe.passos["c"]["status"] == "concluido"


# ---------- escaladas ----------
def test_falha_de_sistema_vira_escalada_com_motivo(sessao):
    executor.definir_falha(sessao, "listar_chargebacks", "fora_do_ar", "lucas")
    exe, _ = _rodar(sessao, "rafael", TRIAGEM_CHARGEBACK, {"lojista_id": "L1003"})
    assert exe.status == m.ESCALADA and "não respondeu" in exe.motivo
    assert "analise" not in exe.passos   # não segue com dados faltando
    assert trilha.listar(sessao, tipo="execucao_escalada")


def test_quem_disparou_sem_permissao_escala(sessao):
    exe, _ = _rodar(sessao, "marina", TRIAGEM_CHARGEBACK, {"lojista_id": "L1003"})
    assert exe.status == m.ESCALADA and "confidencial" in exe.motivo
    assert trilha.listar(sessao, tipo="ferramenta_negada")


def _com_roteiro(fn):
    simulador().roteiros.insert(0, fn)
    return fn


def test_limite_de_iteracoes_escala(sessao):
    def teimoso(chave, sistema, msgs, ferramentas):
        return RespostaLLM(chave, "", chamadas=[ChamadaFerramenta("x", "buscar_politica",
                                                                   {"area": "risco", "consulta": "fraude"})])
    _com_roteiro(teimoso)
    try:
        bp = _bp([{"id": "a", "titulo": "A", "tipo": "agente", "instrucao": "x", "max_iteracoes": 3,
                   "ferramentas": ["buscar_politica"]}])
        exe, _ = _rodar(sessao, "rafael", bp, {})
        assert exe.status == m.ESCALADA and "3 tentativas" in exe.motivo and exe.chamadas_modelo == 3
    finally:
        simulador().roteiros.remove(teimoso)


def test_orcamento_escala(sessao):
    bp = _bp([{"id": "a", "titulo": "A", "tipo": "agente", "instrucao": "x", "max_iteracoes": 10,
               "ferramentas": ["buscar_politica"]}], limites={"max_custo_brl": 2, "max_chamadas_modelo": 2})

    def teimoso(chave, sistema, msgs, ferramentas):
        return RespostaLLM(chave, "", chamadas=[ChamadaFerramenta("x", "buscar_politica",
                                                                   {"area": "risco", "consulta": "fraude"})])
    _com_roteiro(teimoso)
    try:
        exe, _ = _rodar(sessao, "rafael", bp, {})
        assert exe.status == m.ESCALADA and "2 chamadas" in exe.motivo
    finally:
        simulador().roteiros.remove(teimoso)


def test_ferramenta_fora_do_passo_e_recusada_ao_modelo(sessao):
    vistos = []

    def atrevido(chave, sistema, msgs, ferramentas):
        if len(msgs) == 1:
            return RespostaLLM(chave, "", chamadas=[ChamadaFerramenta("x", "bloquear_repasse",
                                                                       {"lojista_id": "L1001", "motivo": "x"})])
        vistos.append(msgs[-1]["content"][0])
        return RespostaLLM(chave, "Ok, sem essa ferramenta.")
    _com_roteiro(atrevido)
    try:
        bp = _bp([{"id": "a", "titulo": "A", "tipo": "agente", "instrucao": "x", "ferramentas": ["buscar_politica"]}])
        exe, _ = _rodar(sessao, "rafael", bp, {})
        assert exe.status == m.CONCLUIDA and vistos[0]["is_error"] and not dados_ficticios.BLOQUEIOS
    finally:
        simulador().roteiros.remove(atrevido)


# ---------- guardrails dentro do loop ----------
def test_marcadores_sao_consistentes_e_sistemas_recebem_o_real(sessao):
    capturado = {}

    def roteiro(chave, sistema, msgs, ferramentas):
        if len(msgs) == 1:
            capturado["inicial"] = msgs[0]["content"]
            return RespostaLLM(chave, "", chamadas=[ChamadaFerramenta(
                "x", "abrir_chamado", {"fila": "risco", "titulo": "Caso", "descricao": "Titular [CPF_1]"})])
        return RespostaLLM(chave, "Chamado aberto para [CPF_1].")
    _com_roteiro(roteiro)
    try:
        bp = _bp([{"id": "a", "titulo": "A", "tipo": "agente", "instrucao": "x", "ferramentas": ["abrir_chamado"]}])
        exe, mapa = _rodar(sessao, "rafael", bp, {"cpf": "529.982.247-25"})
        assert "529.982.247-25" not in capturado["inicial"]
        assert dados_ficticios.CHAMADOS[0]["descricao"] == "Titular 529.982.247-25"   # sistema recebe o real
        assert "529.982.247-25" not in json.dumps(exe.model_dump(), ensure_ascii=False)  # banco só com marcador
        assert mapa["[CPF_1]"] == "529.982.247-25"
    finally:
        simulador().roteiros.remove(roteiro)


# ---------- API ----------
def test_api_executa_exemplo_e_decide(api):
    r = api.post("/api/v1/execucoes", json={"blueprint": TRIAGEM_CHARGEBACK.model_dump(), "entrada": {"lojista_id": "L1003"}},
                 headers=como("rafael"))
    assert r.status_code == 200
    corpo = r.json()
    assert corpo["status"] == "aguardando_aprovacao" and "123.456.789-09" in json.dumps(corpo["passos_tela"])
    pend = api.get("/api/v1/execucoes?pendentes=true", headers=como("rafael")).json()
    assert [e["id"] for e in pend] == [corpo["id"]]
    assert api.get("/api/v1/execucoes/%s" % corpo["id"], headers=como("carla")).status_code == 403
    r = api.post("/api/v1/execucoes/%s/decisao" % corpo["id"], json={"aprovar": True}, headers=como("rafael"))
    assert r.json()["status"] == "concluida"


def test_api_exige_campos_de_entrada(api):
    r = api.post("/api/v1/execucoes", json={"blueprint": DUVIDA_LOJISTA.model_dump(), "entrada": {"lojista_id": "L1001"}},
                 headers=como("marina"))
    assert r.status_code == 422 and "pergunta" in r.json()["detail"]


def test_aprovacao_entrega_o_dado_real_ao_sistema(sessao):
    """A pendência fica mascarada no banco, mas a ação aprovada recebe o valor real (mapa só em memória)."""
    def roteiro(chave, sistema, msgs, ferramentas):
        if len(msgs) == 1:
            return RespostaLLM(chave, "Proponho reter.", chamadas=[ChamadaFerramenta(
                "x", "bloquear_repasse", {"lojista_id": "L1003", "motivo": "Titular [CPF_1] com 12 contestações"})])
        return RespostaLLM(chave, "Feito.")
    _com_roteiro(roteiro)
    try:
        bp = _bp([{"id": "a", "titulo": "A", "tipo": "agente", "instrucao": "x", "ferramentas": ["bloquear_repasse"]}])
        exe, _ = _rodar(sessao, "rafael", bp, {"cpf": "123.456.789-09"})
        assert exe.status == m.AGUARDANDO and "[CPF_1]" in exe.pendencia["entrada"]["motivo"]
        motor.retomar(sessao, exe.id, PERSONAS["rafael"], True)
        assert dados_ficticios.BLOQUEIOS[0]["motivo"] == "Titular 123.456.789-09 com 12 contestações"
    finally:
        simulador().roteiros.remove(roteiro)
