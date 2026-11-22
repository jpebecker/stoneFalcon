"""v8.3/06: o alerta de um processo compartilhado chega ao dono e aos criadores das áreas com quem ele é compartilhado."""
import pytest
from sqlmodel import select

from app.audit import trilha
from app.core.identidade import PERSONAS
from app.observability import alertas
from app.processos import modelos as pm
from app.processos.tipo import ciclo as ciclo_processos
from app.seed import alertas_demo
from app.seed.demo import semear
from app.tools import dados_ficticios, executor
from tests.conftest import como

V1 = "/api/v1"
NOME = alertas_demo.NOME_COMPARTILHADO


@pytest.fixture(autouse=True)
def _limpo():
    dados_ficticios.zerar()
    executor.zerar_limites()


def _compartilhado(s):
    return s.exec(select(pm.Processo).where(pm.Processo.nome == NOME)).one()


def _alerta(s, regra, p):
    return next((a for a in s.exec(select(alertas.Alerta).where(alertas.Alerta.regra == regra)
                                   .where(alertas.Alerta.processo_id == p.id).where(alertas.Alerta.resolvido_em.is_(None)))), None)


def test_o_alerta_vai_ao_dono_e_aos_criadores_da_area_compartilhada_sem_repetir(sessao):
    semear(sessao, alertas=False)
    p = _compartilhado(sessao)
    assert alertas.destinatarios_do_processo(p) == ["lucas", "thiago"]
    alertas_demo._ligar_falhando(sessao, p)
    alertas.avaliar(sessao)
    a = _alerta(sessao, "processo_falhando", p)
    assert a is not None and a.destinatarios == ["lucas", "thiago"]
    for perfil in ("thiago", "lucas", "helena"):                       # o dono, a área receptora e o CoE (por papel)
        assert a.id in {x.id for x in alertas.visiveis(sessao, PERSONAS[perfil])}, perfil
    for perfil in ("marina", "rafael", "carla"):
        assert a.id not in {x.id for x in alertas.visiveis(sessao, PERSONAS[perfil])}, perfil


def test_alerta_de_sistema_do_processo_compartilhado_tambem_nao_repete_ninguem(sessao):
    """A Engenharia já recebe os alertas de sistema: o Lucas é da Engenharia E da área compartilhada, e aparece uma vez só."""
    semear(sessao, alertas=False)
    p = _compartilhado(sessao)
    executor.definir_falha(sessao, "arquivos_adicionar_linha", "fora_do_ar", "sistema")
    alertas.avaliar(sessao)
    a = _alerta(sessao, "conector_fora", p)
    assert a is not None and a.destinatarios == ["lucas", "thiago"]


def test_mudar_as_areas_compartilhadas_muda_os_destinatarios_na_proxima_rodada(sessao):
    semear(sessao, alertas=False)
    p = _compartilhado(sessao)
    alertas_demo._ligar_falhando(sessao, p)
    alertas.avaliar(sessao)
    antes = _alerta(sessao, "processo_falhando", p).id
    ciclo_processos.compartilhar(sessao, PERSONAS["thiago"], p.id, ["engenharia", "risco"])
    alertas.avaliar(sessao)
    a = _alerta(sessao, "processo_falhando", p)
    assert a.id == antes and a.destinatarios == ["lucas", "rafael", "thiago"]      # o mesmo alerta, com mais um destinatário
    ciclo_processos.compartilhar(sessao, PERSONAS["thiago"], p.id, [])
    alertas.avaliar(sessao)
    a = _alerta(sessao, "processo_falhando", p)
    assert a.id == antes and a.destinatarios == ["thiago"]                          # deixou de ser compartilhado: só o dono
    eventos = [e for e in trilha.listar(sessao, tipo="alerta_destinatarios_alterados", limite=50) if e.dados["alerta"] == antes]
    assert len(eventos) == 2 and all(e.ator == "sistema" for e in eventos)         # a trilha guarda cada mudança
    alertas.avaliar(sessao)
    assert len([e for e in trilha.listar(sessao, tipo="alerta_destinatarios_alterados", limite=50) if e.dados["alerta"] == antes]) == 2


def test_a_demo_tem_um_alerta_no_processo_compartilhado_so_para_thiago_lucas_e_helena(sessao):
    semear(sessao)
    p = _compartilhado(sessao)
    a = _alerta(sessao, "processo_falhando", p)
    assert a is not None and a.destinatarios == ["lucas", "thiago"]
    assert not a.lido_por and not a.tratando_por                                   # novo para os dois: dá para assumir ao vivo
    for perfil, persona in PERSONAS.items():
        vê = a.id in {x.id for x in alertas.visiveis(sessao, persona)}
        assert vê == (perfil in ("thiago", "lucas", "helena")), perfil
    ev = [e for e in trilha.listar(sessao, tipo="alerta_aberto", limite=2000) if e.dados["alerta"] == a.id]
    assert len(ev) == 1 and ev[0].ator == "sistema"                                 # aberto pela regra, não inserido


def test_quem_assume_o_alerta_aparece_em_tratamento_para_o_outro(api, sessao):
    semear(sessao)
    do_thiago = next(a for a in api.get(f"{V1}/alertas", headers=como("thiago")).json() if a["titulo"].startswith(NOME))
    assert do_thiago["tratando_por"] is None
    r = api.post(f"{V1}/alertas/{do_thiago['id']}/assumir", json={"nota": "Vendo o registro do incidente."}, headers=como("lucas"))
    assert r.status_code == 200 and r.json()["tratando_nome"] == "Lucas Prado"
    visto = next(a for a in api.get(f"{V1}/alertas", headers=como("thiago")).json() if a["id"] == do_thiago["id"])
    assert visto["tratando_por"] == "lucas" and visto["tratando_nome"] == "Lucas Prado"
    assert visto["tratando_nota"] == "Vendo o registro do incidente."
    outra = api.post(f"{V1}/alertas/{do_thiago['id']}/assumir", json={}, headers=como("thiago"))
    assert outra.status_code == 409 and "Lucas Prado" in outra.json()["detail"]     # já está com o Lucas
    assert api.get(f"{V1}/alertas", headers=como("marina")).status_code == 200
    assert all(a["id"] != do_thiago["id"] for a in api.get(f"{V1}/alertas", headers=como("marina")).json())
    assert api.post(f"{V1}/alertas/{do_thiago['id']}/assumir", json={}, headers=como("marina")).status_code == 404
