"""v7/09: tarefa de rotina (agente com agenda): relógio controlado, permissões de quem agendou, confirmação humana."""
from datetime import datetime, timedelta

import pytest
from sqlmodel import Session

from app import rotinas
from app.core import db
from app.core.relogio import FUSO
from app.seed.demo import semear
from app.tools import dados_ficticios as fx
from tests.conftest import como

V1 = "/api/v1"
SEXTA = datetime(2026, 11, 20, 10, 0, tzinfo=FUSO)          # sexta-feira
SEGUNDA_9H = datetime(2026, 11, 23, 9, 0, tzinfo=FUSO)

ESTOQUE = {
    "nome": "Conferência de estoque", "objetivo": "Consultar o estoque da maquininha toda semana.", "area": "logistica",
    "minutos_manual": 12,
    "campos": [{"id": "modelo", "rotulo": "Modelo", "tipo": "texto", "exemplo": "Maquininha Pro"}],
    "passos": [{"id": "estoque", "titulo": "Consultar o estoque", "tipo": "ferramenta", "ferramenta": "consultar_estoque",
                "entrada": {"modelo": "{{entrada.modelo}}"}}],
}
ENTRADA = {"modelo": "Maquininha Pro"}


@pytest.fixture(autouse=True)
def relogio_parado(motor):          # depois do `motor`, que zera o relógio no começo de cada teste
    rotinas.relogio.fixar(SEXTA)
    yield
    rotinas.relogio.zerar()


def _agente(api, perfil="thiago", bp=ESTOQUE) -> str:
    aid = api.post(f"{V1}/agentes", json={"blueprint": bp, "nota": "rotina"}, headers=como(perfil)).json()["id"]
    assert api.post(f"{V1}/agentes/{aid}/publicar", headers=como(perfil)).json()["estado"] == "publicado"
    return aid


def _criar(api, aid, perfil="thiago", **corpo):
    padrao = {"frequencia": "semanal", "dia_semana": 0, "hora": 9, "minuto": 0, "entrada": ENTRADA}
    return api.post(f"{V1}/agentes/{aid}/rotinas", json={**padrao, **corpo}, headers=como(perfil))


def _tick(momento: datetime) -> list[dict]:
    rotinas.relogio.fixar(momento)
    with Session(db.motor()) as s:
        return rotinas.tick(s)


def _tipos_auditoria(api) -> list[str]:
    return [e["tipo"] for e in api.get(f"{V1}/auditoria?limite=1000", headers=como("helena")).json()["eventos"]]


# ---------- agenda ----------
def test_thiago_agenda_toda_segunda_as_9h_e_ela_aparece_na_pagina_do_agente(api):
    aid = _agente(api)
    r = _criar(api, aid)
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["descricao"] == "toda segunda às 09:00" and d["dono"] == "thiago" and d["ativa"] is True
    assert datetime.fromisoformat(d["proxima_em"]) == SEGUNDA_9H
    lista = api.get(f"{V1}/agentes/{aid}/rotinas", headers=como("thiago")).json()
    assert [x["id"] for x in lista] == [d["id"]] and lista[0]["pode_gerir"] is True
    assert "rotina_criada" in _tipos_auditoria(api)


@pytest.mark.parametrize("freq,dia,hora,esperado", [
    ("semanal", 4, 11, datetime(2026, 11, 20, 11, 0, tzinfo=FUSO)),       # sexta, hora ainda não passou: hoje
    ("semanal", 4, 9, datetime(2026, 11, 27, 9, 0, tzinfo=FUSO)),         # sexta, hora já passou: semana que vem
    ("semanal", 6, 8, datetime(2026, 11, 22, 8, 0, tzinfo=FUSO)),         # domingo
    ("diaria", None, 9, datetime(2026, 11, 21, 9, 0, tzinfo=FUSO)),       # diária, 9h já passou: amanhã
    ("diaria", None, 18, datetime(2026, 11, 20, 18, 0, tzinfo=FUSO)),
])
def test_proximo_disparo_e_sempre_depois_de_agora(api, freq, dia, hora, esperado):
    aid = _agente(api)
    d = _criar(api, aid, frequencia=freq, dia_semana=dia, hora=hora).json()
    assert datetime.fromisoformat(d["proxima_em"]) == esperado


