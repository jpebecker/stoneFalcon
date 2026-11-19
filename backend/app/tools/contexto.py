"""Tipos simples compartilhados pelas ferramentas (sem depender do catálogo, para os plugins importarem sem ciclo)."""
from __future__ import annotations

from dataclasses import dataclass, field


class ErroFerramenta(Exception):
    """Erro esperado de um conector (entrada inválida, registro não encontrado...)."""


class AcessoNegado(ErroFerramenta):
    """O conector existe e a pessoa pode usá-lo, mas não o dado pedido (por exemplo, um arquivo de outra área): vira "negado"."""


@dataclass
class Contexto:
    """Quem está executando. Ferramentas rodam com as permissões de quem DISPAROU o agente."""
    persona_id: str
    agente_id: str | None = None      # id do dono da execução (agente ou processo)
    dono_tipo: str = "agente"
    execucao_id: str | None = None
    extras: dict = field(default_factory=dict)
