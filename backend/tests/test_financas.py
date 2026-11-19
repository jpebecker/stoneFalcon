"""F6: custos, economia do roteador, ROI, orçamento com corte, calculadora e indicadores."""
import pytest
from sqlmodel import select

from app.agents import ciclo
from app.core.identidade import PERSONAS
from app.finance import calculadora, resumo
from app.finance.premissas import Premissas
from app.llm import precos
from app.observability import alertas
from app.runtime import modelos as rm
from app.runtime import motor
from app.seed import historico
from app.seed.agentes_exemplo import DUVIDA_LOJISTA
from app.seed.demo import semear
from app.tools import dados_ficticios, executor
from tests.conftest import como

P = PERSONAS


@pytest.fixture(autouse=True)
def _limpo():
    dados_ficticios.zerar()
    executor.zerar_limites()


def _agente(s):
    a = ciclo.criar(s, P["marina"], DUVIDA_LOJISTA)
    return ciclo.publicar(s, P["marina"], a.id)


def _rodar(s, a, n=1):
    bp = ciclo.blueprint_publicado(s, a)
    return [motor.executar(s, P["marina"], bp, {"lojista_id": "L1001", "pergunta": "estorno?"},
                           agente_id=a.id, versao=a.versao_publicada)[0] for _ in range(n)]


# ---------- o critério de pronto: os números batem com as execuções ----------
def test_numeros_batem_com_as_execucoes_registradas(sessao):
    a = _agente(sessao)
    execs = _rodar(sessao, a, 3)
    r = resumo.resumo(sessao, P["helena"])
    ag = r["por_agente"][0]
    assert ag["execucoes"] == 3 and ag["concluidas"] == 3
    assert ag["custo_brl"] == pytest.approx(precos.usd_para_brl(sum(e.custo_usd for e in execs)), abs=1e-4)
    pr = Premissas()
    assert ag["ganho_brl"] == pytest.approx(3 * (8 - pr.minutos_revisao_humana) / 60 * pr.custo_hora * pr.aproveitamento, abs=0.01)
    # custo por modelo soma o total
    assert sum(m["custo_brl"] for m in r["por_modelo"]) == pytest.approx(r["custo_brl"], abs=0.01)
    assert sum(d["custo_brl"] for d in r["por_dia"]) == pytest.approx(r["custo_brl"], abs=0.01)


def test_por_modelo_e_contrafactual_do_roteador(sessao):
    a = _agente(sessao)
    e = _rodar(sessao, a)[0]
    assert set(e.por_modelo) == {"rapido"} and e.por_modelo["rapido"]["chamadas"] == e.chamadas_modelo
    assert e.custo_tudo_forte_usd == pytest.approx(e.custo_usd * 20, rel=1e-6)   # Haiku custa 1/20 do Sonnet
    assert resumo.resumo(sessao, P["helena"])["economia_roteador_pct"] == pytest.approx(0.95, abs=1e-3)


def test_escalada_nao_gera_ganho(sessao):
    a = _agente(sessao)
    executor.definir_falha(sessao, "consultar_lojista", "erro", "lucas")
    _rodar(sessao, a, 2)
    ag = resumo.resumo(sessao, P["helena"])["por_agente"][0]
    assert ag["execucoes"] == 2 and ag["concluidas"] == 0 and ag["ganho_brl"] == 0


def test_visibilidade_por_area(sessao):
    _agente(sessao)
    assert resumo.resumo(sessao, P["carla"])["por_agente"] == []
    assert len(resumo.resumo(sessao, P["helena"])["por_agente"]) == 1


