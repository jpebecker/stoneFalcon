"""Sistemas internos de MENTIRA, para a demo. Nada aqui é dado real da Stone.

Os CPFs, CNPJs e cartões são válidos só no formato (dígitos verificadores), para
que os guardrails os reconheçam como fariam com dados reais.
"""
import random
import threading
from datetime import date, timedelta

LOJISTAS = {
    "L1001": {"id": "L1001", "nome": "Padaria Pão Dourado", "cnpj": "11.222.333/0001-81", "cidade": "Florianópolis/SC",
              "segmento": "Alimentação", "plano": "Essencial", "cliente_desde": "2021-03-10",
              "email": "contato@paodourado.exemplo.com.br", "faturamento_mensal": 38_000},
    "L1002": {"id": "L1002", "nome": "Ótica Visão Clara", "cnpj": "45.723.174/0001-10", "cidade": "Joinville/SC",
              "segmento": "Varejo", "plano": "Pro", "cliente_desde": "2019-08-22",
              "email": "financeiro@visaoclara.exemplo.com.br", "faturamento_mensal": 92_000},
    "L1003": {"id": "L1003", "nome": "Eletrônicos Relâmpago", "cnpj": "27.865.757/0001-02", "cidade": "São Paulo/SP",
              "segmento": "Eletrônicos", "plano": "Essencial", "cliente_desde": "2026-08-01",
              "email": "vendas@relampago.exemplo.com.br", "faturamento_mensal": 210_000},
    "L1004": {"id": "L1004", "nome": "Pet Shop Amigo Fiel", "cnpj": "60.701.190/0001-04", "cidade": "Curitiba/PR",
              "segmento": "Pet", "plano": "Pro", "cliente_desde": "2022-11-05",
              "email": "amigofiel@exemplo.com.br", "faturamento_mensal": 54_000},
}

# Titular de cada conta (dado pessoal: sempre mascarado antes de ir ao modelo)
TITULARES = {
    "L1001": {"nome": "Joana Ribeiro", "cpf": "529.982.247-25"},
    "L1002": {"nome": "Carlos Menezes", "cpf": "111.444.777-35"},
    "L1003": {"nome": "Diego Sales", "cpf": "123.456.789-09"},
    "L1004": {"nome": "Patrícia Rocha", "cpf": "390.533.447-05"},
}

COLABORADORES = {
    "C501": {"id": "C501", "nome": "Bruno Tavares", "area": "Atendimento", "admissao": "2024-02-01",
             "saldo_ferias_dias": 18, "beneficios": ["VR", "Plano de saúde", "Auxílio home office"]},
    "C502": {"id": "C502", "nome": "Aline Souza", "area": "Risco", "admissao": "2025-06-16",
             "saldo_ferias_dias": 30, "beneficios": ["VR", "Plano de saúde", "Auxílio creche"]},
}

_HOJE = date(2026, 11, 15)


def transacoes(lojista_id: str, dias: int) -> list[dict]:
    """Histórico determinístico por lojista. A L1003 tem o padrão suspeito da demo:
    conta nova, salto de faturamento e muitas contestações na última semana."""
    rnd = random.Random(lojista_id)
    base = LOJISTAS[lojista_id]["faturamento_mensal"] / 30
    saida = []
    for d in range(dias):
        dia = _HOJE - timedelta(days=d)
        fator = 5.0 if (lojista_id == "L1003" and d < 7) else 1.0
        for i in range(rnd.randint(3, 6)):
            saida.append({
                "id": "T%s%03d%d" % (lojista_id[1:], d, i),
                "data": dia.isoformat(),
                "valor": round(base * fator / 4 * rnd.uniform(0.5, 1.5), 2),
                "bandeira": rnd.choice(["Visa", "Mastercard", "Elo"]),
                "modalidade": rnd.choice(["crédito", "débito", "crédito parcelado"]),
                "contestada": lojista_id == "L1003" and d < 7 and rnd.random() < 0.35,
            })
    return saida


# ---------- Estado mutável dos mocks (chamados abertos, notificações, bloqueios) ----------
_trava = threading.Lock()
CHAMADOS: list[dict] = []
NOTIFICACOES: list[dict] = []
BLOQUEIOS: list[dict] = []


def novo_id(prefixo: str, lista: list) -> str:
    with _trava:
        return "%s-%04d" % (prefixo, len(lista) + 1)


def zerar() -> None:
    with _trava:
        CHAMADOS.clear()
        NOTIFICACOES.clear()
        BLOQUEIOS.clear()
