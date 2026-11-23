"""v8.1/06: cada persona entra na demo com pelo menos um alerta aberto pelas regras reais."""
import pytest
from sqlmodel import Session, select

from app.audit import trilha
from app.core import db
from app.core.identidade import PERSONAS
from app.observability import alertas
from app.processos import modelos as pm
from app.roteiros.reinicio import reiniciar
from app.runtime import modelos as rm
from app.seed.demo import semear
from app.tools import dados_ficticios, executor
from tests.conftest import como

V1 = "/api/v1"

# o que cada persona deve ver (regra, parte do título): coerente com o próprio perfil
ESPERADO = {
    "marina": ("processo_lento", "Resposta a dúvidas de lojistas"),
    "rafael": ("processo_falhando", "Triagem de chargebacks"),
    "carla": ("orcamento", "Orientação de férias"),
    "thiago": ("conector_lento", "estoque"),
    "lucas": ("conector_fora", "transações"),
    "helena": ("orcamento", "Revisão mensal do custo de IA"),
}


@pytest.fixture(autouse=True)
def _limpo():
    dados_ficticios.zerar()
    executor.zerar_limites()


def _nao_lidos(s, perfil):
    return [a for a in alertas.visiveis(s, PERSONAS[perfil]) if PERSONAS[perfil].id not in (a.lido_por or [])]


def _abertos(s):
    return list(s.exec(select(alertas.Alerta).where(alertas.Alerta.resolvido_em.is_(None))))


def test_cada_persona_entra_com_um_alerta_nao_lido_coerente_com_o_perfil(sessao):
    semear(sessao)
    for perfil, (regra, trecho) in ESPERADO.items():
        meus = _nao_lidos(sessao, perfil)
        assert any(a.regra == regra and trecho.lower() in a.titulo.lower() for a in meus), (perfil, [(a.regra, a.titulo) for a in meus])


def test_nenhum_alerta_e_inserido_direto_todos_nascem_da_avaliacao(sessao):
    semear(sessao)
    abertos = _abertos(sessao)
    assert abertos
    eventos = {e.dados["alerta"]: e for e in trilha.listar(sessao, tipo="alerta_aberto", limite=500)}
    assert {a.id for a in abertos} <= set(eventos) and all(e.ator == "sistema" for e in eventos.values())
    assert alertas.avaliar(sessao)["abertos"] == []                      # a mesma regra, sobre o mesmo estado: nada novo
    # desfeito o estado, as regras fecham o que abriram (nada ficou "chumbado")
    for cid in ("consultar_estoque", "listar_transacoes", "listar_chargebacks", "consultar_lojista", "buscar_politica"):
        executor.definir_falha(sessao, cid, None, "lucas")
    fechados = alertas.avaliar(sessao)["resolvidos"]
    assert {a.id for a in abertos if a.regra.startswith("conector_")} <= set(fechados)


def test_historico_e_marcado_como_demonstracao(sessao):
    semear(sessao)
    execs = sessao.exec(select(rm.Execucao)).all()
    assert execs and all(e.demo and e.simulado for e in execs)
    assert [e for e in execs if e.status == rm.ESCALADA]                 # a triagem falhando é histórico sintético moldado


def test_reiniciar_a_demo_volta_ao_mesmo_conjunto_de_alertas(sessao):
    semear(sessao)
    antes = sorted((a.regra, a.titulo, a.severidade) for a in _abertos(sessao))
    reiniciar(sessao)
    with Session(db.motor()) as s:
        depois = sorted((a.regra, a.titulo, a.severidade) for a in _abertos(s))
    assert antes == depois and antes


def test_iniciar_um_roteiro_guiado_comeca_sem_alertas(api, sessao):
    semear(sessao)
    assert _abertos(sessao)
    for roteiro in ("lucas", "marina", "helena"):
        assert api.post(f"{V1}/roteiros/{roteiro}/reiniciar", headers=como("helena")).status_code == 200
        with Session(db.motor()) as s:
            assert _abertos(s) == [], roteiro
        assert api.get(f"{V1}/notificacoes/contagem", headers=como("lucas")).json()["nao_lidos"] == 0


def test_api_do_sino_mostra_os_alertas_de_cada_persona(api, sessao):
    semear(sessao)
    for perfil in ESPERADO:
        assert api.get(f"{V1}/notificacoes/contagem", headers=como(perfil)).json()["nao_lidos"] >= 1, perfil


