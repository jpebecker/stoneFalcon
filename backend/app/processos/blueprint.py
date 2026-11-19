"""Blueprint do processo: o fluxo de blocos que uma pessoa monta no canvas, sem código.

Blocos (a paleta do Estúdio de Processos):
  - Entradas/gatilho: os campos que a pessoa preenche para rodar (`campos`, no topo do processo);
  - "dados":    lê dados de um plugin integrado (uma ferramenta de leitura);
  - "agente":   usa um agente trabalhador já criado (`agente_id`);
  - "plugin":   executa uma ação de qualquer plugin integrado;
  - "aprovacao": espera a confirmação de um humano;
  - "condicao": uma regra simples sobre a saída de um bloco anterior (igual, contém, maior que), com ramo "sim" e "não";
  - "saida":    avisa alguém (ex.: mensagem no Slack) ou monta a resposta final.

As saídas de um bloco entram em outros por referência (`{{passos.ID.saida.campo}}`, `{{entrada.campo}}`): a tela monta
isso a partir de uma lista, ninguém digita. O processo é compilado para o grafo de passos do runtime (compilar.py).
"""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

from ..agents.blueprint import CampoEntrada, Limites
from ..tools.catalogo import CATALOGO

TIPOS_BLOCO = ("dados", "agente", "plugin", "aprovacao", "condicao", "saida")
NOME_TIPO = {"dados": "Dados", "agente": "Agente", "plugin": "Ação de plugin", "aprovacao": "Aprovação humana",
             "condicao": "Condição", "saida": "Aviso ou resposta final"}
OPERADORES = {"igual": "é igual a", "contem": "contém", "maior": "é maior que"}


class Regra(BaseModel):
    """Regra de um bloco de condição: `fonte` é `entrada.campo` ou `passos.ID.saida[.campo]`."""
    fonte: str = Field(min_length=3, max_length=120)
    operador: Literal["igual", "contem", "maior"] = "igual"
    valor: str = Field(default="", max_length=200)


class Ramo(BaseModel):
    """Este bloco só roda se a condição `condicao` der `valor` ("sim" ou "nao")."""
    condicao: str
    valor: Literal["sim", "nao"]


class Bloco(BaseModel):
    id: str = Field(pattern=r"^[a-z0-9_]{1,40}$")
    tipo: Literal["dados", "agente", "plugin", "aprovacao", "condicao", "saida"]
    titulo: str = Field(min_length=1, max_length=120)
    depende_de: list[str] = Field(default_factory=list)
    ramo: Ramo | None = None
    agente_id: str | None = None                      # tipo "agente"
    ferramenta: str | None = None                     # tipos "dados", "plugin" e "saida" (aviso)
    entrada: dict[str, Any] = Field(default_factory=dict)
    regra: Regra | None = None                        # tipo "condicao"
    texto: str = Field(default="", max_length=2000)   # tipo "saida" sem ferramenta: a resposta final


class ProcessoBlueprint(BaseModel):
    nome: str = Field(min_length=3, max_length=80)
    objetivo: str = Field(min_length=3, max_length=600)
    area: str
    campos: list[CampoEntrada] = Field(default_factory=list)
    blocos: list[Bloco] = Field(min_length=1, max_length=30)
    limites: Limites = Field(default_factory=Limites)
    minutos_manual: float = Field(default=10, ge=0)   # tempo do processo feito à mão (linha de base do ROI)
    roteiro_id: str | None = None                     # roteiro guiado cujo AS IS -> TO BE este processo realiza

    @model_validator(mode="after")
    def _valida_fluxo(self):
        ids_campos = [c.id for c in self.campos]
        if len(set(ids_campos)) != len(ids_campos):
            raise ValueError("Há campos de entrada com o mesmo nome.")
        ids = [b.id for b in self.blocos]
        if len(set(ids)) != len(ids):
            raise ValueError("Há blocos com o mesmo id.")
        for b in self.blocos:
            for d in b.depende_de:
                if d not in ids:
                    raise ValueError("O bloco “%s” depende de um bloco que não existe mais." % b.titulo)
                if d == b.id:
                    raise ValueError("O bloco “%s” não pode esperar por ele mesmo." % b.titulo)
            if b.tipo == "agente" and not b.agente_id:
                raise ValueError("Escolha o agente do bloco “%s”." % b.titulo)
            if b.tipo in ("dados", "plugin"):
                if not b.ferramenta:
                    raise ValueError("Escolha a ferramenta do bloco “%s”." % b.titulo)
                if b.ferramenta not in CATALOGO:
                    raise ValueError("O bloco “%s” usa uma ferramenta que não está no catálogo." % b.titulo)
            if b.tipo == "dados" and b.ferramenta in CATALOGO and CATALOGO[b.ferramenta].acao != "leitura":
                raise ValueError("O bloco “%s” é de dados: use uma ferramenta que só lê. Para agir, use um bloco de ação." % b.titulo)
            if b.tipo == "saida":
                if b.ferramenta and b.ferramenta not in CATALOGO:
                    raise ValueError("O bloco “%s” usa uma ferramenta que não está no catálogo." % b.titulo)
                if not b.ferramenta and not b.texto.strip():
                    raise ValueError("O bloco “%s” precisa de uma mensagem ou de um texto de resposta." % b.titulo)
            if b.tipo == "condicao" and b.regra is None:
                raise ValueError("Defina a regra do bloco “%s”." % b.titulo)
            if b.ramo is not None:
                alvo = next((x for x in self.blocos if x.id == b.ramo.condicao), None)
                if alvo is None or alvo.tipo != "condicao":
                    raise ValueError("O bloco “%s” segue o ramo de uma condição que não existe." % b.titulo)
                if b.ramo.condicao not in b.depende_de:
                    raise ValueError("O bloco “%s” precisa vir depois da condição em que se apoia." % b.titulo)
        self.niveis()   # dispara erro se houver ciclo
        return self

    def bloco(self, bloco_id: str) -> Bloco:
        return next(b for b in self.blocos if b.id == bloco_id)

    def niveis(self) -> list[list[str]]:
        """Camadas em ordem topológica: blocos da mesma camada rodam ao mesmo tempo."""
        pendentes = {b.id: set(b.depende_de) for b in self.blocos}
        feitos: set[str] = set()
        camadas = []
        while pendentes:
            prontos = [bid for bid, deps in pendentes.items() if deps <= feitos]
            if not prontos:
                titulos = ", ".join("“%s”" % self.bloco(i).titulo for i in sorted(pendentes))
                raise ValueError("Os blocos formam um ciclo (um espera pelo outro): %s." % titulos)
            ordem = [b.id for b in self.blocos if b.id in prontos]
            camadas.append(ordem)
            feitos.update(ordem)
            for bid in ordem:
                pendentes.pop(bid)
        return camadas

    def ids_campos(self) -> list[str]:
        return [c.id for c in self.campos]

    def agentes_usados(self) -> list[str]:
        return sorted({b.agente_id for b in self.blocos if b.tipo == "agente" and b.agente_id})

    def ferramentas_diretas(self) -> set[str]:
        return {b.ferramenta for b in self.blocos if b.ferramenta}
