"""v7/07: Mapa de IA (só da Helena): criadores -> agentes -> plugins/ferramentas -> plataformas."""
import pytest

from app.core.identidade import PERSONAS
from app.mapa import grafo
from app.plugins.catalogo import PLUGINS
from app.seed.demo import semear
from app.tools.catalogo import CATALOGO
from tests.conftest import como

pytestmark = pytest.mark.usefixtures("legado")   # v7: usa fluxos de vários passos como dado de exemplo (veja o fixture)

V1 = "/api/v1"
PERFIS = list(PERSONAS)

AGENTE_NOVO = {
    "nome": "Aviso de estoque", "objetivo": "Consultar o estoque e avisar a logística no canal certo.", "area": "logistica",
    "campos": [{"id": "modelo", "rotulo": "Modelo", "tipo": "texto", "exemplo": "Maquininha Pro"}],
    "passos": [
        {"id": "estoque", "titulo": "Consultar o estoque", "tipo": "ferramenta", "ferramenta": "consultar_estoque",
         "entrada": {"modelo": "{{entrada.modelo}}"}},
        {"id": "aviso", "titulo": "Avisar o canal", "tipo": "agente", "modelo": "rapido", "depende_de": ["estoque"],
         "ferramentas": ["slack_enviar_mensagem"], "instrucao": "Avise o canal #logistica com o resultado do estoque."}],
}


def _ids(m: dict, tipo: str) -> set[str]:
    return {n["id"] for n in m["nos"] if n["tipo"] == tipo}


def _alcanca(m: dict, de: str, para: str) -> bool:
    """Existe um caminho (por qualquer número de ligações) de `de` até `para`?"""
    adj: dict[str, set[str]] = {}
    for l in m["ligacoes"]:
        adj.setdefault(l["de"], set()).add(l["para"])
    visto, fila = set(), [de]
    while fila:
        x = fila.pop()
        if x == para:
            return True
        if x not in visto:
            visto.add(x)
            fila += adj.get(x, ())
    return False


@pytest.mark.parametrize("perfil", PERFIS)
def test_mapa_so_para_a_helena(api, perfil):
    r = api.get(f"{V1}/mapa", headers=como(perfil))
    assert r.status_code == (200 if perfil == "helena" else 403), perfil
    assert ("mapa" in api.get(f"{V1}/eu", headers=como(perfil)).json()["abas"]) == (perfil == "helena")


def test_mapa_exige_pessoa_conhecida(api):
    assert api.get(f"{V1}/mapa").status_code == 401


def test_mapa_mostra_os_agentes_publicados_da_semente_ligados_a_tudo(api, sessao):
    semear(sessao)
    m = api.get(f"{V1}/mapa", headers=como("helena")).json()
    nomes = {n["rotulo"] for n in m["nos"] if n["tipo"] == "agente"}
    assert {"Analista de risco de chargebacks", "Redator de respostas a lojistas", "Orientador de férias e benefícios"} <= nomes
    assert [c["id"] for c in m["colunas"]] == ["criadores", "processos", "agentes", "modelos", "ferramentas", "plataformas"]
    # cada agente tem um criador, modelos, ferramentas e, por elas, plataformas
    liga = {(l["de"], l["para"]) for l in m["ligacoes"]}
    por_destino = {l["para"]: l["de"] for l in m["ligacoes"] if l["de"].startswith("criador:")}
    for n in m["nos"]:
        if n["tipo"] == "agente":
            assert por_destino[n["id"]] == "criador:" + n["dono"]
            assert any(d == n["id"] and p.startswith("modelo:") for d, p in liga)
    for n in m["nos"]:
        if n["tipo"] == "ferramenta":
            assert any(p == n["id"] for _, p in liga) and any(d == n["id"] for d, _ in liga)
        if n["tipo"] == "modelo":
            assert any(p == n["id"] for _, p in liga)


def test_mapa_e_coerente_com_o_catalogo_e_os_agentes_publicados(api, sessao):
    semear(sessao)
    m = api.get(f"{V1}/mapa", headers=como("helena")).json()
    ids = {n["id"] for n in m["nos"]}
    assert all(l["de"] in ids and l["para"] in ids for l in m["ligacoes"])             # nenhuma ligação solta
    for n in m["nos"]:
        if n["tipo"] == "ferramenta":
            assert n["id"].split(":", 1)[1] in CATALOGO and not CATALOGO[n["id"].split(":", 1)[1]].plugin
        if n["tipo"] == "plugin":
            assert n["id"].split(":", 1)[1] in PLUGINS
    publicados = {a["nome"] for a in api.get(f"{V1}/agentes", headers=como("helena")).json() if a["estado"] == "publicado"}
    assert {n["rotulo"] for n in m["nos"] if n["tipo"] == "agente"} == publicados
    assert m["totais"]["agentes"] == len(publicados)
    processos = {p["nome"] for p in api.get(f"{V1}/processos", headers=como("helena")).json() if p["estado"] == "publicado"}
    assert {n["rotulo"] for n in m["nos"] if n["tipo"] == "processo"} == processos and len(processos) == 4
    # colunas coerentes com o tipo
    coluna = {"criador": "criadores", "processo": "processos", "agente": "agentes", "modelo": "modelos", "ferramenta": "ferramentas",
              "plugin": "ferramentas", "sistema": "plataformas"}
    assert all(n["coluna"] == coluna[n["tipo"]] for n in m["nos"])


