"""v6: a interface obedece ao perfil. Mapa de abas (fonte única no back), Painel, Perguntas da Ferramenta e roteiros isolados."""
import pytest

from app.core.identidade import ABAS, PERSONAS
from app.roteiros.catalogo import ROTEIROS
from tests.conftest import como

V1 = "/api/v1"
PERFIS = list(PERSONAS)
SO_HELENA = ("roteiros", "painel", "perguntas")


def _participantes(rid: str) -> set[str]:
    r = ROTEIROS[rid]
    return {r.persona} | {p.perfil for p in r.passos}


@pytest.mark.parametrize("perfil", PERFIS)
def test_mapa_de_abas_vem_do_back(api, perfil):
    eu = api.get(f"{V1}/eu", headers=como(perfil)).json()
    assert set(eu["abas"]) <= set(ABAS)
    assert "inicio" in eu["abas"] and "plugins" in eu["abas"]            # todos os perfis
    for aba in SO_HELENA:
        assert (aba in eu["abas"]) == (perfil == "helena"), (perfil, aba)
    assert eu["abas"] == api.get(f"{V1}/perfis").json()[PERFIS.index(perfil)]["abas"]


@pytest.mark.parametrize("perfil", PERFIS)
def test_painel_so_da_helena(api, perfil):
    r = api.get(f"{V1}/financas/indicadores", headers=como(perfil))
    assert r.status_code == (200 if perfil == "helena" else 403), (perfil, r.text)
    # o que Finanças e a Calculadora usam continua aberto a quem já tinha acesso
    for rota in ("/financas/resumo", "/financas/premissas", "/roteiros/consolidado"):
        assert api.get(V1 + rota, headers=como(perfil)).status_code == 200, (perfil, rota)


@pytest.mark.parametrize("perfil", PERFIS)
def test_perguntas_da_ferramenta_so_da_helena(api, perfil):
    r = api.get(f"{V1}/perguntas", headers=como(perfil))
    assert r.status_code == (200 if perfil == "helena" else 403), (perfil, r.text)
    if perfil == "helena":   # todas as personas continuam cobertas, filtráveis por persona
        assert {q["persona"] for q in r.json()["perguntas"]} == set(PERSONAS)
        assert all(q["persona"] == "rafael" for q in api.get(f"{V1}/perguntas", params={"persona": "rafael"},
                                                              headers=como("helena")).json()["perguntas"])


@pytest.mark.parametrize("perfil", PERFIS)
@pytest.mark.parametrize("rid", list(ROTEIROS))
def test_matriz_persona_x_roteiro(api, perfil, rid):
    """Dono, quem participa de algum passo (quatro olhos) e a Helena abrem o roteiro; os demais recebem 403."""
    esperado = perfil == "helena" or perfil in _participantes(rid)
    for rota in (f"/roteiros/{rid}", f"/roteiros/{rid}/resultado"):
        r = api.get(V1 + rota, headers=como(perfil))
        assert (r.status_code == 200) == esperado, (perfil, rid, rota, r.status_code)
        assert esperado or r.status_code == 403
    r = api.post(f"{V1}/roteiros/{rid}/reiniciar", headers=como(perfil))
    assert (r.status_code == 200) == esperado, (perfil, rid, r.status_code)


@pytest.mark.parametrize("perfil", PERFIS)
def test_listagem_de_roteiros_so_do_proprio_perfil(api, perfil):
    ids = [r["id"] for r in api.get(f"{V1}/roteiros", headers=como(perfil)).json()]
    assert ids == (list(ROTEIROS) if perfil == "helena" else [perfil])


def test_roteiros_que_trocam_de_perfil_continuam_validos():
    """Quatro olhos: a prova de governança exige a troca de perfil, então o participante tem de poder carregar o roteiro."""
    assert _participantes("rafael") == {"rafael", "lucas", "helena"}
    assert _participantes("carla") == {"carla", "lucas"}
    assert "marina" in _participantes("lucas")
    assert _participantes("thiago") >= {"thiago"}


def test_nenhum_roteiro_de_outro_perfil_termina_nas_perguntas():
    for rid, r in ROTEIROS.items():
        assert (r.passos[-1].id == "perguntas") == (rid == "helena")
        assert "perguntas" not in [p.id for p in r.passos] or rid == "helena"


