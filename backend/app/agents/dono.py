"""Dono de um ciclo de vida e de uma execução: o que foi versionado, publicado e executado.

Até a v7 o dono era sempre um agente. Na v8 há dois tipos: o AGENTE (um trabalhador de IA reutilizável) e o
PROCESSO (um fluxo de blocos que usa agentes, plugins e aprovações). O ciclo de vida (rascunho -> revisão ->
publicado <-> pausado -> depreciado, versões imutáveis, quatro olhos, pausa de emergência, trilha encadeada) e o
runtime dos passos são os mesmos para os dois: cada tipo só diz COMO se avalia e se compara o seu blueprint.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

AGENTE = "agente"
PROCESSO = "processo"


@dataclass(frozen=True)
class Dono:
    """Referência ao dono de uma execução: tipo, id e versão que rodou."""
    tipo: str
    id: str
    versao: int | None = None


@dataclass(frozen=True)
class TipoDono:
    """Tudo o que muda de um tipo de dono para o outro; o resto do ciclo de vida é comum."""
    nome: str                                 # "agente" | "processo" (também prefixo dos eventos de auditoria)
    entidade: type                            # tabela do dono
    versao_cls: type                          # tabela das versões
    fk: str                                   # coluna da versão que aponta para o dono
    modelo: type                              # pydantic do blueprint
    slug_padrao: str
    # ganchos (cada um recebe a sessão porque o processo precisa resolver os agentes que usa)
    risco: Callable[..., Any]                 # (s, bp) -> Risco
    sem_permissao: Callable[..., dict]        # (s, pessoa, bp) -> {ferramenta: motivo}
    comparar: Callable[..., list]             # (antes_dict|None, depois_dict) -> mudanças
    ferramentas_novas: Callable[..., set]     # (antes_dict|None, depois_dict) -> ferramentas
    executavel: Callable[..., Any]            # (s, pessoa, dono, blueprint_dict) -> Blueprint que o runtime executa
    normalizar: Callable[..., Any] | None = None    # (s, pessoa, bp) -> bp (por padrão só fixa a área)
    extras_criacao: Callable[..., dict] | None = None  # (bp) -> campos extras da entidade
    antes_de_publicar: Callable[..., None] | None = None  # (s, bp) -> levanta ErroCiclo se algo impede a publicação

    @property
    def plural(self) -> str:
        return self.nome + "s"

    @property
    def rotulo(self) -> str:
        return self.nome.capitalize()

    def versao_id(self, dono_id: str, numero: int) -> str:
        return "%s-v%d" % (dono_id, numero)


_TIPOS: dict[str, TipoDono] = {}


def registrar_tipo(t: TipoDono) -> TipoDono:
    _TIPOS[t.nome] = t
    return t


def tipo(nome: str) -> TipoDono:
    if nome not in _TIPOS:   # cada tipo se registra ao ser importado; aqui garante o import na primeira vez
        if nome == AGENTE:
            from . import ciclo as _  # noqa: F401
        elif nome == PROCESSO:
            from ..processos import tipo as _  # noqa: F401
    return _TIPOS[nome]
