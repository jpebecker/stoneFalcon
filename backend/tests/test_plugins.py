"""v6: marketplace de plugins homologados (simulado): vitrine, integração, governança dos sensíveis e página consolidada."""
import dataclasses

import pytest

from app.core.identidade import PERSONAS, Classificacao
from app.plugins import sistemas as sx
from app.plugins.catalogo import PLUGINS
from app.tools.catalogo import CATALOGO, Especificacao, disponiveis
from app.tools.executor import validar
from tests.conftest import como

pytestmark = pytest.mark.usefixtures("legado")   # v7: usa fluxos de vários passos como dado de exemplo (veja o fixture)

V1 = "/api/v1"
PERFIS = list(PERSONAS)

AGENTE_ZENDESK = {
    "nome": "Resposta pelo Zendesk", "objetivo": "Ler o chamado do lojista e responder dentro do Zendesk.", "area": "atendimento",
    "campos": [{"id": "chamado_id", "rotulo": "Chamado", "tipo": "texto", "exemplo": "Z-4812"}],
    "passos": [
        {"id": "chamado", "titulo": "Ler o chamado", "tipo": "ferramenta", "ferramenta": "zendesk_ler_chamado",
         "entrada": {"chamado_id": "{{entrada.chamado_id}}"}},
        {"id": "politica", "titulo": "Buscar a política", "tipo": "ferramenta", "ferramenta": "buscar_politica",
         "entrada": {"area": "atendimento", "consulta": "Em quanto tempo o estorno cai para o cliente?"}},
        {"id": "resposta", "titulo": "Responder no Zendesk", "tipo": "agente", "modelo": "rapido",
         "depende_de": ["chamado", "politica"], "ferramentas": ["zendesk_responder_chamado"],
         "instrucao": "Responda ao lojista no próprio chamado, citando a regra."}],
}


def _integrar(api, pessoa: str, plugin: str):
    r = api.post(f"{V1}/plugins/{plugin}/integrar", headers=como(pessoa))
    assert r.status_code == 200, r.text
    return r.json()


def _plugin(api, pessoa: str, plugin: str) -> dict:
    return api.get(f"{V1}/plugins/{plugin}", headers=como(pessoa)).json()


def _executar_zendesk(api, pessoa="marina") -> tuple[str, dict]:
    _integrar(api, pessoa, "zendesk")
    aid = api.post(f"{V1}/agentes", json={"blueprint": AGENTE_ZENDESK, "nota": "plugin"}, headers=como(pessoa)).json()["id"]
    assert api.post(f"{V1}/agentes/{aid}/publicar", headers=como(pessoa)).json()["estado"] == "publicado"
    r = api.post(f"{V1}/agentes/{aid}/executar", json={"entrada": {"chamado_id": "Z-4812"}}, headers=como(pessoa))
    assert r.status_code == 200, r.text
    return aid, r.json()


# ======================================================================= 05: vitrine
@pytest.mark.parametrize("perfil", PERFIS)
def test_vitrine_aparece_para_os_6_perfis(api, perfil):
    lista = api.get(f"{V1}/plugins", headers=como(perfil)).json()
    assert [p["nome"] for p in lista] == ["Arquivos e Planilhas", "Zendesk", "Salesforce", "Slack", "Jira", "Google Drive",
                                          "Google Sheets", "ServiceNow", "SAP SuccessFactors", "Datadog"]
    for p in lista:
        assert p["simulado"] is (p["id"] != "arquivos") and p["real"] is (p["id"] == "arquivos")     # só o Arquivos e Planilhas é de verdade
        assert p["categoria"] and p["estado"] == "disponivel"
        assert p["ferramentas"] and all(f["acao"] in ("leitura", "escrita") and f["classificacao"] for f in p["ferramentas"])
        assert isinstance(p["vale_para_minha_area"], bool)
    assert "plugins" in api.get(f"{V1}/eu", headers=como(perfil)).json()["abas"]


def test_cada_cartao_diz_se_vale_para_a_area_de_quem_olha(api):
    def vale(perfil):
        return {p["id"] for p in api.get(f"{V1}/plugins", headers=como(perfil)).json() if p["vale_para_minha_area"]}
    assert vale("marina") == {"arquivos", "zendesk", "salesforce", "slack", "drive"}      # "arquivos" (v8) vale para todas as áreas
    assert vale("carla") == {"arquivos", "slack", "drive", "sap"}
    assert vale("thiago") == {"arquivos", "slack", "drive", "jira", "sheets"}
    assert vale("lucas") == {"arquivos", "slack", "drive", "jira", "servicenow", "datadog"}


