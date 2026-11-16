"""Preços, cliente simulado e roteador de modelos."""
import pytest

from app.llm import precos, roteador
from app.llm.cliente import ChamadaFerramenta, RespostaLLM, obter_cliente, simulador


def test_custo_bate_com_a_tabela():
    assert precos.custo_usd("rapido", 50_000, 0) == pytest.approx(50_000 * 0.10 / 1e6)
    assert precos.custo_usd("forte", 1000, 1000) == pytest.approx((1000 * 2 + 1000 * 10) / 1e6)


def test_haiku_acima_de_100_mil_tokens_custa_5x():
    curto = precos.custo_usd("rapido", 100_000, 1000)
    longo = precos.custo_usd("rapido", 100_001, 1000)
    assert longo == pytest.approx((100_001 * 0.50 + 1000 * 2.50) / 1e6)
    assert longo > 4 * curto


def test_cache_barateia_a_entrada():
    sem = precos.custo_usd("forte", 10_000, 0)
    com = precos.custo_usd("forte", 0, 0, tokens_cache_leitura=10_000)
    assert com == pytest.approx(sem / 20)


def test_simulado_estima_tokens_e_respeita_roteiro():
    cli = obter_cliente()
    r = cli.gerar("rapido", "Você ajuda o atendimento.", [{"role": "user", "content": "Oi"}])
    assert r.simulado and r.tokens_entrada > 0 and r.tokens_saida > 0

    def roteiro(chave, sistema, msgs, ferramentas):
        if ferramentas:
            return RespostaLLM(chave, "", chamadas=[ChamadaFerramenta("t1", "consultar_lojista", {"id": "L1"})])
        return None

    simulador().roteiros.insert(0, roteiro)
    try:
        r = cli.gerar("forte", "s", [{"role": "user", "content": "x"}], ferramentas=[{"name": "consultar_lojista"}])
        assert r.parada == "tool_use" and r.chamadas[0].nome == "consultar_lojista"
    finally:
        simulador().roteiros.remove(roteiro)


# ---- Roteador: estes testes são a especificação de escolher_modelo ----
@pytest.mark.parametrize("nivel,cx,tokens,esperado", [
    ("forte", 0.1, 2_000, "forte"),     # o agente pediu o forte: respeita
    ("rapido", 0.9, 2_000, "rapido"),   # o agente pediu o rápido: respeita
    ("auto", 0.2, 2_000, "rapido"),     # passo simples: o mais barato
    ("auto", 0.7, 2_000, "forte"),      # passo complexo: o forte
    ("auto", 0.2, 150_000, "forte"),    # contexto acima do limite do Haiku: sobe
    ("rapido", 0.2, 150_000, "rapido"), # pedido explícito vale mesmo com contexto longo
])
def test_roteador_casos_basicos(nivel, cx, tokens, esperado):
    assert roteador.escolher_modelo(nivel, cx, tokens) == esperado


def test_roteador_guarda_motivos():
    d = roteador.decidir("auto", "Compare as opções e explique os prós e contras", 1_000)
    assert d.chave_modelo in ("rapido", "forte") and d.motivos
