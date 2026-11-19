"""F5: saúde, observabilidade e alertas ao owner."""
import pytest
from sqlmodel import select

from app.agents import ciclo
from app.audit import trilha
from app.core.identidade import PERSONAS
from app.observability import alertas, metricas
from app.runtime import motor
from app.seed.agentes_exemplo import DUVIDA_LOJISTA, TRIAGEM_CHARGEBACK
from app.tools import dados_ficticios, executor
from tests.conftest import como

pytestmark = pytest.mark.usefixtures("legado")   # v7: usa fluxos de vários passos como dado de exemplo (veja o fixture)

P = PERSONAS


@pytest.fixture(autouse=True)
def _limpo():
    dados_ficticios.zerar()
    executor.zerar_limites()


def _publicar_duvida(s):
    a = ciclo.criar(s, P["marina"], DUVIDA_LOJISTA)
    return ciclo.publicar(s, P["marina"], a.id)


def _rodar(s, a, n, pessoa="marina", entrada=None):
    bp = ciclo.blueprint_publicado(s, a)
    for _ in range(n):
        motor.executar(s, P[pessoa], bp, entrada or {"lojista_id": "L1001", "pergunta": "prazo do estorno?"},
                       agente_id=a.id, versao=a.versao_publicada)


def _abertos(s):
    return list(s.exec(select(alertas.Alerta).where(alertas.Alerta.resolvido_em.is_(None))))


# ---------- métricas ----------
def test_percentil():
    assert metricas.percentil([], 0.95) == 0
    assert metricas.percentil([10, 20, 30, 40], 0.5) == 25
    assert metricas.percentil([100] * 19 + [1000], 0.95) == pytest.approx(145)


def test_resumo_de_execucoes(sessao):
    a = _publicar_duvida(sessao)
    _rodar(sessao, a, 3)
    r = metricas.resumo_execucoes(metricas.execucoes(sessao, a.id))
    assert r["execucoes"] == 3 and r["taxa_sucesso"] == 1.0 and r["latencia_p95_ms"] > 0 and r["custo_brl"] > 0


def test_chamadas_de_ferramenta_por_conector(sessao):
    a = _publicar_duvida(sessao)
    _rodar(sessao, a, 2)
    executor.definir_falha(sessao, "consultar_lojista", "erro", "lucas")
    _rodar(sessao, a, 2)
    c = metricas.chamadas_ferramentas(sessao)["consultar_lojista"]
    assert c["chamadas"] == 4 and c["erros"] == 2 and c["taxa_erro"] == 0.5 and a.id in c["agentes"]


# ---------- o critério de pronto da F5 ----------
def test_falha_injetada_gera_alerta_para_o_owner_e_fecha_sozinha(sessao):
    a = _publicar_duvida(sessao)
    executor.definir_falha(sessao, "buscar_politica", "fora_do_ar", "lucas")
    r = alertas.avaliar(sessao)
    al = [x for x in _abertos(sessao) if x.regra == "conector_fora"]
    assert len(al) == 1 and r["abertos"]
    assert al[0].agente_id == a.id and al[0].severidade == alertas.CRITICO
    assert set(al[0].destinatarios) == {"marina", "lucas"}
    assert al[0] in alertas.visiveis(sessao, P["marina"]) and al[0] not in alertas.visiveis(sessao, P["carla"])
    assert al[0] in alertas.visiveis(sessao, P["helena"])   # CoE vê tudo
    # não duplica
    alertas.avaliar(sessao)
    assert len([x for x in _abertos(sessao) if x.regra == "conector_fora"]) == 1
    # normaliza -> resolve
    executor.definir_falha(sessao, "buscar_politica", None, "lucas")
    r = alertas.avaliar(sessao)
    assert al[0].id in r["resolvidos"] and not _abertos(sessao)
    tipos = [e.tipo for e in trilha.listar(sessao)]
    assert "alerta_aberto" in tipos and "alerta_resolvido" in tipos