def test_validacoes_da_agenda(api):
    aid = _agente(api)
    assert _criar(api, aid, frequencia="mensal").status_code == 422
    assert _criar(api, aid, frequencia="semanal", dia_semana=None).status_code == 422
    assert _criar(api, aid, hora=25).status_code in (422,)
    assert _criar(api, aid, entrada={}).status_code == 422                                  # faltou a entrada fixa
    pii = _criar(api, aid, entrada={"modelo": "Pro, falar com ana@exemplo.com"})
    assert pii.status_code == 422 and "dado pessoal" in pii.json()["detail"]
    assert api.get(f"{V1}/agentes/{aid}/rotinas", headers=como("thiago")).json() == []


def test_so_agente_publicado_tem_rotina(api):
    aid = api.post(f"{V1}/agentes", json={"blueprint": ESTOQUE, "nota": "x"}, headers=como("thiago")).json()["id"]
    assert _criar(api, aid).status_code == 409


# ---------- quem pode ----------
def test_so_criador_com_acesso_ao_agente_agenda(api, sessao):
    semear(sessao)
    triagem = next(a["id"] for a in api.get(f"{V1}/agentes", headers=como("helena")).json() if a["nome"] == "Triagem de chargebacks")
    corpo = {"entrada": {"lojista_id": "L1001"}}
    assert _criar(api, triagem, "marina", **corpo).status_code == 403          # outra área, agente não compartilhado
    assert _criar(api, triagem, "helena", **corpo).status_code == 403          # sem papel de criador
    assert _criar(api, triagem, "lucas", **corpo).status_code == 403
    assert _criar(api, triagem, "rafael", **corpo).status_code == 200


# ---------- relógio controlado ----------
def test_com_o_relogio_controlado_a_rotina_dispara_sozinha_na_hora_marcada(api):
    aid = _agente(api)
    d = _criar(api, aid).json()
    assert _tick(datetime(2026, 11, 22, 23, 59, tzinfo=FUSO)) == []                  # domingo à noite: nada
    feitas = _tick(SEGUNDA_9H)
    assert len(feitas) == 1 and feitas[0]["rotina"] == d["id"] and feitas[0]["status"] == "concluida"
    assert _tick(SEGUNDA_9H + timedelta(minutes=1)) == []                            # nunca dispara duas vezes
    nova = api.get(f"{V1}/agentes/{aid}/rotinas", headers=como("thiago")).json()[0]
    assert datetime.fromisoformat(nova["proxima_em"]) == SEGUNDA_9H + timedelta(days=7)
    assert nova["ultimo_resultado"] == "concluida" and nova["ultima_execucao_id"] == feitas[0]["execucao"]
    assert "rotina_disparada" in _tipos_auditoria(api)


def test_servidor_parado_varias_semanas_roda_uma_vez_so(api):
    aid = _agente(api)
    _criar(api, aid)
    assert len(_tick(SEGUNDA_9H + timedelta(days=21))) == 1
    assert _tick(SEGUNDA_9H + timedelta(days=21, minutes=1)) == []


def test_relogio_da_demo_avanca_e_dispara(api):
    aid = _agente(api)
    _criar(api, aid)
    r = api.post(f"{V1}/rotinas/relogio", json={"avancar_horas": 24 * 3}, headers=como("thiago"))   # sexta 10h + 3 dias
    assert r.status_code == 200
    d = r.json()
    assert datetime.fromisoformat(d["agora"]) >= datetime(2026, 11, 23, 10, 0, tzinfo=FUSO) and len(d["disparadas"]) == 1
    assert api.get(f"{V1}/rotinas/relogio", headers=como("thiago")).json()["demo"] is True


def test_relogio_acelerado_so_no_modo_demo(api, monkeypatch):
    from app.core import config
    monkeypatch.setattr(config, "MODO_DEMO", False)
    assert api.post(f"{V1}/rotinas/relogio", json={"avancar_horas": 1}, headers=como("thiago")).status_code == 403


def test_fator_de_aceleracao_faz_o_tempo_correr(api):
    rotinas.relogio.zerar()
    rotinas.relogio.acelerar(3600)         # 1 s = 1 h
    import time
    antes = rotinas.relogio.agora()
    time.sleep(1.1)
    assert rotinas.relogio.agora() - antes >= timedelta(minutes=50)


