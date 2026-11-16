"""Blueprint: a definição de um agente, no formato que o Estúdio gera e o runtime executa.

Um agente é um grafo de passos (DAG). Passos sem dependência entre si rodam em
paralelo; os demais esperam os passos de que dependem. Três tipos de passo:

  - "ferramenta": chama um conector do catálogo com entrada montada por modelo
                  ({{entrada.campo}} ou {{passos.ID.saida.campo}}). Determinístico, sem IA.
  - "agente":     loop de raciocínio (pensa -> chama ferramenta -> observa -> decide)
                  com as ferramentas permitidas no passo e o modelo escolhido pelo roteador.
  - "aprovacao":  pausa a execução até um humano confirmar.

O criador não escreve código: o Estúdio monta este objeto a partir da descrição
do processo, e o canvas só reorganiza os passos.
"""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

from ..tools.catalogo import CATALOGO


class Passo(BaseModel):
    id: str = Field(pattern=r"^[a-z0-9_]{1,40}$")
    titulo: str = Field(min_length=1, max_length=120)
    tipo: Literal["ferramenta", "agente", "aprovacao"]
    depende_de: list[str] = Field(default_factory=list)
    # tipo "agente"
    instrucao: str = ""
    ferramentas: list[str] = Field(default_factory=list)
    modelo: Literal["auto", "rapido", "forte"] = "auto"
    max_iteracoes: int = Field(default=6, ge=1, le=15)
    # tipo "ferramenta"
    ferramenta: str | None = None
    entrada: dict[str, Any] = Field(default_factory=dict)


class Limites(BaseModel):
    max_custo_brl: float = Field(default=2.0, gt=0)     # por execução
    max_chamadas_modelo: int = Field(default=20, ge=1, le=100)


class Blueprint(BaseModel):
    nome: str = Field(min_length=3, max_length=80)
    objetivo: str = Field(min_length=3, max_length=600)
    area: str
    instrucoes: str = ""                     # tom, regras de negócio da área, o que nunca fazer
    campos_entrada: list[str] = Field(default_factory=list)
    passos: list[Passo] = Field(min_length=1, max_length=20)
    limites: Limites = Field(default_factory=Limites)
    minutos_manual: float = Field(default=10, ge=0)   # tempo da tarefa feita à mão (linha de base do ROI)

    @model_validator(mode="after")
    def _valida_grafo(self):
        ids = [p.id for p in self.passos]
        if len(set(ids)) != len(ids):
            raise ValueError("Há passos com o mesmo id.")
        for p in self.passos:
            for d in p.depende_de:
                if d not in ids:
                    raise ValueError("O passo %s depende de %s, que não existe." % (p.id, d))
            if p.tipo == "ferramenta":
                if p.ferramenta not in CATALOGO:
                    raise ValueError("O passo %s usa uma ferramenta fora do catálogo: %s." % (p.id, p.ferramenta))
            if p.tipo == "agente":
                if not p.instrucao.strip():
                    raise ValueError("O passo %s precisa de uma instrução." % p.id)
                for f in p.ferramentas:
                    if f not in CATALOGO:
                        raise ValueError("O passo %s usa uma ferramenta fora do catálogo: %s." % (p.id, f))
        self.niveis()   # dispara erro se houver ciclo
        return self

    def passo(self, passo_id: str) -> Passo:
        return next(p for p in self.passos if p.id == passo_id)

    def niveis(self) -> list[list[str]]:
        """Ordem topológica em camadas: cada camada roda em paralelo."""
        pendentes = {p.id: set(p.depende_de) for p in self.passos}
        feitos: set[str] = set()
        camadas = []
        while pendentes:
            prontos = [pid for pid, deps in pendentes.items() if deps <= feitos]
            if not prontos:
                raise ValueError("Os passos formam um ciclo: %s." % ", ".join(sorted(pendentes)))
            ordem = [p.id for p in self.passos if p.id in prontos]   # estável
            camadas.append(ordem)
            feitos.update(ordem)
            for pid in ordem:
                pendentes.pop(pid)
        return camadas

    def ferramentas_usadas(self) -> set[str]:
        usadas = set()
        for p in self.passos:
            if p.ferramenta:
                usadas.add(p.ferramenta)
            usadas.update(p.ferramentas)
        return usadas
