"""Custo de cada chamada, a partir dos tokens que a API (ou o simulador) reporta."""
from ..core import config


def custo_usd(chave_modelo: str, tokens_entrada: int, tokens_saida: int, tokens_cache_leitura: int = 0) -> float:
    """US$ de uma chamada. `tokens_entrada` NÃO inclui os lidos do cache.

    No Haiku 5.5, se o prompt inteiro passa de 100 mil tokens, a chamada toda
    é cobrada na faixa longa (5x). Por isso o roteador olha o tamanho do contexto.
    """
    m = config.MODELOS[chave_modelo]
    p_in, p_out = m["preco_entrada"], m["preco_saida"]
    limite = m.get("limite_preco_padrao")
    if limite and (tokens_entrada + tokens_cache_leitura) > limite:
        p_in, p_out = m["preco_entrada_longo"], m["preco_saida_longo"]
    return (tokens_entrada * p_in + tokens_saida * p_out + tokens_cache_leitura * m["preco_cache_leitura"]) / 1_000_000


def usd_para_brl(valor_usd: float) -> float:
    return valor_usd * config.COTACAO_DOLAR