def test_ferramentas_de_plugin_seguem_o_contrato_do_catalogo():
    assert len(PLUGINS) == 10
    base = CATALOGO["abrir_chamado"]
    for p in PLUGINS.values():
        assert p.ferramentas, p.id
        for f in p.ferramentas:
            assert isinstance(f, Especificacao) and CATALOGO[f.id] is f and f.plugin == p.id
            assert isinstance(f.classificacao, Classificacao) and f.acao in ("leitura", "escrita")
            assert f.areas and f.nome and f.descricao and callable(f.executar) and f.latencia_ms > 0
            assert (f.obrigatorios or f.id == "arquivos_listar") and set(f.obrigatorios) <= set(f.parametros)
            assert set(f.para_modelo()) == set(base.para_modelo())          # mesmo formato entregue ao modelo
            assert f.classificacao <= p.classificacao
            assert f.limite_por_minuto <= (10 if f.acao == "escrita" else 30)
        assert p.classificacao == max(f.classificacao for f in p.ferramentas)
    assert {p.id for p in PLUGINS.values() if p.sensivel} == {"salesforce", "sap"}
    assert {k for k, p in PLUGINS.items() if p.janela} == {"zendesk", "slack", "jira"}   # só 3 ganham a janela do sistema externo


def test_ferramentas_de_plugin_executam_e_validam_a_entrada(api):
    from app.tools.catalogo import Contexto
    exemplos = {
        "zendesk_ler_chamado": {"chamado_id": "Z-4812"}, "zendesk_responder_chamado": {"chamado_id": "Z-4812", "resposta": "Ok"},
        "salesforce_consultar_conta": {"lojista_id": "L1001"}, "salesforce_registrar_interacao": {"lojista_id": "L1001", "resumo": "Ligação"},
        "slack_enviar_mensagem": {"canal": "#logistica", "mensagem": "Oi"}, "jira_abrir_item": {"projeto": "LOG", "titulo": "T", "descricao": "D"},
        "jira_consultar_status": {"item_id": "LOG-101"}, "drive_buscar_documento": {"consulta": "política de estorno"},
        "servicenow_abrir_incidente": {"titulo": "T", "descricao": "D"}, "sap_consultar_saldo_ferias": {"colaborador_id": "C501"},
        "datadog_consultar_alerta": {"servico": "api-repasses"}, "sheets_ler_planilha": {"fonte": "local:pedidos-troca"},
    }
    reais = {"arquivos_listar": {}, "arquivos_ler_linhas": {"arquivo": "faq.csv"}, "arquivos_buscar_linha": {"arquivo": "faq.csv", "coluna": "a", "valor": "b"},
             "arquivos_adicionar_linha": {"arquivo": "faq.csv", "valores": "{}"},
             "arquivos_atualizar_linha": {"arquivo": "faq.csv", "coluna_chave": "a", "valor_chave": "b", "valores": "{}"}}
    assert set(exemplos) | set(reais) == {f.id for p in PLUGINS.values() for f in p.ferramentas}
    for fid, entrada in reais.items():       # as de verdade precisam do banco: o comportamento delas está em test_arquivos.py
        assert validar(CATALOGO[fid], entrada) is None, fid
    for fid, entrada in exemplos.items():
        esp = CATALOGO[fid]
        assert validar(esp, entrada) is None, fid
        assert isinstance(esp.executar(entrada, Contexto(persona_id="marina")), dict)
        assert validar(esp, {}) is not None


def test_so_ferramenta_de_plugin_integrado_aparece_no_catalogo(api):
    ids = lambda: {f["id"] for f in api.get(f"{V1}/ferramentas", headers=como("marina")).json()["ferramentas"]}   # noqa: E731
    assert not any(i.startswith(("zendesk", "slack")) for i in ids())
    assert api.get(f"{V1}/ferramentas/zendesk_ler_chamado", headers=como("marina")).status_code == 404
    _integrar(api, "marina", "zendesk")
    assert {"zendesk_ler_chamado", "zendesk_responder_chamado"} <= ids()
    f = api.get(f"{V1}/ferramentas/zendesk_ler_chamado", headers=como("marina")).json()
    assert f["origem"] == "plugin Zendesk" and f["modulo_nome"] == "Plugins integrados"


# ======================================================================= 06: integrar plugin de risco baixo
def test_marina_integra_o_zendesk_e_usa_no_estudio(api):
    assert _plugin(api, "marina", "zendesk")["pode_integrar"] is True
    assert _integrar(api, "marina", "zendesk")["resultado"] == "integrado"
    assert _plugin(api, "marina", "zendesk")["estado"] == "integrado"

    teste = api.post(f"{V1}/estudio/testar", json={"blueprint": AGENTE_ZENDESK, "entrada": {"chamado_id": "Z-4812"}},
                     headers=como("marina")).json()
    assert teste["status"] == "concluida", teste
    assert "Dúvida sobre prazo de estorno" in str(teste["passos"]["chamado"]["saida"])        # resposta realista do sistema
    assert "Padaria Pão Dourado" in teste["passos"]["resposta"]["saida"] or "Zendesk" in teste["passos"]["resposta"]["saida"]
    resposta = sx.ZENDESK[0]["respostas"]
    assert len(resposta) == 1 and "Padaria Pão Dourado" in resposta[0]["texto"] and sx.ZENDESK[0]["status"] == "respondido"


