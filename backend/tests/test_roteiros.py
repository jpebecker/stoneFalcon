"""Ensaio geral: percorre os 6 roteiros do início ao fim pela API, com as entradas do próprio roteiro.

Cada teste faz o que a pessoa faria na tela, sem digitar nada além do que o roteiro mostra e sem chave da API.
"""
import json

import pytest

from app.roteiros.catalogo import ROTEIROS
from app.roteiros.perguntas import PERGUNTAS
from app.tools import dados_ficticios as fx
from tests.conftest import como

V1 = "/api/v1"


def _passo(roteiro_id: str, passo_id: str):
    return next(p for p in ROTEIROS[roteiro_id].passos if p.id == passo_id)


def _iniciar(api, roteiro_id: str):
    r = api.post(f"{V1}/roteiros/{roteiro_id}/reiniciar", headers=como("helena"))
    assert r.status_code == 200, r.text
    assert api.get(f"{V1}/roteiros/{roteiro_id}", headers=como(ROTEIROS[roteiro_id].persona)).status_code == 200


def _criar(api, roteiro_id: str, persona: str, esperado: str):
    """Passo 'criar': descreve o processo com o texto do roteiro e confere o agente montado."""
    texto = _passo(roteiro_id, "criar").preenche["descricao"]
    sug = api.post(f"{V1}/estudio/sugerir", json={"descricao": texto}, headers=como(persona))
    assert sug.status_code == 200, sug.text
    sug = sug.json()
    assert sug["origem"] == "padrao:" + esperado, sug["origem"]
    assert sug["alertas"] == [] and not sug["ferramentas_removidas"]
    bp = sug["blueprint"]
    assert all(c["rotulo"] and c["tipo"] for c in bp["campos"])   # campos em linguagem de usuário
    return bp, sug


def _testar(api, roteiro_id: str, persona: str, bp: dict) -> dict:
    entrada = _passo(roteiro_id, "testar").preenche["entrada"]
    r = api.post(f"{V1}/estudio/testar", json={"blueprint": bp, "entrada": entrada}, headers=como(persona))
    assert r.status_code == 200, r.text
    return r.json()


def _salvar(api, persona: str, bp: dict) -> str:
    r = api.post(f"{V1}/agentes", json={"blueprint": bp, "nota": "roteiro"}, headers=como(persona))
    assert r.status_code == 200, r.text
    return r.json()["id"]


def _publicar(api, persona: str, agente_id: str) -> dict:
    r = api.post(f"{V1}/agentes/{agente_id}/publicar", headers=como(persona))
    assert r.status_code == 200, r.text
    return r.json()


def _executar(api, persona: str, agente_id: str, entrada: dict) -> dict:
    r = api.post(f"{V1}/agentes/{agente_id}/executar", json={"entrada": entrada}, headers=como(persona))
    assert r.status_code == 200, r.text
    return r.json()


def _texto_final(exe: dict, passo: str) -> str:
    return exe["passos"][passo]["saida"] or ""


def _fim(api, roteiro_id: str, agente_id: str | None = None):
    """Passo 'medir': AS IS × TO BE com a origem dos números. As perguntas ficam só na aba da Helena (cada persona
    continua com 3 a 5 perguntas, filtráveis por persona)."""
    persona = ROTEIROS[roteiro_id].persona
    res = api.get(f"{V1}/roteiros/{roteiro_id}/resultado", params={"agente_id": agente_id} if agente_id else {},
                  headers=como(persona)).json()
    linhas = {l["criterio"]: l for l in res["linhas"]}
    assert set(linhas) == {"Tempo por tarefa", "Custo por tarefa", "Produtividade", "Erros", "ROI"}
    for l in linhas.values():
        assert l["origem_as_is"] and l["origem_to_be"]   # cada número diz se é medido ou hipótese
    tempo = linhas["Tempo por tarefa"]
    assert tempo["to_be"] < tempo["as_is"]
    assert "medido" in tempo["origem_to_be"] and tempo["origem_as_is"] == "hipótese"
    perguntas = api.get(f"{V1}/perguntas", params={"persona": persona}, headers=como("helena")).json()["perguntas"]
    assert 3 <= len(perguntas) <= 5
    assert all(q["resposta"] and q["prova"]["rota"] for q in perguntas)
    return res


