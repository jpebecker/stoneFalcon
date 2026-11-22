"""v7/13: matriz de acesso da v7 (seção 4 do plano) para os 6 perfis e todos os roteiros, incluindo o pitch."""
import pytest

from app.core.identidade import PERSONAS
from app.roteiros.catalogo import ROTEIROS
from tests.conftest import como

V1 = "/api/v1"
PERFIS = list(PERSONAS)
CRIADORES = {"marina", "rafael", "carla", "thiago", "lucas", "helena"}   # v8.1: Lucas e Helena também criam o seu processo


@pytest.mark.parametrize("perfil", PERFIS)
def test_mapa_de_ia_so_da_helena(api, perfil):
    eu = api.get(f"{V1}/eu", headers=como(perfil)).json()
    assert ("mapa" in eu["abas"]) == (perfil == "helena")
    assert api.get(f"{V1}/mapa", headers=como(perfil)).status_code == (200 if perfil == "helena" else 403)


@pytest.mark.parametrize("perfil", PERFIS)
def test_atalho_da_extensao_so_para_quem_cria_agentes(api, perfil):
    r = api.post(f"{V1}/extensao/passe", json={}, headers=como(perfil))
    assert (r.status_code == 200) == (perfil in CRIADORES), perfil
    assert ("estudio" in api.get(f"{V1}/eu", headers=como(perfil)).json()["abas"]) == (perfil in CRIADORES)


@pytest.mark.parametrize("perfil", PERFIS)
def test_politica_do_balanceador_e_simulacao(api, perfil):
    assert api.get(f"{V1}/balanceador/politica", headers=como(perfil)).status_code == (200 if perfil in ("helena", "lucas") else 403)
    assert api.post(f"{V1}/balanceador/simular-carga", json={}, headers=como(perfil)).status_code == (200 if perfil == "helena" else 403)
    assert api.post(f"{V1}/balanceador/provedores/google/falha", json={"fora": False}, headers=como(perfil)).status_code == (200 if perfil == "helena" else 403)


@pytest.mark.parametrize("perfil", PERFIS)
def test_modelos_e_financas_por_provedor_abertos_a_todos(api, perfil):
    assert api.get(f"{V1}/modelos", headers=como(perfil)).status_code == 200
    assert "por_provedor" in api.get(f"{V1}/financas/resumo", headers=como(perfil)).json()


@pytest.mark.parametrize("rid", list(ROTEIROS))
def test_todos_os_roteiros_reiniciam_e_carregam_para_o_dono_e_a_helena(api, rid):
    dono = ROTEIROS[rid].persona
    assert api.post(f"{V1}/roteiros/{rid}/reiniciar", headers=como(dono)).status_code == 200
    for perfil in {dono, "helena"}:
        assert api.get(f"{V1}/roteiros/{rid}", headers=como(perfil)).status_code == 200


def test_rotina_so_de_criador_com_acesso_ao_agente(api):
    bp = {"nome": "Estoque semanal", "area": "logistica", "objetivo": "Consultar o estoque da maquininha.", "minutos_manual": 5,
          "campos": [{"id": "modelo", "rotulo": "Modelo", "tipo": "texto", "exemplo": "Maquininha Pro"}],
          "passos": [{"id": "e", "titulo": "Estoque", "tipo": "ferramenta", "ferramenta": "consultar_estoque",
                      "entrada": {"modelo": "{{entrada.modelo}}"}}]}
    aid = api.post(f"{V1}/agentes", json={"blueprint": bp, "nota": "x"}, headers=como("thiago")).json()["id"]
    api.post(f"{V1}/agentes/{aid}/publicar", headers=como("thiago"))
    corpo = {"frequencia": "diaria", "hora": 9, "minuto": 0, "entrada": {"modelo": "Maquininha Pro"}}
    for perfil in PERFIS:
        r = api.post(f"{V1}/agentes/{aid}/rotinas", json=corpo, headers=como(perfil))
        assert (r.status_code == 200) == (perfil == "thiago"), (perfil, r.status_code)
