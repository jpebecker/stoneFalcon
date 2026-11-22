"""Galeria de padrões do Estúdio (v8): cada padrão é um agente TRABALHADOR (um passo) e o PROCESSO pronto que o usa.

Vêm do catálogo da demo (seed/catalogo.py), a fonte única: um padrão por entrada, com os exemplos de como uma pessoa
descreveria o processo. Servem a dois propósitos:
  - no modo simulado, o Estúdio escolhe o padrão mais parecido com a descrição;
  - no modo real, são o exemplo que orienta o modelo (um trabalhador de um passo).
"""
from ..agents.blueprint import Blueprint
from ..seed.catalogo import DEMOS, TRABALHADORES, processo


def _trabalhador(chave: str) -> dict:
    """O trabalhador do padrão, com as entradas e o tempo manual do processo (para testar no sandbox do Estúdio)."""
    p = processo(chave, chave)
    base = {**TRABALHADORES[chave].model_dump(), "campos": p["campos"], "minutos_manual": p["minutos_manual"]}
    return Blueprint.model_validate(base).model_dump()


PADROES = [
    {
        "id": d.padrao,
        "chave": d.chave,
        "titulo": d.nome_processo,
        "area": d.area,
        "exemplos": list(d.exemplos),
        "blueprint": _trabalhador(d.chave),
    }
    for d in DEMOS.values()
]


def por_id(padrao_id: str) -> dict | None:
    return next((p for p in PADROES if p["id"] == padrao_id), None)