def test_ferramenta_de_plugin_nao_integrado_nao_roda_nem_entra_no_agente(api):
    bp = {k: v for k, v in AGENTE_ZENDESK.items()}
    r = api.post(f"{V1}/estudio/validar", json={"blueprint": bp}, headers=como("marina")).json()
    assert r["valido"] is True and "zendesk_ler_chamado" in r["sem_permissao"]
    assert "não está integrado" in r["sem_permissao"]["zendesk_ler_chamado"]
    t = api.post(f"{V1}/ferramentas/zendesk_ler_chamado/testar", json={"entrada": {"chamado_id": "Z-4812"}}, headers=como("marina"))
    assert t.status_code == 404


def test_estudio_oferece_so_o_que_a_pessoa_pode_usar_do_plugin(api):
    _integrar(api, "lucas", "jira")
    # Marina (Atendimento) não pode usar o Jira (Engenharia e Logística): continua fora do agente dela
    from app.core.identidade import PERSONAS as P
    from app.tools.permissoes import avaliar
    assert avaliar(P["thiago"], CATALOGO["jira_abrir_item"]).permitido is True
    v = avaliar(P["marina"], CATALOGO["jira_abrir_item"])
    assert v.permitido is False and "área" in v.motivo


@pytest.mark.parametrize("perfil", ["helena"])
def test_perfil_sem_papel_pede_integracao_e_o_pedido_so_fica_registrado(api, perfil):
    p = _plugin(api, perfil, "zendesk")
    assert p["pode_integrar"] is False and p["pode_pedir"] is True
    assert api.post(f"{V1}/plugins/zendesk/integrar", headers=como(perfil)).status_code == 403
    r = api.post(f"{V1}/plugins/zendesk/pedir", json={"motivo": "Quero ver a fila"}, headers=como(perfil)).json()
    assert r["resultado"] == "registrado" and r["pedido"]["estado"] == "registrado"
    assert _plugin(api, perfil, "zendesk")["estado"] == "disponivel"                       # nada mudou
    assert api.get(f"{V1}/plugins/pedidos", headers=como("lucas")).json() == []           # não entra na fila da Segurança
    assert not disponiveis().get("zendesk_ler_chamado")


def test_criador_de_outra_area_nao_integra(api):
    assert _plugin(api, "marina", "jira")["pode_integrar"] is False and _plugin(api, "marina", "jira")["pode_pedir"] is True
    r = api.post(f"{V1}/plugins/jira/integrar", headers=como("marina"))
    assert r.status_code == 403 and "área" in r.json()["detail"]


def test_remover_tira_as_ferramentas_e_sinaliza_os_agentes(api):
    aid, exe = _executar_zendesk(api)
    assert exe["status"] == "concluida"
    r = api.delete(f"{V1}/plugins/zendesk/integracao", headers=como("marina"))
    assert r.status_code == 200 and [a["id"] for a in r.json()["agentes_afetados"]] == [aid]
    assert _plugin(api, "marina", "zendesk")["estado"] == "disponivel"
    assert "zendesk_ler_chamado" not in {f["id"] for f in api.get(f"{V1}/ferramentas", headers=como("marina")).json()["ferramentas"]}

    agente = api.get(f"{V1}/agentes/{aid}", headers=como("marina")).json()            # a página do agente não quebra
    assert agente["plugins_indisponiveis"] == [{"id": "zendesk", "nome": "Zendesk"}]
    lista = {a["id"]: a for a in api.get(f"{V1}/agentes", headers=como("marina")).json()}
    assert lista[aid]["plugins_indisponiveis"]
    exe2 = api.post(f"{V1}/agentes/{aid}/executar", json={"entrada": {"chamado_id": "Z-4812"}}, headers=como("marina")).json()
    assert exe2["status"] == "escalada" and "Zendesk" in (exe2["motivo"] or "") + str(exe2["passos"]["chamado"])   # com motivo, não em silêncio
    alertas = api.get(f"{V1}/alertas", headers=como("marina")).json()
    assert any(a["regra"] == "plugin_removido" and "Zendesk" in a["titulo"] for a in alertas)

    _integrar(api, "marina", "zendesk")                                                   # integrar de novo desfaz a sinalização
    assert api.get(f"{V1}/agentes/{aid}", headers=como("marina")).json()["plugins_indisponiveis"] == []
    assert not [a for a in api.get(f"{V1}/alertas", headers=como("marina")).json() if a["regra"] == "plugin_removido"]


def test_so_quem_integrou_ou_a_engenharia_remove(api):
    _integrar(api, "marina", "slack")
    assert api.delete(f"{V1}/plugins/slack/integracao", headers=como("thiago")).status_code == 403
    assert api.delete(f"{V1}/plugins/slack/integracao", headers=como("lucas")).status_code == 200


