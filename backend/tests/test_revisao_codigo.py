"""Regressões dos achados da revisão de código (antes do primeiro commit)."""
import pytest

from app.agents import ciclo
from app.audit import trilha
from app.core.identidade import PERSONAS
from app.llm.cliente import ChamadaFerramenta, RespostaLLM, simulador
from app.runtime import modelos as m
from app.runtime import motor
from app.agents.blueprint import Blueprint
from app.seed.agentes_exemplo import TRIAGEM_CHARGEBACK
from app.tools import dados_ficticios, executor
from tests.conftest import como

P = PERSONAS


@pytest.fixture(autouse=True)
def _limpo():
    dados_ficticios.zerar()
    executor.zerar_limites()


def _triagem_publicada(s):
    a = ciclo.criar(s, P["rafael"], TRIAGEM_CHARGEBACK)
    ciclo.publicar(s, P["rafael"], a.id)
    ciclo.revisar(s, P["lucas"], a.id, True, "ok")
    a, bp = ciclo.checar_execucao(s, P["rafael"], a.id)
    exe, _ = motor.executar(s, P["rafael"], bp, {"lojista_id": "L1003"}, agente_id=a.id, versao=1)
    assert exe.status == m.AGUARDANDO
    return a, exe


# ---- #2: pausa de emergência barra ação pendente ----
def test_agente_pausado_nao_confirma_acao_pendente(sessao):
    a, exe = _triagem_publicada(sessao)
    ciclo.pausar(sessao, P["lucas"], a.id, "emergência")
    with pytest.raises(motor.ErroRetomada, match="pausado"):
        motor.retomar(sessao, exe.id, P["rafael"], True)
    assert not dados_ficticios.BLOQUEIOS
    assert motor.retomar(sessao, exe.id, P["rafael"], False).status == m.CONCLUIDA   # recusar continua possível


def test_agente_depreciado_nao_confirma_acao_pendente(sessao):
    a, exe = _triagem_publicada(sessao)
    ciclo.depreciar(sessao, P["rafael"], a.id, "fim")
    with pytest.raises(motor.ErroRetomada, match="depreciado"):
        motor.retomar(sessao, exe.id, P["rafael"], True)


# ---- #7: só quem disparou ou um curador decide ----
def test_quem_nao_disparou_nem_e_curador_nao_decide(sessao, monkeypatch):
    _, exe = _triagem_publicada(sessao)
    sem_papel = P["rafael"].__class__(**{**P["rafael"].__dict__, "id": "ana", "papeis": frozenset({"usuario"})})
    with pytest.raises(motor.ErroRetomada, match="curador"):
        motor.retomar(sessao, exe.id, sem_papel, True)


# ---- #3: execução de blueprint livre só para criadores, na própria área, como teste ----
def test_blueprint_livre_exige_criador(api):
    bp = {"nome": "Livre", "objetivo": "testar bypass", "area": "risco",
          "passos": [{"id": "a", "titulo": "A", "tipo": "ferramenta", "ferramenta": "abrir_chamado",
                      "entrada": {"fila": "ti", "titulo": "t", "descricao": "d"}}]}
    assert api.post("/api/v1/execucoes", json={"blueprint": bp}, headers=como("helena")).status_code == 403
    r = api.post("/api/v1/execucoes", json={"blueprint": bp}, headers=como("marina")).json()
    assert r["area"] == "atendimento" and r["agente_id"] == "sandbox"


# ---- #4: dado de sistema confidencial não vaza para ferramenta interna ----
def test_dado_confidencial_nao_sai_por_ferramenta_interna(sessao, monkeypatch):
    from app.tools import catalogo
    original = catalogo.CATALOGO["consultar_colaborador"].executar
    esp = catalogo.CATALOGO["consultar_colaborador"]
    monkeypatch.setitem(catalogo.CATALOGO, "consultar_colaborador", esp.__class__(**{
        **esp.__dict__, "executar": lambda e, c: {**original(e, c), "cpf": "390.533.447-05"}}))

    def roteiro(chave, sistema, msgs, ferramentas):
        if len(msgs) == 1:
            return RespostaLLM(chave, "", chamadas=[ChamadaFerramenta("x", "enviar_notificacao", {
                "canal": "slack", "destino": "#geral", "mensagem": "CPF do colaborador: [CPF_1]; pedido de [CPF_2]"})])
        return RespostaLLM(chave, "ok")
    simulador().roteiros.insert(0, roteiro)
    try:
        bp = Blueprint.model_validate({"nome": "Vazamento", "objetivo": "testar fluxo", "area": "pessoas", "passos": [
            {"id": "f", "titulo": "Ficha", "tipo": "ferramenta", "ferramenta": "consultar_colaborador",
             "entrada": {"colaborador_id": "C501"}},
            {"id": "n", "titulo": "Avisar", "tipo": "agente", "instrucao": "x", "ferramentas": ["enviar_notificacao"],
             "depende_de": ["f"]}]})
        exe, mapa = motor.executar(sessao, P["carla"], bp, {"solicitante": "529.982.247-25"})
        assert exe.status == m.CONCLUIDA
        enviada = dados_ficticios.NOTIFICACOES[0]["mensagem"]
        cpf_ficha = next(k for k, v in mapa.items() if v == "390.533.447-05")
        cpf_pedido = next(k for k, v in mapa.items() if v == "529.982.247-25")
        assert "390.533.447-05" not in enviada and cpf_ficha in enviada        # confidencial: fica marcador
        assert "529.982.247-25" in enviada and cpf_pedido not in enviada       # digitado por quem disparou: real
        ev = next(e for e in trilha.listar(sessao, tipo="ferramenta_executada") if e.dados["conector"] == "enviar_notificacao")
        assert cpf_ficha in ev.dados["dados_retidos"]
    finally:
        simulador().roteiros.remove(roteiro)


# ---- #8: limite de texto nos campos enviados aos sistemas ----
def test_campo_de_texto_tem_limite(sessao):
    r = executor.executar(sessao, P["marina"], "abrir_chamado",
                          {"fila": "ti", "titulo": "t", "descricao": "x" * (executor.LIMITE_TEXTO + 1)})
    assert r.tipo_erro == "invalido" and "caracteres" in r.erro


# ---- #5: leituras não gravam alertas ----
def test_contagem_do_sino_nao_grava_auditoria(api):
    h = como("helena")
    antes = api.get("/api/v1/auditoria/verificar", headers=h).json()["total"]
    for _ in range(3):
        api.get("/api/v1/notificacoes/contagem", headers=h)
        api.get("/api/v1/alertas", headers=h)
        api.get("/api/v1/saude/agentes", headers=h)
    assert api.get("/api/v1/auditoria/verificar", headers=h).json()["total"] == antes