# ---------------------------------------------------------------- Marina
def test_roteiro_marina(api):
    _iniciar(api, "marina")
    # estado inicial do roteiro: o agente dela ainda não existe
    nomes = [a["nome"] for a in api.get(f"{V1}/agentes", headers=como("marina")).json()]
    assert "Resposta a dúvidas de lojistas" not in nomes

    bp, sug = _criar(api, "marina", "marina", "duvida_lojista")
    assert bp["minutos_manual"] == 8
    assert sug["risco"]["nivel"] == "baixo"
    teste = _testar(api, "marina", "marina", bp)
    assert teste["status"] == "concluida"
    assert "estorno" in _texto_final(teste, "resposta").lower() or "faturas" in _texto_final(teste, "resposta")
    assert "resposta simulada" not in _texto_final(teste, "resposta").lower()

    aid = _salvar(api, "marina", bp)
    assert _publicar(api, "marina", aid)["estado"] == "publicado"      # risco baixo: sem fila

    exe = _executar(api, "marina", aid, _passo("marina", "usar").preenche["entrada"])
    assert exe["status"] == "concluida"
    assert "Ótica Visão Clara" in _texto_final(exe, "resposta")
    assert exe["passos"]["cadastro"]["duracao_estimada_ms"] and exe["passos"]["politica"]["duracao_estimada_ms"]
    res = _fim(api, "marina", aid)
    assert res["execucao"]["id"] == exe["id"] and res["origem"] == "medido"


# ---------------------------------------------------------------- Rafael
def test_roteiro_rafael(api):
    _iniciar(api, "rafael")
    bp, sug = _criar(api, "rafael", "rafael", "triagem_chargeback")
    assert sug["risco"]["nivel"] == "alto" and sug["risco"]["exige_revisao_seguranca"]

    seguro = _testar(api, "rafael", "rafael", bp)                      # L1001: sem risco
    assert seguro["status"] == "concluida" and not fx.BLOQUEIOS

    aid = _salvar(api, "rafael", bp)
    assert _publicar(api, "rafael", aid)["estado"] == "em_revisao"     # risco alto: quatro olhos
    fila = api.get(f"{V1}/revisoes", headers=como("lucas")).json()
    assert [i["agente"]["id"] for i in fila] == [aid]
    parecer = _passo("rafael", "revisao").preenche["parecer"]
    r = api.post(f"{V1}/agentes/{aid}/revisao", json={"aprovar": True, "parecer": parecer}, headers=como("lucas"))
    assert r.status_code == 200 and r.json()["estado"] == "publicado"

    exe = _executar(api, "rafael", aid, _passo("rafael", "usar").preenche["entrada"])
    assert exe["status"] == "aguardando_aprovacao"                      # a retenção pausa
    assert not fx.BLOQUEIOS
    assert "Eletrônicos Relâmpago" in _texto_final(exe, "analise") and "Risco ALTO" in _texto_final(exe, "analise")
    assert exe["passos"]["analise"]["modelo"] and exe["passos"]["analise"]["motivos_modelo"]   # o roteador explica
    d = api.post(f"{V1}/execucoes/{exe['id']}/decisao", json={"aprovar": True}, headers=como("rafael"))
    assert d.status_code == 200 and d.json()["status"] == "concluida"
    assert [b["lojista_id"] for b in fx.BLOQUEIOS] == ["L1003"]

    auditoria = api.get(f"{V1}/auditoria", headers=como("helena")).json()
    assert auditoria["cadeia"]["integra"] is True
    res = _fim(api, "rafael", aid)
    assert res["execucao"]["status"] == "concluida"


