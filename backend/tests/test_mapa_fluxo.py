"""v7/08: fluxo no mapa (pulso por execução), camada de modelos por provedor e filtros por área e provedor."""
from app.llm import registro
from app.seed.demo import semear
from tests.conftest import como

V1 = "/api/v1"


def _mapa(api, query: str = "") -> dict:
    r = api.get(f"{V1}/mapa{query}", headers=como("helena"))
    assert r.status_code == 200, r.text
    return r.json()


def _executar(api, perfil: str, agente: str, entrada: dict | None = None) -> dict:
    r = api.post(f"{V1}/agentes/{agente}/executar", json={"entrada": entrada or {}}, headers=como(perfil))
    assert r.status_code == 200, r.text
    return r.json()


def _agente_id(api, nome: str) -> str:
    return next(a["id"] for a in api.get(f"{V1}/agentes", headers=como("helena")).json() if a["nome"] == nome)


def test_camada_de_modelos_mostra_so_os_provedores_usados_no_periodo(api, sessao):
    semear(sessao)
    m = _mapa(api)
    modelos = [n for n in m["nos"] if n["tipo"] == "modelo"]
    assert modelos and all(n["coluna"] == "modelos" and n["provedor"] and n["provedor_nome"] for n in modelos)
    # só aparece modelo que alguma execução do período (ou a estimativa de um agente publicado) usou
    assert {n["provedor"] for n in modelos} >= {"anthropic"} and len({n["provedor"] for n in modelos}) >= 3
    for n in modelos:
        assert n["simulado"] == (n["provedor"] != "anthropic") and n["custo_brl"] >= 0 and n["chamadas"] >= 0
    assert m["totais"]["modelos"] == len(modelos)
    # custo por provedor bate com Finanças
    fin = api.get(f"{V1}/financas/resumo?dias=7", headers=como("helena")).json()
    por_prov = {}
    for n in modelos:
        por_prov[n["provedor"]] = por_prov.get(n["provedor"], 0) + n["custo_brl"]
    for p in fin["por_provedor"]:
        assert abs(por_prov.get(p["provedor"], 0) - p["custo_brl"]) < 0.05 * max(1, len(modelos))


def test_modelo_so_aparece_se_alguem_o_usou(api, sessao):
    semear(sessao)
    usados = {n["id"] for n in _mapa(api)["nos"] if n["tipo"] == "modelo"}
    assert len(usados) < len(registro.todos())       # nem todo modelo do registro entra no mapa


def test_filtro_por_area(api, sessao):
    semear(sessao)
    m = _mapa(api, "?area=risco")
    agentes = [n for n in m["nos"] if n["tipo"] == "agente"]
    assert agentes and {n["area"] for n in agentes} == {"risco"}
    assert {n["area"] for n in m["nos"] if n["tipo"] == "criador"} == {"risco"}
    assert m["filtros"]["area"] == "risco" and "risco" in m["filtros"]["areas"]
    ids = {n["id"] for n in m["nos"]}
    assert all(l["de"] in ids and l["para"] in ids for l in m["ligacoes"])


def test_filtro_por_provedor(api, sessao):
    semear(sessao)
    m = _mapa(api, "?provedor=openai")
    modelos = [n for n in m["nos"] if n["tipo"] == "modelo"]
    assert modelos and {n["provedor"] for n in modelos} == {"openai"}
    assert [n for n in m["nos"] if n["tipo"] == "processo"]
    liga = {(l["de"], l["para"]) for l in m["ligacoes"]}
    for a in (n for n in m["nos"] if n["tipo"] in ("agente", "processo")):
        assert any(d == a["id"] and p.startswith("modelo:") for d, p in liga)       # todo agente restante usa o provedor
    assert api.get(f"{V1}/mapa?provedor=nada", headers=como("helena")).status_code == 404


def test_filtros_se_combinam(api, sessao):
    semear(sessao)
    todos = len([n for n in _mapa(api)["nos"] if n["tipo"] == "agente"])
    so_area = len([n for n in _mapa(api, "?area=atendimento")["nos"] if n["tipo"] == "agente"])
    ambos = _mapa(api, "?area=atendimento&provedor=anthropic")
    n_ambos = len([n for n in ambos["nos"] if n["tipo"] == "agente"])
    assert 0 < so_area < todos and 0 < n_ambos <= so_area
    assert {n["area"] for n in ambos["nos"] if n["tipo"] == "agente"} == {"atendimento"}
    assert {n["provedor"] for n in ambos["nos"] if n["tipo"] == "modelo"} == {"anthropic"}
    vazio = _mapa(api, "?area=gestao")
    assert [n for n in vazio["nos"] if n["tipo"] == "agente"] == []


