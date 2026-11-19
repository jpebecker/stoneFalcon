"""Correções da revisão da v7 (itens 1 a 12): comparativo, relógio, perfil, queda do Claude, rotinas, Estúdio, Mapa,
esforço e planilhas."""
from datetime import timedelta
from pathlib import Path

import pytest
from sqlmodel import Session

from app import rotinas
from app.agents import modelos as am
from app.core import db
from app.core.identidade import PERSONAS
from app.finance.resumo import _custo_em
from app.llm import balanceador, precos, registro
from app.llm.cliente import ErroModelo
from app.plugins import planilhas
from app.roteiros.catalogo import ROTEIROS
from app.runtime import modelos as rm
from app.seed.demo import semear
from app.studio import sugestao
from tests.conftest import como
from tests.test_rotinas import SEGUNDA_9H, SEXTA, _agente, _criar, _criar_processo, _processo_triagem

V1 = "/api/v1"


# ---------- 1. comparativo: a faixa "contexto longo" vale por chamada, não pelo total da execução ----------
def test_comparativo_cobra_cada_chamada_na_faixa_dela():
    # 6 chamadas de 20 mil tokens: 120 mil no total, mas nenhuma chamada passa do limite de 100 mil do Haiku
    e = rm.Execucao(id="x", chamadas_modelo=6, tokens_entrada=120_000, tokens_saida=6_000,
                    por_modelo={"forte": {"chamadas": 6, "custo_usd": 0.0, "tokens_entrada": 120_000, "tokens_saida": 6_000}})
    esperado = 6 * precos.custo_usd("rapido", 20_000, 1_000)
    assert abs(_custo_em("rapido", e) - esperado) < 1e-12
    assert _custo_em("rapido", e) < precos.custo_usd("rapido", 120_000, 6_000)   # o cálculo antigo caía na faixa longa


def test_comparativo_sem_detalhe_por_modelo_usa_as_chamadas_da_execucao():
    e = rm.Execucao(id="y", chamadas_modelo=2, tokens_entrada=4_000, tokens_saida=800, tokens_cache=200, por_modelo={})
    assert abs(_custo_em("forte", e) - 2 * precos.custo_usd("forte", 2_000, 400, 100)) < 1e-12


# ---------- 2. relógio da demo: só o CoE e os criadores ----------
def test_relogio_so_coe_e_criadores(api):
    assert api.post(f"{V1}/rotinas/relogio", json={"avancar_horas": 1}, headers=como("lucas")).status_code == 403
    assert api.get(f"{V1}/rotinas/relogio", headers=como("lucas")).json()["pode_mexer"] is False
    for quem in ("helena", "thiago"):
        assert api.get(f"{V1}/rotinas/relogio", headers=como(quem)).json()["pode_mexer"] is True
        assert api.post(f"{V1}/rotinas/relogio", json={"zerar": True}, headers=como(quem)).status_code == 200


# ---------- 3. ?perfil= no endereço da planilha fictícia não escolhe o perfil ----------
def test_planilha_ficticia_nao_le_o_perfil_do_endereco():
    html = (Path(__file__).resolve().parents[1] / "app" / "static" / "planilha.html").read_text(encoding="utf-8")
    assert 'get("perfil")' not in html and "URLSearchParams(location.search)" not in html
    assert all("perfil=" not in p.rota for p in ROTEIROS["pitch"].passos)


# ---------- 4. modo real: a queda simulada do Claude delega a um provedor simulado ----------
def test_queda_do_claude_no_modo_real_delega():
    try:
        assert balanceador.escolher(2, so_reais=True).modelo.provedor == "anthropic"
        balanceador.marcar_fora("anthropic", True)
        for idx in (1, 2, 3):
            e = balanceador.escolher(idx, n_ferramentas=1, so_reais=True)
            assert e.modo == "delegado" and e.modelo.provedor != "anthropic"
            assert not registro.roda_de_verdade(e.modelo.chave) and "simulado" in e.motivo
    finally:
        balanceador.zerar()


def test_falha_real_sem_queda_simulada_continua_sem_simulados():
    # falha de verdade numa chamada (excluir), sem queda simulada: segue a regra antiga (reserva), sem inventar provedor
    e = balanceador.escolher(2, so_reais=True, excluir={"anthropic"})
    assert e.modo == "emergencia" and e.modelo.provedor == "anthropic"


# =============================================================
# Sugestões 5 a 12 da revisão
# =============================================================
@pytest.fixture()
def relogio_na_sexta(motor):
    rotinas.relogio.fixar(SEXTA)
    yield
    rotinas.relogio.zerar()


# ---------- 5. "Rodar agora" só por quem agendou (a execução usa o acesso dessa pessoa) ----------
def test_rodar_agora_so_quem_agendou(api, sessao, relogio_na_sexta):
    triagem = _processo_triagem(api)
    assert api.post(f"{V1}/processos/{triagem}/compartilhar", json={"areas": ["atendimento"]}, headers=como("rafael")).status_code == 200
    rid = _criar_processo(api, triagem, "marina", entrada={"lojista_id": "L1003"}).json()["id"]
    lista = {r["id"]: r for r in api.get(f"{V1}/rotinas", headers=como("rafael")).json()}
    assert lista[rid]["pode_gerir"] is True and lista[rid]["pode_rodar"] is False
    r = api.post(f"{V1}/rotinas/{rid}/rodar", headers=como("rafael"))          # dono do agente, mas não agendou
    assert r.status_code == 403 and "quem agendou" in r.json()["detail"]
    assert api.post(f"{V1}/rotinas/{rid}/pausar", headers=como("rafael")).status_code == 200   # gerir continua valendo
    assert api.post(f"{V1}/rotinas/{rid}/rodar", headers=como("marina")).status_code == 200


