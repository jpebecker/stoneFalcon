"""v7/11: roteiro do pitch integrado (planilha -> extensão -> Estúdio -> rotina -> Mapa de IA -> provedores -> Finanças)."""
from app import rotinas
from app.llm import balanceador
from app.plugins import estado as plugins_estado
from app.roteiros.catalogo import ROTEIROS
from app.roteiros.perguntas import PERGUNTAS
from tests.conftest import como

V1 = "/api/v1"
R = ROTEIROS["pitch"]
NOME_AGENTE = "Troca de maquininha pela planilha"


def _passo(pid: str):
    return next(p for p in R.passos if p.id == pid)


def _agente(api, perfil="helena") -> dict | None:
    return next((a for a in api.get(f"{V1}/agentes", headers=como(perfil)).json() if a["nome"] == NOME_AGENTE), None)


def _iniciar(api):
    assert api.post(f"{V1}/roteiros/pitch/reiniciar", headers=como("thiago")).status_code == 200


def test_o_roteiro_roda_do_inicio_ao_fim_sem_digitar_e_sem_chave(api):
    _iniciar(api)
    estado_inicial = api.get(f"{V1}/plugins/sheets", headers=como("thiago")).json()["estado"]
    assert estado_inicial == "integrado" and api.get(f"{V1}/plugins/slack", headers=como("thiago")).json()["estado"] == "integrado"
    assert _agente(api) is None and api.get(f"{V1}/rotinas", headers=como("helena")).json() == []

    # 3. criar: o Estúdio abre com a fonte e monta o agente da planilha (a mesma chamada do botão "Montar meu agente")
    criar = _passo("criar").preenche
    sug = api.post(f"{V1}/estudio/sugerir", json={"descricao": criar["descricao"], "fonte": criar["fonte"]}, headers=como("thiago")).json()
    assert sug["origem"] == "planilha" and not sug["ferramentas_removidas"] and sug["alertas"] == []
    assert "slack_enviar_mensagem" in str(sug["blueprint"]["passos"])               # o aviso ao canal entra (Slack integrado)

    # 4. testar: sem chave, com a entrada pré-determinada; o balanceador explica cada passo com IA
    exe = api.post(f"{V1}/estudio/testar", json={"blueprint": sug["blueprint"], "entrada": _passo("testar").preenche["entrada"]},
                   headers=como("thiago")).json()
    assert exe["status"] == "concluida" and exe["simulado"] is True
    ia = [p for p in exe["passos"].values() if p["tipo"] == "agente"]
    assert ia and all(p["esforco"] and p["balanceador"]["candidatos"] and p["balanceador"]["motivo"] for p in ia)

    # 5. publicar
    aid = api.post(f"{V1}/agentes", json={"blueprint": sug["blueprint"], "nota": "pitch"}, headers=como("thiago")).json()["id"]
    assert api.post(f"{V1}/agentes/{aid}/publicar", headers=como("thiago")).json()["estado"] == "publicado"

    # 6. rotina semanal + Rodar agora
    rot = _passo("rotina").preenche
    r = api.post(f"{V1}/agentes/{aid}/rotinas", headers=como("thiago"),
                 json={"frequencia": rot["frequencia"], "dia_semana": rot["dia_semana"], "hora": 9, "minuto": 0, "entrada": rot["entrada"]})
    assert r.status_code == 200 and r.json()["descricao"] == "toda segunda às 09:00"
    rodou = api.post(f"{V1}/rotinas/{r.json()['id']}/rodar", headers=como("thiago")).json()
    assert rodou["status"] == "concluida" and rodou["execucao_detalhe"]["rotina"]["origem"] == "manual"

    # 7. mapa (Helena): o agente apareceu sozinho, com o selo da rotina na última execução
    mapa = api.get(f"{V1}/mapa", headers=como("helena")).json()
    assert "agente:" + aid in {n["id"] for n in mapa["nos"]}
    assert any(e["id"] == rodou["execucao"] and e["rotina"] for e in mapa["execucoes_recentes"])
    # o relógio da demo avança uma semana e a rotina dispara sozinha (o pulso do mapa)
    sozinha = api.post(f"{V1}/rotinas/relogio", json={"avancar_horas": 24 * 7}, headers=como("helena")).json()["disparadas"]
    assert len(sozinha) == 1 and sozinha[0]["status"] == "concluida"

    # 8. queda de provedor + carga (só Helena): o balanceador delega e a Saúde avisa
    assert api.post(f"{V1}/balanceador/provedores/anthropic/falha", json={"fora": True}, headers=como("helena")).status_code == 200
    carga = api.post(f"{V1}/balanceador/simular-carga", json={"passos": 300}, headers=como("helena")).json()
    assert "anthropic" not in {p["provedor"] for p in carga["por_provedor"]} and carga["custo_brl"] < carga["custo_tudo_forte_brl"]
    assert any(a["regra"] == "provedor_fora" for a in api.get(f"{V1}/alertas", headers=como("helena")).json())

    # 9. finanças: gasto por provedor e comparativo
    fin = api.get(f"{V1}/financas/resumo", headers=como("helena")).json()
    assert fin["por_provedor"] and api.get(f"{V1}/financas/comparativo?modelo=gpt-sol", headers=como("helena")).json()["cenarios"]

    # 10. cartão AS IS × TO BE com a rotina contando no ganho
    res = api.get(f"{V1}/roteiros/pitch/resultado?agente_id={aid}", headers=como("helena")).json()
    assert res["agente"]["nome"] == NOME_AGENTE and res["execucao"] and res["linhas"]
    assert res["rotina"]["agendas"] == ["toda segunda às 09:00"] and res["rotina"]["execucoes_feitas"] == 2
    assert res["rotina"]["execucoes_por_mes"] > 4 and res["rotina"]["ganho_mensal_brl"] > 0 and "premissa" in res["rotina"]["origem"]
    assert api.get(f"{V1}/auditoria", headers=como("helena")).json()["cadeia"]["integra"] is True


