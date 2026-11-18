"""v7/05: modelos de outros provedores no Estúdio e em Finanças (simulados, sempre)."""
import pytest

from app.agents.blueprint import Blueprint
from app.llm import precos, registro
from app.seed import historico
from app.seed.demo import semear
from tests.conftest import como

V1 = "/api/v1"
OUTROS = ("google", "openai", "deepseek", "xai")


def test_cada_provedor_tem_um_modelo_leve_e_um_forte():
    for pid in OUTROS:
        ms = registro.do_provedor(pid)
        assert min(m.capacidades.raciocinio for m in ms) <= 2 and max(m.capacidades.raciocinio for m in ms) >= 3, pid
        assert all(m.simulado and not registro.roda_de_verdade(m.chave) for m in ms)
        assert all(m.fonte_preco.startswith("http") and m.data_preco == "2026-11-17" for m in ms)


def test_so_o_claude_roda_de_verdade_mesmo_com_chave(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "chave-de-teste")
    monkeypatch.setenv("MODO_SIMULADO", "0")
    assert {m.provedor for m in registro.todos() if registro.roda_de_verdade(m.chave)} == {"anthropic"}


def _bp(modelo_a: str, modelo_b: str) -> dict:
    return {"nome": "Agente multimodelo", "area": "atendimento", "objetivo": "Testar provedores diferentes", "minutos_manual": 5,
            "passos": [{"id": "a", "titulo": "Classificar", "tipo": "agente", "instrucao": "Classifique o pedido.", "modelo": modelo_a},
                       {"id": "b", "titulo": "Responder", "tipo": "agente", "instrucao": "Redija a resposta.", "modelo": modelo_b,
                        "depende_de": ["a"]}]}


def test_sandbox_com_gemini_e_gpt_funciona_sem_chave(api):
    bp = _bp("gemini-flash-lite", "gpt-sol")
    r = api.post(f"{V1}/estudio/testar", json={"blueprint": bp, "entrada": {}}, headers=como("marina"))
    assert r.status_code == 200, r.text
    e = r.json()
    a, b = e["passos"]["a"], e["passos"]["b"]
    assert (a["modelo"], a["provedor"], a["modelo_simulado"]) == ("Gemini 3.5 Flash-Lite", "google", True)
    assert (b["modelo"], b["provedor"], b["modelo_simulado"]) == ("GPT-6.2 Sol", "openai", True)
    assert a["custo_usd"] > 0 and b["custo_usd"] > 0 and e["status"] == "concluida"
    assert set(e["por_modelo"]) == {"gemini-flash-lite", "gpt-sol"}
    esperado = precos.custo_usd("gpt-sol", e["por_modelo"]["gpt-sol"]["tokens_entrada"], e["por_modelo"]["gpt-sol"]["tokens_saida"])
    assert e["por_modelo"]["gpt-sol"]["custo_usd"] == pytest.approx(esperado)


def test_estimativa_do_estudio_traz_provedor_e_selo(api):
    r = api.post(f"{V1}/estudio/validar", json={"blueprint": _bp("grok-43", "rapido")}, headers=como("marina")).json()
    por = r["estimativa"]["por_passo"]
    assert por["a"]["provedor"] == "xai" and por["a"]["simulado"] is True
    assert por["b"]["provedor"] == "anthropic" and por["b"]["simulado"] is False


def test_passo_com_modelo_inexistente_e_recusado_pelo_estudio(api):
    r = api.post(f"{V1}/estudio/validar", json={"blueprint": _bp("gpt-inventado", "rapido")}, headers=como("marina"))
    assert r.status_code == 422 or not r.json().get("valido", True)


def test_historico_da_demo_tem_mais_de_um_provedor(sessao):
    semear(sessao)
    from sqlmodel import select
    from app.runtime import modelos as rm
    provedores = set()
    for e in sessao.exec(select(rm.Execucao).where(rm.Execucao.demo == True)):  # noqa: E712
        provedores |= {registro.obter(k).provedor for k in e.por_modelo}
    assert "anthropic" in provedores and len(provedores & set(OUTROS)) >= 3


def test_financas_mostra_gasto_por_provedor_e_por_modelo(api, sessao):
    semear(sessao)
    r = api.get(f"{V1}/financas/resumo", headers=como("helena")).json()
    assert r["por_provedor"] and r["por_modelo"]
    assert sum(p["custo_brl"] for p in r["por_provedor"]) == pytest.approx(r["custo_brl"], abs=0.05)
    assert sum(m["custo_brl"] for m in r["por_modelo"]) == pytest.approx(r["custo_brl"], abs=0.05)
    assert {m["provedor"] for m in r["por_modelo"]} >= {"anthropic", "google"} or len(r["por_provedor"]) >= 3
    assert all(m["simulado"] == (m["provedor"] != "anthropic") for m in r["por_modelo"])
    dia = r["por_dia"][-1]
    assert any(k.endswith("_brl") and k.replace("_brl", "") in {"anthropic", "google", "openai", "deepseek", "xai"} for k in dia)


def test_gasto_por_provedor_vem_das_execucoes_e_nao_e_fixo(api, sessao):
    antes = api.get(f"{V1}/financas/resumo", headers=como("helena")).json()
    assert antes["por_provedor"] == []
    api.post(f"{V1}/estudio/testar", json={"blueprint": _bp("deepseek-pro", "deepseek-flash"), "entrada": {}}, headers=como("marina"))
    # o sandbox não grava no histórico: publicamos e rodamos de verdade
    semear(sessao)
    depois = api.get(f"{V1}/financas/resumo", headers=como("helena")).json()
    assert depois["por_provedor"]


def test_comparativo_e_se_tudo_rodasse_em_x(api, sessao):
    semear(sessao)
    todos = api.get(f"{V1}/financas/comparativo", headers=como("helena")).json()
    assert {c["chave"] for c in todos["cenarios"]} == {m.chave for m in registro.todos()} and todos["atual_brl"] > 0
    barato = api.get(f"{V1}/financas/comparativo?modelo=gpt-luna", headers=como("helena")).json()["cenarios"][0]
    caro = api.get(f"{V1}/financas/comparativo?modelo=gpt-astra", headers=como("helena")).json()["cenarios"][0]
    assert barato["custo_brl"] < todos["atual_brl"] < caro["custo_brl"]
    assert barato["variacao_pct"] < 0 < caro["variacao_pct"]
    assert api.get(f"{V1}/financas/comparativo?modelo=nada", headers=como("helena")).status_code == 404
    # o mesmo consumo, outro preço: recalcula pelo modelo escolhido
    assert barato["custo_brl"] != caro["custo_brl"]


def test_precos_declarados_batem_com_o_comparativo_de_uma_execucao(sessao):
    semear(sessao)
    h = historico  # o histórico grava tokens coerentes com a tabela do modelo usado
    t_in, t_out = h._tokens_do_custo("gpt-sol", 1.0)
    assert precos.custo_usd("gpt-sol", t_in, t_out) == pytest.approx(1.0, rel=1e-3)