# ---------------------------------------------------------------- Carla
def test_roteiro_carla(api):
    _iniciar(api, "carla")
    bp, sug = _criar(api, "carla", "carla", "ferias_colaborador")
    assert sug["risco"]["nivel"] == "medio"
    teste = _testar(api, "carla", "carla", bp)
    assert teste["status"] == "concluida"

    aid = _salvar(api, "carla", bp)
    assert _publicar(api, "carla", aid)["estado"] == "publicado"
    exe = _executar(api, "carla", aid, _passo("carla", "usar").preenche["entrada"])
    assert exe["status"] == "concluida"
    final = _texto_final(exe, "resposta")
    assert "18 dias" in final and "Bruno" in final

    # nada de dado pessoal no modelo, no log nem no resultado salvo
    cpf = fx.COLABORADORES["C501"]["cpf"]
    email = fx.COLABORADORES["C501"]["email"]
    auditoria = api.get(f"{V1}/auditoria", params={"limite": 1000}, headers=como("lucas")).json()
    bruto = json.dumps(auditoria, ensure_ascii=False) + json.dumps(exe["passos"], ensure_ascii=False)
    bruto += json.dumps(api.get(f"{V1}/execucoes/{exe['id']}", headers=como("carla")).json(), ensure_ascii=False)
    assert cpf not in bruto and email not in bruto and cpf[:3] + cpf[3:] not in final
    ev = [e for e in auditoria["eventos"] if e["tipo"] == "ferramenta_executada" and e["dados"].get("conector") == "consultar_colaborador"]
    assert ev and any(m["tipo"] in ("cpf", "email") or "CPF" in str(m) for e in ev for m in e["dados"].get("mascarados", []))
    _fim(api, "carla", aid)


# ---------------------------------------------------------------- Thiago
def test_roteiro_thiago(api):
    from app.plugins import sistemas as sx
    _iniciar(api, "thiago")
    # passo 'integrar': sem o plugin, o Estúdio orienta a integrar o Slack; integrar é direto (Slack é interno)
    texto = _passo("thiago", "criar").preenche["descricao"]
    antes = api.post(f"{V1}/estudio/sugerir", json={"descricao": texto}, headers=como("thiago")).json()
    assert any("plugin do Slack" in a for a in antes["alertas"]) and "canal" not in [p["id"] for p in antes["blueprint"]["passos"]]
    r = api.post(f"{V1}/plugins/slack/integrar", headers=como("thiago"))
    assert r.status_code == 200 and r.json()["resultado"] == "integrado", r.text
    cat = {f["id"]: f for f in api.get(f"{V1}/ferramentas", headers=como("thiago")).json()["ferramentas"]}
    assert cat["slack_enviar_mensagem"]["origem"] == "plugin Slack"

    bp, sug = _criar(api, "thiago", "thiago", "troca_maquininha_estoque")
    assert sug["risco"]["nivel"] == "medio"
    assert sug["niveis"][0] == ["cadastro", "regra", "estoque"]         # três passos em paralelo
    assert "canal" in [p["id"] for p in bp["passos"]]                   # depois do chamado, avisa o canal
    teste = _testar(api, "thiago", "thiago", bp)
    assert teste["status"] == "concluida"

    aid = _salvar(api, "thiago", bp)
    assert _publicar(api, "thiago", aid)["estado"] == "publicado"
    exe = _executar(api, "thiago", aid, _passo("thiago", "usar").preenche["entrada"])
    assert exe["status"] == "concluida"
    assert "estoque baixo" in _texto_final(exe, "chamado") and "Maquininha Smart" in _texto_final(exe, "chamado")
    assert fx.CHAMADOS[-1]["fila"] == "logistica" and "Smart" in fx.CHAMADOS[-1]["titulo"]
    assert fx.NOTIFICACOES, "o aviso ao lojista foi enviado"
    msg = sx.SLACK[-1]
    assert msg["canal"] == "#logistica" and "Smart" in msg["mensagem"] and fx.CHAMADOS[-1]["id"] in msg["mensagem"]
    assert "#logistica" in _texto_final(exe, "canal")
    inicios = [exe["passos"][p]["duracao_estimada_ms"] for p in ("cadastro", "regra", "estoque")]
    assert exe["duracao_estimada_ms"] < sum(inicios) + exe["passos"]["chamado"]["duracao_estimada_ms"] +         exe["passos"]["aviso"]["duracao_estimada_ms"] + exe["passos"]["canal"]["duracao_estimada_ms"]   # paralelo: não soma

    # passo 'canal': a página consolidada do Slack mostra a mensagem que o agente publicou
    pg = api.get(f"{V1}/plugins/slack/consolidado", headers=como("thiago")).json()
    canal = next(c for c in pg["janela"]["canais"] if c["canal"] == "#logistica")
    assert any("Smart" in m["texto"] and "Troca de maquininha com estoque" in m["autor"] for m in canal["mensagens"])
    assert pg["numeros"]["chamadas_mes"] >= 2 and [a["nome"] for a in pg["agentes"]] == ["Troca de maquininha com estoque"]
    res = _fim(api, "thiago", aid)
    assert any("Slack" in p for p in ROTEIROS["thiago"].to_be["passos"] + ROTEIROS["thiago"].as_is["passos"])   # o cartão considera o aviso ao canal
    assert res["execucao"]["id"] == exe["id"]

    # reiniciar o roteiro devolve o Slack a "disponível"
    _iniciar(api, "thiago")
    slack = api.get(f"{V1}/plugins/slack", headers=como("thiago")).json()
    assert slack["estado"] == "disponivel" and not sx.SLACK


