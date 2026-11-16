"""Portado do v3: dados sensíveis são mascarados antes de qualquer envio."""
from app import guardrails
from tests.conftest import como

ORIGINAL = ("CPF 123.456.789-09, cartão 4111 1111 1111 1111, CNPJ 11.222.333/0001-81, "
            "fone (48) 99999-1234, a.b@x.com.br, senha: abc123")


def test_mascara_todos_os_tipos_e_restaura():
    masc, mapa, resumo = guardrails.mascarar(ORIGINAL)
    for dado in ("123.456.789-09", "4111 1111 1111 1111", "11.222.333/0001-81", "99999-1234", "a.b@x.com.br", "abc123"):
        assert dado not in masc
    assert guardrails.restaurar(masc, mapa) == ORIGINAL
    assert sum(r["quantidade"] for r in resumo) == 6


def test_numeros_comuns_nao_sao_mascarados():
    limpo = "Venda de R$ 40 mil em 2026, 12 contestações, prazo de 30 dias, pedido 12345678901"
    assert guardrails.mascarar(limpo)[0] == limpo


def test_cpf_formatado_mesmo_invalido_e_mascarado():
    assert guardrails.mascarar("cpf 111.111.111-11 e 529.982.247-25")[0].count("[CPF_") == 2


def test_mesmo_dado_recebe_mesmo_marcador():
    masc, mapa, _ = guardrails.mascarar("CPF 529.982.247-25 e de novo 529.982.247-25")
    assert masc.count("[CPF_1]") == 2 and len(mapa) == 1


def test_guardrail_de_saida_remove_dado_escrito_pelo_modelo():
    limpo, removidos = guardrails.limpar_saida("O titular é 529.982.247-25.")
    assert removidos == 1 and "529" not in limpo


def test_rota_mostra_o_que_sairia_para_o_modelo(api):
    r = api.post("/api/v1/guardrails/testar", json={"texto": ORIGINAL}, headers=como("rafael"))
    assert r.status_code == 200
    corpo = r.json()
    assert "[CPF_1]" in corpo["enviado_ao_modelo"] and "123.456.789-09" not in corpo["enviado_ao_modelo"]