def test_integracao_e_remocao_ficam_na_auditoria(api):
    _integrar(api, "marina", "zendesk")
    api.delete(f"{V1}/plugins/zendesk/integracao", headers=como("marina"))
    ev = [e for e in api.get(f"{V1}/auditoria", params={"limite": 1000}, headers=como("helena")).json()["eventos"]
          if e["tipo"].startswith("plugin_")]
    assert [e["tipo"] for e in reversed(ev)] == ["plugin_integrado", "plugin_removido"]
    assert ev[1]["dados"]["plugin"] == "zendesk" and ev[1]["ator"] == "marina"
    assert api.get(f"{V1}/auditoria", headers=como("helena")).json()["cadeia"]["integra"] is True


def test_reiniciar_a_demo_volta_todos_os_plugins_ao_estado_inicial(api):
    _integrar(api, "marina", "zendesk")
    _integrar(api, "lucas", "datadog")
    api.post(f"{V1}/plugins/salesforce/integrar", headers=como("marina"))
    assert api.post(f"{V1}/demo/reiniciar", headers=como("helena")).status_code == 200
    estados = {p["id"]: p["estado"] for p in api.get(f"{V1}/plugins", headers=como("marina")).json()}
    assert estados.pop("arquivos") == "integrado"                  # o plugin real (v8) já nasce integrado com os arquivos da demo
    assert set(estados.values()) == {"disponivel"}
    assert api.get(f"{V1}/plugins/pedidos", headers=como("lucas")).json() == []
    assert {f.plugin for f in disponiveis().values() if f.plugin} == {"arquivos"}


# ======================================================================= 07: plugin sensível
def test_plugin_sensivel_vira_pedido_para_a_seguranca(api):
    r = api.post(f"{V1}/plugins/sap/integrar", json={"motivo": "Orientar férias com o saldo do SAP"}, headers=como("carla")).json()
    assert r["resultado"] == "pedido" and r["pedido"]["estado"] == "pendente"
    assert _plugin(api, "carla", "sap")["estado"] == "aguardando_aprovacao"
    assert "sap_consultar_saldo_ferias" not in disponiveis()
    fila = api.get(f"{V1}/plugins/pedidos", headers=como("lucas")).json()
    assert len(fila) == 1 and fila[0]["plugin_nome"] == "SAP SuccessFactors" and fila[0]["classificacao"] == "confidencial"
    assert fila[0]["motivo"].startswith("Orientar") and fila[0]["area_nome"] == "Pessoas (RH)"
    assert [f["id"] for f in fila[0]["ferramentas"]] == ["sap_consultar_saldo_ferias"]
    assert api.post(f"{V1}/plugins/sap/integrar", headers=como("carla")).status_code == 409      # não duplica o pedido


def test_aprovar_integra_e_avisa_quem_pediu(api):
    pid = api.post(f"{V1}/plugins/sap/integrar", headers=como("carla")).json()["pedido"]["id"]
    assert api.post(f"{V1}/plugins/pedidos/{pid}/decisao", json={"aprovar": True}, headers=como("lucas")).status_code == 422   # parecer
    r = api.post(f"{V1}/plugins/pedidos/{pid}/decisao", json={"aprovar": True, "parecer": "Leitura apenas, área de Pessoas."},
                 headers=como("lucas"))
    assert r.status_code == 200 and r.json()["estado"] == "aprovado"
    assert _plugin(api, "carla", "sap")["estado"] == "integrado" and "sap_consultar_saldo_ferias" in disponiveis()
    avisos = [a for a in api.get(f"{V1}/alertas", headers=como("carla")).json() if a["regra"] == "plugin_pedido"]
    assert len(avisos) == 1 and "aprovada" in avisos[0]["titulo"] and "Leitura apenas" in avisos[0]["detalhe"]
    assert api.get(f"{V1}/notificacoes/contagem", headers=como("carla")).json()["nao_lidos"] >= 1
    assert api.get(f"{V1}/plugins/pedidos", headers=como("lucas")).json() == []                  # saiu da fila


def test_recusar_volta_para_disponivel_com_parecer_visivel(api):
    pid = api.post(f"{V1}/plugins/sap/integrar", headers=como("carla")).json()["pedido"]["id"]
    r = api.post(f"{V1}/plugins/pedidos/{pid}/decisao", json={"aprovar": False, "parecer": "Dado restrito: pedir DLP antes."},
                 headers=como("lucas"))
    assert r.json()["estado"] == "recusado"
    p = _plugin(api, "carla", "sap")
    assert p["estado"] == "disponivel" and p["meu_pedido"]["estado"] == "recusado" and "DLP" in p["meu_pedido"]["parecer"]
    assert p["meu_pedido"]["revisor"] == "Lucas Prado"
    avisos = [a for a in api.get(f"{V1}/alertas", headers=como("carla")).json() if a["regra"] == "plugin_pedido"]
    assert avisos and "recusada" in avisos[0]["titulo"]
    assert "sap_consultar_saldo_ferias" not in disponiveis()
    assert api.post(f"{V1}/plugins/sap/integrar", headers=como("carla")).status_code == 200     # pode pedir de novo


