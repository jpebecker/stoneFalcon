"""v8/13: aprovar e publicar plugins internos (analista de IA; Segurança para dado sensível; quatro olhos)."""
import pytest
from sqlmodel import select

from app.audit.trilha import EventoAuditoria
from app.observability.alertas import Alerta
from app.plugins.catalogo import PLUGINS
from app.tools.catalogo import CATALOGO
from tests.conftest import como

V1 = "/api/v1"
PI = f"{V1}/plugins-internos"
DESCRICAO = ("Acme Agenda permite marcar reuniões, reservar salas e ver o calendário da equipe. Envia convite aos participantes, "
             "cancela e remarca compromissos e mostra a disponibilidade de cada sala em cada horário.")


def _pedir(api, perfil="thiago", classificacao="interna", marca="Acme Agenda"):
    corpo = {"ferramenta_mercado": marca, "descricao_publica": DESCRICAO, "finalidade": "Reservar salas e marcar reuniões entre áreas.",
             "areas": ["logistica"], "classificacao": classificacao, "aceita_aviso_publico": True}
    spec = api.post(f"{PI}/rascunho", json=corpo, headers=como(perfil)).json()["spec"]
    r = api.post(PI, json={**corpo, "spec": spec}, headers=como(perfil))
    assert r.status_code == 200, r.text
    return r.json()


def _decidir(api, perfil, pedido_id, etapa, aprovar=True, parecer="Faz sentido para a empresa."):
    return api.post(f"{PI}/{pedido_id}/{etapa}", json={"aprovar": aprovar, "parecer": parecer}, headers=como(perfil))


def _estados(api, perfil="thiago"):
    return {p["id"]: p["estado"] for p in api.get(PI, headers=como(perfil)).json()}


def test_caminho_simples_helena_aprova_e_o_plugin_vai_para_o_marketplace(api, sessao):
    p = _pedir(api)
    assert p["pode_decidir"] is False and p["estado"] == "aguardando_analista"
    assert api.get(f"{PI}/{p['id']}", headers=como("helena")).json()["pode_decidir"] is True
    r = _decidir(api, "helena", p["id"], "analista")
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["estado"] == "publicado" and d["plugin_id"] and d["decisao_analista"]["por"] == "helena"
    # marketplace: aparece para todos, com os selos "interno · conceitual" e "simulado", e as ferramentas no catálogo com a origem dele
    pg = api.get(f"{V1}/plugins/{d['plugin_id']}", headers=como("marina")).json()
    assert pg["interno"] is True and pg["simulado"] is True and pg["real"] is False and pg["estado"] == "disponivel"
    assert pg["nome"] == "Ferramenta interna de agendamento" and {f["acao"] for f in pg["ferramentas"]} == {"leitura", "escrita"}
    assert d["plugin_id"] in PLUGINS and all(f["id"] in CATALOGO for f in pg["ferramentas"])
    # o solicitante é avisado; tudo na trilha
    assert any("publicado" in a.titulo.lower() and "thiago" in a.destinatarios for a in sessao.exec(select(Alerta)).all())
    tipos = [e.tipo for e in sessao.exec(select(EventoAuditoria)).all()]
    for t in ("plugin_interno_solicitado", "plugin_interno_aprovado_analista", "plugin_interno_publicado"):
        assert t in tipos, t
    assert api.get(f"{V1}/auditoria/verificar", headers=como("helena")).json()["integra"] is True


def test_recusar_exige_parecer_fecha_o_pedido_e_avisa(api, sessao):
    p = _pedir(api)
    assert _decidir(api, "helena", p["id"], "analista", parecer="").status_code == 422
    r = _decidir(api, "helena", p["id"], "analista", aprovar=False, parecer="Já temos uma ferramenta de agenda aprovada.")
    assert r.status_code == 200 and r.json()["estado"] == "recusado" and r.json()["plugin_id"] is None
    assert _decidir(api, "helena", p["id"], "analista").status_code == 409                    # fechado: não decide de novo
    assert any("recusado" in a.titulo.lower() and "thiago" in a.destinatarios for a in sessao.exec(select(Alerta)).all())
    assert not any(v.interno for v in PLUGINS.values())


def test_so_a_analista_decide_e_ninguem_decide_o_proprio_pedido(api):
    p = _pedir(api)
    for perfil in ("thiago", "marina", "lucas"):
        assert _decidir(api, perfil, p["id"], "analista").status_code == 403, perfil
    assert _decidir(api, "helena", p["id"], "seguranca").status_code == 409                    # não é a etapa dela
    assert api.get(f"{PI}/{p['id']}", headers=como("thiago")).json()["pode_decidir"] is False


def test_dado_confidencial_passa_pela_seguranca_depois_da_analista(api):
    p = _pedir(api, classificacao="confidencial")
    assert p["exige_seguranca"] is True
    assert _decidir(api, "lucas", p["id"], "seguranca").status_code == 409                     # antes da analista: ainda não
    a = _decidir(api, "helena", p["id"], "analista")
    assert a.json()["estado"] == "aguardando_seguranca" and a.json()["plugin_id"] is None
    assert not any(v.interno for v in PLUGINS.values())                                        # ainda não publicou
    assert api.get(f"{PI}/{p['id']}", headers=como("lucas")).json()["pode_decidir"] is True      # a Segurança vê e decide
    assert _decidir(api, "helena", p["id"], "seguranca").status_code == 403                    # a analista não dá o aval de segurança
    assert _decidir(api, "thiago", p["id"], "seguranca").status_code == 403
    fim = _decidir(api, "lucas", p["id"], "seguranca", parecer="Escrita protegida por confirmação; áreas restritas. Aprovado.")
    assert fim.status_code == 200 and fim.json()["estado"] == "publicado" and fim.json()["decisao_seguranca"]["por"] == "lucas"
    assert any(v.interno for v in PLUGINS.values())
    escrita = [f for v in PLUGINS.values() if v.interno for f in v.ferramentas if f.acao == "escrita"]
    assert escrita and all(f.exige_aprovacao for f in escrita)                                 # escrita em dado confidencial pede confirmação


