"""F4: ciclo de vida, versões, revisão de segurança e execução por agente publicado."""
import pytest

from app.agents import ciclo
from app.agents import modelos as m
from app.agents.blueprint import Blueprint
from app.agents.diff import comparar
from app.audit import trilha
from app.core.identidade import PERSONAS
from app.seed.agentes_exemplo import DUVIDA_LOJISTA, TRIAGEM_CHARGEBACK
from app.seed.demo import semear
from app.tools import dados_ficticios, executor
from tests.conftest import como

P = PERSONAS


@pytest.fixture(autouse=True)
def _limpo():
    dados_ficticios.zerar()
    executor.zerar_limites()


def _tipos(s, agente_id):
    return [e.tipo for e in reversed(trilha.listar(s, agente_id=agente_id))]


# ---------- o critério de pronto da F4 ----------
def test_ciclo_completo_fica_na_trilha(sessao):
    a = ciclo.criar(sessao, P["marina"], DUVIDA_LOJISTA)
    assert a.estado == m.RASCUNHO
    novo = DUVIDA_LOJISTA.model_copy(update={"instrucoes": "Tom cordial. Sempre cite o canal de atendimento."})
    v = ciclo.editar(sessao, P["marina"], a.id, novo, "Ajuste de tom")
    assert v.numero == 1   # ainda rascunho: mesma versão
    a = ciclo.publicar(sessao, P["marina"], a.id)
    assert a.estado == m.PUBLICADO and a.versao_publicada == 1
    v2 = ciclo.editar(sessao, P["marina"], a.id, novo.model_copy(update={"minutos_manual": 9}))
    assert v2.numero == 2 and ciclo.versao(sessao, a.id, 1).estado == m.V_PUBLICADA
    ciclo.publicar(sessao, P["marina"], a.id)
    assert ciclo.versao(sessao, a.id, 1).estado == m.V_SUBSTITUIDA
    ciclo.pausar(sessao, P["helena"], a.id, "Revisão de custos")
    ciclo.retomar(sessao, P["marina"], a.id)
    ciclo.depreciar(sessao, P["marina"], a.id, "Substituído pelo atendimento unificado")
    assert _tipos(sessao, a.id) == ["agente_criado", "agente_modificado", "agente_publicado", "agente_modificado",
                                    "agente_publicado", "agente_pausado", "agente_retomado", "agente_depreciado"]
    assert trilha.verificar(sessao)["integra"]


# ---------- revisão de segurança ----------
def test_risco_alto_passa_pela_revisao_com_quatro_olhos(sessao):
    a = ciclo.criar(sessao, P["rafael"], TRIAGEM_CHARGEBACK)
    a = ciclo.publicar(sessao, P["rafael"], a.id)
    assert a.estado == m.EM_REVISAO and a.versao_publicada is None
    with pytest.raises(ciclo.ErroCiclo, match="Segurança"):
        ciclo.revisar(sessao, P["rafael"], a.id, True, "ok")
    with pytest.raises(ciclo.ErroCiclo, match="parecer"):
        ciclo.revisar(sessao, P["lucas"], a.id, True, "  ")
    with pytest.raises(ciclo.ErroCiclo, match="revisão"):
        ciclo.editar(sessao, P["rafael"], a.id, TRIAGEM_CHARGEBACK.model_copy(update={"minutos_manual": 30}))
    a = ciclo.revisar(sessao, P["lucas"], a.id, True, "Ação sensível com confirmação humana. Aprovado.")
    assert a.estado == m.PUBLICADO and ciclo.versao(sessao, a.id, 1).revisor == "lucas"


def test_revisor_nao_revisa_a_propria_versao(sessao):
    # Lucas não cria agentes, mas o caso protege o princípio: autor != revisor
    a = ciclo.criar(sessao, P["rafael"], TRIAGEM_CHARGEBACK)
    ciclo.publicar(sessao, P["rafael"], a.id)
    v = ciclo.versao(sessao, a.id, 1)
    v.autor = "lucas"
    sessao.add(v)
    sessao.commit()
    with pytest.raises(ciclo.ErroCiclo, match="não pode revisá-la"):
        ciclo.revisar(sessao, P["lucas"], a.id, True, "ok")


def test_rejeicao_volta_para_rascunho_e_exige_nova_versao(sessao):
    a = ciclo.criar(sessao, P["rafael"], TRIAGEM_CHARGEBACK)
    ciclo.publicar(sessao, P["rafael"], a.id)
    a = ciclo.revisar(sessao, P["lucas"], a.id, False, "Falta limitar a retenção a casos com 5+ contestações.")
    assert a.estado == m.RASCUNHO and ciclo.versao(sessao, a.id, 1).estado == m.V_REJEITADA
    with pytest.raises(ciclo.ErroCiclo, match="rascunho"):
        ciclo.publicar(sessao, P["rafael"], a.id)
    v2 = ciclo.editar(sessao, P["rafael"], a.id, TRIAGEM_CHARGEBACK.model_copy(update={"instrucoes": "Só proponha retenção com 5+ contestações."}))
    assert v2.numero == 2
    assert ciclo.publicar(sessao, P["rafael"], a.id).estado == m.EM_REVISAO


def test_nova_versao_de_agente_publicado_em_revisao_mantem_a_anterior_no_ar(sessao):
    a = ciclo.criar(sessao, P["rafael"], TRIAGEM_CHARGEBACK)
    ciclo.publicar(sessao, P["rafael"], a.id)
    ciclo.revisar(sessao, P["lucas"], a.id, True, "ok, aprovado")
    ciclo.editar(sessao, P["rafael"], a.id, TRIAGEM_CHARGEBACK.model_copy(update={"minutos_manual": 40}))
    a = ciclo.publicar(sessao, P["rafael"], a.id)
    assert a.estado == m.PUBLICADO and a.versao_publicada == 1   # v2 em revisão, v1 segue rodando
    _, bp = ciclo.checar_execucao(sessao, P["rafael"], a.id)
    assert bp.minutos_manual == 25


