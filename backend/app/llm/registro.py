"""Registro único de modelos: provedor, nome, preços, capacidades e se roda de verdade ou é simulado.

Nomes, preços e velocidade de cada modelo vivem SÓ aqui (Finanças, Estúdio, roteador, cliente e telas leem daqui).
As chaves "rapido" e "forte" são as chaves históricas gravadas nas execuções e nos blueprints: continuam valendo como
apelidos do Claude Haiku e do Claude Sonnet, então nada do que já existe precisa ser migrado.

Preços em US$ por milhão de tokens, da tabela pública de cada provedor, com fonte e data da conferência.
Só o Claude roda de verdade (com chave); os demais provedores são SIMULADOS (selo "simulado" em toda tela).
"""
from __future__ import annotations

from dataclasses import dataclass, field

# Níveis de esforço/raciocínio (usados pelo balanceador do v7): do mais leve ao crítico.
ESFORCOS = ("leve", "moderado", "alto", "critico")


@dataclass(frozen=True)
class Capacidades:
    ferramentas: bool        # sabe chamar ferramentas (tool use)
    contexto_longo: bool     # aguenta prompts longos sem sobretaxa de preço
    raciocinio: int          # 1 a 4: o maior nível de esforço (ESFORCOS) que o modelo atende bem


@dataclass(frozen=True)
class Provedor:
    id: str
    nome: str
    real: bool               # False: só simulado (a plataforma não tem cliente real para ele)


@dataclass(frozen=True)
class Modelo:
    chave: str                       # chave canônica gravada nas execuções ("rapido", "forte", ...)
    provedor: str
    nome: str
    id_api: str                      # id que o provedor usa na API
    preco_entrada: float             # US$/milhão de tokens
    preco_saida: float
    preco_cache_leitura: float
    capacidades: Capacidades
    velocidade: tuple[int, int]      # (tokens de saída/s, latência fixa em ms): estima duração no simulador
    fonte_preco: str
    data_preco: str                  # AAAA-MM-DD da conferência
    max_tokens: int = 4096
    limite_preco_padrao: int | None = None    # acima deste tamanho de prompt vale a faixa "longo"
    preco_entrada_longo: float | None = None
    preco_saida_longo: float | None = None
    simulado: bool = False           # True: nunca roda de verdade, mesmo com chave
    esforco_api: str | None = None   # parâmetro de esforço da API (Anthropic)
    reserva_servidor: bool = False   # Anthropic: o servidor refaz a chamada em outro modelo se um classificador recusar
    apelidos: tuple[str, ...] = field(default_factory=tuple)

    @property
    def peso(self) -> float:
        """Custo de referência para ordenar do mais barato ao mais caro (1 milhão de tokens de entrada + 1 de saída)."""
        return self.preco_entrada + self.preco_saida


PROVEDORES: dict[str, Provedor] = {
    "anthropic": Provedor("anthropic", "Anthropic (Claude)", real=True),
    "google": Provedor("google", "Google (Gemini)", real=False),
    "openai": Provedor("openai", "OpenAI (GPT)", real=False),
    "deepseek": Provedor("deepseek", "DeepSeek", real=False),
    "xai": Provedor("xai", "xAI (Grok)", real=False),
}

_FONTE_ANTHROPIC = "tabela oficial de preços da Anthropic"
# Preços dos demais provedores: tabelas públicas conferidas em 17/11/2026 (páginas citadas abaixo). São SIMULADOS:
# o preço só alimenta a contabilidade e o balanceador. Confira de novo na véspera da apresentação.
_FONTE_GOOGLE = "https://ai.google.dev/gemini-api/docs/pricing (camada paga, padrão)"
_FONTE_OPENAI = "https://developers.openai.com/api/docs/pricing (padrão; faixa longa acima de 272 mil tokens)"
_FONTE_DEEPSEEK = "https://api-docs.deepseek.com/quick_start/pricing/ (tarifa de pico; fora do pico custa metade)"
_FONTE_XAI = "https://docs.x.ai/developers/pricing (faixa longa a partir de 200 mil tokens)"
_DATA_V7 = "2026-11-17"

