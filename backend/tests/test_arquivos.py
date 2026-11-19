"""v8/10: Arquivos e Planilhas, o plugin que funciona de verdade (CSV e XLSX, offline)."""
import base64
import io

import pytest
from openpyxl import Workbook, load_workbook
from sqlmodel import select

from app.audit.trilha import EventoAuditoria
from app.plugins import arquivos
from app.plugins.catalogo import PLUGINS
from app.seed.demo import semear
from tests.conftest import como

V1 = "/api/v1"
BASE = f"{V1}/plugins/arquivos"


def _b64(b: bytes) -> str:
    return base64.b64encode(b).decode()


def _csv(texto: str) -> bytes:
    return texto.encode("utf-8")


def _xlsx(linhas: list[list]) -> bytes:
    wb = Workbook()
    ws = wb.active
    for l in linhas:
        ws.append(l)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _integrar(api, perfil="thiago"):
    r = api.post(f"{V1}/plugins/arquivos/integrar", headers=como(perfil))
    assert r.status_code == 200 and r.json()["resultado"] == "integrado", r.text


def _enviar(api, perfil, nome, conteudo, classificacao="interna", areas=()):
    return api.post(f"{BASE}/arquivos", json={"nome": nome, "conteudo_base64": _b64(conteudo), "classificacao": classificacao,
                                              "areas": list(areas)}, headers=como(perfil))


def _ferramenta(api, perfil, fid, entrada, confirmar=False):
    r = api.post(f"{V1}/ferramentas/{fid}/testar", json={"entrada": entrada, "confirmar": confirmar}, headers=como(perfil))
    assert r.status_code == 200, r.text
    return r.json()


CLIENTES = "codigo;nome;cpf;email;status\n1;Ana Souza;123.456.789-09;ana@exemplo.com;pendente\n2;Bruno Lima;987.654.321-00;bruno@exemplo.com;pendente\n"


# ---------------------------------------------------------------- vitrine
def test_aparece_no_marketplace_para_todas_as_areas_com_o_selo_real(api):
    for perfil in ("marina", "rafael", "carla", "thiago", "lucas", "helena"):
        p = next(x for x in api.get(f"{V1}/plugins", headers=como(perfil)).json() if x["id"] == "arquivos")
        assert p["real"] is True and p["simulado"] is False and p["vale_para_minha_area"] and p["estado"] == "disponivel"
        assert {f["id"] for f in p["ferramentas"]} == {"arquivos_listar", "arquivos_ler_linhas", "arquivos_buscar_linha",
                                                       "arquivos_adicionar_linha", "arquivos_atualizar_linha"}
    assert PLUGINS["arquivos"].real and not PLUGINS["zendesk"].real
    assert api.get(f"{BASE}/arquivos", headers=como("marina")).status_code == 409        # só depois de integrar


# ---------------------------------------------------------------- enviar CSV e XLSX
def test_envia_csv_e_xlsx_e_mostra_a_previa(api):
    _integrar(api)
    r = _enviar(api, "thiago", "pedidos.csv", _csv("modelo;qtd\nPro;3\nMini;5\n"), areas=["logistica"])
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["formato"] == "csv" and d["colunas"] == ["modelo", "qtd"] and d["total_linhas"] == 2 and d["previa"][0] == {"modelo": "Pro", "qtd": "3"} or d["previa"][0]["modelo"] == "Pro"
    x = _enviar(api, "thiago", "estoque.xlsx", _xlsx([["modelo", "disponivel"], ["Pro", 42], ["Mini", 7.5], [None, None]]))
    assert x.status_code == 200, x.text
    dx = x.json()
    assert dx["formato"] == "xlsx" and dx["colunas"] == ["modelo", "disponivel"] and dx["total_linhas"] == 2     # linha vazia é ignorada
    assert dx["previa"][0]["disponivel"] == 42
    lim = api.get(f"{BASE}/arquivos/limites", headers=como("thiago")).json()
    assert lim["bytes"] == 2_000_000 and lim["linhas"] == 5000 and lim["colunas"] == 30 and lim["formatos"] == ["csv", "xlsx"]


