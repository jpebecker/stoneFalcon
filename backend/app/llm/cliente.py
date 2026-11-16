"""Cliente de modelos: real (API da Anthropic) ou simulado (sem chave, sem custo).

Os dois devolvem o mesmo `RespostaLLM`, então o runtime, a auditoria e os custos
funcionam igual nos dois modos. O modo simulado existe para a demo rodar sem
internet; o texto das respostas é de exemplo, mas tokens e custos são estimados
com a mesma régua.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Protocol

from ..core import config
from ..texto.semelhanca import estimar_tokens


class ErroModelo(Exception):
    """Falha ao falar com o modelo, com mensagem pronta para a tela."""


@dataclass
class ChamadaFerramenta:
    id: str
    nome: str
    entrada: dict[str, Any]


@dataclass
class RespostaLLM:
    chave_modelo: str
    texto: str
    chamadas: list[ChamadaFerramenta] = field(default_factory=list)
    tokens_entrada: int = 0
    tokens_saida: int = 0
    tokens_cache_leitura: int = 0
    parada: str = "end_turn"          # end_turn | tool_use | max_tokens | refusal
    simulado: bool = False
    conteudo_bruto: list[Any] = field(default_factory=list)   # para devolver ao modelo no loop


class ClienteLLM(Protocol):
    def gerar(self, chave_modelo: str, sistema: str, mensagens: list[dict],
              ferramentas: list[dict] | None = None, max_tokens: int | None = None) -> RespostaLLM: ...


# =============================================================
# Modo real
# =============================================================
_ESFORCO = {"rapido": "low", "forte": "medium"}


class ClienteAnthropic:
    def __init__(self) -> None:
        import anthropic
        self._anthropic = anthropic
        self._cliente = anthropic.Anthropic(max_retries=2, timeout=60.0)

    def gerar(self, chave_modelo, sistema, mensagens, ferramentas=None, max_tokens=None):
        a = self._anthropic
        m = config.MODELOS[chave_modelo]
        pedido: dict[str, Any] = {
            "model": m["id"],
            "max_tokens": max_tokens or m["max_tokens"],
            # instruções do agente se repetem a cada passo: cache barateia o loop
            "system": [{"type": "text", "text": sistema, "cache_control": {"type": "ephemeral"}}],
            "messages": mensagens,
            "output_config": {"effort": _ESFORCO.get(chave_modelo, "medium")},
        }
        if ferramentas:
            pedido["tools"] = ferramentas
        try:
            if chave_modelo == "forte":
                # Sonnet 5.5: se um classificador de segurança recusar, a API refaz no modelo de reserva
                r = self._cliente.beta.messages.create(
                    betas=["server-side-fallback-2026-07-01"], fallbacks="default", **pedido)
            else:
                r = self._cliente.messages.create(**pedido)
        except a.AuthenticationError:
            raise ErroModelo("A chave da API foi recusada. Confira o arquivo backend/.env.")
        except a.NotFoundError:
            raise ErroModelo("O modelo %s não foi encontrado. Confira app/core/config.py." % m["id"])
        except a.RateLimitError:
            raise ErroModelo("Limite de uso da API atingido. Aguarde um pouco ou confira os créditos.")
        except a.APIStatusError as e:
            raise ErroModelo("A API respondeu com erro %d." % e.status_code)
        except a.APIConnectionError:
            raise ErroModelo("Não foi possível falar com a API. Confira a internet.")

        texto = "".join(b.text for b in r.content if b.type == "text").strip()
        chamadas = [ChamadaFerramenta(b.id, b.name, dict(b.input)) for b in r.content if b.type == "tool_use"]
        uso = r.usage
        return RespostaLLM(
            chave_modelo=chave_modelo, texto=texto, chamadas=chamadas,
            tokens_entrada=int(uso.input_tokens or 0) + int(getattr(uso, "cache_creation_input_tokens", 0) or 0),
            tokens_saida=int(uso.output_tokens or 0),
            tokens_cache_leitura=int(getattr(uso, "cache_read_input_tokens", 0) or 0),
            parada=r.stop_reason or "end_turn", simulado=False, conteudo_bruto=list(r.content),
        )


# =============================================================
# Modo simulado
# =============================================================
Roteiro = Callable[[str, str, list[dict], list[dict] | None], "RespostaLLM | None"]


def _texto_mensagens(mensagens: list[dict]) -> str:
    partes = []
    for msg in mensagens:
        c = msg.get("content")
        if isinstance(c, str):
            partes.append(c)
        elif isinstance(c, list):
            for b in c:
                if isinstance(b, dict):
                    partes.append(str(b.get("text") or b.get("content") or ""))
    return "\n".join(partes)


class ClienteSimulado:
    """Determinístico. Um `roteiro` opcional decide respostas e chamadas de ferramenta
    (o runtime e o Estúdio registram os seus); sem roteiro, devolve um texto de exemplo."""

    def __init__(self) -> None:
        self.roteiros: list[Roteiro] = []

    def registrar_roteiro(self, roteiro: Roteiro) -> None:
        self.roteiros.append(roteiro)

    def gerar(self, chave_modelo, sistema, mensagens, ferramentas=None, max_tokens=None):
        resposta = None
        for roteiro in self.roteiros:
            resposta = roteiro(chave_modelo, sistema, mensagens, ferramentas)
            if resposta is not None:
                break
        if resposta is None:
            nome = config.MODELOS[chave_modelo]["nome"]
            resposta = RespostaLLM(chave_modelo=chave_modelo, texto=(
                "Resposta simulada. Com a chave da API ligada, o %s responderia aqui de verdade. "
                "Tokens e custo desta chamada foram estimados como no modo real." % nome))
        resposta.simulado = True
        resposta.chave_modelo = chave_modelo
        if not resposta.tokens_entrada:
            resposta.tokens_entrada = estimar_tokens(sistema) + estimar_tokens(_texto_mensagens(mensagens)) \
                + sum(estimar_tokens(str(f)) for f in (ferramentas or []))
        if not resposta.tokens_saida:
            resposta.tokens_saida = estimar_tokens(resposta.texto) + sum(
                estimar_tokens(str(c.entrada)) + 10 for c in resposta.chamadas)
        if resposta.chamadas and resposta.parada == "end_turn":
            resposta.parada = "tool_use"
        return resposta


_simulado = ClienteSimulado()
_real: ClienteAnthropic | None = None


def obter_cliente(simulado: bool | None = None) -> ClienteLLM:
    """Cliente do modo atual. `simulado=True` força o simulador (testes, demo gravada)."""
    global _real
    if simulado or (simulado is None and not config.modo_real()):
        return _simulado
    if _real is None:
        _real = ClienteAnthropic()
    return _real


def simulador() -> ClienteSimulado:
    return _simulado