# ---------- orçamento ----------
def test_orcamento_alerta_em_80_e_corta_em_100(sessao, monkeypatch):
    a = _agente(sessao)
    _rodar(sessao, a)
    assert resumo.gasto_no_mes(sessao, a.id) > 0
    gasto = {"v": 85.0}
    monkeypatch.setattr(resumo, "gasto_no_mes", lambda s, agente_id: gasto["v"])
    ciclo.definir_orcamento(sessao, P["helena"], a.id, 100)
    alertas.avaliar(sessao)
    al = [x for x in sessao.exec(select(alertas.Alerta)) if x.regra == "orcamento"]
    assert al and al[0].severidade == alertas.ATENCAO and "85%" in al[0].detalhe
    gasto["v"] = 100.0
    with pytest.raises(ciclo.ErroCiclo, match="orçamento do mês") as e:
        ciclo.checar_execucao(sessao, P["marina"], a.id)
    assert e.value.status == 402
    alertas.avaliar(sessao)
    al = [x for x in sessao.exec(select(alertas.Alerta)) if x.regra == "orcamento"][0]
    assert al.severidade == alertas.CRITICO
    with pytest.raises(ciclo.ErroCiclo, match="dono"):
        ciclo.definir_orcamento(sessao, P["lucas"], a.id, 1000)


