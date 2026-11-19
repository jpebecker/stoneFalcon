"""Arquivos do estado inicial da demo para o plugin Arquivos e Planilhas (o REAL). Dados fictícios.

Cada persona tem um uso de verdade (v8/11); aqui ficam os arquivos e quem pode usá-los. O plugin nasce integrado, para os
processos da demo já poderem usar o bloco "Arquivos e Planilhas".
"""
from __future__ import annotations

from sqlmodel import Session

from ..core.identidade import Classificacao, PERSONAS
from ..plugins import arquivos
from ..plugins import servico as plugins

I, C, R = int(Classificacao.INTERNA), int(Classificacao.CONFIDENCIAL), int(Classificacao.RESTRITA)

# (nome, quem envia, classificação, áreas, colunas, linhas)
FAQ_COLUNAS = ["assunto", "pergunta", "resposta", "prazo"]
FAQ = [
    ("Estorno", "Em quanto tempo o estorno cai para o cliente?", "O estorno de venda no crédito aparece na fatura em até 2 faturas; no débito, em até 5 dias úteis.", "5 dias úteis"),
    ("Estorno", "Posso estornar uma venda de outro mês?", "Sim, até 90 dias da data da venda, pelo aplicativo ou pelo atendimento.", "90 dias"),
    ("Taxas", "Como a taxa de antecipação é calculada?", "A taxa de antecipação depende do prazo e do plano do lojista; a simulação aparece antes de confirmar.", "imediato"),
    ("Maquininha", "Minha maquininha não liga, o que faço?", "Conecte o carregador original por 30 minutos; se não ligar, abra a troca pelo atendimento.", "2 dias úteis"),
    ("Maquininha", "Como troco o modelo da minha maquininha?", "A troca por defeito é gratuita até 12 meses depois da entrega; a troca de modelo tem custo do plano.", "3 dias úteis"),
    ("Repasse", "Quando recebo o repasse das vendas?", "O repasse acontece no dia útil seguinte para o débito e conforme o plano para o crédito.", "1 dia útil"),
    ("Contestação", "O que é uma contestação?", "É quando o portador do cartão não reconhece a compra; o lojista tem 10 dias para enviar a defesa.", "10 dias"),
    ("Conta", "Como altero os dados do meu cadastro?", "No aplicativo, em Conta > Dados cadastrais; mudança de CNPJ pede documento pelo atendimento.", "1 dia útil"),
]

ARQUIVOS = [
    ("faq-atendimento.csv", "marina", I, ["atendimento", "logistica"], FAQ_COLUNAS,
     [dict(zip(FAQ_COLUNAS, linha)) for linha in FAQ]),
]


def semear(s: Session) -> None:
    """Integra o plugin (como a Marina, que é criadora) e cria os arquivos da demo, marcados para a limpeza do reinício."""
    try:
        plugins.integrar(s, PERSONAS["marina"], arquivos.PLUGIN_ID, "Estado inicial da demonstração.")
    except plugins.ErroPlugin:
        pass
    for nome, dono, classificacao, areas, colunas, linhas in ARQUIVOS:
        arquivos.criar_pelo_sistema(s, PERSONAS[dono], nome, colunas, linhas, classificacao, areas, demo=True)