@pytest.mark.parametrize("nome,conteudo,trecho", [
    ("vazio.csv", b"", "vazio"),
    ("foto.png", b"abc", "CSV ou XLSX"),
    ("sem-nome.csv", b",,\n1,2,3\n", "nome de cada coluna"),
    ("repetida.csv", b"a,a\n1,2\n", "mesmo nome"),
    ("quebrada.xlsx", b"isto nao e uma planilha", "Não consegui abrir"),
    ("grande.csv", b"a\n" + b"x" * 2_100_000, "máximo"),
])
def test_arquivo_invalido_recebe_mensagem_em_portugues(api, nome, conteudo, trecho):
    _integrar(api)
    r = _enviar(api, "thiago", nome, conteudo)
    assert r.status_code in (403, 422) and trecho in r.json()["detail"]


def test_limites_de_linhas_e_colunas(api):
    _integrar(api)
    linhas = "n\n" + "\n".join(str(i) for i in range(arquivos.MAX_LINHAS + 1))
    assert "linhas" in _enviar(api, "thiago", "longo.csv", _csv(linhas)).json()["detail"]
    colunas = ",".join("c%d" % i for i in range(arquivos.MAX_COLUNAS + 1)) + "\n1\n"
    assert "colunas" in _enviar(api, "thiago", "largo.csv", _csv(colunas)).json()["detail"]
    assert _enviar(api, "thiago", "ok.csv", _csv("a\n1\n")).status_code == 200
    assert _enviar(api, "thiago", "OK.csv", _csv("a\n1\n")).status_code == 409           # mesmo nome


# ---------------------------------------------------------------- classificação e permissão
def test_classificacao_nao_passa_do_nivel_de_quem_envia(api):
    _integrar(api)
    r = _enviar(api, "thiago", "segredo.csv", _csv("a\n1\n"), classificacao="confidencial")     # Thiago tem nível interno
    assert r.status_code == 403 and "nível de acesso" in r.json()["detail"]
    assert _enviar(api, "carla", "beneficios.csv", _csv("a\n1\n"), classificacao="confidencial", areas=["pessoas"]).status_code == 200
    assert _enviar(api, "rafael", "lista.csv", _csv("a\n1\n"), classificacao="restrita", areas=["risco"]).status_code == 200
    assert api.get(f"{BASE}/arquivos/limites", headers=como("thiago")).json()["classificacoes"] == ["publica", "interna"]


def test_so_le_quem_tem_a_area_e_o_nivel(api):
    _integrar(api)
    rid = _enviar(api, "rafael", "lista-risco.csv", _csv("lojista;valor\nL1003;100\n"), classificacao="restrita", areas=["risco"]).json()["id"]
    cid = _enviar(api, "carla", "beneficios.csv", _csv("colaborador;beneficio\nC501;VR\n"), classificacao="confidencial", areas=["pessoas"]).json()["id"]
    uid = _enviar(api, "thiago", "geral.csv", _csv("a\n1\n"), areas=["*"]).json()["id"]
    visiveis = lambda p: {a["nome"] for a in api.get(f"{BASE}/arquivos", headers=como(p)).json()}   # noqa: E731
    assert visiveis("rafael") == {"lista-risco.csv", "geral.csv"}
    assert visiveis("carla") == {"beneficios.csv", "geral.csv"}
    assert visiveis("marina") == {"geral.csv"}                     # outra área
    assert visiveis("lucas") == {"geral.csv"}                      # nível confidencial, mas a área não está na lista
    for perfil, aid in (("marina", rid), ("thiago", cid), ("lucas", rid)):
        assert api.get(f"{BASE}/arquivos/{aid}", headers=como(perfil)).status_code == 403
        assert api.get(f"{BASE}/arquivos/{aid}/download", headers=como(perfil)).status_code == 403
    assert api.get(f"{BASE}/arquivos/{uid}", headers=como("marina")).status_code == 200


def test_nivel_insuficiente_mesmo_com_a_area_certa(api, sessao):
    _integrar(api)
    a = arquivos.criar_pelo_sistema(sessao, __import__("app.core.identidade", fromlist=["x"]).PERSONAS["rafael"], "alto.csv",
                                    ["a"], [{"a": "1"}], 3, ["logistica", "risco"])
    assert api.get(f"{BASE}/arquivos/{a.id}", headers=como("thiago")).status_code == 403   # área sim, nível interno não
    assert api.get(f"{BASE}/arquivos/{a.id}", headers=como("rafael")).status_code == 200