def test_publicar_um_agente_novo_faz_ele_aparecer_no_mapa(api, sessao):
    semear(sessao)
    antes = api.get(f"{V1}/mapa", headers=como("helena")).json()
    assert "Aviso de estoque" not in {n["rotulo"] for n in antes["nos"]}
    api.post(f"{V1}/plugins/slack/integrar", headers=como("thiago"))
    aid = api.post(f"{V1}/agentes", json={"blueprint": AGENTE_NOVO, "nota": "novo"}, headers=como("thiago")).json()["id"]
    assert api.post(f"{V1}/agentes/{aid}/publicar", headers=como("thiago")).json()["estado"] == "publicado"
    depois = api.get(f"{V1}/mapa", headers=como("helena")).json()
    assert "agente:" + aid in _ids(depois, "agente")
    assert "criador:thiago" in _ids(depois, "criador")
    liga = {(l["de"], l["para"]) for l in depois["ligacoes"]}
    assert ("criador:thiago", "agente:" + aid) in liga
    assert _alcanca(depois, "agente:" + aid, "ferramenta:consultar_estoque") and _alcanca(depois, "agente:" + aid, "plugin:slack")
    assert ("agente:" + aid, "modelo:rapido") in liga and ("modelo:rapido", "plugin:slack") in liga
    assert ("plugin:slack", "sistema:ext:slack") in liga and ("ferramenta:consultar_estoque", "sistema:estoque") in liga
    assert depois["totais"]["agentes"] == antes["totais"]["agentes"] + 1


def test_integrar_e_remover_um_plugin_muda_o_mapa(api, sessao):
    semear(sessao)
    antes = api.get(f"{V1}/mapa", headers=como("helena")).json()
    assert "plugin:zendesk" not in _ids(antes, "plugin")
    assert api.post(f"{V1}/plugins/zendesk/integrar", headers=como("marina")).status_code == 200
    com = api.get(f"{V1}/mapa", headers=como("helena")).json()
    z = next(n for n in com["nos"] if n["id"] == "plugin:zendesk")
    assert z["integrado"] is True and "sistema:ext:zendesk" in _ids(com, "sistema")
    assert api.delete(f"{V1}/plugins/zendesk/integracao", headers=como("marina")).status_code == 200
    sem = api.get(f"{V1}/mapa", headers=como("helena")).json()
    assert "plugin:zendesk" not in _ids(sem, "plugin") and "sistema:ext:zendesk" not in _ids(sem, "sistema")


def test_agente_que_depende_de_plugin_removido_continua_no_mapa_marcado(api, sessao):
    semear(sessao)
    api.post(f"{V1}/plugins/slack/integrar", headers=como("thiago"))
    aid = api.post(f"{V1}/agentes", json={"blueprint": AGENTE_NOVO, "nota": "novo"}, headers=como("thiago")).json()["id"]
    api.post(f"{V1}/agentes/{aid}/publicar", headers=como("thiago"))
    api.delete(f"{V1}/plugins/slack/integracao", headers=como("thiago"))
    m = api.get(f"{V1}/mapa", headers=como("helena")).json()
    slack = next(n for n in m["nos"] if n["id"] == "plugin:slack")
    assert slack["integrado"] is False and _alcanca(m, "agente:" + aid, "plugin:slack")


def test_cada_no_clicavel_aponta_para_a_pagina_dele(api, sessao):
    semear(sessao)
    m = api.get(f"{V1}/mapa", headers=como("helena")).json()
    for n in m["nos"]:
        if n["tipo"] == "agente":
            assert n["rota"] == "/agentes/" + n["id"].split(":", 1)[1]
        if n["tipo"] == "plugin":
            assert n["rota"] == "/plugins/" + n["id"].split(":", 1)[1]


def test_mapa_conta_as_execucoes_do_periodo(api, sessao):
    semear(sessao)
    m = api.get(f"{V1}/mapa?dias=30", headers=como("helena")).json()
    assert m["totais"]["execucoes"] > 0 and m["tem_demo"] is True
    assert sum(n["execucoes"] for n in m["nos"] if n["tipo"] in ("agente", "processo")) == m["totais"]["execucoes"]
    assert grafo(sessao, 7)["dias"] == 7
