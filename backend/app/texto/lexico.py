"""Léxico em português usado para reconhecer significado sem chamar modelo.

Portado do v3 (funil/config.py). Em produção, esta etapa usaria embeddings.
"""

# Semelhança (0 a 1) entre um texto e um texto de referência.
LIMIAR_BASE = 0.62     # a partir daqui é "a mesma coisa"
LIMIAR_DUVIDA = 0.45   # entre os dois limiares fica a zona de dúvida

TERMOS_DE_ANALISE = [
    "compare", "comparar", "comparacao", "analise", "analisar", "avalie", "avaliar",
    "explique por que", "justifique", "pros e contras", "vantagens e desvantagens",
    "plano", "estrategia", "calcule", "simule", "projete", "cenario", "cenarios",
    "recomende", "priorize", "monte", "elabore", "diagnostico", "sinais de fraude",
    "passo a passo detalhado", "impacto", "riscos",
]

# ---------- Sinônimos (ajudam a camada 1 a reconhecer o significado) ----------
# Expressões: trocadas antes de separar as palavras. Palavras: trocadas depois.
EXPRESSOES = {
    "vale refeicao": "valerefeicao", "vale alimentacao": "valerefeicao", "vr": "valerefeicao",
    "home office": "homeoffice", "trabalho remoto": "homeoffice", "ajuda de custo": "auxilio",
    "plano de saude": "planosaude", "convenio medico": "planosaude", "convenio": "planosaude",
    "demonstrativo de pagamento": "holerite", "contra cheque": "holerite",
    "cartao de credito": "cartao", "venda contestada": "chargeback", "vendas contestadas": "chargeback",
    "que dia": "quando", "qual a data": "quando", "quanto tempo": "prazo", "em quanto tempo": "prazo",
    "passo a passo": "procedimento", "o que fazer": "procedimento", "o que faco": "procedimento",
    "acesso remoto": "acessoremoto",
}
SINONIMOS = {
    "pedir": "solicitar", "peco": "solicitar", "pedido": "solicitar", "requisitar": "solicitar",
    "requerer": "solicitar", "solicitacao": "solicitar", "solicito": "solicitar", "solicita": "solicitar",
    "marcar": "solicitar", "tirar": "solicitar",
    "trocar": "redefinir", "troco": "redefinir", "resetar": "redefinir", "alterar": "redefinir",
    "mudar": "redefinir", "recuperar": "redefinir", "esqueci": "redefinir", "redefino": "redefinir",
    "contracheque": "holerite", "holerites": "holerite",
    "maquina": "maquininha", "pos": "maquininha", "terminal": "maquininha",
    "devolucao": "estorno", "estornar": "estorno", "reembolso": "estorno", "ressarcimento": "estorno",
    "contestacao": "chargeback", "contestacoes": "chargeback", "contestada": "chargeback",
    "computador": "notebook", "pc": "notebook", "maquina": "maquininha",
    "devagar": "lento", "travando": "lento", "lenta": "lento",
    "programa": "software", "aplicativo": "software", "app": "software",
    "permissao": "acesso", "liberacao": "acesso",
    "creditado": "credito", "cai": "credito", "caem": "credito", "entra": "credito",
    "golpe": "fraude", "fraudes": "fraude",
    "coordenador": "coordenacao", "encaminho": "escalar", "encaminhar": "escalar",
    "filho": "dependente", "filha": "dependente", "conjuge": "dependente",
    "colocar": "incluir", "adicionar": "incluir", "incluo": "incluir", "inclusao": "incluir",
    "instalo": "instalar", "baixar": "instalar", "configuro": "configurar", "conectar": "configurar",
    "contato": "canal", "canais": "canal", "suporte": "atendimento",
    "papel": "bobina", "bobinas": "bobina",
    "quebrou": "defeito", "quebrada": "defeito", "estragou": "defeito",
    "demora": "prazo", "leva": "prazo",
}
PALAVRAS_VAZIAS = set(
    """a o as os um uma uns umas de do da dos das em no na nos nas por para pra pro com sem
    e ou que qual quais como onde quem se ao aos me meu minha meus minhas eu ele ela
    voce voces nosso nossa seu sua seus suas este esta isso isto esse essa aquele aquela
    e eh ser sou foi sao esta estou estao tem tenho ter ha mais muito ja so tambem
    posso pode podem devo deve quero queria gostaria preciso precisa faco fazer faz
    favor ola oi bom dia tarde noite obrigado obrigada la aqui ai sobre entre ate
    quando""".split()
) - {"quando"}