def test_mostrar_na_tela_leva_ao_passo_certo_com_o_perfil_certo():
    """Cada prova das Perguntas da Ferramenta aponta para um passo que existe, e o perfil da prova é o do passo."""
    from app.roteiros.perguntas import PERGUNTAS
    for q in PERGUNTAS:
        prova = q["prova"]
        assert prova["perfil"] in PERSONAS and prova["roteiro"] in ROTEIROS, q["id"]
        if prova["passo"]:
            passo = next((p for p in ROTEIROS[prova["roteiro"]].passos if p.id == prova["passo"]), None)
            assert passo is not None, (q["id"], prova["passo"])
            assert passo.perfil == prova["perfil"], (q["id"], passo.perfil, prova["perfil"])
        # a Helena abre o roteiro de qualquer persona antes de trocar de perfil
        assert PERSONAS[prova["perfil"]] and (prova["perfil"] in _participantes(prova["roteiro"]) or not prova["passo"])


@pytest.mark.parametrize("pergunta", [q["id"] for q in __import__("app.roteiros.perguntas", fromlist=["PERGUNTAS"]).PERGUNTAS])
def test_helena_carrega_o_roteiro_de_toda_prova_e_a_persona_da_prova_tambem(api, pergunta):
    from app.roteiros.perguntas import PERGUNTAS
    prova = next(q for q in PERGUNTAS if q["id"] == pergunta)["prova"]
    assert api.get(f"{V1}/roteiros/{prova['roteiro']}", headers=como("helena")).status_code == 200
    if prova["passo"]:   # depois da troca de perfil, a barra do roteiro continua conseguindo carregá-lo
        assert api.get(f"{V1}/roteiros/{prova['roteiro']}", headers=como(prova["perfil"])).status_code == 200


# ------------------------------------------------------------------ ensaio geral v6: roteiros ponta a ponta com o isolamento ativo
_ABA_DA_ROTA = [("/roteiros", "roteiros"), ("/painel", "painel"), ("/perguntas", "perguntas"), ("/plugins", "plugins"),
                ("/estudio", "estudio"), ("/agentes", "agentes"), ("/revisoes", "revisoes"), ("/auditoria", "auditoria"),
                ("/financas", "financas"), ("/ferramentas", "ferramentas"), ("/execucoes", "execucoes"), ("/saude", "saude")]


def _aba(rota: str) -> str | None:
    caminho = rota.split("?")[0]
    return next((aba for prefixo, aba in _ABA_DA_ROTA if caminho == prefixo or caminho.startswith(prefixo + "/")), None)


@pytest.mark.parametrize("rid", list(ROTEIROS))
def test_cada_passo_dos_roteiros_abre_para_o_perfil_do_passo(api, rid):
    """O roteiro troca de perfil nos passos de quatro olhos: em cada passo, o perfil do passo tem a aba da tela do passo
    e consegue carregar o roteiro (a barra precisa dele). Passos externos (helpdesk) abrem fora do app."""
    r = ROTEIROS[rid]
    assert api.post(f"{V1}/roteiros/{rid}/reiniciar", headers=como(r.persona)).status_code == 200
    for passo in r.passos:
        abas = api.get(f"{V1}/eu", headers=como(passo.perfil)).json()["abas"]
        assert api.get(f"{V1}/roteiros/{rid}", headers=como(passo.perfil)).status_code == 200, (rid, passo.id)
        if passo.externa:
            continue
        if passo.rota.startswith("/roteiro/"):   # cartão AS IS × TO BE: só do dono (e da Helena)
            assert passo.perfil == r.persona or "roteiros" in abas, (rid, passo.id)
            continue
        aba = _aba(passo.rota)
        assert aba is None or aba in abas, (rid, passo.id, passo.rota, passo.perfil)


def test_roteiro_do_rafael_troca_para_lucas_e_helena_sem_erro_de_acesso(api):
    api.post(f"{V1}/roteiros/rafael/reiniciar", headers=como("rafael"))
    assert [p.perfil for p in ROTEIROS["rafael"].passos if p.perfil != "rafael"] == ["lucas", "helena"]
    for quem in ("rafael", "lucas", "helena"):
        assert api.get(f"{V1}/roteiros/rafael", headers=como(quem)).status_code == 200
    assert api.get(f"{V1}/roteiros/rafael", headers=como("marina")).status_code == 403
    assert api.get(f"{V1}/revisoes", headers=como("lucas")).status_code == 200       # a tela do passo de revisão
    assert api.get(f"{V1}/auditoria", headers=como("helena")).status_code == 200     # e a da auditoria