# ---------------------------------------------------------------- ferramentas
def test_ferramentas_listam_leem_filtram_e_acham(api):
    _integrar(api)
    _enviar(api, "thiago", "pedidos.csv", _csv("codigo,modelo,status\nP1,Pro,pendente\nP2,Mini,tratado\nP3,Pro,pendente\n"), areas=["logistica"])
    lista = _ferramenta(api, "thiago", "arquivos_listar", {})
    assert lista["ok"] and [a["nome"] for a in lista["saida"]["arquivos"]] == ["pedidos.csv"]
    todas = _ferramenta(api, "thiago", "arquivos_ler_linhas", {"arquivo": "pedidos.csv"})["saida"]
    assert todas["total_linhas"] == 3 and todas["linhas_encontradas"] == 3 and todas["linhas"][0]["linha"] == 1
    pend = _ferramenta(api, "thiago", "arquivos_ler_linhas", {"arquivo": "pedidos.csv", "coluna": "status", "valor": "PENDENTE"})["saida"]
    assert [l["codigo"] for l in pend["linhas"]] == ["P1", "P3"]
    achada = _ferramenta(api, "thiago", "arquivos_buscar_linha", {"arquivo": "pedidos.csv", "coluna": "codigo", "valor": "p2"})["saida"]
    assert achada["encontrada"] and achada["linha"]["modelo"] == "Mini" and achada["linha"]["linha"] == 2
    assert not _ferramenta(api, "thiago", "arquivos_buscar_linha", {"arquivo": "pedidos.csv", "coluna": "codigo", "valor": "P9"})["saida"]["encontrada"]
    erro = _ferramenta(api, "thiago", "arquivos_ler_linhas", {"arquivo": "pedidos.csv", "coluna": "nada", "valor": "x"})
    assert not erro["ok"] and "não tem a coluna" in erro["erro"]


def test_leitura_mascara_dado_pessoal_antes_do_modelo(api):
    _integrar(api, "carla")
    _enviar(api, "carla", "clientes.csv", _csv(CLIENTES), classificacao="confidencial", areas=["pessoas"])
    r = _ferramenta(api, "carla", "arquivos_ler_linhas", {"arquivo": "clientes.csv"})
    assert r["ok"]
    visto_pelo_modelo = r["enviado_ao_modelo"]
    assert "123.456.789-09" not in visto_pelo_modelo and "ana@exemplo.com" not in visto_pelo_modelo       # o modelo só vê marcadores
    assert r["mascarados"] and "Ana Souza" in visto_pelo_modelo
    assert "123.456.789-09" in str(r["saida"])                         # quem disparou vê o real na tela dela


def test_ler_arquivo_de_outra_area_e_negado_e_auditado(api, sessao):
    _integrar(api)
    _enviar(api, "rafael", "lista-risco.csv", _csv("lojista;valor\nL1003;100\n"), classificacao="restrita", areas=["risco"])
    r = _ferramenta(api, "marina", "arquivos_ler_linhas", {"arquivo": "lista-risco.csv"})
    assert not r["ok"] and r["tipo_erro"] == "negado"
    assert "L1003" not in str(r)
    negadas = [e for e in sessao.exec(select(EventoAuditoria)).all() if e.tipo == "ferramenta_negada" and e.ator == "marina"]
    assert negadas and negadas[-1].dados["conector"] == "arquivos_ler_linhas"
    assert "lista-risco.csv" not in _ferramenta(api, "marina", "arquivos_listar", {})["enviado_ao_modelo"]


