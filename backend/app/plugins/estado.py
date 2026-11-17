"""Quais plugins estão integrados agora (cache em memória do que está gravado no banco).

Fica separado para o controle de permissão das ferramentas consultar sem depender do banco: `servico.sincronizar`
recarrega este conjunto a partir da tabela (na partida, depois de cada mudança e depois de reiniciar a demo).
"""
INTEGRADOS: set[str] = set()


def integrado(plugin_id: str) -> bool:
    return plugin_id in INTEGRADOS


def zerar() -> None:
    INTEGRADOS.clear()