# ---------------------------------------------------------------- Lucas
def test_roteiro_lucas(api):
    _iniciar(api, "lucas")
    fila = api.get(f"{V1}/revisoes", headers=como("lucas")).json()
    assert len(fila) == 1 and fila[0]["agente"]["nome"] == "Triagem de chargebacks"
    assert any("Slack" in str(m["depois"]) or "enviar_notificacao" in str(m["depois"]) for m in fila[0]["mudancas"])
    parecer = _passo("lucas", "revisao").preenche["parecer"]
    r = api.post(f"{V1}/agentes/{fila[0]['agente']['id']}/revisao", json={"aprovar": True, "parecer": parecer},
                 headers=como("lucas"))
    assert r.status_code == 200 and r.json()["estado"] == "publicado"

    agentes = api.get(f"{V1}/agentes", headers=como("marina")).json()
    duvida = next(a for a in agentes if a["nome"] == "Resposta a dúvidas de lojistas")
    f = api.post(f"{V1}/ferramentas/consultar_lojista/falha", json={"falha": "fora_do_ar"}, headers=como("lucas"))
    assert f.status_code == 200
    exe = _executar(api, "marina", duvida["id"], _passo("lucas", "usar").preenche["entrada"])
    assert exe["status"] == "escalada" and exe["motivo"]
    assert api.get(f"{V1}/notificacoes/contagem", headers=como("marina")).json()["criticos"] >= 1

    p = api.post(f"{V1}/agentes/{duvida['id']}/pausar", json={"motivo": "Sistema de cadastro fora do ar"}, headers=como("lucas"))
    assert p.status_code == 200 and p.json()["estado"] == "pausado"
    api.post(f"{V1}/ferramentas/consultar_lojista/falha", json={"falha": None}, headers=como("lucas"))
    abertos = [a for a in api.get(f"{V1}/alertas", headers=como("marina")).json() if not a.get("resolvido_em")]
    assert not [a for a in abertos if a["regra"] == "conector_fora"]    # o alerta fecha sozinho
    assert api.post(f"{V1}/agentes/{duvida['id']}/retomar", headers=como("lucas")).json()["estado"] == "publicado"