def test_ninguem_aprova_o_proprio_pedido(api):
    # a Engenharia também passa pelos quatro olhos: o pedido dela precisa de outra pessoa da Segurança
    pid = api.post(f"{V1}/plugins/salesforce/integrar", headers=como("lucas")).json()["pedido"]["id"]
    r = api.post(f"{V1}/plugins/pedidos/{pid}/decisao", json={"aprovar": True, "parecer": "Eu mesmo aprovo."}, headers=como("lucas"))
    assert r.status_code == 403 and "quatro olhos" in r.json()["detail"]
    assert _plugin(api, "lucas", "salesforce")["estado"] == "aguardando_aprovacao"
    # quem não é da Segurança nem do CoE não decide
    assert api.post(f"{V1}/plugins/pedidos/{pid}/decisao", json={"aprovar": True, "parecer": "ok"}, headers=como("thiago")).status_code == 403


def test_pedido_aprovacao_e_recusa_ficam_na_auditoria(api):
    a = api.post(f"{V1}/plugins/sap/integrar", headers=como("carla")).json()["pedido"]["id"]
    api.post(f"{V1}/plugins/pedidos/{a}/decisao", json={"aprovar": False, "parecer": "Não agora."}, headers=como("lucas"))
    b = api.post(f"{V1}/plugins/sap/integrar", headers=como("carla")).json()["pedido"]["id"]
    api.post(f"{V1}/plugins/pedidos/{b}/decisao", json={"aprovar": True, "parecer": "Pode."}, headers=como("lucas"))
    tipos = [e["tipo"] for e in reversed(api.get(f"{V1}/auditoria", params={"limite": 1000}, headers=como("helena")).json()["eventos"])
             if e["tipo"].startswith("plugin_")]
    assert tipos == ["plugin_pedido_criado", "plugin_pedido_recusado", "plugin_pedido_criado", "plugin_pedido_aprovado", "plugin_integrado"]


def test_area_e_nivel_continuam_valendo_depois_de_integrar(api):
    """Aprovado, o SAP (confidencial, só Pessoas) roda para a Carla, mas não para o Atendimento: integrar não é porta dos fundos."""
    pid = api.post(f"{V1}/plugins/sap/integrar", headers=como("carla")).json()["pedido"]["id"]
    api.post(f"{V1}/plugins/pedidos/{pid}/decisao", json={"aprovar": True, "parecer": "Pode."}, headers=como("lucas"))
    assert api.get(f"{V1}/ferramentas/sap_consultar_saldo_ferias", headers=como("carla")).json()["disponivel_para_mim"] is True
    f = api.get(f"{V1}/ferramentas/sap_consultar_saldo_ferias", headers=como("marina")).json()
    assert f["disponivel_para_mim"] is False and "área" in f["motivo"]


# ======================================================================= 08: página consolidada
def test_pagina_do_plugin_so_para_integrado(api):
    assert api.get(f"{V1}/plugins/zendesk/consolidado", headers=como("marina")).status_code == 409
    _integrar(api, "marina", "zendesk")
    assert api.get(f"{V1}/plugins/zendesk/consolidado", headers=como("marina")).status_code == 200
    assert _plugin(api, "marina", "zendesk")["pode_remover"] is True


def test_numeros_vem_das_execucoes_e_a_janela_reflete_os_agentes(api):
    aid, exe = _executar_zendesk(api)
    pg = api.get(f"{V1}/plugins/zendesk/consolidado", headers=como("marina")).json()
    n = pg["numeros"]
    assert n["agentes"] == 1 and n["chamadas_mes"] == 2 and n["execucoes"] == 1 and n["custo_brl"] > 0 and n["latencia_p95_ms"] > 0
    assert [(a["nome"], a["chamadas"]) for a in pg["agentes"]] == [("Resposta pelo Zendesk", 2)]
    assert pg["saude"]["status"] == "ok" and {t["id"] for t in pg["saude"]["por_ferramenta"]} == {"zendesk_ler_chamado", "zendesk_responder_chamado"}
    fila = pg["janela"]["itens"]
    assert pg["janela"]["tipo"] == "fila" and len(fila) == 3
    z = next(c for c in fila if c["id"] == "Z-4812")
    assert z["status"] == "respondido" and "Resposta pelo Zendesk" in z["respostas"][0]["autor"]
    # mais uma execução: os números sobem (não são fixos na tela)
    api.post(f"{V1}/agentes/{aid}/executar", json={"entrada": {"chamado_id": "Z-4813"}}, headers=como("marina"))
    n2 = api.get(f"{V1}/plugins/zendesk/consolidado", headers=como("marina")).json()["numeros"]
    assert n2["chamadas_mes"] == 4 and n2["execucoes"] == 2 and n2["custo_brl"] > n["custo_brl"]


