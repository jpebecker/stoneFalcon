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


class CampoEntrada(BaseModel):
    """Um campo que a pessoa preenche para rodar o agente. Em linguagem de usuário:
    ninguém digita `lojista_id`; o tipo diz como a tela pergunta (busca por nome, "eu mesmo"...)."""
    id: str = Field(pattern=r"^[a-z0-9_]{1,40}$")
    rotulo: str = Field(min_length=1, max_length=80)
    tipo: Literal["texto", "texto_longo", "lojista", "colaborador", "opcao"] = "texto"
    exemplo: str = Field(default="", max_length=300)
    ajuda: str = Field(default="", max_length=300)
    opcoes: list[str] = Field(default_factory=list)   # só para tipo "opcao"


_TEXTOS_LONGOS = {"pergunta", "relato", "tema", "consulta", "descricao", "texto", "mensagem"}
_ROTULOS = {
    "lojista_id": ("Lojista", "lojista", "", "Escolha o lojista pelo nome."),
    "colaborador_id": ("Colaborador", "colaborador", "", "Você mesmo, ou outra pessoa se o seu perfil permitir."),
    "pergunta": ("Pergunta", "texto_longo", "Qual o prazo de estorno de uma venda no débito?", ""),
    "relato": ("Relato do caso", "texto_longo", "A maquininha parou de ligar ontem.", ""),
    "tema": ("Tema", "texto", "Prazo de estorno", ""),
    "destino": ("Destino do aviso", "texto", "#time-atendimento", "Canal (#nome) ou e-mail."),
}


def campo_a_partir_do_id(cid: str) -> "CampoEntrada":
    """Converte um nome técnico antigo (`lojista_id`) num campo com rótulo e tipo."""
    rotulo, tipo, exemplo, ajuda = _ROTULOS.get(
        cid, (cid.replace("_", " ").capitalize(), "texto_longo" if cid in _TEXTOS_LONGOS else "texto", "", ""))
    return CampoEntrada(id=cid, rotulo=rotulo, tipo=tipo, exemplo=exemplo, ajuda=ajuda)


class Limites(BaseModel):
    max_custo_brl: float = Field(default=2.0, gt=0)     # por execução
    max_chamadas_modelo: int = Field(default=20, ge=1, le=100)


class Blueprint(BaseModel):
    nome: str = Field(min_length=3, max_length=80)
    objetivo: str = Field(min_length=3, max_length=600)
    area: str
    instrucoes: str = ""                     # tom, regras de negócio da área, o que nunca fazer
    campos: list[CampoEntrada] = Field(default_factory=list)
    passos: list[Passo] = Field(min_length=1, max_length=20)
    limites: Limites = Field(default_factory=Limites)
    minutos_manual: float = Field(default=10, ge=0)   # tempo da tarefa feita à mão (linha de base do ROI)

    @model_validator(mode="before")
    @classmethod
    def _aceita_formato_antigo(cls, dados):
        """Versões já gravadas (e blueprints de modelos) trazem `campos_entrada: [ids]`: viram `campos`."""
        if isinstance(dados, dict) and "campos_entrada" in dados:
            dados = dict(dados)
            antigos = dados.pop("campos_entrada") or []
            if not dados.get("campos"):
                dados["campos"] = [campo_a_partir_do_id(c) if isinstance(c, str) else c for c in antigos]
        return dados

    @model_validator(mode="after")
    def _valida_grafo(self):
        ids_campos = [c.id for c in self.campos]
        if len(set(ids_campos)) != len(ids_campos):
            raise ValueError("Há campos de entrada com o mesmo id.")
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

    def ids_campos(self) -> list[str]:
        return [c.id for c in self.campos]

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