# ---------------------------------------------------------------- Helena
def test_roteiro_helena(api):
    _iniciar(api, "helena")
    ind = api.get(f"{V1}/financas/indicadores", headers=como("helena")).json()
    assert ind["tempo_execucao"]["reducao_pct"] and ind["custo_operacional"]["economia_roteador_pct"]
    cons = api.get(f"{V1}/roteiros/consolidado", headers=como("helena")).json()
    assert [p["roteiro"] for p in cons["processos"]] == ["marina", "rafael", "carla", "thiago"]
    for p in cons["processos"]:
        assert p["to_be_min"] < p["as_is_min"] and p["origem_as_is"] == "hipótese"
        assert p["calculadora"]["minutos_por_tarefa"] == p["as_is_min"]
    assert cons["totais"]["reducao_pct"] > 0.7
    calc = api.post(f"{V1}/financas/calculadora", json={**api.get(f"{V1}/financas/premissas", headers=como("helena")).json()["valores"],
                    **cons["processos"][0]["calculadora"]}, headers=como("helena"))
    assert calc.status_code == 200 and calc.json()["roi"] is not None
    res = api.get(f"{V1}/perguntas", params={"persona": "helena"}, headers=como("helena")).json()
    assert 3 <= len(res["perguntas"]) <= 5
    assert [p.id for p in ROTEIROS["helena"].passos][-2:] == ["medir", "perguntas"]


# ---------------------------------------------------------------- estrutura
@pytest.mark.parametrize("rid", list(ROTEIROS))
def test_estrutura_dos_roteiros(api, rid):
    r = ROTEIROS[rid]
    assert r.passos[0].id == "contexto"
    # só o roteiro da Helena mostra as Perguntas da Ferramenta; os demais terminam no cartão AS IS × TO BE
    assert r.passos[-1].id == ("perguntas" if rid == "helena" else "medir")
    assert "medir" in [p.id for p in r.passos] and "banca" not in [p.id for p in r.passos]
    assert len({p.id for p in r.passos}) == len(r.passos)
    perguntas = [q for q in PERGUNTAS if q["persona"] == rid]
    assert 3 <= len(perguntas) <= 5
    d = api.get(f"{V1}/roteiros/{rid}", headers=como(r.persona)).json()
    assert d["persona_dados"]["id"] == r.persona


def test_reiniciar_roteiro_devolve_o_estado_inicial(api):
    def foto():
        return sorted(a["nome"] for a in api.get(f"{V1}/agentes", headers=como("helena")).json())
    _iniciar(api, "marina")
    inicial = foto()
    bp, _ = _criar(api, "marina", "marina", "duvida_lojista")
    aid = _salvar(api, "marina", bp)
    _publicar(api, "marina", aid)
    assert foto() != inicial
    _iniciar(api, "marina")
    assert foto() == inicial and not fx.CHAMADOS


def test_campos_pedem_nome_e_nao_codigo(api):
    ex = api.get(f"{V1}/agentes-exemplo", headers=como("marina")).json()
    for bp in ex.values():
        for c in bp["campos"]:
            assert c["rotulo"] and not c["rotulo"].endswith("_id")
    achados = api.get(f"{V1}/lojistas", params={"q": "relampago"}, headers=como("marina")).json()
    assert [l["id"] for l in achados] == ["L1003"] and achados[0]["nome"] == "Eletrônicos Relâmpago"
    eu = api.get(f"{V1}/colaboradores", headers=como("marina")).json()
    assert eu["itens"][0]["eu"] is True and eu["itens"][0]["id"] == "C601" and not eu["pode_buscar_outros"]
    rh = api.get(f"{V1}/colaboradores", params={"q": "bruno"}, headers=como("carla")).json()
    assert rh["pode_buscar_outros"] and rh["itens"][0]["eu"] and any(c["nome"] == "Bruno Tavares" for c in rh["itens"])


