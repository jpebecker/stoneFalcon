"""Trilha encadeada: qualquer alteração ou remoção depois de gravada é detectada."""
from sqlalchemy import text

from app.audit import trilha
from tests.conftest import como


def _popular(s, n=5):
    for i in range(n):
        trilha.registrar(s, "execucao", "marina", agente_id="ag-1", dados={"passo": i})


def test_cadeia_integra(sessao):
    _popular(sessao)
    assert trilha.verificar(sessao) == {"integra": True, "quebra_em": None, "total": 5}


def test_detecta_alteracao(sessao):
    _popular(sessao)
    sessao.exec(text("UPDATE auditoria SET dados = '{\"passo\": 99}' WHERE seq = 3"))
    sessao.commit()
    sessao.expire_all()
    r = trilha.verificar(sessao)
    assert not r["integra"] and r["quebra_em"] == 3


def test_detecta_remocao(sessao):
    _popular(sessao)
    sessao.exec(text("DELETE FROM auditoria WHERE seq = 2"))
    sessao.commit()
    sessao.expire_all()
    r = trilha.verificar(sessao)
    assert not r["integra"] and r["quebra_em"] == 3


def test_auditoria_so_para_coe_e_seguranca(api):
    assert api.get("/api/v1/auditoria", headers=como("marina")).status_code == 403
    assert api.get("/api/v1/auditoria", headers=como("helena")).status_code == 200
    assert api.get("/api/v1/auditoria/verificar", headers=como("lucas")).json()["integra"] is True


def test_sem_login_e_recusado(api):
    assert api.get("/api/v1/eu").status_code == 401
    assert api.get("/api/v1/eu", headers=como("helena")).json()["papeis"] == ["ai_analyst", "criador", "gestor_ia", "usuario"]


def test_saude_informa_modo_simulado(api):
    corpo = api.get("/api/v1/saude").json()
    assert corpo["ok"] and corpo["modo"] == "simulado" and corpo["modelos"]["rapido"] == "Claude Haiku 5.5"
