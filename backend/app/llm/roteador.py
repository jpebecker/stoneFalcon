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

NIVEIS = ("auto", "rapido", "forte")


@dataclass
class Decisao:
    chave_modelo: str                 # "rapido" | "forte"
    complexidade: float
    motivos: list[str] = field(default_factory=list)

    @property
    def nome_modelo(self) -> str:
        return config.MODELOS[self.chave_modelo]["nome"]


def escolher_modelo(nivel: str, complexidade: float, tokens_contexto: int) -> str:
    """Decide qual modelo atende um passo. Devolve "rapido" ou "forte".

    nivel           -- o que o blueprint do agente pediu para o passo:
                       "auto" (o roteador decide), "rapido" ou "forte".
    complexidade    -- nota de 0 a 1 calculada a partir do texto do passo.
    tokens_contexto -- tamanho estimado do prompt que será enviado neste passo.

    Constantes úteis em config: COMPLEXIDADE_FORTE (0.60) e
    MODELOS["rapido"]["limite_preco_padrao"] (100 mil tokens).
    """
    # Pedido explícito do blueprint é respeitado: comportamento previsível para quem
    # criou o agente e para a revisão de segurança (o custo já aparece no Estúdio).
    if nivel in ("rapido", "forte"):
        return nivel
    # Auto: contexto acima do limite do Haiku indica passo pesado (muito material para
    # sintetizar) e tira boa parte da vantagem de preço dele, então sobe para o forte.
    limite = config.MODELOS["rapido"]["limite_preco_padrao"]
    if complexidade >= config.COMPLEXIDADE_FORTE or (limite and tokens_contexto > limite):
        return "forte"
    return "rapido"


def decidir(nivel: str, texto_passo: str, tokens_contexto: int) -> Decisao:
    """Calcula a complexidade do passo e aplica `escolher_modelo`, guardando os motivos
    para a trilha "como o agente decidiu"."""
    if nivel not in NIVEIS:
        raise ValueError("Nível de modelo inválido: %r" % nivel)
    nota, motivos = complexidade(texto_passo)
    chave = escolher_modelo(nivel, nota, tokens_contexto)
    if nivel != "auto":
        motivos = ["o agente pediu o modelo %s" % nivel] + motivos
    elif tokens_contexto > (config.MODELOS["rapido"]["limite_preco_padrao"] or float("inf")):
        motivos = motivos + ["contexto longo (%d mil tokens)" % (tokens_contexto // 1000)]
    return Decisao(chave_modelo=chave, complexidade=nota, motivos=motivos)