def test_formato_antigo_de_campos_continua_valido():
    from app.agents.blueprint import Blueprint
    bp = Blueprint.model_validate({
        "nome": "Agente antigo", "objetivo": "Versão gravada antes dos campos rotulados.", "area": "atendimento",
        "campos_entrada": ["lojista_id", "pergunta"],
        "passos": [{"id": "politica", "titulo": "Buscar", "tipo": "ferramenta", "ferramenta": "buscar_politica",
                    "entrada": {"area": "atendimento", "consulta": "{{entrada.pergunta}}"}}]})
    assert [(c.id, c.tipo) for c in bp.campos] == [("lojista_id", "lojista"), ("pergunta", "texto_longo")]
    assert bp.campos[0].rotulo == "Lojista" and "campos_entrada" not in bp.model_dump()


# ---------------------------------------------------------------- extensão copiloto
def test_extensao_sugere_o_agente_e_preenche_os_campos(api):
    _iniciar(api, "helena")   # estado completo: 3 agentes publicados
    trecho = ("Atenção, time de risco: o lojista Eletrônicos Relâmpago (L1003) recebeu um volume incomum de contestações "
              "nos últimos dias. Peço uma análise de chargebacks.")
    r = api.post(f"{V1}/extensao/analisar", json={"trecho": trecho}, headers=como("rafael")).json()
    assert r["lojista"]["id"] == "L1003"
    melhor = r["agentes"][0]
    assert melhor["nome"] == "Triagem de chargebacks" and r["sugerido"] == melhor["id"]
    assert melhor["preenchido"] == {"lojista_id": "L1003"} and "Lojista: Eletrônicos Relâmpago" in melhor["detectado"]

    duvida = ("Oi! Em quanto tempo o estorno cai para o cliente? Equipe da Padaria Pão Dourado.")
    r = api.post(f"{V1}/extensao/analisar", json={"trecho": duvida}, headers=como("marina")).json()
    a = r["agentes"][0]
    assert a["nome"] == "Resposta a dúvidas de lojistas" and a["preenchido"]["lojista_id"] == "L1001"
    assert a["preenchido"]["pergunta"] == duvida
    assert api.post(f"{V1}/extensao/analisar", json={"trecho": ""}, headers=como("marina")).json()["sugerido"] is None


def test_helpdesk_de_demonstracao_e_servido(api):
    r = api.get("/demo/helpdesk")
    assert r.status_code == 200 and "HelpDesk Fictício" in r.text and "4816" in r.text


def test_resultado_de_todos_os_roteiros_responde(api):
    """Lucas e Helena não têm tarefa para comparar: o resultado traz indicadores medidos, nunca erro."""
    _iniciar(api, "lucas")
    for rid in ROTEIROS:
        r = api.get(f"{V1}/roteiros/{rid}/resultado", headers=como("helena"))
        assert r.status_code == 200, (rid, r.text)
        d = r.json()
        assert d["linhas"] or d["indicadores"]
    ind = {i["nome"]: i for i in api.get(f"{V1}/roteiros/lucas/resultado", headers=como("lucas")).json()["indicadores"]}
    assert ind["Agentes publicados sem código novo"]["valor"] == 3
    assert ind["Revisões de segurança feitas"]["valor"] == 1


# ---------------------------------------------------------------- correções da revisão de código
def test_reiniciar_fora_do_modo_demo_so_o_coe(api, monkeypatch):
    from app.core import config
    monkeypatch.setattr(config, "MODO_DEMO", False)
    assert api.post(f"{V1}/roteiros/marina/reiniciar", headers=como("marina")).status_code == 403
    assert api.post(f"{V1}/roteiros/marina/reiniciar", headers=como("helena")).status_code == 200


def test_resultado_nao_vaza_agente_de_outra_area(api):
    _iniciar(api, "helena")
    triagem = next(a for a in api.get(f"{V1}/agentes", headers=como("helena")).json() if a["nome"] == "Triagem de chargebacks")
    r = api.get(f"{V1}/roteiros/marina/resultado", params={"agente_id": triagem["id"]}, headers=como("marina"))
    assert r.status_code == 403
    assert api.get(f"{V1}/roteiros/rafael/resultado", params={"agente_id": triagem["id"]}, headers=como("rafael")).status_code == 200