def test_execucao_nova_aparece_nas_recentes_com_o_caminho_do_pulso(api, sessao):
    semear(sessao)
    antes = {e["id"] for e in _mapa(api)["execucoes_recentes"]}
    aid = _agente_id(api, "Redator de respostas a lojistas")
    exe = _executar(api, "marina", aid, {"lojista_id": "L1001", "pergunta": "Em quanto tempo o estorno cai para o cliente?"})
    m = _mapa(api)
    nova = next(e for e in m["execucoes_recentes"] if e["id"] == exe["id"])
    assert exe["id"] not in antes and nova["agente_id"] == aid and nova["status"] == exe["status"]
    assert nova["modelos"] and nova["custo_brl"] > 0
    # o caminho é agente -> modelo -> ferramenta/plugin -> plataforma, em etapas 0, 1 e 2, e só por ligações que existem
    liga = {(l["de"], l["para"]) for l in m["ligacoes"]}
    assert all((de, para) in liga for de, para, _ in nova["arestas"])
    etapas = {o for _, _, o in nova["arestas"]}
    assert 0 in etapas and 1 in etapas and 2 in etapas
    assert all(de == "agente:" + aid for de, _, o in nova["arestas"] if o == 0)
    assert all(de.startswith("modelo:") for de, _, o in nova["arestas"] if o == 1)
    assert all(para.startswith("sistema:") for _, para, o in nova["arestas"] if o == 2)


def test_recentes_trazem_a_cor_do_resultado_por_status(api, sessao):
    semear(sessao)
    status = {e["status"] for e in _mapa(api, "?dias=30")["execucoes_recentes"]}
    assert status <= {"concluida", "escalada", "falhou", "negada", "aguardando_aprovacao", "em_andamento"}
    assert all(e["quando"] and e["agente"] for e in _mapa(api)["execucoes_recentes"])


def test_sem_execucoes_o_mapa_fica_parado(api):
    """Sem execuções no período não há pulso a animar: a lista de recentes vem vazia e o grafo continua legível."""
    bp = {"nome": "Agente sem uso", "area": "logistica", "objetivo": "Consultar o estoque de maquininhas.", "minutos_manual": 5,
          "campos": [{"id": "modelo", "rotulo": "Modelo", "tipo": "texto", "exemplo": "Pro"}],
          "passos": [{"id": "e", "titulo": "Consultar estoque", "tipo": "ferramenta", "ferramenta": "consultar_estoque",
                      "entrada": {"modelo": "{{entrada.modelo}}"}}]}
    aid = api.post(f"{V1}/agentes", json={"blueprint": bp, "nota": "x"}, headers=como("thiago")).json()["id"]
    api.post(f"{V1}/agentes/{aid}/publicar", headers=como("thiago"))
    m = _mapa(api)
    assert m["totais"]["execucoes"] == 0 and m["execucoes_recentes"] == []
    assert "agente:" + aid in {n["id"] for n in m["nos"]}
    # agente sem passo de IA liga direto à ferramenta, sem camada de modelos
    assert ("agente:" + aid, "ferramenta:consultar_estoque") in {(l["de"], l["para"]) for l in m["ligacoes"]}


def test_so_a_helena_usa_os_filtros(api, sessao):
    semear(sessao)
    for perfil in ("marina", "lucas", "thiago"):
        assert api.get(f"{V1}/mapa?area=risco&provedor=openai", headers=como(perfil)).status_code == 403


def test_execucao_de_processo_acende_o_pulso_criador_processo_agentes_modelos_ferramentas(api, sessao):
    semear(sessao)
    pid = next(p["id"] for p in api.get(f"{V1}/processos", headers=como("helena")).json() if p["nome"] == "Resposta a dúvidas de lojistas")
    exe = api.post(f"{V1}/processos/{pid}/executar", json={"entrada": {"lojista_id": "L1001", "pergunta": "Prazo do estorno?"}},
                   headers=como("marina")).json()
    m = _mapa(api)
    nova = next(e for e in m["execucoes_recentes"] if e["id"] == exe["id"])
    assert nova["dono_tipo"] == "processo" and nova["dono_id"] == pid and nova["agente_id"] is None
    liga = {(l["de"], l["para"]) for l in m["ligacoes"]}
    assert all((de, para) in liga for de, para, _ in nova["arestas"])
    assert all(de == "processo:" + pid for de, _, o in nova["arestas"] if o == 0)
    # criador -> processo -> agente trabalhador (a camada de processos do mapa)
    no_processo = next(n for n in m["nos"] if n["id"] == "processo:" + pid)
    assert no_processo["coluna"] == "processos" and ("criador:" + no_processo["dono"], "processo:" + pid) in liga
    assert any(de == "processo:" + pid and para.startswith("agente:") for de, para in liga)
    # filtros de área continuam valendo para a camada nova
    risco = _mapa(api, "?area=risco")
    assert {n["area"] for n in risco["nos"] if n["tipo"] == "processo"} == {"risco"}
