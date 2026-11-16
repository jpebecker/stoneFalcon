"""Diferença entre duas versões de um blueprint, em linguagem de quem revisa."""
from typing import Any

_CAMPOS_TOPO = {"nome": "nome", "objetivo": "objetivo", "instrucoes": "regras da área",
                "campos_entrada": "campos de entrada", "minutos_manual": "tempo manual de referência",
                "limites": "limites de custo"}
_CAMPOS_PASSO = {"titulo": "título", "instrucao": "instrução", "ferramentas": "ferramentas", "modelo": "modelo",
                 "depende_de": "dependências", "ferramenta": "ferramenta", "entrada": "entrada", "tipo": "tipo",
                 "max_iteracoes": "tentativas máximas"}


def comparar(antes: dict[str, Any] | None, depois: dict[str, Any]) -> list[dict]:
    """Lista de mudanças: {tipo: adicionado|removido|alterado, alvo, campo, antes, depois}."""
    if not antes:
        return [{"tipo": "adicionado", "alvo": "agente", "campo": None, "antes": None, "depois": depois.get("nome")}]
    mudancas = []
    for campo, rotulo in _CAMPOS_TOPO.items():
        if antes.get(campo) != depois.get(campo):
            mudancas.append({"tipo": "alterado", "alvo": "agente", "campo": rotulo,
                             "antes": antes.get(campo), "depois": depois.get(campo)})
    pa = {p["id"]: p for p in antes.get("passos", [])}
    pd = {p["id"]: p for p in depois.get("passos", [])}
    for pid in pd.keys() - pa.keys():
        mudancas.append({"tipo": "adicionado", "alvo": "passo:" + pid, "campo": None, "antes": None, "depois": pd[pid]["titulo"]})
    for pid in pa.keys() - pd.keys():
        mudancas.append({"tipo": "removido", "alvo": "passo:" + pid, "campo": None, "antes": pa[pid]["titulo"], "depois": None})
    for pid in sorted(pa.keys() & pd.keys()):
        for campo, rotulo in _CAMPOS_PASSO.items():
            if pa[pid].get(campo) != pd[pid].get(campo):
                mudancas.append({"tipo": "alterado", "alvo": "passo:" + pid, "campo": rotulo,
                                 "antes": pa[pid].get(campo), "depois": pd[pid].get(campo)})
    return mudancas


def ferramentas_novas(antes: dict | None, depois: dict) -> set[str]:
    def usadas(bp):
        s = set()
        for p in (bp or {}).get("passos", []):
            if p.get("ferramenta"):
                s.add(p["ferramenta"])
            s.update(p.get("ferramentas", []))
        return s
    return usadas(depois) - usadas(antes)
