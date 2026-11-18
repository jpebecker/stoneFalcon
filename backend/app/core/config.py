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
# Moram em app/llm/registro.py (registro único: provedor, preços, capacidades, simulado ou real).

# ---------- Roteador ----------
COMPLEXIDADE_FORTE = 0.60   # a partir daqui um passo "auto" vai ao modelo forte


# No modo real, se o modelo falhar (rede, limite, chave), o passo usa a resposta pré-determinada
# do roteiro em vez de escalar. Desligue com STONEFALCON_RESERVA=0.
RESERVA_SIMULADA = os.environ.get("STONEFALCON_RESERVA", "1") != "0"

# Modo demonstração: qualquer perfil pode reiniciar a plataforma por um roteiro (isso APAGA o banco, inclusive a
# trilha de auditoria). Em qualquer ambiente que não seja de apresentação, defina STONEFALCON_DEMO=0: só o CoE reinicia.
MODO_DEMO = os.environ.get("STONEFALCON_DEMO", "1") != "0"
