"""Vitrine de plugins homologados: leitura do catálogo (as definições estão em `definicoes.py`).

Importe `tools.catalogo` antes deste módulo, direta ou indiretamente (este módulo já faz isso), para o registro das
ferramentas dos plugins no catálogo acontecer na ordem certa.
"""
from __future__ import annotations

from dataclasses import dataclass

from ..core.identidade import Classificacao, Persona
from ..tools.catalogo import CATALOGO, TODAS, Especificacao
from .definicoes import VITRINE


@dataclass(frozen=True)
class Plugin:
    id: str
    nome: str
    categoria: str
    categoria_nome: str
    descricao: str
    janela: bool                       # tem uma "janela" simulada do sistema externo (Zendesk, Slack, Jira)
    ferramentas: tuple[Especificacao, ...]
    real: bool = False                 # v8: funciona de verdade (não é um sistema de mentira)
    interno: bool = False              # v8/13: plugin interno criado por um pedido "Crie o seu plugin" (conceitual, simulado)

    @property
    def classificacao(self) -> Classificacao:
        return max(f.classificacao for f in self.ferramentas)

    @property
    def areas(self) -> tuple[str, ...]:
        if any(TODAS in f.areas for f in self.ferramentas):
            return (TODAS,)
        return tuple(sorted({a for f in self.ferramentas for a in f.areas}))

    @property
    def sensivel(self) -> bool:
        """Confidencial ou restrito: integrar passa pela aprovação da Segurança (quatro olhos)."""
        return self.classificacao >= Classificacao.CONFIDENCIAL

    def vale_para(self, pessoa: Persona) -> bool:
        return TODAS in self.areas or pessoa.area in self.areas


PLUGINS: dict[str, Plugin] = {
    v["id"]: Plugin(v["id"], v["nome"], v["categoria"], v["categoria_nome"], v["descricao"], v["janela"],
                    tuple(e for e in CATALOGO.values() if e.plugin == v["id"]), v.get("real", False))
    for v in VITRINE
}


def obter(plugin_id: str) -> Plugin | None:
    return PLUGINS.get(plugin_id)


def usados_por(ferramentas_usadas: set[str]) -> set[str]:
    """Ids dos plugins cujas ferramentas aparecem no conjunto (por exemplo, `blueprint.ferramentas_usadas()`)."""
    return {CATALOGO[f].plugin for f in ferramentas_usadas if f in CATALOGO and CATALOGO[f].plugin}