# ---------- 6. uma rotina com defeito não derruba as outras do mesmo tick ----------
def test_tick_isola_a_rotina_que_falha(api, monkeypatch, relogio_na_sexta):
    r1 = _criar(api, _agente(api)).json()["id"]
    r2 = _criar(api, _agente(api)).json()["id"]
    original = rotinas.motor.executar

    def executar(s, pessoa, bp, entrada, **kw):
        if kw.get("agente_id") == primeira_agente:
            raise RuntimeError("defeito de teste")
        return original(s, pessoa, bp, entrada, **kw)

    with Session(db.motor()) as s:
        primeira_agente = s.get(rotinas.Rotina, r1).agente_id
    monkeypatch.setattr(rotinas.motor, "executar", executar)
    rotinas.relogio.fixar(SEGUNDA_9H + timedelta(minutes=1))
    with Session(db.motor()) as s:
        feitas = {f["rotina"]: f for f in rotinas.tick(s)}
    assert feitas[r1]["status"] == "pulada" and "defeito de teste" in feitas[r1]["motivo"]
    assert feitas[r2]["execucao"] is not None
    with Session(db.motor()) as s:
        assert s.get(rotinas.Rotina, r1).ultimo_resultado.startswith("falhou")
        assert s.get(rotinas.Rotina, r1).proxima_em > (SEGUNDA_9H + timedelta(minutes=1)).isoformat()   # não tenta de novo


# ---------- 7. erro do ciclo vira resposta HTTP, não 500 ----------
def test_rotina_de_agente_que_sumiu_responde_404(api, sessao, relogio_na_sexta):
    aid = _agente(api)
    rid = _criar(api, aid).json()["id"]
    sessao.delete(sessao.get(am.Agente, aid))
    sessao.commit()
    for rota in ("pausar", "retomar", "rodar"):
        assert api.post(f"{V1}/rotinas/{rid}/{rota}", headers=como("thiago")).status_code == 404, rota
    assert api.delete(f"{V1}/rotinas/{rid}", headers=como("thiago")).status_code == 404


# ---------- 8. planilha sem o plugin Sheets: o modelo real continua sendo tentado ----------
def test_planilha_sem_plugin_ainda_tenta_o_modelo_real(monkeypatch):
    chamadas = []

    def com_modelo(pessoa, descricao):
        chamadas.append(descricao)
        raise ErroModelo("sem modelo no teste")

    monkeypatch.setattr(sugestao, "_com_modelo", com_modelo)
    sug = sugestao.sugerir(PERSONAS["thiago"], "Tratar os pedidos de troca de maquininha da planilha", simulado=False,
                           fonte={"tipo": "planilha", "url": planilhas.LOCAL_ID})
    assert chamadas and sug.origem != "planilha"
    assert any("Google Sheets" in a for a in sug.alertas)


# ---------- 9. Mapa: o filtro de provedor vale para as execuções recentes e para os totais ----------
def test_mapa_filtrado_por_provedor_so_mostra_execucoes_dele(api, sessao):
    semear(sessao)
    for pid in ("anthropic", "google"):
        m = api.get(f"{V1}/mapa?dias=30&provedor={pid}", headers=como("helena")).json()
        nomes = {mo.nome for mo in registro.do_provedor(pid)}
        assert all(set(e["modelos"]) <= nomes and e["modelos"] for e in m["execucoes_recentes"]), pid
        assert sum(n["execucoes"] for n in m["nos"] if n["tipo"] in ("agente", "processo")) == m["totais"]["execucoes"], pid
    todos = api.get(f"{V1}/mapa?dias=30", headers=como("helena")).json()["totais"]["execucoes"]
    google = api.get(f"{V1}/mapa?dias=30&provedor=google", headers=como("helena")).json()["totais"]["execucoes"]
    assert 0 < google < todos


# ---------- 10. nível de esforço não depende da ordem das regras ----------
def test_risco_alto_com_muitas_ferramentas_e_critico_mesmo_com_texto_medio():
    assert balanceador.classificar_esforco(0.40, 3, 1_000, "alto")[0] == 4
    assert balanceador.classificar_esforco(0.70, 3, 1_000, "alto")[0] == 4
    assert balanceador.classificar_esforco(0.40, 1, 1_000, "alto")[0] == 3


# ---------- 11. gid da planilha não injeta parâmetros no endereço do CSV ----------
def test_gid_nao_injeta_parametros():
    base = "https://docs.google.com/spreadsheets/d/abc123/edit"
    assert planilhas.endereco_csv(base + "?gid=42") == "https://docs.google.com/spreadsheets/d/abc123/export?format=csv&gid=42"
    sujo = planilhas.endereco_csv(base + "?gid=0%26format%3Dhtml")
    assert sujo == "https://docs.google.com/spreadsheets/d/abc123/export?format=csv" and "html" not in sujo
