"""Roteador de modelos: o funil do v3, agora aplicado a CADA PASSO de um agente.

No v3, a pergunta inteira parava na camada mais barata que resolvia. No v4, um
agente executa vários passos (classificar, consultar ferramenta, redigir,
decidir...). O roteador escolhe, passo a passo, o modelo mais barato que dá conta.
A lição do documento de custos guia a regra: o modelo forte faz 12% das chamadas
e gera ~92% do custo, então ele só deve entrar quando o passo pede.

O cache de respostas aprovadas (a camada 1 do v3) fica na base de conhecimento do
agente e é consultado antes de qualquer modelo; este módulo cuida das camadas 2 e 3.
"""
from dataclasses import dataclass, field

from ..core import config
from ..texto.semelhanca import complexidade
from . import balanceador, registro
from .balanceador import NIVEL_AUTO


@dataclass
class Decisao:
    chave_modelo: str                 # chave do modelo no registro ("rapido", "forte", "gpt-sol"...)
    complexidade: float
    motivos: list[str] = field(default_factory=list)
    esforco: str | None = None        # leve | moderado | alto | critico
    modo: str = "fixado"              # fixado | normal | economia | delegado | emergencia
    candidatos: list[dict] = field(default_factory=list)
    entrada: dict = field(default_factory=dict, repr=False)   # sinais usados (para decidir de novo ao delegar)

    @property
    def nome_modelo(self) -> str:
        return registro.obter(self.chave_modelo).nome

    def trilha(self) -> dict:
        """"Como o agente decidiu": nível, candidatos, escolhido e motivo (vai no registro do passo)."""
        m = registro.obter(self.chave_modelo)
        return {"esforco": self.esforco, "modo": self.modo, "escolhido": m.chave, "provedor": m.provedor,
                "motivo": self.motivos[-1] if self.motivos else "", "candidatos": self.candidatos}


def escolher_modelo(nivel: str, complexidade: float, tokens_contexto: int) -> str:
    """Escolha simples entre o Claude rápido e o forte (a regra do v4, mantida para os testes e para quem
    só quer a decisão sem o balanceador): devolve "rapido" ou "forte"."""
    if nivel != NIVEL_AUTO:
        return registro.obter(nivel).chave
    limite = registro.obter("rapido").limite_preco_padrao
    if complexidade >= config.COMPLEXIDADE_FORTE or (limite and tokens_contexto > limite):
        return "forte"
    return "rapido"


def decidir(nivel: str, texto_passo: str, tokens_contexto: int, *, n_ferramentas: int = 0, risco: str = "baixo",
            economia: bool = False, so_reais: bool = False, excluir: frozenset[str] | set[str] = frozenset()) -> Decisao:
    """Calcula o esforço do passo e escolhe o modelo, guardando os motivos para a trilha "como o agente decidiu".

    nivel -- o que o blueprint pediu: "auto" (o balanceador decide) ou um modelo do registro (respeitado).
    """
    if nivel != NIVEL_AUTO and not registro.existe(nivel):
        raise ValueError("Nível de modelo inválido: %r" % nivel)
    nota, motivos_texto = complexidade(texto_passo)
    idx, motivos_esforco = balanceador.classificar_esforco(nota, n_ferramentas, tokens_contexto, risco)
    esforco = balanceador.NIVEIS[idx - 1]
    sinais = dict(nivel=nivel, texto_passo=texto_passo, tokens_contexto=tokens_contexto, n_ferramentas=n_ferramentas,
                  risco=risco, economia=economia, so_reais=so_reais)
    cabecalho = ["esforço %s (%s)" % (esforco, ", ".join(motivos_esforco))] + motivos_texto
    if nivel != NIVEL_AUTO:
        m = registro.obter(nivel)
        return Decisao(m.chave, nota, ["o agente pediu o modelo %s" % nivel] + cabecalho, esforco, "fixado", [], sinais)
    e = balanceador.escolher(idx, n_ferramentas=n_ferramentas, tokens_contexto=tokens_contexto, economia=economia,
                             so_reais=so_reais, excluir=excluir)
    return Decisao(e.modelo.chave, nota, cabecalho + ["escolhi %s: %s" % (e.modelo.nome, e.motivo)], esforco, e.modo,
                   e.candidatos, sinais)


def delegar(anterior: Decisao, provedor_que_falhou: str, motivo: str) -> Decisao:
    """O modelo escolhido falhou: decide de novo, sem esse provedor, e registra a delegação."""
    sinais = dict(anterior.entrada)
    excluir = set(sinais.pop("excluir", ())) | {provedor_que_falhou}
    nova = decidir(sinais.pop("nivel"), sinais.pop("texto_passo"), sinais.pop("tokens_contexto"), excluir=excluir, **sinais)
    nova.modo = "delegado" if nova.modo != "emergencia" else nova.modo
    nova.motivos.append("delegado: %s falhou (%s)" % (registro.PROVEDORES[provedor_que_falhou].nome, motivo))
    nova.entrada["excluir"] = sorted(excluir)
    return nova