# ---------- rodar agora e selo ----------
def test_rodar_agora_executa_e_a_execucao_ganha_o_selo_rotina(api):
    aid = _agente(api)
    rid = _criar(api, aid).json()["id"]
    r = api.post(f"{V1}/rotinas/{rid}/rodar", headers=como("thiago"))
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["status"] == "concluida" and d["execucao_detalhe"]["rotina"] == {"rotina": rid, "origem": "manual"}
    lista = api.get(f"{V1}/execucoes", headers=como("thiago")).json()
    assert next(e for e in lista if e["id"] == d["execucao"])["rotina"]["rotina"] == rid
    assert api.get(f"{V1}/execucoes/{d['execucao']}", headers=como("thiago")).json()["rotina"]["origem"] == "manual"
    assert api.get(f"{V1}/agentes/{aid}/execucoes", headers=como("thiago")).json()[0]["rotina"]["rotina"] == rid
    manual = api.post(f"{V1}/agentes/{aid}/executar", json={"entrada": ENTRADA}, headers=como("thiago")).json()
    assert api.get(f"{V1}/execucoes/{manual['id']}", headers=como("thiago")).json()["rotina"] is None   # a manual não tem selo


def test_execucao_de_rotina_aparece_no_mapa_com_o_selo(api):
    aid = _agente(api)
    rid = _criar(api, aid).json()["id"]
    exe = api.post(f"{V1}/rotinas/{rid}/rodar", headers=como("thiago")).json()["execucao"]
    recentes = api.get(f"{V1}/mapa", headers=como("helena")).json()["execucoes_recentes"]
    assert next(e for e in recentes if e["id"] == exe)["rotina"] is True


def test_rotina_roda_em_nome_de_quem_agendou(api):
    aid = _agente(api)
    rid = _criar(api, aid).json()["id"]
    exe = api.post(f"{V1}/rotinas/{rid}/rodar", headers=como("thiago")).json()["execucao"]
    assert api.get(f"{V1}/execucoes/{exe}", headers=como("thiago")).json()["persona"] == "thiago"
    feitas = _tick(SEGUNDA_9H)
    assert api.get(f"{V1}/execucoes/{feitas[0]['execucao']}", headers=como("helena")).json()["persona"] == "thiago"


# ---------- mesmas permissões, guardrails e orçamento ----------
def test_rotina_nao_roda_ferramenta_que_quem_agendou_nao_poderia(api, sessao):
    semear(sessao)
    triagem = next(a["id"] for a in api.get(f"{V1}/agentes", headers=como("helena")).json() if a["nome"] == "Triagem de chargebacks")
    assert api.post(f"{V1}/agentes/{triagem}/compartilhar", json={"areas": ["atendimento"]}, headers=como("rafael")).status_code == 200
    rid = _criar(api, triagem, "marina", entrada={"lojista_id": "L1003"}).json()["id"]          # Marina só tem acesso interno
    r = api.post(f"{V1}/rotinas/{rid}/rodar", headers=como("marina")).json()
    exe = api.get(f"{V1}/execucoes/{r['execucao']}", headers=como("marina")).json()
    assert exe["status"] == "escalada" and not fx.BLOQUEIOS
    negadas = [e for e in api.get(f"{V1}/auditoria?limite=1000", headers=como("helena")).json()["eventos"]
               if e["tipo"] in ("ferramenta_negada", "execucao_negada") and e["ator"] == "marina"]
    assert negadas


def test_acao_sensivel_dentro_da_rotina_espera_confirmacao_humana(api, sessao):
    semear(sessao)
    triagem = next(a["id"] for a in api.get(f"{V1}/agentes", headers=como("helena")).json() if a["nome"] == "Triagem de chargebacks")
    rid = _criar(api, triagem, "rafael", entrada={"lojista_id": "L1003"}).json()["id"]
    feitas = _tick(SEGUNDA_9H)
    assert feitas and feitas[0]["status"] == "aguardando_aprovacao"
    assert not fx.BLOQUEIOS                                           # nada executou sozinho
    d = api.post(f"{V1}/execucoes/{feitas[0]['execucao']}/decisao", json={"aprovar": True}, headers=como("rafael"))
    assert d.status_code == 200 and [b["lojista_id"] for b in fx.BLOQUEIOS] == ["L1003"]
    assert rid


