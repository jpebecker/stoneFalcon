"""Portado do v3: reconhecer a mesma pergunta escrita de outro jeito (e não confundir
perguntas quase iguais). Esse motor serve à base de conhecimento dos agentes e ao
Estúdio no modo simulado."""
import pytest

from app.seed.conhecimento import BASE_INICIAL
from app.texto import lexico
from app.texto.semelhanca import Indice, complexidade


def _indice(agente):
    return Indice([{"id": "%s-%d" % (agente, i), **it} for i, it in enumerate(BASE_INICIAL[agente])])


DEVE = [
    ("rh", p) for p in ["Como faço para pedir férias?", "Quero marcar minhas férias", "que dia cai o VR",
                        "Onde vejo meu contracheque?", "Como coloco meu filho no plano de saúde?",
                        "como pedir auxilio creche", "Como baixo meu holerite?"]
] + [
    ("ti", p) for p in ["esqueci a senha", "Como faço pra resetar minha senha?", "como instalar a vpn",
                        "meu computador está muito lento", "Como instalar um programa novo?"]
] + [
    ("atendimento", p) for p in ["quanto tempo demora o estorno no cartão?", "A maquininha do lojista quebrou, como troca?",
                                 "lojista recebeu chargeback, o que fazer?", "como o lojista pede bobina?"]
] + [
    ("risco", p) for p in ["chegou uma denúncia de fraude, qual o procedimento?", "que documentos pedir em cadastro suspeito?"]
]

NAO_DEVE = [
    ("rh", p) for p in ["Posso vender minhas férias?", "Como solicito licença maternidade?", "Qual o valor do vale-refeição?",
                        "Como incluo um dependente no imposto de renda?", "Qual o valor do auxílio creche?"]
] + [
    ("ti", p) for p in ["Qual a diferença entre a VPN e o acesso remoto?", "A VPN funciona no celular?", "A senha da VPN expira?"]
] + [
    ("atendimento", p) for p in ["A maquininha funciona no exterior?", "Qual o prazo de antecipação de uma venda no cartão?",
                                 "Qual o prazo de estorno no pix?", "A maquininha funciona sem internet?"]
] + [
    ("risco", p) for p in ["O que é um chargeback?", "O que caracteriza uma conta laranja?"]
]


@pytest.mark.parametrize("agente,pergunta", DEVE)
def test_reconhece_mesma_pergunta(agente, pergunta):
    assert _indice(agente).buscar(pergunta, 1)[0]["nota"] >= lexico.LIMIAR_BASE


@pytest.mark.parametrize("agente,pergunta", NAO_DEVE)
def test_nao_confunde_pergunta_parecida(agente, pergunta):
    assert _indice(agente).buscar(pergunta, 1)[0]["nota"] < lexico.LIMIAR_BASE


def test_complexidade_sobe_com_pedido_de_analise():
    simples, _ = complexidade("Como solicito férias?")
    dificil, motivos = complexidade("Compare antecipar recebíveis com esperar o prazo normal para um lojista "
                                    "que fatura R$ 40 mil e explique os prós e contras")
    assert simples < 0.3 < 0.6 <= dificil
    assert any("análise" in m for m in motivos)
