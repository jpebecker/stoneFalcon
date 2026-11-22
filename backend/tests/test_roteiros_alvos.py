"""v8.3/09: os passos dos roteiros apontam controles (`data-alvo`) para o falcão guiar; nenhum aponta para o nada."""
import re
from pathlib import Path

from app.roteiros.catalogo import ALVOS_CONHECIDOS, ROTEIROS
from tests.conftest import como

V1 = "/api/v1"
TELAS = Path(__file__).resolve().parents[2] / "frontend" / "src"
PERSONAS_COM_ROTEIRO = ("marina", "rafael", "carla", "thiago", "lucas", "helena")


def test_todo_alvo_declarado_e_conhecido():
    declarados = {(r.id, p.id, p.alvo) for r in ROTEIROS.values() for p in r.passos if p.alvo}
    assert declarados
    desconhecidos = [d for d in declarados if d[2] not in ALVOS_CONHECIDOS]
    assert not desconhecidos, desconhecidos


def test_todo_alvo_conhecido_ainda_existe_no_codigo_das_telas():
    """Se uma tela mudar e o controle perder o `data-alvo`, o roteiro deixaria de apontar para ele: o teste acusa."""
    codigo = [(f, f.read_text(encoding="utf-8")) for f in TELAS.rglob("*.tsx")]
    for nome in sorted(ALVOS_CONHECIDOS):
        achou = any(re.search(r'data-alvo=\{?[^\n]*"%s"' % re.escape(nome), texto) for _f, texto in codigo)
        assert achou, f'nenhuma tela tem data-alvo="{nome}"'


def test_cada_roteiro_de_persona_aponta_os_controles_claros_dos_seus_passos():
    for persona in PERSONAS_COM_ROTEIRO:
        passos = {p.id: p for p in ROTEIROS[persona].passos}
        assert any(p.alvo for p in passos.values()), persona
        for pid in ("testar", "publicar", "usar", "alerta", "revisao", "pausar"):   # executar, publicar, tratar o alerta, aprovar, pausar
            if pid in passos and not passos[pid].externa:
                assert passos[pid].alvo, (persona, pid)
        assert passos["alerta"].alvo == "acao-alerta", persona


def test_o_alvo_vai_na_api_do_roteiro(api):
    r = api.get(f"{V1}/roteiros/marina", headers=como("marina")).json()
    por_id = {p["id"]: p for p in r["passos"]}
    assert por_id["publicar"]["alvo"] == "acao-publicar" and por_id["alerta"]["alvo"] == "acao-alerta"
    assert por_id["contexto"]["alvo"] is None            # sem controle claro: o falcão só fala do poleiro
