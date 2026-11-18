"""v7/06: balanceador por nível de esforço (nível, candidatos, motivo, queda de provedor, orçamento, carga de teste)."""
import pytest
from sqlmodel import Session

from app.agents.blueprint import Blueprint
from app.core import db
from app.core.identidade import PERSONAS
from app.llm import balanceador, registro, roteador
from app.llm.cliente import ClienteSimulado, ErroModelo
from app.runtime import motor
from tests.conftest import como

V1 = "/api/v1"
ANALISE = ("Analise o risco comparando as contestações com o faturamento, avalie a tendência, calcule a "
           "probabilidade de fraude e justifique cada fator da decisão; considere 3 sinais e 2 hipóteses.")


def _bp(modelo: str = "auto", instrucao: str = "Redija a resposta.") -> dict:
    return {"nome": "Agente do balanceador", "area": "atendimento", "objetivo": "Testar o balanceador de modelos",
            "minutos_manual": 5,
            "passos": [{"id": "a", "titulo": "Passo", "tipo": "agente", "instrucao": instrucao, "modelo": modelo}]}


# ---------- nível de esforço ----------
@pytest.mark.parametrize("nota,ferr,ctx,risco,esperado", [
    (0.10, 0, 1_000, "baixo", "leve"),
    (0.40, 1, 1_000, "baixo", "moderado"),
    (0.70, 1, 1_000, "baixo", "alto"),
    (0.90, 1, 1_000, "baixo", "critico"),
    (0.40, 3, 1_000, "baixo", "alto"),          # muitas ferramentas sobem um nível
    (0.40, 1, 1_000, "alto", "alto"),           # agente de risco alto
    (0.70, 3, 1_000, "alto", "critico"),
    (0.10, 0, 150_000, "baixo", "alto"),        # contexto longo
])
def test_nivel_de_esforco_pelos_quatro_sinais(nota, ferr, ctx, risco, esperado):
    idx, motivos = balanceador.classificar_esforco(nota, ferr, ctx, risco)
    assert balanceador.NIVEIS[idx - 1] == esperado and motivos


def test_passo_leve_vai_a_modelo_leve_e_critico_a_modelo_forte():
    leve = roteador.decidir("auto", "Redija a resposta.", 800)
    critico = roteador.decidir("auto", ANALISE * 3, 800, n_ferramentas=3, risco="alto")
    assert leve.esforco == "leve" and registro.obter(leve.chave_modelo).capacidades.raciocinio <= 2
    assert critico.esforco == "critico" and registro.obter(critico.chave_modelo).capacidades.raciocinio == 4
    assert registro.obter(leve.chave_modelo).peso < registro.obter(critico.chave_modelo).peso


def test_decisao_traz_nivel_candidatos_escolhido_e_motivo():
    d = roteador.decidir("auto", ANALISE, 800, n_ferramentas=2)
    t = d.trilha()
    assert t["esforco"] == d.esforco and t["escolhido"] == d.chave_modelo and t["motivo"] and t["provedor"]
    assert len(t["candidatos"]) == len(registro.todos())
    escolhido = next(c for c in t["candidatos"] if c["chave"] == d.chave_modelo)
    assert escolhido["descartado"] is None
    assert any(c["descartado"] for c in t["candidatos"])          # os que não atendem dizem por quê
    assert any("escolhi" in m for m in d.motivos)


def test_modelo_fixado_pelo_criador_continua_respeitado():
    d = roteador.decidir("gpt-astra", "Redija a resposta.", 800)
    assert (d.chave_modelo, d.modo) == ("gpt-astra", "fixado")
    balanceador.marcar_fora("openai", True)           # mesmo com o provedor fora, o criador mandou
    assert roteador.decidir("gpt-astra", "x", 10).chave_modelo == "gpt-astra"
    assert roteador.decidir("rapido", "x", 10).chave_modelo == "rapido"


# ---------- escolha ----------
def test_normal_prefere_o_homologado_dentro_da_tolerancia_e_economia_vai_ao_mais_barato():
    normal = balanceador.escolher(3)
    economia = balanceador.escolher(3, economia=True)
    assert normal.modelo.provedor == "anthropic" and normal.modo == "normal"
    assert economia.modelo.peso < normal.modelo.peso and economia.modo == "economia" and "orçamento" in economia.motivo