# ---------- calculadora ----------
def test_calculadora_coerente():
    pr = Premissas(incluir_modulos=False, adocao_alvo=0.25, meses_rampa=1, tarefas_por_usuario_dia=1, meses=12)
    r = calculadora.projetar(pr)
    execs = 6000 * 0.25 * 22
    assert r["meses"][0]["execucoes"] == round(execs)
    fluxo = execs * pr.ganho_por_tarefa - execs * pr.custo_por_execucao - pr.custo_fixo_mensal
    assert r["meses"][0]["fluxo"] == pytest.approx(fluxo, abs=0.01)
    assert r["payback_mes"] == int(-(-690_000 // fluxo))
    assert r["tir_anual"] > 0 and r["vpl"] > 0


def test_tir_e_ponto_de_equilibrio():
    assert calculadora.tir([-100, 110]) == pytest.approx(0.10, abs=1e-6)
    assert calculadora.tir([100, 100]) is None
    pr = Premissas()
    assert calculadora.ponto_de_equilibrio(pr) == round(pr.custo_fixo_mensal / (pr.ganho_por_tarefa - pr.custo_por_execucao))
    assert calculadora.ponto_de_equilibrio(Premissas(custo_hora=0)) is None


def test_sem_adocao_nao_ha_payback():
    r = calculadora.projetar(Premissas(adocao_alvo=0))
    assert r["payback_mes"] is None and r["vpl"] < 0


# ---------- histórico de demonstração e indicadores ----------
def test_historico_demo_marcado_e_removivel(sessao):
    semear(sessao)
    demo = sessao.exec(select(rm.Execucao).where(rm.Execucao.demo == True)).all()  # noqa: E712
    assert len(demo) > 200 and all(e.simulado for e in demo)
    assert resumo.resumo(sessao, P["helena"])["tem_demo"]
    assert alertas.avaliar(sessao)["abertos"] == []   # demo começa sem alerta
    assert historico.apagar(sessao) == len(demo)


def test_indicadores_da_banca(sessao):
    semear(sessao)
    i = resumo.indicadores(sessao, P["helena"])
    assert 0 < i["tempo_execucao"]["agente_min"] < i["tempo_execucao"]["manual_min"]
    assert i["custo_operacional"]["agente_brl"] < i["custo_operacional"]["manual_brl"]
    assert i["produtividade"]["tarefas_concluidas"] > 0 and i["produtividade"]["agentes_ativos"] == 4
    assert 0 < i["taxa_erros"]["agente"] < 0.2
    assert i["roi"]["projecao_payback_mes"] is not None


def test_api_financas(api):
    h = como("helena")
    assert api.post("/api/v1/demo/historico", headers=como("marina")).status_code == 403
    assert api.get("/api/v1/financas/resumo", headers=h).json()["execucoes"] == 0
    r = api.post("/api/v1/financas/calculadora", json={"adocao_alvo": 0.1}, headers=h).json()
    assert len(r["meses"]) == 36 and "ponto_de_equilibrio_execucoes_mes" in r
    assert api.post("/api/v1/financas/calculadora", json={"adocao_alvo": 2}, headers=h).status_code == 422
    assert "custo_hora" in api.get("/api/v1/financas/premissas", headers=h).json()["descricoes"]
    assert set(api.get("/api/v1/financas/indicadores", headers=h).json()) >= {
        "tempo_execucao", "custo_operacional", "produtividade", "taxa_erros", "roi"}


def test_premissas_trazem_medidas_e_demo_reinicia(api):
    h = como("helena")
    assert api.get("/api/v1/financas/premissas", headers=h).json()["medidas"] == {}
    assert api.post("/api/v1/demo/reiniciar", headers=como("marina")).status_code == 403
    assert api.post("/api/v1/demo/reiniciar", headers=h).json()["ok"]
    p = api.get("/api/v1/financas/premissas", headers=h).json()
    assert p["medidas"]["minutos_por_tarefa"] > 0 and p["medidas_demo"]
    assert len(api.get("/api/v1/agentes", headers=h).json()) == 4
    assert api.get("/api/v1/auditoria/verificar", headers=h).json()["integra"]


# ---------- v8/08: custo e ROI por processo, com o detalhe dos agentes dentro dele ----------
def test_financas_por_processo_com_detalhe_por_agente(sessao):
    semear(sessao)
    r = resumo.resumo(sessao, P["helena"])
    processos = [x for x in r["por_agente"] if x["tipo"] == "processo"]
    assert len(processos) == 4 and all(x["execucoes"] > 0 and x["custo_brl"] > 0 and x["ganho_brl"] > 0 for x in processos)
    triagem = next(x for x in processos if x["nome"] == "Triagem de chargebacks")
    assert [a["nome"] for a in triagem["agentes"]] == ["Analista de risco de chargebacks"]
    assert 0 < triagem["agentes"][0]["execucoes"] <= triagem["execucoes"]       # escaladas antes do agente não contam nele
    assert triagem["agentes"][0]["custo_brl"] == pytest.approx(triagem["custo_brl"], rel=0.02)      # o agente carrega o custo do processo
    assert sum(x["custo_brl"] for x in r["por_agente"]) == pytest.approx(r["custo_brl"], abs=0.01)   # nada contado duas vezes


def test_financas_o_que_seria_se_tudo_rodasse_em_x_inclui_processos(sessao):
    semear(sessao)
    c = resumo.comparativo(sessao, P["helena"], 30)
    r = resumo.resumo(sessao, P["helena"], 30)
    assert c["execucoes"] == r["execucoes"] and c["atual_brl"] == pytest.approx(r["custo_brl"], abs=0.01)


def test_financas_cada_um_ve_so_os_processos_da_sua_area(sessao):
    semear(sessao)
    nomes = {x["nome"] for x in resumo.resumo(sessao, P["marina"])["por_agente"]}
    assert "Resposta a dúvidas de lojistas" in nomes and "Triagem de chargebacks" not in nomes


def test_orcamento_do_processo(api, sessao):
    semear(sessao)
    h = como("helena")
    pid = next(p["id"] for p in api.get("/api/v1/processos", headers=h).json() if p["nome"] == "Triagem de chargebacks")
    assert api.put(f"/api/v1/processos/{pid}/orcamento", json={"valor_brl": 150}, headers=h).json()["orcamento_mensal_brl"] == 150
    assert api.put(f"/api/v1/processos/{pid}/orcamento", json={"valor_brl": 1}, headers=como("marina")).status_code == 403
    linha = next(x for x in api.get("/api/v1/financas/resumo", headers=h).json()["por_agente"] if x["id"] == pid)
    assert linha["orcamento_mensal_brl"] == 150 and linha["tipo"] == "processo"
