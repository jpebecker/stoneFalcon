"""v8/11: um uso real do plugin Arquivos e Planilhas para cada uma das seis personas (arquivos e processos do estado inicial)."""
import pytest
from sqlmodel import select

from app.audit.trilha import EventoAuditoria
from app.seed.demo import semear
from tests.conftest import como

V1 = "/api/v1"
ARQ = f"{V1}/plugins/arquivos/arquivos"


@pytest.fixture()
def demo(sessao):
    semear(sessao)


def _processo(api, perfil, nome):
    return next(p for p in api.get(f"{V1}/processos", headers=como(perfil)).json() if p["nome"] == nome)


def _rodar(api, perfil, nome, entrada):
    p = _processo(api, perfil, nome)
    r = api.post(f"{V1}/processos/{p['id']}/executar", json={"entrada": entrada}, headers=como(perfil))
    assert r.status_code == 200, r.text
    return r.json()


def _arquivo(api, perfil, nome):
    return next(a for a in api.get(ARQ, headers=como(perfil)).json() if a["nome"] == nome)


def test_seis_arquivos_semeados_com_classificacao_e_areas_certas(api, demo):
    todos = {}
    for perfil in ("marina", "rafael", "carla", "thiago", "lucas", "helena"):
        for a in api.get(ARQ, headers=como(perfil)).json():
            todos[a["nome"]] = a
    assert {n: (a["classificacao"], sorted(a["areas"])) for n, a in todos.items()} == {
        "faq-atendimento.csv": ("interna", ["atendimento", "logistica"]),
        "chargebacks-triagem.csv": ("restrita", ["risco"]),
        "beneficios-rh.csv": ("confidencial", ["pessoas"]),
        "pedidos-troca.csv": ("interna", ["atendimento", "logistica"]),
        "registro-incidentes.csv": ("interna", ["engenharia", "logistica"]),
        "financas-resumo-inicial.csv": ("interna", ["gestao"]),
    }
    assert all(a["demo"] for a in todos.values())


def test_marina_le_o_faq_para_responder(api, demo):
    exe = _rodar(api, "marina", "Consulta ao FAQ de atendimento", {"assunto": "Estorno"})
    assert exe["status"] == "concluida"
    saida = exe["passos"]["faq"]["saida"]
    assert saida["linhas_encontradas"] == 2 and "estorno" in str(saida).lower()


def test_rafael_le_a_lista_e_registra_a_decisao_com_confirmacao(api, demo, sessao):
    entrada = {"lojista_id": "L1003", "lojista": "Eletrônicos Relâmpago", "decisao": "reter repasse"}
    exe = _rodar(api, "rafael", "Registro da decisão de triagem", entrada)
    assert exe["status"] == "aguardando_aprovacao"                       # arquivo restrito: um humano confirma antes de gravar
    assert exe["passos"]["lista"]["saida"]["linha"]["decisao"] == "pendente"
    assert _arquivo(api, "rafael", "chargebacks-triagem.csv")["total_linhas"] == 3
    d = api.post(f"{V1}/execucoes/{exe['id']}/decisao", json={"aprovar": True}, headers=como("rafael"))
    assert d.status_code == 200 and d.json()["status"] == "concluida"
    a = api.get(f"{ARQ}/{_arquivo(api, 'rafael', 'chargebacks-triagem.csv')['id']}", headers=como("rafael")).json()
    assert a["total_linhas"] == 4 and a["previa"][-1]["decisao"] == "reter repasse" and a["previa"][-1]["lojista_id"] == "L1003"
    ev = [e for e in sessao.exec(select(EventoAuditoria)).all() if e.tipo == "arquivo_linha_adicionada"]
    assert ev and ev[-1].ator == "rafael" and ev[-1].dono_tipo == "processo" and ev[-1].dados["linha"] == 4