def test_adicionar_e_atualizar_linha_entram_na_auditoria(api, sessao):
    _integrar(api)
    aid = _enviar(api, "thiago", "pedidos.csv", _csv("codigo,modelo,status\nP1,Pro,pendente\nP2,Mini,pendente\n"), areas=["logistica"]).json()["id"]
    novo = _ferramenta(api, "thiago", "arquivos_adicionar_linha", {"arquivo": "pedidos.csv", "valores": '{"codigo": "P3", "modelo": "Smart"}'})
    assert novo["ok"] and novo["saida"]["linha"] == 3
    upd = _ferramenta(api, "thiago", "arquivos_atualizar_linha", {"arquivo": "pedidos.csv", "coluna_chave": "codigo", "valor_chave": "P2",
                                                                  "valores": '{"status": "tratado"}'})
    assert upd["ok"] and upd["saida"]["linha"] == 2 and upd["saida"]["colunas_alteradas"] == ["status"]
    a = api.get(f"{BASE}/arquivos/{aid}", headers=como("thiago")).json()
    assert a["total_linhas"] == 3 and a["versao"] == 3 and a["previa"][1]["status"] == "tratado" and a["previa"][2]["status"] == ""
    eventos = {e.tipo: e for e in sessao.exec(select(EventoAuditoria)).all() if e.tipo.startswith("arquivo_linha_")}
    assert eventos["arquivo_linha_adicionada"].ator == "thiago" and eventos["arquivo_linha_adicionada"].dados["linha"] == 3
    assert eventos["arquivo_linha_atualizada"].dados["linha"] == 2 and eventos["arquivo_linha_atualizada"].dados["arquivo"] == aid
    assert api.get(f"{V1}/auditoria/verificar", headers=como("helena")).json()["integra"] is True
    # erros claros
    assert _ferramenta(api, "thiago", "arquivos_adicionar_linha", {"arquivo": "pedidos.csv", "valores": '{"codigo": "P4", "modelo": "Smart"}'})["ok"]
    dupla = _ferramenta(api, "thiago", "arquivos_adicionar_linha", {"arquivo": "pedidos.csv", "valores": '{"codigo": "P5", "modelo": "Smart"}'})
    dupla = _ferramenta(api, "thiago", "arquivos_atualizar_linha", {"arquivo": "pedidos.csv", "coluna_chave": "modelo", "valor_chave": "Smart",
                                                                   "valores": '{"status": "y"}'})
    assert not dupla["ok"] and "linhas com modelo" in dupla["erro"]
    assert not _ferramenta(api, "thiago", "arquivos_adicionar_linha", {"arquivo": "pedidos.csv", "valores": "isto nao e json"})["ok"]
    assert not _ferramenta(api, "thiago", "arquivos_adicionar_linha", {"arquivo": "pedidos.csv", "valores": '{"coluna_inexistente": 1}'})["ok"]


def test_escrita_em_arquivo_confidencial_espera_a_confirmacao(api, sessao):
    _integrar(api, "carla")
    aid = _enviar(api, "carla", "beneficios.csv", _csv("colaborador;beneficio\nC501;VR\n"), classificacao="confidencial", areas=["pessoas"]).json()["id"]
    pedido = {"arquivo": "beneficios.csv", "valores": '{"colaborador": "C502", "beneficio": "VA"}'}
    r = _ferramenta(api, "carla", "arquivos_adicionar_linha", pedido)
    assert not r["ok"] and r["aguardando_aprovacao"]
    assert api.get(f"{BASE}/arquivos/{aid}", headers=como("carla")).json()["total_linhas"] == 1      # nada gravou sozinho
    ok = _ferramenta(api, "carla", "arquivos_adicionar_linha", pedido, confirmar=True)
    assert ok["ok"] and api.get(f"{BASE}/arquivos/{aid}", headers=como("carla")).json()["total_linhas"] == 2
    # arquivo interno: grava direto
    _enviar(api, "carla", "avisos.csv", _csv("aviso\nolá\n"), classificacao="interna", areas=["pessoas"])
    assert _ferramenta(api, "carla", "arquivos_adicionar_linha", {"arquivo": "avisos.csv", "valores": '{"aviso": "novo"}'})["ok"]


def test_plugin_nao_integrado_nao_deixa_usar_as_ferramentas(api):
    r = api.post(f"{V1}/ferramentas/arquivos_listar/testar", json={"entrada": {}}, headers=como("thiago"))
    assert r.status_code == 404                          # a ferramenta de um plugin não integrado nem aparece no catálogo
    from sqlmodel import Session

    from app.core import db
    from app.core.identidade import PERSONAS
    from app.tools import executor
    with Session(db.motor()) as s:
        res = executor.executar(s, PERSONAS["thiago"], "arquivos_listar", {})
    assert not res.ok and res.tipo_erro == "negado" and "plugin" in res.erro