def test_queda_do_provedor_delega_a_outro_provedor_capaz():
    antes = balanceador.escolher(2)
    balanceador.marcar_fora(antes.modelo.provedor, True)
    depois = balanceador.escolher(2)
    assert depois.modelo.provedor != antes.modelo.provedor and depois.modo == "delegado"
    assert "indisponível" in depois.motivo
    caiu = [c for c in depois.candidatos if c["provedor"] == antes.modelo.provedor]
    assert caiu and all(c["descartado"] == "provedor indisponível" for c in caiu)


def test_modo_real_so_considera_modelos_que_rodam_de_verdade():
    e = balanceador.escolher(3, economia=True, so_reais=True)
    assert e.modelo.provedor == "anthropic"
    assert balanceador.escolher(4, so_reais=True).modo == "emergencia"     # nenhum real atende o crítico


def test_sem_nenhum_capaz_o_claude_entra_como_emergencia():
    for pid in registro.PROVEDORES:
        balanceador.marcar_fora(pid, True)
    e = balanceador.escolher(2)
    assert e.modo == "emergencia" and e.modelo.provedor == "anthropic"


# ---------- na execução ----------
def test_execucao_mostra_nivel_candidatos_e_motivo_em_cada_passo_auto(api):
    r = api.post(f"{V1}/estudio/testar", json={"blueprint": _bp(), "entrada": {}}, headers=como("marina")).json()
    p = r["passos"]["a"]
    assert p["esforco"] == "leve" and p["balanceador"]["candidatos"] and p["balanceador"]["motivo"]
    assert p["motivos_modelo"] and p["modelo_chave"]


def test_queda_simulada_muda_o_provedor_dos_proximos_passos_e_abre_alerta(api):
    antes = api.post(f"{V1}/estudio/testar", json={"blueprint": _bp(), "entrada": {}}, headers=como("marina")).json()["passos"]["a"]
    r = api.post(f"{V1}/balanceador/provedores/{antes['provedor']}/falha", json={"fora": True}, headers=como("helena"))
    assert r.status_code == 200 and next(p for p in r.json()["provedores"] if p["id"] == antes["provedor"])["fora"]
    depois = api.post(f"{V1}/estudio/testar", json={"blueprint": _bp(), "entrada": {}}, headers=como("marina")).json()["passos"]["a"]
    assert depois["provedor"] != antes["provedor"] and depois["balanceador"]["modo"] == "delegado"
    assert "indisponível" in depois["balanceador"]["motivo"]
    assert any(a["regra"] == "provedor_fora" for a in api.get(f"{V1}/alertas", headers=como("helena")).json())
    assert any(a["regra"] == "provedor_fora" for a in api.get(f"{V1}/alertas", headers=como("lucas")).json())
    # a volta fecha o alerta
    api.post(f"{V1}/balanceador/provedores/{antes['provedor']}/falha", json={"fora": False}, headers=como("helena"))
    assert not any(a["regra"] == "provedor_fora" for a in api.get(f"{V1}/alertas", headers=como("helena")).json())


def test_agente_acima_do_orcamento_usa_o_modelo_capaz_mais_barato(api, monkeypatch):
    monkeypatch.setattr(motor, "_uso_do_orcamento", lambda s, agente_id: 0.9)
    bp = Blueprint.model_validate(_bp(instrucao=ANALISE))
    with Session(db.motor()) as s:
        exe, _ = motor.executar(s, PERSONAS["marina"], bp, {}, agente_id="qualquer")
    p = exe.passos["a"]
    assert p["balanceador"]["modo"] == "economia"
    assert any("orçamento do mês em 90%" in m for m in p["motivos_modelo"])
    idx = balanceador.NIVEIS.index(p["esforco"]) + 1
    assert p["modelo_chave"] == balanceador.escolher(idx, n_ferramentas=0, economia=True).modelo.chave