def test_erros_diz_o_tamanho_da_amostra(api):
    _iniciar(api, "marina")
    bp, _ = _criar(api, "marina", "marina", "duvida_lojista")
    aid = _salvar(api, "marina", bp)
    _publicar(api, "marina", aid)
    _executar(api, "marina", aid, _passo("marina", "usar").preenche["entrada"])
    linha = next(l for l in _fim(api, "marina", aid)["linhas"] if l["criterio"].startswith("Erros"))
    assert linha["to_be"] == 0.0 and "1 execução" in linha["origem_to_be"] and "amostra pequena" in linha["origem_to_be"]
    assert linha["origem_as_is"].startswith("premissa")


def test_analise_de_risco_so_afirma_o_que_os_dados_mostram(sessao):
    from app.runtime import motor
    from app.seed.agentes_exemplo import TRIAGEM_CHARGEBACK
    from app.core.identidade import PERSONAS
    exe, _ = motor.executar(sessao, PERSONAS["rafael"], TRIAGEM_CHARGEBACK, {"lojista_id": "L1003"})
    analise = exe.passos["analise"]["saida"]
    assert "10 contestações" in analise and "R$ 210.000" in analise
    assert "acima do perfil" not in analise      # não inventa comparação que os dados não trazem


def _cliente_que_falha(fatal: bool):
    from app.llm.cliente import ErroModelo

    class Falha:
        def gerar(self, *a, **k):
            raise ErroModelo("API fora do ar", fatal=fatal)
    return Falha()


def test_reserva_do_modo_real_e_visivel_e_nao_mascara_erro_de_chave(sessao, monkeypatch):
    from app.core.identidade import PERSONAS
    from app.runtime import motor
    from app.seed.agentes_exemplo import DUVIDA_LOJISTA
    entrada = {"lojista_id": "L1001", "pergunta": "Em quanto tempo o estorno cai para o cliente?"}
    bp = DUVIDA_LOJISTA.model_copy(update={"area": "atendimento"})

    monkeypatch.setattr(motor, "obter_cliente", lambda simulado=None: _cliente_que_falha(False) if not simulado else __import__("app.llm.cliente", fromlist=["simulador"]).simulador())
    exe, _ = motor.executar(sessao, PERSONAS["marina"], bp, entrada)
    r = exe.passos["resposta"]
    assert exe.status == "concluida" and r["reserva"] and "reserva" in r["reserva"].lower()   # visível, não silenciosa

    monkeypatch.setattr(motor, "obter_cliente", lambda simulado=None: _cliente_que_falha(True))
    exe, _ = motor.executar(sessao, PERSONAS["marina"], bp, entrada)
    assert exe.status == "escalada" and "reserva" not in exe.passos["resposta"]   # chave errada escala, não finge


def test_extensao_nao_sugere_sem_assunto_em_comum(api):
    _iniciar(api, "helena")
    r = api.post(f"{V1}/extensao/analisar", json={"trecho": "Qual o melhor time de futebol do estado?"}, headers=como("marina")).json()
    assert r["sugerido"] is None and r["lojista"] is None


def test_texto_selecionado_nao_vai_na_url():
    from pathlib import Path
    raiz = Path(__file__).resolve().parents[2]
    for arquivo in ("extensao/painel.js", "backend/app/static/helpdesk.html"):
        assert "trecho=" not in (raiz / arquivo).read_text(encoding="utf-8") and "set('trecho'" not in (raiz / arquivo).read_text(encoding="utf-8")


def test_so_o_rh_busca_outros_colaboradores(api):
    assert api.get(f"{V1}/colaboradores", params={"q": "bruno"}, headers=como("helena")).json()["itens"][0]["eu"] is True
    assert len(api.get(f"{V1}/colaboradores", params={"q": "bruno"}, headers=como("helena")).json()["itens"]) == 1