def test_seguranca_recusa_e_o_pedido_fecha(api):
    p = _pedir(api, classificacao="restrita")
    _decidir(api, "helena", p["id"], "analista")
    r = _decidir(api, "lucas", p["id"], "seguranca", aprovar=False, parecer="Dado restrito demais para um plugin conceitual.")
    assert r.json()["estado"] == "recusado" and r.json()["decisao_seguranca"]["aprovar"] is False
    assert not any(v.interno for v in PLUGINS.values())


def test_pedido_do_lucas_o_proprio_lucas_nao_aprova_a_etapa_de_seguranca(api):
    p = _pedir(api, perfil="lucas", classificacao="confidencial")
    assert _decidir(api, "lucas", p["id"], "analista").status_code == 403
    _decidir(api, "helena", p["id"], "analista")
    assert _decidir(api, "lucas", p["id"], "seguranca").status_code == 403                    # nunca o próprio pedido
    r = _decidir(api, "helena", p["id"], "seguranca")                                          # a outra pessoa decide (regra do v6)
    assert r.status_code == 200 and r.json()["estado"] == "publicado"


def test_integrar_usar_num_processo_e_remover_sinaliza_o_processo(api, sessao):
    pid = _decidir(api, "helena", _pedir(api)["id"], "analista").json()["plugin_id"]
    assert api.post(f"{V1}/plugins/{pid}/integrar", headers=como("thiago")).json()["resultado"] == "integrado"
    leitura = next(f for f in api.get(f"{V1}/plugins/{pid}", headers=como("thiago")).json()["ferramentas"] if f["acao"] == "leitura")
    cat = api.get(f"{V1}/ferramentas/{leitura['id']}", headers=como("thiago")).json()
    assert cat["origem"] == "plugin interno Ferramenta interna de agendamento"
    bp = {"nome": "Ver agenda da sala", "objetivo": "Consultar a agenda da sala pelo plugin interno.", "area": "logistica", "minutos_manual": 5,
          "campos": [{"id": "codigo", "rotulo": "Sala", "tipo": "texto", "exemplo": "Sala 3"}],
          "blocos": [{"id": "agenda", "tipo": "dados", "titulo": "Ver a agenda", "depende_de": [], "ferramenta": leitura["id"],
                      "entrada": {"codigo": "{{entrada.codigo}}"}}]}
    proc = api.post(f"{V1}/processos", json={"blueprint": bp}, headers=como("thiago")).json()
    assert api.post(f"{V1}/processos/{proc['id']}/publicar", headers=como("thiago")).json()["estado"] == "publicado"
    exe = api.post(f"{V1}/processos/{proc['id']}/executar", json={"entrada": {"codigo": "Sala 3"}}, headers=como("thiago")).json()
    assert exe["status"] == "concluida" and exe["passos"]["agenda"]["saida"]["simulado"] is True
    assert exe["passos"]["agenda"]["saida"]["registro"]["codigo"] == "Sala 3"
    # remover o plugin sinaliza o processo que depende dele
    r = api.delete(f"{V1}/plugins/{pid}/integracao", headers=como("thiago")).json()
    assert [x["nome"] for x in r["processos_afetados"]] == ["Ver agenda da sala"]
    assert any("depende" in a.titulo and "thiago" in a.destinatarios for a in sessao.exec(select(Alerta)).all())
    again = api.post(f"{V1}/processos/{proc['id']}/executar", json={"entrada": {"codigo": "Sala 3"}}, headers=como("thiago")).json()
    assert again["status"] != "concluida"


def test_ferramenta_de_escrita_do_plugin_interno_devolve_dado_ficticio(api):
    pid = _decidir(api, "helena", _pedir(api)["id"], "analista").json()["plugin_id"]
    api.post(f"{V1}/plugins/{pid}/integrar", headers=como("thiago"))
    escrita = next(f for f in api.get(f"{V1}/plugins/{pid}", headers=como("thiago")).json()["ferramentas"] if f["acao"] == "escrita")
    entrada = {k: "x" for k in escrita["parametros"]}
    r = api.post(f"{V1}/ferramentas/{escrita['id']}/testar", json={"entrada": entrada}, headers=como("thiago")).json()
    assert r["ok"] and r["saida"]["status"] == "registrado (simulado)" and r["saida"]["registro_id"].startswith("INT-")


def test_reiniciar_a_demo_remove_os_plugins_internos(api):
    pid = _decidir(api, "helena", _pedir(api)["id"], "analista").json()["plugin_id"]
    assert pid in PLUGINS
    assert api.post(f"{V1}/demo/reiniciar", headers=como("helena")).status_code == 200
    assert pid not in PLUGINS and not any(v.interno for v in PLUGINS.values())
    assert api.get(f"{V1}/plugins/{pid}", headers=como("thiago")).status_code == 404
    assert api.get(PI, headers=como("helena")).json() == []
    assert not any(k.startswith("interno_") for k in CATALOGO)


def test_plugin_interno_publicado_volta_na_partida(api, sessao):
    from app.plugins import servico
    pid = _decidir(api, "helena", _pedir(api)["id"], "analista").json()["plugin_id"]
    from app.plugins import interno
    interno.retirar_internos()                        # simula o servidor reiniciando: o registro em memória some
    assert pid not in PLUGINS
    servico.sincronizar(sessao)                       # o que a partida faz
    assert pid in PLUGINS and PLUGINS[pid].interno