def test_slack_e_jira_tem_janela_e_os_outros_so_numeros(api):
    _integrar(api, "thiago", "slack")
    _integrar(api, "thiago", "jira")
    _integrar(api, "marina", "drive")
    sl = api.get(f"{V1}/plugins/slack/consolidado", headers=como("thiago")).json()["janela"]
    assert sl["tipo"] == "canais" and [c["canal"] for c in sl["canais"]][0] == "#logistica"
    jr = api.get(f"{V1}/plugins/jira/consolidado", headers=como("thiago")).json()["janela"]
    assert jr["tipo"] == "quadro" and [c["nome"] for c in jr["colunas"]] == ["A fazer", "Em andamento", "Concluído"]
    assert api.get(f"{V1}/plugins/drive/consolidado", headers=como("marina")).json()["janela"] is None


def test_falha_simulada_aparece_como_alerta_de_saude_na_pagina(api):
    _integrar(api, "marina", "zendesk")
    antes = api.get(f"{V1}/plugins/zendesk/consolidado", headers=como("marina")).json()["saude"]
    assert antes["status"] == "ok" and antes["alertas"] == []
    f = api.post(f"{V1}/ferramentas/zendesk_ler_chamado/falha", json={"falha": "fora_do_ar"}, headers=como("lucas"))
    assert f.status_code == 200
    saude = api.get(f"{V1}/plugins/zendesk/consolidado", headers=como("marina")).json()["saude"]
    assert saude["status"] == "fora" and saude["alertas"][0]["conector"] == "zendesk_ler_chamado"
    assert next(t for t in saude["por_ferramenta"] if t["id"] == "zendesk_ler_chamado")["falha"] == "fora_do_ar"
    api.post(f"{V1}/ferramentas/zendesk_ler_chamado/falha", json={"falha": None}, headers=como("lucas"))
    assert api.get(f"{V1}/plugins/zendesk/consolidado", headers=como("marina")).json()["saude"]["status"] == "ok"
    # a Saúde de conectores também enxerga o plugin integrado (e só ele)
    ids = {c["id"] for c in api.get(f"{V1}/saude/conectores", headers=como("marina")).json()}
    assert "zendesk_ler_chamado" in ids and "slack_enviar_mensagem" not in ids


def test_sem_nivel_para_a_classificacao_so_numeros_agregados(sessao):
    """Os 6 perfis têm nível interno ou mais; o caso é montado com uma pessoa de nível público."""
    from app.plugins import servico
    servico._integrar_agora(sessao, PLUGINS["zendesk"], PERSONAS["marina"], "direta")
    sem_nivel = dataclasses.replace(PERSONAS["marina"], nivel=Classificacao.PUBLICA)
    pg = servico.consolidado(sessao, sem_nivel, "zendesk")
    assert pg["nivel_suficiente"] is False and pg["janela"] is None and "numeros" in pg and "saude" in pg
    com_nivel = servico.consolidado(sessao, PERSONAS["marina"], "zendesk")
    assert com_nivel["nivel_suficiente"] is True and com_nivel["janela"]["tipo"] == "fila"


def test_agentes_de_outra_area_nao_aparecem_na_lista_de_quem_nao_pode_ve_los(api):
    _executar_zendesk(api)
    # Helena (CoE) enxerga todos os agentes; Thiago, de Logística, não vê o da Marina, mas o número agregado inclui
    pg = api.get(f"{V1}/plugins/zendesk/consolidado", headers=como("thiago")).json()
    assert pg["numeros"]["agentes"] == 1 and pg["agentes"] == [] and pg["agentes_ocultos"] == 1
    assert [a["nome"] for a in api.get(f"{V1}/plugins/zendesk/consolidado", headers=como("helena")).json()["agentes"]] == ["Resposta pelo Zendesk"]


def test_plugin_inexistente_responde_404(api):
    assert api.get(f"{V1}/plugins/naoexiste", headers=como("marina")).status_code == 404
    assert api.post(f"{V1}/plugins/naoexiste/integrar", headers=como("marina")).status_code == 404