def test_rotina_respeita_o_orcamento_do_mes(api):
    aid = _agente(api)
    rid = _criar(api, aid).json()["id"]
    api.post(f"{V1}/agentes/{aid}/executar", json={"entrada": ENTRADA}, headers=como("thiago"))
    from sqlmodel import select
    from app.runtime import modelos as rm
    with Session(db.motor()) as s:
        for e in s.exec(select(rm.Execucao).where(rm.Execucao.agente_id == aid)):
            e.custo_usd = 10.0
            s.add(e)
        s.commit()
    assert api.put(f"{V1}/agentes/{aid}/orcamento", json={"valor_brl": 1}, headers=como("thiago")).status_code == 200
    r = api.post(f"{V1}/rotinas/{rid}/rodar", headers=como("thiago")).json()
    assert r["execucao"] is None and r["status"] == "pulada" and "orçamento" in r["motivo"]
    assert "rotina_pulada" in _tipos_auditoria(api)
    assert api.get(f"{V1}/agentes/{aid}/rotinas", headers=como("thiago")).json()[0]["ultimo_resultado"].startswith("pulada")


def test_agente_pausado_pula_a_rotina(api):
    aid = _agente(api)
    _criar(api, aid)
    assert api.post(f"{V1}/agentes/{aid}/pausar", json={"motivo": "teste"}, headers=como("thiago")).status_code == 200
    feitas = _tick(SEGUNDA_9H)
    assert feitas and feitas[0]["status"] == "pulada" and feitas[0]["execucao"] is None


# ---------- pausar, retomar, remover ----------
def test_pausar_retomar_e_remover_ficam_na_auditoria(api):
    aid = _agente(api)
    rid = _criar(api, aid).json()["id"]
    assert api.post(f"{V1}/rotinas/{rid}/pausar", headers=como("thiago")).json()["ativa"] is False
    assert _tick(SEGUNDA_9H) == []                                               # pausada não dispara
    r = api.post(f"{V1}/rotinas/{rid}/retomar", headers=como("thiago")).json()
    assert r["ativa"] is True and datetime.fromisoformat(r["proxima_em"]) > SEGUNDA_9H
    assert api.delete(f"{V1}/rotinas/{rid}", headers=como("thiago")).json()["ok"] is True
    assert api.get(f"{V1}/agentes/{aid}/rotinas", headers=como("thiago")).json() == []
    tipos = _tipos_auditoria(api)
    assert {"rotina_criada", "rotina_pausada", "rotina_retomada", "rotina_removida"} <= set(tipos)


def test_so_quem_agendou_ou_os_criadores_da_area_gerem(api):
    aid = _agente(api)
    rid = _criar(api, aid).json()["id"]
    for rota in ("pausar", "retomar", "rodar"):
        assert api.post(f"{V1}/rotinas/{rid}/{rota}", headers=como("marina")).status_code == 403, rota
    assert api.delete(f"{V1}/rotinas/{rid}", headers=como("marina")).status_code == 403
    assert api.post(f"{V1}/rotinas/nada/pausar", headers=como("thiago")).status_code == 404


def test_auditoria_continua_integra_com_as_rotinas(api):
    aid = _agente(api)
    rid = _criar(api, aid).json()["id"]
    api.post(f"{V1}/rotinas/{rid}/rodar", headers=como("thiago"))
    _tick(SEGUNDA_9H)
    assert api.get(f"{V1}/auditoria", headers=como("helena")).json()["cadeia"]["integra"] is True


# ---------- reiniciar ----------
def test_reiniciar_a_demo_remove_as_agendas_e_volta_o_relogio(api):
    aid = _agente(api)
    _criar(api, aid)
    assert api.get(f"{V1}/rotinas", headers=como("thiago")).json()
    assert api.post(f"{V1}/demo/reiniciar", headers=como("helena")).json()["ok"]
    assert api.get(f"{V1}/rotinas", headers=como("helena")).json() == []
    assert rotinas.relogio.fator == 1.0 and abs((rotinas.relogio.agora() - datetime.now(FUSO)).total_seconds()) < 5