# ---------------------------------------------------------------- baixar e remover
def test_baixa_a_versao_atual_em_csv_e_xlsx(api):
    _integrar(api)
    _enviar(api, "thiago", "pedidos.csv", _csv("codigo,status\nP1,pendente\n"), areas=["logistica"])
    aid_x = _enviar(api, "thiago", "estoque.xlsx", _xlsx([["modelo", "qtd"], ["Pro", 3]]), areas=["logistica"]).json()["id"]
    _ferramenta(api, "thiago", "arquivos_adicionar_linha", {"arquivo": "pedidos.csv", "valores": '{"codigo": "P2", "status": "novo"}'})
    _ferramenta(api, "thiago", "arquivos_adicionar_linha", {"arquivo": "estoque.xlsx", "valores": '{"modelo": "=1+1", "qtd": "9"}'})
    csv_id = next(a["id"] for a in api.get(f"{BASE}/arquivos", headers=como("thiago")).json() if a["nome"] == "pedidos.csv")
    r = api.get(f"{BASE}/arquivos/{csv_id}/download", headers=como("thiago"))
    assert r.status_code == 200 and "pedidos.csv" in r.headers["content-disposition"]
    assert r.content.decode("utf-8-sig").splitlines() == ["codigo,status", "P1,pendente", "P2,novo"]
    rx = api.get(f"{BASE}/arquivos/{aid_x}/download", headers=como("thiago"))
    ws = load_workbook(io.BytesIO(rx.content)).active
    linhas = [[c.value for c in row] for row in ws.iter_rows()]
    assert linhas[0] == ["modelo", "qtd"] and linhas[1] == ["Pro", 3] and linhas[2][0] == "'=1+1"       # fórmula não executa ao abrir


def test_baixar_arquivo_com_nome_fora_do_latin1_nao_quebra_o_cabecalho(api):
    _integrar(api)
    aid = _enviar(api, "thiago", "relatório – maio.csv", _csv("a\n1\n"), areas=["logistica"]).json()["id"]
    r = api.get(f"{BASE}/arquivos/{aid}/download", headers=como("thiago"))
    assert r.status_code == 200
    assert "filename*=UTF-8''relat%C3%B3rio%20%E2%80%93%20maio.csv" in r.headers["content-disposition"]


def test_so_quem_enviou_remove(api):
    _integrar(api)
    aid = _enviar(api, "thiago", "geral.csv", _csv("a\n1\n"), areas=["*"]).json()["id"]
    assert api.delete(f"{BASE}/arquivos/{aid}", headers=como("marina")).status_code == 403
    assert api.delete(f"{BASE}/arquivos/{aid}", headers=como("thiago")).status_code == 200
    assert api.get(f"{BASE}/arquivos/{aid}", headers=como("thiago")).status_code == 404


# ---------------------------------------------------------------- reiniciar a demo
def test_reiniciar_a_demo_restaura_os_arquivos_do_estado_inicial(api, sessao):
    semear(sessao)
    assert [a["nome"] for a in api.get(f"{BASE}/arquivos", headers=como("marina")).json()] == ["faq-atendimento.csv", "pedidos-troca.csv"]
    _enviar(api, "marina", "extra.csv", _csv("a\n1\n"))
    _ferramenta(api, "marina", "arquivos_adicionar_linha", {"arquivo": "faq-atendimento.csv", "valores": '{"assunto": "Novo"}'})
    assert api.post(f"{V1}/demo/reiniciar", headers=como("helena")).status_code == 200
    depois = api.get(f"{BASE}/arquivos", headers=como("marina")).json()
    assert [a["nome"] for a in depois] == ["faq-atendimento.csv", "pedidos-troca.csv"] and depois[0]["total_linhas"] == 8 and depois[0]["demo"] is True
    assert api.get(f"{V1}/plugins/arquivos", headers=como("marina")).json()["estado"] == "integrado"


def test_a_pagina_do_plugin_traz_os_numeros_de_uso_e_saude(api):
    _integrar(api)
    _enviar(api, "thiago", "pedidos.csv", _csv("a\n1\n"), areas=["logistica"])
    _ferramenta(api, "thiago", "arquivos_listar", {})
    c = api.get(f"{V1}/plugins/arquivos/consolidado", headers=como("thiago")).json()
    assert c["simulado"] is False and c["plugin"]["real"] is True and c["numeros"]["chamadas_mes"] >= 1
    assert c["saude"]["status"] == "ok" and {f["id"] for f in c["saude"]["por_ferramenta"]} >= {"arquivos_listar"}
