"""Diferença entre duas versões de um processo, em linguagem de quem revisa (mesmo formato do diff de agentes)."""
from typing import Any

_TOPO = {"nome": "nome", "objetivo": "objetivo", "campos": "campos de entrada", "minutos_manual": "tempo manual de referência",
         "limites": "limites de custo", "roteiro_id": "processo AS IS ligado"}
_BLOCO = {"titulo": "título", "tipo": "tipo", "agente_id": "agente", "ferramenta": "ferramenta", "entrada": "entrada",
          "depende_de": "dependências", "regra": "regra", "ramo": "ramo", "texto": "texto"}


def _norm(bp: dict | None) -> dict | None:
    if not bp:
        return bp
    from .blueprint import ProcessoBlueprint
    try:
        return ProcessoBlueprint.model_validate(bp).model_dump()
    except Exception:
        return bp


def comparar(antes: dict[str, Any] | None, depois: dict[str, Any]) -> list[dict]:
    antes, depois = _norm(antes), _norm(depois)
    if not antes:
        return [{"tipo": "adicionado", "alvo": "processo", "campo": None, "antes": None, "depois": depois.get("nome")}]
    mudancas = []
    for campo, rotulo in _TOPO.items():
        if antes.get(campo) != depois.get(campo):
            mudancas.append({"tipo": "alterado", "alvo": "processo", "campo": rotulo, "antes": antes.get(campo), "depois": depois.get(campo)})
    ba = {b["id"]: b for b in antes.get("blocos", [])}
    bd = {b["id"]: b for b in depois.get("blocos", [])}
    for bid in [i for i in bd if i not in ba]:
        mudancas.append({"tipo": "adicionado", "alvo": "bloco:" + bid, "campo": None, "antes": None, "depois": bd[bid]["titulo"]})
    for bid in [i for i in ba if i not in bd]:
        mudancas.append({"tipo": "removido", "alvo": "bloco:" + bid, "campo": None, "antes": ba[bid]["titulo"], "depois": None})
    for bid in [i for i in bd if i in ba]:
        for campo, rotulo in _BLOCO.items():
            if ba[bid].get(campo) != bd[bid].get(campo):
                mudancas.append({"tipo": "alterado", "alvo": "bloco:" + bid, "campo": rotulo,
                                 "antes": ba[bid].get(campo), "depois": bd[bid].get(campo)})
    return mudancas


def ferramentas_novas(antes: dict | None, depois: dict) -> set[str]:
    def usadas(bp):
        return {b["ferramenta"] for b in (bp or {}).get("blocos", []) if b.get("ferramenta")}
    return usadas(depois) - usadas(antes)