def test_cada_cenario_toca_so_a_propria_persona(sessao):
    """Ninguém recebe alerta de cenário de outra persona (a Helena vê todos, a Engenharia recebe os de sistema): cada alerta
    de processo que a pessoa vê é de um processo dela, e o principal dela continua entre os não lidos."""
    semear(sessao)
    for perfil, (regra, trecho) in ESPERADO.items():
        if perfil == "helena":
            continue
        for a in alertas.visiveis(sessao, PERSONAS[perfil], so_abertos=False):
            if perfil == "lucas" and a.regra.startswith(("conector_", "provedor_")):
                continue                                                  # a Engenharia recebe os alertas de sistema
            proc = sessao.get(pm.Processo, a.processo_id) if a.processo_id else None
            assert proc is not None and (proc.dono == perfil or PERSONAS[perfil].area in (proc.compartilhado_com or [])), (perfil, a.titulo)
        assert any(a.regra == regra and trecho.lower() in a.titulo.lower() for a in _nao_lidos(sessao, perfil)), perfil


def test_o_processo_do_lucas_segue_de_pe_para_triar_o_incidente(api, sessao):
    semear(sessao)
    pid = next(p["id"] for p in api.get(f"{V1}/processos", headers=como("lucas")).json() if p["nome"] == "Triagem de incidente de sistema")
    r = api.post(f"{V1}/processos/{pid}/executar", json={"entrada": {"sistema": "Transações e contestações"}}, headers=como("lucas"))
    assert r.status_code == 200, r.text
    assert "CRÍTICO" in str(r.json())


def test_a_moldagem_do_orcamento_e_do_sistema_nao_de_uma_pessoa(sessao):
    semear(sessao)
    moldados = [e for e in trilha.listar(sessao, tipo="orcamento_definido", limite=500) if (e.dados or {}).get("origem")]
    assert moldados and all(e.ator == "sistema" for e in moldados)


# ---- v8.3.1/04: pelo menos 2 alertas não lidos por persona, e a mistura lido / em tratamento / resolvido continua ----

def _todos_visiveis(s, perfil):
    return alertas.visiveis(s, PERSONAS[perfil], so_abertos=False)


def test_cada_persona_tem_ao_menos_2_nao_lidos_e_a_mistura_completa(sessao):
    semear(sessao)
    for perfil, persona in PERSONAS.items():
        abertos = alertas.visiveis(sessao, persona)
        nao_lidos = [a for a in abertos if perfil not in (a.lido_por or [])]
        lidos = [a for a in abertos if perfil in (a.lido_por or []) and a.tratando_por is None]
        tratando = [a for a in abertos if a.tratando_por == perfil and a.tratando_nota]
        resolvidos = [a for a in _todos_visiveis(sessao, perfil) if a.resolvido_em]
        assert len(nao_lidos) >= 2, (perfil, [(a.regra, a.titulo) for a in nao_lidos])
        assert lidos and tratando and resolvidos, (perfil, len(lidos), len(tratando), len(resolvidos))


def test_os_novos_alertas_de_marina_rafael_e_carla_sao_dos_processos_deles(sessao):
    semear(sessao)
    donos = {"marina": "Resposta a dúvidas de lojistas", "rafael": "Triagem de chargebacks", "carla": "Orientação de férias"}
    for perfil, processo in donos.items():
        novos = [a for a in _nao_lidos(sessao, perfil) if a.regra == "conector_lento"
                 and a.conector in ("consultar_lojista", "buscar_politica")]
        assert novos, perfil
        for a in novos:
            assert perfil in a.destinatarios and processo.lower() in sessao.get(pm.Processo, a.processo_id).nome.lower(), (perfil, a.titulo)
    # Helena, Lucas e Thiago já leram os novos: a contagem deles não cresce por causa deles
    for perfil in ("helena", "lucas", "thiago"):
        assert not [a for a in _nao_lidos(sessao, perfil) if a.conector in ("consultar_lojista", "buscar_politica")], perfil


def test_os_novos_alertas_nascem_da_avaliacao_e_sobrevivem_a_duas_rodadas_da_vigia(sessao):
    semear(sessao)
    novos = [a for a in _abertos(sessao) if a.conector in ("consultar_lojista", "buscar_politica")]
    assert len(novos) >= 6                              # um por processo que depende do sistema (cadastro e política)
    abertura = {e.dados["alerta"]: e for e in trilha.listar(sessao, tipo="alerta_aberto", limite=1000)}
    assert all(a.id in abertura and abertura[a.id].ator == "sistema" for a in novos)    # nunca inseridos direto
    antes = sorted(a.id for a in _abertos(sessao))
    for _ in range(2):
        resultado = alertas.avaliar(sessao)
        assert resultado["abertos"] == [] and resultado["resolvidos"] == []
    assert sorted(a.id for a in _abertos(sessao)) == antes


def test_roteiro_guiado_continua_comecando_limpo_e_o_passo_do_alerta_funciona(sessao):
    reiniciar(sessao, "helena")
    assert not [a for a in _abertos(sessao) if a.conector in ("consultar_lojista", "buscar_politica")]   # os sistemas lentos novos não vazam
    from app.seed.alertas_demo import moldar_persona
    moldar_persona(sessao, "helena")
    assert [a.regra for a in _abertos(sessao)] == ["orcamento"]