MODELOS: dict[str, Modelo] = {m.chave: m for m in [
    Modelo(
        chave="rapido", provedor="anthropic", nome="Claude Haiku 5.5", id_api="claude-haiku-5-5",
        preco_entrada=0.10, preco_saida=0.50,
        preco_cache_leitura=0.01,   # estimativa: 10% da entrada (padrão da tabela); conferir
        # Haiku 5.5: o preço acima vale para prompts de até 100 mil tokens (acima disso, 0,50 / 2,50)
        limite_preco_padrao=100_000, preco_entrada_longo=0.50, preco_saida_longo=2.50,
        max_tokens=4096, capacidades=Capacidades(ferramentas=True, contexto_longo=False, raciocinio=2),
        velocidade=(180, 400), fonte_preco=_FONTE_ANTHROPIC, data_preco="2026-11-15",
        esforco_api="low", apelidos=("haiku", "claude-haiku-5-5"),
    ),
    Modelo(
        chave="forte", provedor="anthropic", nome="Claude Sonnet 5.5", id_api="claude-sonnet-5-5",
        preco_entrada=2.00, preco_saida=10.00, preco_cache_leitura=0.10,
        max_tokens=8192, capacidades=Capacidades(ferramentas=True, contexto_longo=True, raciocinio=3),
        velocidade=(70, 900), fonte_preco=_FONTE_ANTHROPIC, data_preco="2026-11-15",
        esforco_api="medium", reserva_servidor=True, apelidos=("sonnet", "claude-sonnet-5-5"),
    ),
    # ---- Google ----
    Modelo(
        chave="gemini-flash-lite", provedor="google", nome="Gemini 3.5 Flash-Lite", id_api="gemini-3.5-flash-lite",
        preco_entrada=0.30, preco_saida=2.50, preco_cache_leitura=0.03, max_tokens=4096,
        capacidades=Capacidades(ferramentas=True, contexto_longo=True, raciocinio=1),
        velocidade=(220, 350), fonte_preco=_FONTE_GOOGLE, data_preco=_DATA_V7, simulado=True,
    ),
    Modelo(
        chave="gemini-carbon", provedor="google", nome="Gemini 4 Carbon", id_api="gemini-4-carbon",
        preco_entrada=2.00, preco_saida=10.00, preco_cache_leitura=0.10, max_tokens=8192,
        capacidades=Capacidades(ferramentas=True, contexto_longo=True, raciocinio=3),
        velocidade=(80, 800), simulado=True, data_preco=_DATA_V7,
        fonte_preco=_FONTE_GOOGLE + "; preço promocional até 30/11/2026 (depois US$ 4,00 / 20,00)",
    ),
    # ---- OpenAI ----
    Modelo(
        chave="gpt-luna", provedor="openai", nome="GPT-6 Luna", id_api="gpt-6-luna",
        preco_entrada=0.10, preco_saida=0.50, preco_cache_leitura=0.01, max_tokens=4096,
        limite_preco_padrao=272_000, preco_entrada_longo=0.20, preco_saida_longo=0.75,
        capacidades=Capacidades(ferramentas=True, contexto_longo=True, raciocinio=2),
        velocidade=(200, 380), fonte_preco=_FONTE_OPENAI, data_preco=_DATA_V7, simulado=True,
    ),
    Modelo(
        chave="gpt-sol", provedor="openai", nome="GPT-6.2 Sol", id_api="gpt-6.2-sol",
        preco_entrada=2.00, preco_saida=10.00, preco_cache_leitura=0.10, max_tokens=8192,
        limite_preco_padrao=272_000, preco_entrada_longo=4.00, preco_saida_longo=15.00,
        capacidades=Capacidades(ferramentas=True, contexto_longo=True, raciocinio=3),
        velocidade=(90, 800), fonte_preco=_FONTE_OPENAI, data_preco=_DATA_V7, simulado=True,
    ),
    Modelo(
        chave="gpt-astra", provedor="openai", nome="GPT-6.2 Astra", id_api="gpt-6.2-astra",
        preco_entrada=8.00, preco_saida=40.00, preco_cache_leitura=0.40, max_tokens=8192,
        limite_preco_padrao=272_000, preco_entrada_longo=16.00, preco_saida_longo=60.00,
        capacidades=Capacidades(ferramentas=True, contexto_longo=True, raciocinio=4),
        velocidade=(60, 1100), fonte_preco=_FONTE_OPENAI, data_preco=_DATA_V7, simulado=True,
    ),
    # ---- DeepSeek ----
    Modelo(
        chave="deepseek-flash", provedor="deepseek", nome="DeepSeek V4.1 Flash", id_api="deepseek-flash",
        preco_entrada=0.30, preco_saida=1.20, preco_cache_leitura=0.006, max_tokens=4096,
        capacidades=Capacidades(ferramentas=True, contexto_longo=True, raciocinio=2),
        velocidade=(150, 500), fonte_preco=_FONTE_DEEPSEEK, data_preco=_DATA_V7, simulado=True,
    ),
    Modelo(
        chave="deepseek-pro", provedor="deepseek", nome="DeepSeek V4 Pro", id_api="deepseek-v4-pro",
        preco_entrada=1.32, preco_saida=3.96, preco_cache_leitura=0.044, max_tokens=8192,
        capacidades=Capacidades(ferramentas=True, contexto_longo=True, raciocinio=3),
        velocidade=(70, 900), fonte_preco=_FONTE_DEEPSEEK, data_preco=_DATA_V7, simulado=True,
    ),
    # ---- xAI ----
    Modelo(
        chave="grok-43", provedor="xai", nome="Grok 4.3", id_api="grok-4.3",
        preco_entrada=1.25, preco_saida=2.50, preco_cache_leitura=0.20, max_tokens=4096,
        limite_preco_padrao=200_000, preco_entrada_longo=2.50, preco_saida_longo=5.00,
        capacidades=Capacidades(ferramentas=True, contexto_longo=True, raciocinio=2),
        velocidade=(130, 550), fonte_preco=_FONTE_XAI, data_preco=_DATA_V7, simulado=True,
    ),
    Modelo(
        chave="grok-47", provedor="xai", nome="Grok 4.7", id_api="grok-4.7",
        preco_entrada=2.00, preco_saida=6.00, preco_cache_leitura=0.50, max_tokens=8192,
        limite_preco_padrao=200_000, preco_entrada_longo=4.00, preco_saida_longo=12.00,
        capacidades=Capacidades(ferramentas=True, contexto_longo=True, raciocinio=3),
        velocidade=(85, 750), fonte_preco=_FONTE_XAI, data_preco=_DATA_V7, simulado=True,
    ),
]}

