"""F3: Estúdio (descrição -> agente), governança automática e sandbox."""
import pytest

from app.agents.blueprint import Blueprint
from app.agents.governanca import ALTO, BAIXO, MEDIO, avaliar_risco, estimar_custo
from app.core.identidade import PERSONAS
from app.seed.agentes_exemplo import DUVIDA_LOJISTA, TRIAGEM_CHARGEBACK
from app.studio.sugestao import extrair_minutos, sugerir
from app.tools import dados_ficticios, executor
from tests.conftest import como


@pytest.fixture(autouse=True)
def _limpo():
    dados_ficticios.zerar()
    executor.zerar_limites()


@pytest.mark.parametrize("pessoa,descricao,padrao", [
    ("marina", "Quando o lojista liga dizendo que a maquininha quebrou, eu confiro o cadastro e abro chamado de troca", "troca_maquininha"),
    ("marina", "Lojistas perguntam sobre o prazo do estorno e eu procuro a regra para responder", "duvida_lojista"),
    ("carla", "Os colaboradores me perguntam quantos dias de férias ainda têm e como pedir", "ferias_colaborador"),
    ("rafael", "Toda manhã confiro os lojistas com chargeback e decido se abro chamado ou bloqueio o repasse", "triagem_chargeback"),
])
def test_descricao_vira_o_agente_certo(pessoa, descricao, padrao):
    s = sugerir(PERSONAS[pessoa], descricao)
    assert s.origem == "padrao:" + padrao and s.blueprint.area == PERSONAS[pessoa].area
    assert len(s.explicacao) == len(s.blueprint.passos)


def test_processo_desconhecido_vira_agente_basico_com_aviso():
    s = sugerir(PERSONAS["marina"], "Preciso organizar a escala de plantão do time no fim de semana")
    assert s.origem == "basico" and s.alertas


def test_ferramentas_sem_permissao_saem_e_sao_explicadas():
    s = sugerir(PERSONAS["marina"], "Toda manhã confiro os lojistas com chargeback e decido se abro chamado ou bloqueio o repasse")
    assert set(s.removidas) == {"listar_chargebacks", "bloquear_repasse"}
    assert "listar_chargebacks" not in s.blueprint.ferramentas_usadas()
    assert all(d in {p.id for p in s.blueprint.passos} for p in s.blueprint.passos for d in p.depende_de)


def test_dados_pessoais_saem_da_descricao_e_tempo_vira_linha_de_base():
    s = sugerir(PERSONAS["marina"], "O lojista CPF 529.982.247-25 diz que a maquininha quebrou, abro chamado de troca. Levo 20 minutos")
    assert any("dados pessoais" in a for a in s.alertas)
    assert "529.982.247-25" not in s.blueprint.model_dump_json()
    assert s.blueprint.minutos_manual == 20


@pytest.mark.parametrize("texto,minutos", [("levo 20 minutos", 20), ("uns 1,5 horas", 90), ("2h por dia", 120), ("rápido", None)])
def test_extrair_minutos(texto, minutos):
    assert extrair_minutos(texto) == minutos


def test_risco_calculado_pelas_ferramentas():
    assert avaliar_risco(TRIAGEM_CHARGEBACK).nivel == ALTO      # retenção de repasse
    assert avaliar_risco(DUVIDA_LOJISTA).nivel == BAIXO
    bp = Blueprint.model_validate({**DUVIDA_LOJISTA.model_dump(), "passos": [
        {"id": "c", "titulo": "C", "tipo": "agente", "instrucao": "x", "ferramentas": ["abrir_chamado"]}]})
    assert avaliar_risco(bp).nivel == MEDIO


def test_estimativa_de_custo_segue_o_roteador():
    est = estimar_custo(TRIAGEM_CHARGEBACK)
    assert est.por_passo["cadastro"]["custo_brl"] == 0
    assert est.por_passo["acao"]["modelo"] == "Claude Haiku 5.5"
    assert est.custo_brl > 0 and est.chamadas_modelo == 4


# ---------- API: o critério de pronto da F3 ----------
def test_marina_cria_e_testa_um_agente_sem_codigo(api):
    h = como("marina")
    sug = api.post("/api/v1/estudio/sugerir", headers=h, json={
        "descricao": "Quando o lojista diz que a maquininha quebrou eu confiro o cadastro e abro chamado de troca na logística"}).json()
    bp = sug["blueprint"]
    assert sug["risco"]["nivel"] == MEDIO and not sug["risco"]["exige_revisao_seguranca"]
    # ajusta no canvas: renomeia e valida ao vivo
    bp["nome"] = "Troca de maquininha (Marina)"
    v = api.post("/api/v1/estudio/validar", headers=h, json={"blueprint": bp}).json()
    assert v["valido"] and v["niveis"] == [["cadastro", "politica"], ["chamado"]]
    # testa no sandbox
    exe = api.post("/api/v1/estudio/testar", headers=h,
                   json={"blueprint": bp, "entrada": {"lojista_id": "L1001", "relato": "não liga"}}).json()
    assert exe["status"] == "concluida" and exe["agente_id"] == "sandbox"
    assert dados_ficticios.CHAMADOS[0]["fila"] == "logistica"


def test_validar_aponta_erros_em_linguagem_simples(api):
    bp = DUVIDA_LOJISTA.model_dump()
    bp["passos"][2]["depende_de"] = ["inexistente"]
    v = api.post("/api/v1/estudio/validar", headers=como("marina"), json={"blueprint": bp}).json()
    assert not v["valido"] and "inexistente" in v["erros"][0]


def test_validar_mostra_ferramenta_sem_permissao(api):
    v = api.post("/api/v1/estudio/validar", headers=como("marina"),
                 json={"blueprint": TRIAGEM_CHARGEBACK.model_dump()}).json()
    assert "listar_chargebacks" in v["sem_permissao"] and v["risco"]["exige_revisao_seguranca"]


def test_so_criadores_usam_o_estudio(api):
    r = api.post("/api/v1/estudio/sugerir", headers=como("helena"), json={"descricao": "x" * 20})
    assert r.status_code == 403
