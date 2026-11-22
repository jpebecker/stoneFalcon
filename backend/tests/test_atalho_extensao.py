"""v7/03: atalho "Criar Agente de IA" na extensão. Passe de uso único, sem perfil nem texto no endereço."""
import pytest

from app.api import extensao
from app.core.identidade import PERSONAS
from tests.conftest import como, sem_criador

V1 = "/api/v1/extensao"
CRIADORES = ["marina", "rafael", "carla", "thiago", "lucas", "helena"]   # v8.1: todos criam
SEM_ESTUDIO = ["helena", "lucas"]            # os que perdem o papel nos testes de "quem não cria"


@pytest.fixture(autouse=True)
def _limpo():
    extensao.zerar_passes()
    yield
    extensao.zerar_passes()


@pytest.fixture()
def tempo(monkeypatch):
    t = {"agora": 1000.0}
    monkeypatch.setattr(extensao, "_relogio", lambda: t["agora"])
    return t


def test_regra_do_atalho_vem_da_lista_de_abas():
    """O botão só existe para quem tem a aba Estúdio; a fonte da verdade é a lista de abas do back."""
    for pid, p in PERSONAS.items():
        assert ("estudio" in p.publico()["abas"]) == (pid in CRIADORES)


@pytest.mark.parametrize("perfil", CRIADORES)
def test_criador_emite_e_troca_o_passe_uma_vez(api, perfil):
    r = api.post(f"{V1}/passe", json={}, headers=como(perfil))
    assert r.status_code == 200 and r.json()["valido_por_s"] == 60
    passe = r.json()["passe"]
    t = api.post(f"{V1}/passe/trocar", json={"passe": passe})   # sem cabeçalho de perfil: o passe é a credencial
    assert t.status_code == 200 and t.json()["pessoa"]["id"] == perfil and "estudio" in t.json()["pessoa"]["abas"]
    assert api.post(f"{V1}/passe/trocar", json={"passe": passe}).status_code == 410   # só vale uma vez


@pytest.mark.parametrize("perfil", SEM_ESTUDIO)
def test_quem_nao_cria_agentes_nao_recebe_passe(api, perfil, monkeypatch):
    sem_criador(monkeypatch, perfil)
    assert api.post(f"{V1}/passe", json={}, headers=como(perfil)).status_code == 403


def test_passe_exige_pessoa_conhecida(api):
    assert api.post(f"{V1}/passe", json={}).status_code == 401
    assert api.post(f"{V1}/passe", json={}, headers=como("ninguem")).status_code == 401


def test_passe_vence_em_60_segundos(api, tempo):
    passe = api.post(f"{V1}/passe", json={}, headers=como("thiago")).json()["passe"]
    tempo["agora"] += 61
    r = api.post(f"{V1}/passe/trocar", json={"passe": passe})
    assert r.status_code == 410 and "venceu" in r.json()["detail"]


def test_passe_ainda_vale_perto_do_limite(api, tempo):
    passe = api.post(f"{V1}/passe", json={}, headers=como("thiago")).json()["passe"]
    tempo["agora"] += 59
    assert api.post(f"{V1}/passe/trocar", json={"passe": passe}).status_code == 200


def test_passe_inventado_e_recusado(api):
    assert api.post(f"{V1}/passe/trocar", json={"passe": "abc"}).status_code == 410


def test_passe_leva_a_pessoa_certa_mesmo_com_outro_perfil_logado(api):
    """O passe de um perfil nunca troca por outro, qualquer que seja o cabeçalho da requisição."""
    passe = api.post(f"{V1}/passe", json={}, headers=como("thiago")).json()["passe"]
    r = api.post(f"{V1}/passe/trocar", json={"passe": passe}, headers=como("helena"))
    assert r.json()["pessoa"]["id"] == "thiago"


def test_trecho_viaja_no_corpo_e_volta_na_troca(api):
    texto = "A maquininha Pro da loja não liga."
    passe = api.post(f"{V1}/passe", json={"trecho": texto}, headers=como("thiago")).json()["passe"]
    assert texto not in passe and "thiago" not in passe          # nada do perfil ou do texto no que vai no endereço
    assert api.post(f"{V1}/passe/trocar", json={"passe": passe}).json()["rascunho"] == texto


def test_trecho_grande_demais_e_recusado(api):
    assert api.post(f"{V1}/passe", json={"trecho": "x" * 8001}, headers=como("thiago")).status_code == 422


def test_passes_sao_diferentes_e_imprevisiveis(api):
    a = api.post(f"{V1}/passe", json={}, headers=como("thiago")).json()["passe"]
    b = api.post(f"{V1}/passe", json={}, headers=como("thiago")).json()["passe"]
    assert a != b and len(a) >= 24


def test_emitir_e_usar_ficam_na_auditoria_sem_o_texto(api):
    passe = api.post(f"{V1}/passe", json={"trecho": "segredo do cliente"}, headers=como("thiago")).json()["passe"]
    api.post(f"{V1}/passe/trocar", json={"passe": passe})
    ev = api.get("/api/v1/auditoria?limite=50", headers=como("helena")).json()["eventos"]
    tipos = [e["tipo"] for e in ev]
    assert "passe_extensao_emitido" in tipos and "passe_extensao_usado" in tipos
    assert "segredo do cliente" not in str(ev) and passe not in str(ev)


def test_trecho_vira_sugestao_de_agente_no_estudio(api):
    """O trecho recebido na troca alimenta a sugestão do Estúdio (a tela chama /estudio/sugerir com ele)."""
    passe = api.post(f"{V1}/passe", json={"trecho": "O lojista pediu a troca da maquininha, que não liga. Confira o cadastro e abra um chamado."},
                     headers=como("thiago")).json()["passe"]
    rascunho = api.post(f"{V1}/passe/trocar", json={"passe": passe}).json()["rascunho"]
    s = api.post("/api/v1/estudio/sugerir", json={"descricao": rascunho}, headers=como("thiago"))
    assert s.status_code == 200 and s.json()["blueprint"]["passos"]