def test_reiniciar_devolve_planilha_plugin_agenda_e_balanceador_ao_estado_inicial(api):
    _iniciar(api)
    sug = api.post(f"{V1}/estudio/sugerir", json={"descricao": _passo("criar").preenche["descricao"], "fonte": _passo("criar").preenche["fonte"]},
                   headers=como("thiago")).json()
    aid = api.post(f"{V1}/agentes", json={"blueprint": sug["blueprint"], "nota": "p"}, headers=como("thiago")).json()["id"]
    api.post(f"{V1}/agentes/{aid}/publicar", headers=como("thiago"))
    api.post(f"{V1}/agentes/{aid}/rotinas", headers=como("thiago"),
             json={"frequencia": "semanal", "dia_semana": 0, "hora": 9, "minuto": 0, "entrada": {"planilha": "local:pedidos-troca"}})
    api.post(f"{V1}/rotinas/relogio", json={"avancar_horas": 48}, headers=como("helena"))
    api.post(f"{V1}/balanceador/provedores/google/falha", json={"fora": True}, headers=como("helena"))
    api.post(f"{V1}/balanceador/simular-carga", json={}, headers=como("helena"))
    api.post(f"{V1}/plugins/sheets/integracao", headers=como("thiago"))
    api.delete(f"{V1}/plugins/sheets/integracao", headers=como("thiago"))

    assert api.post(f"{V1}/roteiros/pitch/reiniciar", headers=como("helena")).status_code == 200
    assert _agente(api) is None and api.get(f"{V1}/rotinas", headers=como("helena")).json() == []
    assert not balanceador.fora_do_ar() and balanceador.ultima_carga() is None
    assert plugins_estado.integrado("sheets") and plugins_estado.integrado("slack")
    assert rotinas.relogio.fator == 1.0
    # a planilha da demo continua a mesma (4 linhas fictícias, 3 pendentes)
    assert len(api.get(f"{V1}/demo/planilha").json()["linhas"]) == 4


def test_roteiro_do_pitch_so_aparece_para_a_helena_mas_o_thiago_consegue_carregar(api):
    assert "pitch" in [r["id"] for r in api.get(f"{V1}/roteiros", headers=como("helena")).json()]
    assert "pitch" not in [r["id"] for r in api.get(f"{V1}/roteiros", headers=como("thiago")).json()]
    for perfil, ok in [("thiago", True), ("helena", True), ("marina", False), ("rafael", False), ("carla", False), ("lucas", False)]:
        assert (api.get(f"{V1}/roteiros/pitch", headers=como(perfil)).status_code == 200) == ok, perfil


def test_falas_marcam_onde_cada_recurso_da_v7_aparece_e_cabem_no_tempo():
    marcas = {pid: _passo(pid).fala for pid in ("criar", "testar", "rotina", "mapa", "queda", "financas")}
    assert all("[v7:" in f for f in marcas.values()), marcas
    palavras = sum(len(p.fala.split()) for p in R.passos)
    assert palavras / 150 <= 5          # fala corrida (150 palavras/min) <= 5 min; o resto do tempo são cliques e telas
    assert R.duracao_min <= 10          # o pitch de 8 a 10 minutos (ENSAIO-GERAL.md)


def test_perguntas_novas_apontam_para_passos_do_pitch_com_o_perfil_certo():
    novas = [q for q in PERGUNTAS if q["id"] in ("helena-6", "helena-7", "thiago-6")]
    assert len(novas) == 3
    for q in novas:
        passo = _passo(q["prova"]["passo"])
        assert q["prova"]["roteiro"] == "pitch" and passo.perfil == q["prova"]["perfil"]
    assert "simulados" in next(q for q in novas if q["id"] == "helena-6")["resposta"]


def test_plano_b_para_o_que_depende_do_navegador_e_da_internet():
    """O roteiro nunca depende da internet: a planilha é a local e o helpdesk fictício vem da própria plataforma."""
    assert _passo("planilha").externa and _passo("planilha").rota.startswith("/demo/")
    assert _passo("criar").preenche["fonte"]["url"] == "local:pedidos-troca"
