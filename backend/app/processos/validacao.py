"""Validação por bloco, em português, para a tela destacar o que falta em cada bloco enquanto a pessoa monta o fluxo.

Trabalha sobre o dicionário cru (não sobre o modelo validado): um bloco incompleto não esconde os problemas dos outros.
Sem pessoa, só confere o que não depende de quem olha (configuração e ligações): é o que vale ao publicar.
"""
from __future__ import annotations

import re
from typing import Any

from sqlmodel import Session

from ..agents import ciclo
from ..agents import modelos as am
from ..core.identidade import Persona
from ..tools.catalogo import CATALOGO
from ..tools.permissoes import avaliar

_REF = re.compile(r"\{\{\s*([a-z_]+(?:\.[A-Za-z0-9_]+)*)\s*\}\}")


def referencias(valor: Any) -> list[str]:
    if isinstance(valor, str):
        return _REF.findall(valor)
    if isinstance(valor, dict):
        return [r for v in valor.values() for r in referencias(v)]
    if isinstance(valor, list):
        return [r for v in valor for r in referencias(v)]
    return []


def _ancestrais(blocos: dict[str, dict], bid: str) -> set[str]:
    vistos: set[str] = set()
    pilha = list(blocos.get(bid, {}).get("depende_de") or [])
    while pilha:
        d = pilha.pop()
        if d in vistos or d not in blocos:
            continue
        vistos.add(d)
        pilha.extend(blocos[d].get("depende_de") or [])
    return vistos


def problemas_por_bloco(s: Session, pessoa: Persona | None, dados: dict[str, Any]) -> dict[str, list[str]]:
    blocos_l = [b for b in (dados.get("blocos") or []) if isinstance(b, dict) and b.get("id")]
    blocos = {b["id"]: b for b in blocos_l}
    campos = {c.get("id") for c in (dados.get("campos") or []) if isinstance(c, dict)}
    titulo = lambda i: (blocos.get(i) or {}).get("titulo") or i   # noqa: E731
    saida: dict[str, list[str]] = {}

    for b in blocos_l:
        p: list[str] = []
        tipo = b.get("tipo")
        ferr = b.get("ferramenta")
        esp = CATALOGO.get(ferr) if ferr else None

        if tipo == "agente":
            if not b.get("agente_id"):
                p.append("Escolha o agente.")
            else:
                a = s.get(am.Agente, b["agente_id"])
                if a is None:
                    p.append("O agente escolhido não existe mais.")
                elif a.estado == am.DEPRECIADO:
                    p.append("O agente “%s” foi depreciado." % a.nome)
                elif pessoa is not None and not ciclo.pode_executar(pessoa, a):
                    p.append("A sua área não tem acesso ao agente “%s”." % a.nome)
        elif tipo in ("dados", "plugin") or (tipo == "saida" and ferr):
            if not ferr:
                p.append("Escolha a ferramenta (o plugin e a ação).")
            elif esp is None:
                p.append("A ferramenta escolhida não está no catálogo.")
            else:
                if tipo == "dados" and esp.acao != "leitura":
                    p.append("Bloco de dados só lê: para agir em outro sistema, use um bloco de ação.")
                if pessoa is not None:
                    v = avaliar(pessoa, esp)
                    if not v.permitido:
                        p.append(v.motivo)
                entrada = b.get("entrada") or {}
                for nome in esp.obrigatorios:
                    if entrada.get(nome) in (None, ""):
                        p.append("Falta preencher “%s”." % (esp.parametros.get(nome, {}).get("description") or nome))
        elif tipo == "condicao":
            regra = b.get("regra") or {}
            if not regra.get("fonte"):
                p.append("Escolha o que a condição verifica.")
        elif tipo == "saida":
            if not (b.get("texto") or "").strip():
                p.append("Escreva a resposta final ou escolha um aviso a enviar.")
        elif tipo != "aprovacao":
            p.append("Tipo de bloco desconhecido.")

        if "{{?}}" in str(b.get("entrada")) or "{{?}}" in str(b.get("texto")):   # a tela marca "vai ligar a um resultado" mas ainda não escolheu
            p.append("Escolha de onde vem o valor que ficou sem origem.")
        # ligações: só se pode usar o que existe nas entradas ou o resultado de um bloco que vem antes
        ancestrais = _ancestrais(blocos, b["id"])
        regra_fonte = (b.get("regra") or {}).get("fonte")
        fontes = referencias(b.get("entrada")) + referencias(b.get("texto")) + ([regra_fonte] if regra_fonte else [])
        for ref in dict.fromkeys(fontes):
            partes = ref.split(".")
            if partes[0] == "entrada":
                if len(partes) < 2 or partes[1] not in campos:
                    p.append("Usa uma entrada (“%s”) que não existe." % (partes[1] if len(partes) > 1 else ref))
            elif partes[0] == "passos" and len(partes) >= 3 and partes[2] == "saida":
                if partes[1] not in blocos:
                    p.append("Usa o resultado de um bloco que não existe mais.")
                elif partes[1] not in ancestrais:
                    p.append("Usa o resultado de “%s”, que não vem antes deste bloco." % titulo(partes[1]))
            else:
                p.append("Referência inválida (“%s”)." % ref)
        if p:
            saida[b["id"]] = list(dict.fromkeys(p))
    return saida