# ======================================================================= correções da revisão da v6
def test_chamadas_por_agente_sao_as_de_cada_agente(api):
    """Dois agentes no mesmo plugin: cada um mostra as próprias chamadas, não o total da ferramenta."""
    aid, _ = _executar_zendesk(api)
    outro = dict(AGENTE_ZENDESK, nome="Segunda resposta pelo Zendesk")
    aid2 = api.post(f"{V1}/agentes", json={"blueprint": outro, "nota": "plugin"}, headers=como("marina")).json()["id"]
    assert api.post(f"{V1}/agentes/{aid2}/publicar", headers=como("marina")).json()["estado"] == "publicado"
    for chamado in ("Z-4813", "Z-4814"):
        r = api.post(f"{V1}/agentes/{aid2}/executar", json={"entrada": {"chamado_id": chamado}}, headers=como("marina"))
        assert r.status_code == 200, r.text
    pg = api.get(f"{V1}/plugins/zendesk/consolidado", headers=como("marina")).json()
    por_agente = {a["nome"]: a["chamadas"] for a in pg["agentes"]}
    assert por_agente == {"Resposta pelo Zendesk": 2, "Segunda resposta pelo Zendesk": 4}
    assert sum(por_agente.values()) == pg["numeros"]["chamadas_mes"]


def test_janela_respeita_a_area_alem_do_nivel(api):
    """Zendesk é só do Atendimento: o Thiago (Logística) vê os números, não a fila; a Helena (CoE) vê tudo."""
    _executar_zendesk(api)
    thiago = api.get(f"{V1}/plugins/zendesk/consolidado", headers=como("thiago")).json()
    assert thiago["nivel_suficiente"] is True and thiago["area_permitida"] is False
    assert thiago["janela"] is None and thiago["numeros"]["chamadas_mes"] == 2
    helena = api.get(f"{V1}/plugins/zendesk/consolidado", headers=como("helena")).json()
    assert helena["area_permitida"] is True and helena["janela"]["tipo"] == "fila"
    marina = api.get(f"{V1}/plugins/zendesk/consolidado", headers=como("marina")).json()
    assert marina["area_permitida"] is True and marina["janela"]["tipo"] == "fila"


@pytest.fixture()
def motor_arquivo(tmp_path):
    """SQLite em arquivo, como em produção: cada thread com a própria conexão. (O banco em memória dos testes
    compartilha UMA conexão entre threads, o que embaralha as transações e não serve para testar concorrência.)"""
    from app.core import db
    from app.plugins import servico as plugins
    m = db.criar_motor("sqlite:///%s" % (tmp_path / "corrida.db").as_posix())
    db.usar_motor(m)
    db.criar_tabelas()
    plugins.zerar()
    yield m
    plugins.zerar()
    m.dispose()


