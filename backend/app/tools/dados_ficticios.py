"""Sistemas internos de MENTIRA, para a demo. Nada aqui é dado real da Stone.

Os CPFs, CNPJs e cartões são válidos só no formato (dígitos verificadores), para
que os guardrails os reconheçam como fariam com dados reais.
"""
import random
import threading
from datetime import date, timedelta

LOJISTAS = {
    "L1001": {"id": "L1001", "maquininha": "Maquininha Mini", "nome": "Padaria Pão Dourado", "cnpj": "11.222.333/0001-81", "cidade": "Florianópolis/SC",
              "segmento": "Alimentação", "plano": "Essencial", "cliente_desde": "2021-03-10",
              "email": "contato@paodourado.exemplo.com.br", "faturamento_mensal": 38_000},
    "L1002": {"id": "L1002", "maquininha": "Maquininha Pro", "nome": "Ótica Visão Clara", "cnpj": "45.723.174/0001-10", "cidade": "Joinville/SC",
              "segmento": "Varejo", "plano": "Pro", "cliente_desde": "2019-08-22",
              "email": "financeiro@visaoclara.exemplo.com.br", "faturamento_mensal": 92_000},
    "L1003": {"id": "L1003", "maquininha": "Maquininha Smart", "nome": "Eletrônicos Relâmpago", "cnpj": "27.865.757/0001-02", "cidade": "São Paulo/SP",
              "segmento": "Eletrônicos", "plano": "Essencial", "cliente_desde": "2026-08-01",
              "email": "vendas@relampago.exemplo.com.br", "faturamento_mensal": 210_000},
    "L1004": {"id": "L1004", "maquininha": "Maquininha Pro", "nome": "Pet Shop Amigo Fiel", "cnpj": "60.701.190/0001-04", "cidade": "Curitiba/PR",
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

# Matrículas das próprias personas (cada pessoa também é colaboradora: "Eu mesmo" nos campos)
COLABORADORES.update({
    "C601": {"id": "C601", "nome": "Marina Duarte", "area": "Atendimento", "admissao": "2023-05-08",
             "saldo_ferias_dias": 12, "beneficios": ["VR", "Plano de saúde", "Auxílio home office"]},
    "C602": {"id": "C602", "nome": "Rafael Lima", "area": "Prevenção a Fraudes", "admissao": "2022-09-12",
             "saldo_ferias_dias": 22, "beneficios": ["VR", "Plano de saúde"]},
    "C603": {"id": "C603", "nome": "Carla Nogueira", "area": "Pessoas (RH)", "admissao": "2021-02-01",
             "saldo_ferias_dias": 30, "beneficios": ["VR", "Plano de saúde", "Auxílio creche"]},
    "C604": {"id": "C604", "nome": "Thiago Moreira", "area": "Logística", "admissao": "2024-07-15",
             "saldo_ferias_dias": 8, "beneficios": ["VR", "Plano de saúde", "Auxílio home office"]},
    "C605": {"id": "C605", "nome": "Lucas Prado", "area": "Engenharia de Plataforma", "admissao": "2020-11-03",
             "saldo_ferias_dias": 25, "beneficios": ["VR", "Plano de saúde", "Auxílio home office"]},
    "C606": {"id": "C606", "nome": "Helena Castro", "area": "CoE de IA", "admissao": "2022-01-17",
             "saldo_ferias_dias": 15, "beneficios": ["VR", "Plano de saúde"]},
})

# Estoque de maquininhas por modelo (sistema de logística fictício)
ESTOQUE = {
    "Maquininha Mini": {"modelo": "Maquininha Mini", "disponivel": 128, "centro": "Centro de distribuição de Florianópolis/SC", "prazo_envio_dias": 2},
    "Maquininha Pro": {"modelo": "Maquininha Pro", "disponivel": 46, "centro": "Centro de distribuição de São Paulo/SP", "prazo_envio_dias": 1},
    "Maquininha Smart": {"modelo": "Maquininha Smart", "disponivel": 9, "centro": "Centro de distribuição de São Paulo/SP", "prazo_envio_dias": 3},
}

# Dado pessoal de cada colaborador (CPF e e-mail): sempre mascarado antes de ir ao modelo
_CPFS = ['398.259.791-94', '907.483.378-06', '876.232.860-30', '129.040.479-80', '666.972.510-85', '273.464.686-27', '958.969.350-48', '492.589.913-97']
for _c, _cpf in zip(["C501", "C502", "C601", "C602", "C603", "C604", "C605", "C606"], _CPFS):
    COLABORADORES[_c]["cpf"] = _cpf
    COLABORADORES[_c]["email"] = "%s@stonefalcon.exemplo.com.br" % COLABORADORES[_c]["nome"].split()[0].lower()

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
