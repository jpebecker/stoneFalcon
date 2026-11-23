"""v8.3/02: o selo de versão do seed. Banco semeado por código antigo recebe a demonstração atual sem apagar arquivo; banco
atual não é tocado (reiniciar o servidor no meio de uma demonstração mantém tudo)."""
import logging
import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.audit import trilha
from app.core import db
from app.core.identidade import PERSONAS
from app.observability import alertas
from app.seed import selo
from app.seed.demo import semear
from app.seed.partida import preparar
from app.tools import dados_ficticios, executor
from tests.conftest import como

V1 = "/api/v1"
FIXTURE_V7 = Path(__file__).parent / "fixtures" / "banco_v7.db"


@pytest.fixture(autouse=True)
def _limpo():
    dados_ficticios.zerar()
    executor.zerar_limites()


@pytest.fixture()
def banco_v7(tmp_path):
    """Um banco da v7: tem dados e nenhum selo (como qualquer banco semeado antes do selo existir)."""
    copia = tmp_path / "banco_v7.db"
    shutil.copy(FIXTURE_V7, copia)
    anterior = db._motor
    m = db.criar_motor("sqlite:///" + str(copia).replace("\\", "/"))
    db.usar_motor(m)
    db.criar_tabelas()           # o que a partida faz: acrescenta tabelas e colunas novas (inclusive a do selo, vazia)
    yield m
    m.dispose()
    db.usar_motor(anterior)


def _abertos(s):
    return sorted((a.id, a.regra) for a in s.exec(select(alertas.Alerta).where(alertas.Alerta.resolvido_em.is_(None))))


def _todas_as_personas_veem_alerta(s):
    for perfil, persona in PERSONAS.items():
        assert alertas.visiveis(s, persona), f"{perfil} não vê nenhum alerta"


def test_banco_vazio_e_semeado_e_ganha_o_selo(sessao):
    assert selo.ler(sessao) is None
    assert preparar(sessao) == "semeado"
    assert selo.ler(sessao) == selo.VERSAO_SEMENTE and selo.atualizado(sessao)
    _todas_as_personas_veem_alerta(sessao)


def test_banco_da_v7_sem_selo_e_refeito_e_todas_as_personas_veem_alerta(banco_v7, caplog):
    with Session(db.motor()) as s:
        assert selo.ler(s) is None and not _abertos(s)       # o estado de hoje: dados antigos, nenhum alerta, nenhum selo
        with caplog.at_level(logging.INFO, logger="stonefalcon.semente"):
            assert preparar(s) == "reiniciado"
    avisos = [r for r in caplog.records if r.name == "stonefalcon.semente" and "Refazendo" in r.getMessage()]
    assert len(avisos) == 1 and "ausente" in avisos[0].getMessage()      # uma linha só, com o motivo
    with Session(db.motor()) as s:
        assert selo.ler(s) == selo.VERSAO_SEMENTE
        _todas_as_personas_veem_alerta(s)
        assert trilha.verificar(s)["integra"] is True


def test_selo_mais_antigo_tambem_refaz(sessao):
    semear(sessao)
    sessao.merge(selo.SeloSemente(chave=selo.CHAVE, versao=selo.VERSAO_SEMENTE - 1))
    sessao.commit()
    assert preparar(sessao) == "reiniciado"
    with Session(db.motor()) as s:
        assert selo.ler(s) == selo.VERSAO_SEMENTE
        _todas_as_personas_veem_alerta(s)


def test_banco_atual_nao_e_tocado_numa_nova_partida(sessao):
    assert preparar(sessao) == "semeado"
    # a demonstração anda: a Helena assume um alerta (muda o estado e a trilha)
    alerta = alertas.visiveis(sessao, PERSONAS["helena"])[0]
    alerta.lido_por = [*(alerta.lido_por or []), "helena"]
    sessao.add(alerta)
    sessao.commit()
    antes = (_abertos(sessao), len(trilha.listar(sessao, limite=5000)), list(alerta.lido_por))
    assert preparar(sessao) == "mantido"
    with Session(db.motor()) as s:
        depois = (_abertos(s), len(trilha.listar(s, limite=5000)), list(s.get(alertas.Alerta, alerta.id).lido_por))
    assert antes == depois


def test_os_alertas_sobrevivem_a_duas_rodadas_da_vigia(sessao):
    semear(sessao)
    antes = _abertos(sessao)
    assert antes
    for _ in range(2):                       # a vigia de 60 s roda sobre o mesmo estado: nada abre nem fecha sozinho
        resultado = alertas.avaliar(sessao)
        assert resultado["abertos"] == [] and resultado["resolvidos"] == []
    assert _abertos(sessao) == antes
    _todas_as_personas_veem_alerta(sessao)


def test_o_servidor_ao_subir_com_um_banco_antigo_mostra_alertas_para_todos(banco_v7, monkeypatch):
    """De ponta a ponta: o ciclo de vida do app (o que roda ao iniciar) refaz o banco da v7 e a API mostra os alertas."""
    from app.main import app
    monkeypatch.setenv("STONEFALCON_SEMEAR", "1")
    with TestClient(app) as c:
        for perfil in PERSONAS:
            assert c.get(f"{V1}/notificacoes/contagem", headers=como(perfil)).json()["nao_lidos"] >= 1, perfil


def test_semear_zero_nao_toca_num_banco_antigo(banco_v7):
    from app.main import app          # o conftest já desliga o seed (STONEFALCON_SEMEAR=0)
    with TestClient(app):
        pass
    with Session(db.motor()) as s:
        assert selo.ler(s) is None and not _abertos(s)
