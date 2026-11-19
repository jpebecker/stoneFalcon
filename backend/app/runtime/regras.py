"""Regras dos blocos de condição: igual, contém, maior que. Simples de propósito (quem monta o processo não escreve código)."""
from __future__ import annotations

import json
from typing import Any


class ErroRegra(Exception):
    pass


def _texto(v: Any) -> str:
    return v if isinstance(v, str) else json.dumps(v, ensure_ascii=False)


def _numero(v: Any) -> float:
    if isinstance(v, bool):
        raise ErroRegra("“%s” não é um número." % v)
    if isinstance(v, (int, float)):
        return float(v)
    try:
        return float(str(v).strip().replace(".", "").replace(",", ".") if "," in str(v) else str(v).strip())
    except ValueError:
        raise ErroRegra("“%s” não é um número." % _texto(v)) from None


def avaliar(operador: str, valor: Any, esperado: str) -> bool:
    """`valor` é o que veio do bloco anterior; `esperado` é o que a pessoa escreveu na regra."""
    if operador == "igual":
        try:
            return _numero(valor) == _numero(esperado)
        except ErroRegra:
            return _texto(valor).strip().lower() == esperado.strip().lower()
    if operador == "contem":
        return esperado.strip().lower() in _texto(valor).lower()
    if operador == "maior":
        return _numero(valor) > _numero(esperado)
    raise ErroRegra("Operador desconhecido: %s." % operador)