def _em_paralelo(funcao, vezes: int = 2) -> list:
    """Roda `funcao(sessao)` em threads, cada uma com a própria sessão; devolve o resultado ou a exceção de cada uma."""
    import threading

    from sqlmodel import Session

    from app.core import db
    saida, comeca = [], threading.Barrier(vezes)

    def rodar():
        with Session(db.motor()) as s:
            comeca.wait()
            try:
                saida.append(funcao(s))
            except Exception as e:  # noqa: BLE001
                saida.append(e)
    threads = [threading.Thread(target=rodar) for _ in range(vezes)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    return saida


def test_dois_cliques_em_integrar_integram_uma_vez(motor_arquivo):
    from sqlmodel import Session, select

    from app.audit.trilha import EventoAuditoria
    from app.plugins import servico
    saida = _em_paralelo(lambda s: servico.integrar(s, PERSONAS["thiago"], "slack"))
    assert sum(1 for r in saida if r == {"resultado": "integrado"}) == 1
    erro = next(r for r in saida if isinstance(r, Exception))
    assert isinstance(erro, servico.ErroPlugin) and erro.status == 409
    with Session(motor_arquivo) as s:
        assert len(s.exec(select(EventoAuditoria).where(EventoAuditoria.tipo == "plugin_integrado")).all()) == 1


def test_dois_cliques_em_aprovar_decidem_uma_vez(motor_arquivo):
    from sqlmodel import Session, select

    from app.audit.trilha import EventoAuditoria
    from app.plugins import servico
    with Session(motor_arquivo) as s:
        pid = servico.integrar(s, PERSONAS["carla"], "sap")["pedido"]["id"]
    saida = _em_paralelo(lambda s: servico.decidir(s, PERSONAS["lucas"], pid, True, "Pode."))
    assert sum(1 for r in saida if isinstance(r, dict) and r["estado"] == "aprovado") == 1
    erro = next(r for r in saida if isinstance(r, Exception))
    assert isinstance(erro, servico.ErroPlugin) and erro.status == 409
    with Session(motor_arquivo) as s:
        tipos = [e.tipo for e in s.exec(select(EventoAuditoria)) if e.tipo.startswith("plugin_")]
    assert tipos.count("plugin_pedido_aprovado") == 1 and tipos.count("plugin_integrado") == 1


def test_prova_do_slack_nao_depende_do_estado_da_demo():
    """'Mostrar na tela' da pergunta do Slack começa no passo de integrar, que funciona com o Slack integrado ou não."""
    from app.roteiros import perguntas
    from app.roteiros.catalogo import ROTEIROS
    q = next(x for x in perguntas.PERGUNTAS if x["id"] == "thiago-5")
    assert q["prova"]["roteiro"] == "thiago" and q["prova"]["passo"] == "integrar"
    passo = next(p for p in ROTEIROS["thiago"].passos if p.id == "integrar")
    assert passo.rota == q["prova"]["rota"] and passo.perfil == q["prova"]["perfil"]


# ======================================================================= revisão da v6: itens 6 a 15
def test_escrita_de_plugin_em_dado_sensivel_exige_confirmacao_humana():
    for p in PLUGINS.values():
        for f in p.ferramentas:
            assert f.exige_aprovacao == (f.acao == "escrita" and f.classificacao >= Classificacao.CONFIDENCIAL), f.id
    assert CATALOGO["salesforce_registrar_interacao"].exige_aprovacao is True
    assert PLUGINS["sap"].classificacao == Classificacao.CONFIDENCIAL and PLUGINS["sap"].sensivel


def test_pedido_da_seguranca_e_decidido_pela_helena(api):
    r = api.post(f"{V1}/plugins/salesforce/integrar", headers=como("lucas")).json()
    assert r["resultado"] == "pedido" and r["pedido"]["estado"] == "pendente"
    pid = r["pedido"]["id"]
    # a Helena fica sabendo e vê o pedido (na página do plugin e na lista de pedidos)
    avisos = [a for a in api.get(f"{V1}/alertas", headers=como("helena")).json() if a["regra"] == "plugin_pedido"]
    assert len(avisos) == 1 and "Salesforce" in avisos[0]["titulo"]
    assert _plugin(api, "helena", "salesforce")["pedido_pendente"]["pode_decidir"] is True
    assert _plugin(api, "lucas", "salesforce")["pedido_pendente"]["pode_decidir"] is False
    fila = api.get(f"{V1}/plugins/pedidos", headers=como("helena")).json()
    assert [(x["id"], x["pode_decidir"]) for x in fila] == [(pid, True)]
    d = api.post(f"{V1}/plugins/pedidos/{pid}/decisao", json={"aprovar": True, "parecer": "Ok do CoE."}, headers=como("helena"))
    assert d.status_code == 200 and d.json()["estado"] == "aprovado" and d.json()["revisor"] == "helena"
    assert _plugin(api, "lucas", "salesforce")["estado"] == "integrado"


def test_helena_nao_decide_pedido_de_quem_nao_e_da_seguranca(api):
    pid = api.post(f"{V1}/plugins/sap/integrar", headers=como("carla")).json()["pedido"]["id"]
    assert _plugin(api, "helena", "sap")["pedido_pendente"]["pode_decidir"] is False
    assert api.get(f"{V1}/plugins/pedidos", headers=como("helena")).json() == []
    r = api.post(f"{V1}/plugins/pedidos/{pid}/decisao", json={"aprovar": True, "parecer": "ok"}, headers=como("helena"))
    assert r.status_code == 403
    assert not [a for a in api.get(f"{V1}/alertas", headers=como("helena")).json() if a["regra"] == "plugin_pedido"]


def test_resposta_do_zendesk_nao_ocupa_o_lugar_do_chamado_da_plataforma():
    from app.runtime.respostas import Contexto as Ctx
    ctx = Ctx(entrada={})
    ctx.absorver({"chamado_id": "Z-4812", "status": "respondido", "respostas": 1})
    assert ctx.zendesk and ctx.zendesk["chamado_id"] == "Z-4812" and ctx.chamado is None
    ctx.absorver({"chamado_id": "CH-1001", "status": "aberto", "fila": "logistica"})
    assert ctx.chamado["chamado_id"] == "CH-1001"


@pytest.mark.parametrize("descricao, entra", [
    ("Confiro o estoque e aviso o canal de vendas por telefone.", False),
    ("Confiro o estoque e aviso o time no Slack.", True),
    ("Confiro o estoque e aviso o #logistica.", True),
])
def test_passo_do_slack_so_quando_a_descricao_fala_do_slack(descricao, entra):
    from app.plugins import estado
    from app.studio.sugestao import _slack_no_processo
    estado.INTEGRADOS.add("slack")
    try:
        usa, avisos = _slack_no_processo(PERSONAS["thiago"], descricao)
        assert avisos == [] and usa is entra
    finally:
        estado.INTEGRADOS.discard("slack")


def test_ids_dos_sistemas_simulados_nao_se_repetem_em_paralelo():
    import threading

    from app.tools.catalogo import Contexto
    sx.zerar()
    esp = CATALOGO["slack_enviar_mensagem"]
    comeca = threading.Barrier(8)

    def enviar():
        comeca.wait()
        esp.executar({"canal": "#geral", "mensagem": "oi"}, Contexto(persona_id="thiago"))
    threads = [threading.Thread(target=enviar) for _ in range(8)]
    for th in threads:
        th.start()
    for th in threads:
        th.join()
    ids = [m["id"] for m in sx.SLACK]
    assert len(ids) == 8 and len(set(ids)) == 8
    sx.zerar()
