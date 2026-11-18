"""v7/04: registro único de modelos (provedor, preços, capacidades, simulado/real) e apelidos "rapido"/"forte"."""
import re
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.agents.blueprint import Blueprint
from app.llm import precos, registro
from tests.conftest import como

RAIZ = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize("modelo", registro.todos(), ids=lambda m: m.chave)
def test_todo_modelo_tem_ficha_completa(modelo):
    assert modelo.provedor in registro.PROVEDORES
    assert modelo.nome and modelo.id_api
    assert modelo.preco_entrada > 0 and modelo.preco_saida > 0 and modelo.preco_cache_leitura > 0
    assert modelo.preco_saida >= modelo.preco_entrada
    assert isinstance(modelo.capacidades.ferramentas, bool) and isinstance(modelo.capacidades.contexto_longo, bool)
    assert 1 <= modelo.capacidades.raciocinio <= len(registro.ESFORCOS)
    assert modelo.fonte_preco and re.fullmatch(r"\d{4}-\d{2}-\d{2}", modelo.data_preco)
    vel, lat = modelo.velocidade
    assert vel > 0 and lat > 0
    if modelo.limite_preco_padrao:   # faixa longa declarada por inteiro
        assert modelo.preco_entrada_longo and modelo.preco_saida_longo


def test_chaves_unicas_e_apelidos_nao_colidem():
    chaves = [m.chave for m in registro.todos()]
    assert len(chaves) == len(set(chaves))
    apelidos = [a for m in registro.todos() for a in m.apelidos]
    assert len(apelidos) == len(set(apelidos)) and not (set(apelidos) & set(chaves))


def test_rapido_e_forte_sao_apelidos_de_haiku_e_sonnet():
    assert registro.obter("rapido").nome == "Claude Haiku 5.5" == registro.obter("haiku").nome
    assert registro.obter("forte").nome == "Claude Sonnet 5.5" == registro.obter("claude-sonnet-5-5").nome
    with pytest.raises(KeyError):
        registro.obter("modelo-que-nao-existe")
    assert registro.existe("rapido") and not registro.existe("nada")


def test_so_o_claude_roda_de_verdade():
    for m in registro.todos():
        assert registro.roda_de_verdade(m.chave) == (m.provedor == "anthropic" and not m.simulado)


def test_precos_vem_so_do_registro_e_batem_com_a_v6():
    assert precos.custo_usd("rapido", 1000, 1000) == pytest.approx((1000 * 0.10 + 1000 * 0.50) / 1e6)
    assert precos.custo_usd("forte", 1000, 1000) == pytest.approx((1000 * 2.0 + 1000 * 10.0) / 1e6)
    assert precos.custo_usd("haiku", 1000, 1000) == precos.custo_usd("rapido", 1000, 1000)   # apelido, mesmo preço
    assert precos.custo_usd("rapido", 100_001, 1000) == pytest.approx((100_001 * 0.50 + 1000 * 2.50) / 1e6)   # faixa longa


def test_blueprint_antigo_com_rapido_e_forte_continua_valido():
    bp = Blueprint.model_validate({
        "nome": "Antigo", "area": "atendimento", "objetivo": "Objetivo de teste", "minutos_manual": 5,
        "passos": [{"id": "a", "titulo": "A", "tipo": "agente", "instrucao": "x", "modelo": "rapido"},
                   {"id": "b", "titulo": "B", "tipo": "agente", "instrucao": "y", "modelo": "forte", "depende_de": ["a"]}]})
    assert [p.modelo for p in bp.passos] == ["rapido", "forte"]


def test_blueprint_com_modelo_desconhecido_e_recusado():
    with pytest.raises(ValidationError, match="modelo desconhecido"):
        Blueprint.model_validate({
            "nome": "X", "area": "atendimento", "objetivo": "Objetivo de teste", "minutos_manual": 5,
            "passos": [{"id": "a", "titulo": "A", "tipo": "agente", "instrucao": "x", "modelo": "gpt-inventado"}]})


def test_rota_de_modelos_devolve_o_registro(api):
    r = api.get("/api/v1/modelos", headers=como("marina")).json()
    assert {m["chave"] for m in r["modelos"]} == {m.chave for m in registro.todos()}
    assert {p["id"] for p in r["provedores"]} == set(registro.PROVEDORES)
    haiku = next(m for m in r["modelos"] if m["chave"] == "rapido")
    assert haiku["preco_entrada"] == 0.10 and haiku["simulado"] is False and haiku["provedor"] == "anthropic"
    assert api.get("/api/v1/saude").json()["modelos"]["rapido"] == "Claude Haiku 5.5"


def test_nomes_e_precos_nao_se_repetem_fora_do_registro():
    """Nenhuma tabela de nomes ou preços fora de app/llm/registro.py (nem em Finanças, nem no cliente web)."""
    codigo = [p for p in (RAIZ / "backend/app").rglob("*.py") if p.name != "registro.py"]
    codigo += [p for p in (RAIZ / "frontend/src").rglob("*.ts*")]
    for arq in codigo:
        texto = arq.read_text(encoding="utf-8")
        assert not re.search(r'"Claude (Haiku|Sonnet) 5\.5"', texto), arq
        assert not re.search(r"preco_(entrada|saida)\s*[:=]\s*[0-9]", texto), arq
        assert "MODELOS = {" not in texto, arq