def test_carla_le_beneficios_confidenciais_com_dado_pessoal_mascarado(api, demo):
    exe = _rodar(api, "carla", "Consulta de benefícios do colaborador", {"colaborador_id": "C501"})
    assert exe["status"] == "concluida" and exe["passos"]["beneficios"]["saida"]["linhas_encontradas"] == 2
    bruto = str(exe["passos"]["beneficios"])
    assert "529.982.247-25" not in bruto and "bruno.tavares@exemplo.com.br" not in bruto       # o que o modelo e o log veem
    assert "Plano de saúde" in bruto


def test_thiago_le_os_pendentes_e_marca_o_pedido_tratado(api, demo):
    exe = _rodar(api, "thiago", "Pedidos de troca pendentes", {"codigo": "P-102"})
    assert exe["status"] == "concluida" and exe["passos"]["pendentes"]["saida"]["linhas_encontradas"] == 3
    a = api.get(f"{ARQ}/{_arquivo(api, 'thiago', 'pedidos-troca.csv')['id']}", headers=como("thiago")).json()
    assert next(l for l in a["previa"] if l["codigo"] == "P-102")["status"] == "tratado"
    again = _rodar(api, "thiago", "Pedidos de troca pendentes", {"codigo": "P-999"})
    assert again["status"] in ("escalada", "falhou")                       # pedido que não existe não inventa linha


def test_lucas_ve_o_registro_de_incidentes_e_o_processo_de_sistema_fora_anota(api, demo):
    antes = _arquivo(api, "lucas", "registro-incidentes.csv")["total_linhas"]
    exe = _rodar(api, "lucas", "Registro de incidente de sistema",
                 {"sistema": "Cadastro de lojistas", "descricao": "Consultas com tempo esgotado.", "severidade": "alta"})
    assert exe["status"] == "concluida"
    a = api.get(f"{ARQ}/{_arquivo(api, 'lucas', 'registro-incidentes.csv')['id']}", headers=como("lucas")).json()
    assert a["total_linhas"] == antes + 1 and a["previa"][-1]["sistema"] == "Cadastro de lojistas" and a["previa"][-1]["severidade"] == "alta"


def test_helena_exporta_as_financas_para_uma_planilha_que_ela_ve_e_baixa(api, demo):
    h = como("helena")
    assert api.post(f"{V1}/financas/exportar-planilha", headers=como("marina")).status_code == 403
    r = api.post(f"{V1}/financas/exportar-planilha", headers=h)
    assert r.status_code == 200, r.text
    nome = r.json()["arquivo"]["nome"]
    assert nome.startswith("financas-") and r.json()["linhas"] >= 9
    a = next(x for x in api.get(ARQ, headers=h).json() if x["nome"] == nome)
    assert a["classificacao"] == "interna" and a["areas"] == ["gestao"]
    down = api.get(f"{ARQ}/{a['id']}/download", headers=h)
    texto = down.content.decode("utf-8-sig")
    assert texto.splitlines()[0].startswith("tipo,nome,area,execucoes") and "Triagem de chargebacks" in texto
    assert api.get(f"{ARQ}/{a['id']}", headers=como("marina")).status_code == 403          # outra área não abre


def test_leitura_entre_areas_e_negada(api, demo, sessao):
    # Marina (Atendimento, nível interno) não lê a lista restrita de risco nem a tabela confidencial de RH
    for nome in ("chargebacks-triagem.csv", "beneficios-rh.csv"):
        r = api.post(f"{V1}/ferramentas/arquivos_ler_linhas/testar", json={"entrada": {"arquivo": nome}}, headers=como("marina")).json()
        assert not r["ok"] and r["tipo_erro"] == "negado", nome
    # Carla (nível confidencial) é da área certa para os benefícios, mas não para a lista de risco
    r = api.post(f"{V1}/ferramentas/arquivos_ler_linhas/testar", json={"entrada": {"arquivo": "chargebacks-triagem.csv"}}, headers=como("carla")).json()
    assert not r["ok"] and r["tipo_erro"] == "negado"
    negadas = [e for e in sessao.exec(select(EventoAuditoria)).all() if e.tipo == "ferramenta_negada" and e.dados["conector"] == "arquivos_ler_linhas"]
    assert {e.ator for e in negadas} == {"marina", "carla"}