def test_agente_falhando_alerta_o_dono_com_o_motivo(sessao):
    a = _publicar_duvida(sessao)
    _rodar(sessao, a, 2)
    executor.definir_falha(sessao, "consultar_lojista", "erro", "lucas")
    _rodar(sessao, a, 3)
    alertas.avaliar(sessao)
    al = next(x for x in _abertos(sessao) if x.regra == "agente_falhando")
    assert al.destinatarios == ["marina"] and "3 de 5" in al.detalhe and "erro 500" in al.detalhe
    assert al.severidade == alertas.CRITICO   # 3/5 = 60%


def test_conector_sem_agente_dependente_avisa_so_a_engenharia(sessao):
    executor.definir_falha(sessao, "consultar_colaborador", "erro", "lucas")
    alertas.avaliar(sessao)
    al = _abertos(sessao)
    assert len(al) == 1 and al[0].agente_id is None and al[0].destinatarios == ["lucas"]


def test_conector_lento_e_atencao(sessao):
    _publicar_duvida(sessao)
    executor.definir_falha(sessao, "consultar_lojista", "lento", "lucas")
    alertas.avaliar(sessao)
    al = _abertos(sessao)
    assert [x.regra for x in al] == ["conector_lento"] and al[0].severidade == alertas.ATENCAO


def test_score_de_saude():
    assert alertas.score(None, []) == {"nota": 100, "status": "saudavel"}
    assert alertas.score(1.0, [])["nota"] == 100
    crit = alertas.Alerta(id="x", chave="k", regra="r", severidade=alertas.CRITICO, titulo="t", detalhe="d",
                          aberto_em="", atualizado_em="")
    assert alertas.score(0.5, [crit]) == {"nota": 45, "status": "critico"}


def test_agente_pausado_continua_monitorado_mas_depreciado_nao(sessao):
    a = _publicar_duvida(sessao)
    ciclo.pausar(sessao, P["marina"], a.id)
    executor.definir_falha(sessao, "buscar_politica", "erro", "lucas")
    alertas.avaliar(sessao)
    assert any(x.agente_id == a.id for x in _abertos(sessao))
    ciclo.depreciar(sessao, P["marina"], a.id, "fim")
    alertas.avaliar(sessao)
    assert not any(x.agente_id == a.id for x in _abertos(sessao))


def test_api_da_demo_de_falha(api):
    h = como("marina")
    a = api.post("/api/v1/agentes", json={"blueprint": DUVIDA_LOJISTA.model_dump()}, headers=h).json()
    api.post(f"/api/v1/agentes/{a['id']}/publicar", headers=h)
    assert api.get("/api/v1/notificacoes/contagem", headers=h).json()["nao_lidos"] == 0
    api.post("/api/v1/ferramentas/consultar_lojista/falha", json={"falha": "fora_do_ar"}, headers=como("lucas"))
    exe = api.post(f"/api/v1/agentes/{a['id']}/executar", headers=h,
                   json={"entrada": {"lojista_id": "L1001", "pergunta": "prazo?"}}).json()
    assert exe["status"] == "escalada"
    cont = api.get("/api/v1/notificacoes/contagem", headers=h).json()
    assert cont == {"nao_lidos": 1, "criticos": 1}
    al = api.get("/api/v1/alertas", headers=h).json()[0]
    assert al["regra"] == "conector_fora" and not al["lido"]
    api.post(f"/api/v1/alertas/{al['id']}/lido", headers=h)
    assert api.get("/api/v1/notificacoes/contagem", headers=h).json()["nao_lidos"] == 0
    assert api.post(f"/api/v1/alertas/{al['id']}/lido", headers=como("carla")).status_code == 404
    saude = api.get("/api/v1/saude/agentes", headers=h).json()
    assert saude[0]["score"]["status"] in ("atencao", "critico") and saude[0]["alertas"]
    det = api.get(f"/api/v1/saude/agentes/{a['id']}", headers=h).json()
    assert {f["id"]: f["falha"] for f in det["ferramentas"]}["consultar_lojista"] == "fora_do_ar"
    con = {c["id"]: c for c in api.get("/api/v1/saude/conectores", headers=h).json()}
    assert con["consultar_lojista"]["status"] == "fora" and con["buscar_politica"]["status"] == "ok"