def test_balanceador_troca_de_provedor_quando_a_chamada_falha(api, monkeypatch):
    class Instavel(ClienteSimulado):
        def gerar(self, chave_modelo, *a, **k):
            if registro.obter(chave_modelo).provedor == "anthropic":
                raise ErroModelo("Limite de uso da API atingido.")
            return super().gerar(chave_modelo, *a, **k)
    monkeypatch.setattr(motor, "obter_cliente", lambda simulado=None: Instavel())
    r = api.post(f"{V1}/estudio/testar", json={"blueprint": _bp(), "entrada": {}}, headers=como("marina")).json()
    p = r["passos"]["a"]
    assert r["status"] == "concluida" and p["provedor"] != "anthropic" and p["balanceador"]["modo"] == "delegado"
    assert any("delegado" in m and "falhou" in m for m in p["motivos_modelo"])


# ---------- política e carga de teste ----------
def test_politica_legivel_para_helena_e_lucas_e_nao_para_os_demais(api):
    for perfil, ok in [("helena", True), ("lucas", True), ("marina", False), ("rafael", False), ("carla", False), ("thiago", False)]:
        r = api.get(f"{V1}/balanceador/politica", headers=como(perfil))
        assert r.status_code == (200 if ok else 403), perfil
    p = api.get(f"{V1}/balanceador/politica", headers=como("helena")).json()
    assert [n["id"] for n in p["niveis"]] == list(balanceador.NIVEIS)
    assert all(n["raciocinio_min"] == i + 1 and n["escolha"]["modelo"] for i, n in enumerate(p["niveis"]))
    assert p["pode_simular"] is True
    assert api.get(f"{V1}/balanceador/politica", headers=como("lucas")).json()["pode_simular"] is False


def test_so_a_helena_simula_queda_e_carga(api):
    for perfil in ("lucas", "marina", "thiago"):
        assert api.post(f"{V1}/balanceador/provedores/google/falha", json={"fora": True}, headers=como(perfil)).status_code == 403
        assert api.post(f"{V1}/balanceador/simular-carga", json={}, headers=como(perfil)).status_code == 403
    assert api.post(f"{V1}/balanceador/provedores/inexistente/falha", json={}, headers=como("helena")).status_code == 404


def test_carga_de_teste_mostra_distribuicao_custo_e_comparacao_com_tudo_forte(api):
    r = api.post(f"{V1}/balanceador/simular-carga", json={"passos": 400}, headers=como("helena")).json()
    assert r["passos"] == 400 and sum(n["passos"] for n in r["por_nivel"]) == 400
    assert sum(p["passos"] for p in r["por_provedor"]) == 400
    assert 0 < r["custo_brl"] < r["custo_tudo_forte_brl"] and 0 < r["economia_pct"] < 1
    assert api.get(f"{V1}/balanceador/politica", headers=como("helena")).json()["ultima_carga"]["passos"] == 400
    assert api.post(f"{V1}/balanceador/simular-carga", json={"passos": 400}, headers=como("helena")).json() == r   # determinística


def test_carga_muda_com_a_queda_de_um_provedor(api):
    normal = api.post(f"{V1}/balanceador/simular-carga", json={"passos": 400}, headers=como("helena")).json()
    api.post(f"{V1}/balanceador/provedores/anthropic/falha", json={"fora": True}, headers=como("helena"))
    queda = api.post(f"{V1}/balanceador/simular-carga", json={"passos": 400}, headers=como("helena")).json()
    assert queda["fora"] == ["anthropic"]
    assert "anthropic" not in {p["provedor"] for p in queda["por_provedor"]}
    assert {p["provedor"] for p in normal["por_provedor"]} != {p["provedor"] for p in queda["por_provedor"]}
    assert queda["custo_brl"] != normal["custo_brl"]


def test_reiniciar_a_demo_desfaz_a_queda_e_a_carga(api):
    api.post(f"{V1}/balanceador/provedores/google/falha", json={"fora": True}, headers=como("helena"))
    api.post(f"{V1}/balanceador/simular-carga", json={}, headers=como("helena"))
    assert balanceador.fora_do_ar() and balanceador.ultima_carga()
    assert api.post(f"{V1}/demo/reiniciar", headers=como("helena")).json()["ok"]
    assert not balanceador.fora_do_ar() and balanceador.ultima_carga() is None