# ---------- permissões ----------
def test_nao_cria_com_ferramenta_que_nao_pode_usar(sessao):
    with pytest.raises(ciclo.ErroCiclo, match="não pode usar"):
        ciclo.criar(sessao, P["marina"], TRIAGEM_CHARGEBACK)
    with pytest.raises(ciclo.ErroCiclo, match="não cria"):
        ciclo.criar(sessao, P["helena"], DUVIDA_LOJISTA)


def test_outra_area_nao_edita_nem_executa(sessao):
    a = ciclo.criar(sessao, P["marina"], DUVIDA_LOJISTA)
    ciclo.publicar(sessao, P["marina"], a.id)
    with pytest.raises(ciclo.ErroCiclo, match="Só criadores"):
        ciclo.editar(sessao, P["carla"], a.id, DUVIDA_LOJISTA)
    with pytest.raises(ciclo.ErroCiclo, match="não tem acesso"):
        ciclo.checar_execucao(sessao, P["carla"], a.id)
    assert "execucao_negada" in _tipos(sessao, a.id)
    ciclo.compartilhar(sessao, P["marina"], a.id, ["pessoas"])
    assert ciclo.checar_execucao(sessao, P["carla"], a.id)


def test_seguranca_pausa_qualquer_agente_mas_so_dono_ou_coe_depreciam(sessao):
    a = ciclo.criar(sessao, P["marina"], DUVIDA_LOJISTA)
    ciclo.publicar(sessao, P["marina"], a.id)
    ciclo.pausar(sessao, P["lucas"], a.id, "Comportamento estranho reportado")
    with pytest.raises(ciclo.ErroCiclo, match="pausado: Comportamento"):
        ciclo.checar_execucao(sessao, P["marina"], a.id)
    with pytest.raises(ciclo.ErroCiclo, match="dono"):
        ciclo.depreciar(sessao, P["lucas"], a.id, "x")
    ciclo.depreciar(sessao, P["helena"], a.id, "Fim do processo")
    with pytest.raises(ciclo.ErroCiclo):
        ciclo.retomar(sessao, P["marina"], a.id)
    with pytest.raises(ciclo.ErroCiclo, match="depreciado"):
        ciclo.editar(sessao, P["marina"], a.id, DUVIDA_LOJISTA)


# ---------- diff ----------
def test_diff_descreve_mudancas_para_quem_revisa():
    antes = DUVIDA_LOJISTA.model_dump()
    depois = DUVIDA_LOJISTA.model_dump()
    depois["passos"][2]["ferramentas"] = ["abrir_chamado"]
    depois["passos"] = depois["passos"][1:]
    depois["nome"] = "Novo nome"
    mud = comparar(antes, depois)
    assert {"tipo": "alterado", "alvo": "agente", "campo": "nome", "antes": antes["nome"], "depois": "Novo nome"} in mud
    assert any(x["tipo"] == "removido" and x["alvo"] == "passo:cadastro" for x in mud)
    assert any(x["campo"] == "ferramentas" and x["depois"] == ["abrir_chamado"] for x in mud)


# ---------- seed e API ----------
def test_semente_da_demo_publica_agentes_e_mantem_trilha_integra(sessao):
    assert semear(sessao) and not semear(sessao)
    estados = {a.nome: (a.estado, a.versao_publicada) for a in sessao.exec(__import__("sqlmodel").select(m.Agente))}
    assert estados["Analista de risco de chargebacks"] == (m.PUBLICADO, 1)
    assert len(estados) == 4 and trilha.verificar(sessao)["integra"]


def test_api_publicar_revisar_executar(api):
    bp = TRIAGEM_CHARGEBACK.model_dump()
    a = api.post("/api/v1/agentes", json={"blueprint": bp}, headers=como("rafael")).json()
    assert api.post(f"/api/v1/agentes/{a['id']}/publicar", headers=como("rafael")).json()["estado"] == "em_revisao"
    fila = api.get("/api/v1/revisoes", headers=como("lucas")).json()
    assert fila[0]["agente"]["id"] == a["id"] and fila[0]["mudancas"][0]["tipo"] == "adicionado"
    assert api.get("/api/v1/revisoes", headers=como("marina")).status_code == 403
    r = api.post(f"/api/v1/agentes/{a['id']}/revisao", json={"aprovar": True, "parecer": "Aprovado."}, headers=como("lucas"))
    assert r.json()["estado"] == "publicado"
    exe = api.post(f"/api/v1/agentes/{a['id']}/executar", json={"entrada": {"lojista_id": "L1001"}}, headers=como("rafael")).json()
    assert exe["status"] == "concluida" and exe["agente_id"] == a["id"] and exe["versao"] == 1
    d = api.get(f"/api/v1/agentes/{a['id']}", headers=como("helena")).json()
    assert d["execucoes"] == 1 and [v["numero"] for v in d["versoes"]] == [1]
    assert {"agente_criado", "agente_enviado_revisao", "revisao_aprovada", "agente_publicado"} <= {e["tipo"] for e in d["historico"]}
    assert api.get(f"/api/v1/agentes/{a['id']}", headers=como("carla")).status_code == 403
    assert api.post(f"/api/v1/agentes/{a['id']}/executar", json={"entrada": {"lojista_id": "L1001"}},
                    headers=como("marina")).status_code == 403