_APELIDOS = {a: m.chave for m in MODELOS.values() for a in m.apelidos}


def obter(chave: str) -> Modelo:
    """Modelo pela chave canônica ou por um apelido (ex.: "haiku", o id da API)."""
    m = MODELOS.get(chave) or MODELOS.get(_APELIDOS.get(chave, ""))
    if m is None:
        raise KeyError("Modelo desconhecido: %r" % (chave,))
    return m


def existe(chave: str) -> bool:
    return chave in MODELOS or chave in _APELIDOS


def todos() -> list[Modelo]:
    return list(MODELOS.values())


def do_provedor(provedor: str) -> list[Modelo]:
    return [m for m in MODELOS.values() if m.provedor == provedor]


def roda_de_verdade(chave: str) -> bool:
    """Só roda de verdade quem não é simulado e tem provedor com cliente real."""
    m = obter(chave)
    return not m.simulado and PROVEDORES[m.provedor].real


def publico(m: Modelo) -> dict:
    """Retrato do modelo para a API e as telas (nunca duplicado no cliente)."""
    p = PROVEDORES[m.provedor]
    return {
        "chave": m.chave, "nome": m.nome, "provedor": m.provedor, "provedor_nome": p.nome,
        "simulado": not roda_de_verdade(m.chave), "id_api": m.id_api,
        "preco_entrada": m.preco_entrada, "preco_saida": m.preco_saida, "preco_cache_leitura": m.preco_cache_leitura,
        "limite_preco_padrao": m.limite_preco_padrao,
        "capacidades": {"ferramentas": m.capacidades.ferramentas, "contexto_longo": m.capacidades.contexto_longo,
                        "raciocinio": m.capacidades.raciocinio, "esforco_maximo": ESFORCOS[m.capacidades.raciocinio - 1]},
        "fonte_preco": m.fonte_preco, "data_preco": m.data_preco, "apelidos": list(m.apelidos),
    }
