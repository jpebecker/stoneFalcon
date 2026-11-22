"""O catálogo da demo (persona -> trabalhador + processo) e a galeria do Estúdio que sai dele (v8.1)."""
import pytest

from app.agents.blueprint import Blueprint
from app.core.identidade import PERSONAS
from app.processos.blueprint import ProcessoBlueprint
from app.processos.compilar import trabalhador
from app.seed import catalogo
from app.studio.modelos_prontos import PADROES
from app.studio.sugestao import sugerir


def test_cada_entrada_tem_trabalhador_de_um_passo_e_processo_valido():
    assert set(catalogo.DEMOS) == set(catalogo.TRABALHADORES) == set(catalogo.CHAVES)
    for chave, demo in catalogo.DEMOS.items():
        assert demo.persona in PERSONAS and PERSONAS[demo.persona].area == demo.area
        assert trabalhador(catalogo.TRABALHADORES[chave]) is not None      # um agente, uma tarefa
        pbp = ProcessoBlueprint.model_validate(catalogo.processo(chave, "ag"))
        assert [b.agente_id for b in pbp.blocos if b.tipo == "agente"] == ["ag"]
        assert catalogo.fluxo(chave).passos                                 # compila sem banco, com o trabalhador do catálogo


def test_a_aplicacao_nao_importa_formato_legado():
    import pathlib
    app = pathlib.Path(__file__).resolve().parents[1] / "app"
    for arquivo in app.rglob("*.py"):
        assert "agentes_exemplo" not in arquivo.read_text(encoding="utf-8"), arquivo


def test_galeria_so_tem_trabalhadores_de_um_passo():
    assert {p["id"] for p in PADROES} == {d.padrao for d in catalogo.DEMOS.values()}
    for p in PADROES:
        assert len(Blueprint.model_validate(p["blueprint"]).passos) == 1


@pytest.fixture()
def plugin_arquivos():
    """Os processos de Lucas e Helena leem arquivos: na demo o plugin nasce integrado."""
    from app.plugins import estado
    estado.INTEGRADOS.add("arquivos")
    yield
    estado.INTEGRADOS.discard("arquivos")


@pytest.mark.parametrize("padrao", [p["id"] for p in PADROES])
def test_cada_exemplo_cai_no_padrao_certo(padrao, plugin_arquivos):
    demo = catalogo.por_padrao(padrao)
    for texto in demo.exemplos:
        s = sugerir(PERSONAS[demo.persona], texto)
        assert s.origem == "padrao:" + padrao, texto
        assert len(s.blueprint.passos) == 1 and s.processo and s.processo["nome"] == demo.nome_processo
        assert not [a for a in s.alertas if "legado" in a.lower()]
