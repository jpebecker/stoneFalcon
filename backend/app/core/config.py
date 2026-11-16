"""Configuração do StoneFalcon v4.

Tudo o que muda entre ambientes vem de variáveis de ambiente (ou do arquivo .env
na pasta backend/). Premissas de negócio editáveis ficam aqui, com a fonte.
Protótipo acadêmico (UFSC / StoneLab). Nomes, áreas e dados são FICTÍCIOS.
"""
import os
from pathlib import Path

from dotenv import load_dotenv

RAIZ_BACKEND = Path(__file__).resolve().parents[2]
load_dotenv(RAIZ_BACKEND / ".env", override=False)


def _env(nome: str, padrao: str = "") -> str:
    return os.environ.get(nome, padrao).strip()


# ---------- Ambiente ----------
URL_BANCO = _env("STONEFALCON_DB", "sqlite:///" + (RAIZ_BACKEND / "dados" / "stonefalcon.db").as_posix())
ORIGENS_CORS = [o for o in _env("STONEFALCON_CORS", "http://localhost:5173,http://127.0.0.1:5173").split(",") if o]


def modo_real() -> bool:
    """Modelos reais só com chave e sem MODO_SIMULADO=1. Sem chave: simulado, sem custo."""
    return bool(_env("ANTHROPIC_API_KEY")) and _env("MODO_SIMULADO", "0") != "1"


# ---------- Câmbio ----------
# docs/custos-estimados.txt usa R$ 5,52. Confiram a cotação no dia da apresentação.
COTACAO_DOLAR = float(_env("COTACAO_DOLAR", "5.52"))

# ---------- Modelos e preços ----------
# US$ por milhão de tokens, tabela oficial da Anthropic (conferida em 15/11/2026).
# Haiku 5.5: preço vale para prompts de até 100 mil tokens (acima disso, 0,50 / 2,50).
MODELOS = {
    "rapido": {
        "nome": "Claude Haiku 5.5",
        "id": "claude-haiku-5-5",
        "preco_entrada": 0.10,
        "preco_saida": 0.50,
        "preco_cache_leitura": 0.01,   # estimativa: 10% da entrada (padrão da tabela); conferir
        "limite_preco_padrao": 100_000,
        "preco_entrada_longo": 0.50,
        "preco_saida_longo": 2.50,
        "max_tokens": 4096,
    },
    "forte": {
        "nome": "Claude Sonnet 5.5",
        "id": "claude-sonnet-5-5",
        "preco_entrada": 2.00,
        "preco_saida": 10.00,
        "preco_cache_leitura": 0.10,
        "limite_preco_padrao": None,
        "max_tokens": 8192,
    },
}

# ---------- Roteador ----------
COMPLEXIDADE_FORTE = 0.60   # a partir daqui um passo "auto" vai ao modelo forte
