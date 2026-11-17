"""F8: gera entregaveis/analise-financeira.xlsx com fórmulas vivas.

Uso:  .venv/Scripts/python.exe gerar_excel.py   (depois: recalcular.py e testar_consistencia.py)

Regra: uma fonte única de premissas (aba Premissas, mesmos nomes de backend/app/finance/premissas.py).
Toda conta é fórmula do Excel; o Python só escreve a estrutura.
"""
from __future__ import annotations

from pathlib import Path

from openpyxl import Workbook
from openpyxl.chart import BarChart, LineChart, Reference
from openpyxl.chart.label import DataLabelList
from openpyxl.comments import Comment
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter as L
from openpyxl.workbook.defined_name import DefinedName
from openpyxl.worksheet.datavalidation import DataValidation

SAIDA = Path(__file__).resolve().parents[1] / "analise-financeira.xlsx"
DATA_CONF = "15/11/2026"

# ---------- identidade e estilos ----------
VERDE, VERDE_ESC, ROSA, TINTA, PAPEL = "128C5E", "0B6342", "D63384", "10201A", "F6F5F1"
F = "Arial"
f_txt = Font(name=F, size=10, color=TINTA)
f_neg = Font(name=F, size=10, bold=True, color=TINTA)
f_in = Font(name=F, size=10, color="0000FF")             # premissa editável
f_link = Font(name=F, size=10, color="008000")           # vem de outra aba
f_calc = Font(name=F, size=10, color="000000")           # fórmula
f_calc_b = Font(name=F, size=10, color="000000", bold=True)
f_tit = Font(name=F, size=16, bold=True, color=VERDE_ESC)
f_sub = Font(name=F, size=10, italic=True, color="46564F")
f_cab = Font(name=F, size=10, bold=True, color="FFFFFF")
f_sec = Font(name=F, size=11, bold=True, color=VERDE_ESC)
p_cab = PatternFill("solid", fgColor=VERDE)
p_sec = PatternFill("solid", fgColor="E2F3EB")
p_chave = PatternFill("solid", fgColor="FFFF00")
p_kpi = PatternFill("solid", fgColor="FBE7F2")
fino = Side(style="thin", color="E4E4DC")
borda = Border(bottom=fino)
quebra = Alignment(wrap_text=True, vertical="top")

BRL = '"R$" #,##0;("R$" #,##0);"-"'
BRL2 = '"R$" #,##0.00;("R$" #,##0.00);"-"'
BRL4 = '"R$" #,##0.0000;("R$" #,##0.0000);"-"'
USD4 = '"US$" #,##0.0000;("US$" #,##0.0000);"-"'
USD2 = '"US$" #,##0.00;("US$" #,##0.00);"-"'
EUR = '"€" #,##0;("€" #,##0);"-"'
PCT = '0.0%;(0.0%);"-"'
NUM = '#,##0;(#,##0);"-"'
NUM1 = '#,##0.0;(#,##0.0);"-"'
NUM2 = '#,##0.00;(#,##0.00);"-"'
MES = '"mês "0'

S_PREM, S_CAPEX, S_OPEX, S_TOK, S_BEN = "Premissas", "Investimento (CAPEX)", "Operação (OPEX)", "Tokens", "Benefícios"
S_FLUXO, S_CEN, S_SENS, S_CXC, S_RES, S_MOTOR = ("Fluxo de caixa", "Cenários", "Sensibilidade", "Construir × comprar",
                                                  "Resumo para slides", "Motor")


def q(s: str) -> str:
    return "'%s'" % s


wb = Workbook()
NOMES: dict[str, str] = {}


def nomear(nome: str, aba: str, ref: str) -> None:
    alvo = "%s!%s" % (q(aba), ref)
    NOMES[nome] = alvo
    wb.defined_names[nome] = DefinedName(nome, attr_text=alvo)


def cel(ws, ref, valor=None, fonte=f_txt, fmt=None, preench=None, alin=None):
    c = ws[ref]
    if valor is not None:
        c.value = valor
    c.font = fonte
    if fmt:
        c.number_format = fmt
    if preench:
        c.fill = preench
    if alin:
        c.alignment = alin
    return c


def titulo(ws, texto, sub=None):
    cel(ws, "A1", texto, f_tit)
    if sub:
        cel(ws, "A2", sub, f_sub)
    ws.sheet_view.showGridLines = False


def cabecalho(ws, linha, textos, col0=1):
    for i, t in enumerate(textos):
        c = ws.cell(row=linha, column=col0 + i, value=t)
        c.font, c.fill = f_cab, p_cab
        c.alignment = Alignment(wrap_text=True, vertical="center")


def secao(ws, linha, texto, ncols=8):
    for i in range(1, ncols + 1):
        ws.cell(row=linha, column=i).fill = p_sec
    c = ws.cell(row=linha, column=1, value=texto)
    c.font = f_sec


def larguras(ws, mapa):
    for col, w in mapa.items():
        ws.column_dimensions[col].width = w


def fechar_grafico(ch, eixos=True):
    ch.roundedCorners = False
    if ch.legend is not None:
        ch.legend.overlay = False
    if eixos:
        ch.x_axis.delete = False
        ch.y_axis.delete = False
    return ch


# =====================================================================
# 2. Premissas
# =====================================================================
wp = wb.active
wp.title = S_PREM
CENARIOS = ["Base", "Conservador", "Otimista", "Base medido"]
COLS = ["E", "F", "G", "H"]
LIN0 = 8
titulo(wp, "Premissas: a fonte única do modelo",
       "Azul = premissa editável · preto = fórmula · verde = vem de outra aba · fundo amarelo = o que muda no cenário. "
       "Nomes iguais aos de backend/app/finance/premissas.py.")
cel(wp, "A4", "Cenário em uso nas abas Fluxo de caixa, Tokens, OPEX e Benefícios:", f_neg)
cel(wp, "D4", "Base", Font(name=F, size=11, bold=True, color="0000FF"), preench=p_chave)
dv = DataValidation(type="list", formula1='"Base,Conservador,Otimista,Base medido"', allow_blank=False)
wp.add_data_validation(dv)
dv.add("D4")
nomear("cenario_ativo", S_PREM, "$D$4")
cel(wp, "A5", "Conferência das fontes: " + DATA_CONF + ". Revisar na véspera da apresentação (preços, câmbio, faixas).", f_sub)
cabecalho(wp, 7, ["Grupo", "Premissa", "Nome no código", "Em uso", *CENARIOS, "Unidade", "Status", "Fonte"])
larguras(wp, {"A": 14, "B": 46, "C": 26, "D": 13, "E": 13, "F": 13, "G": 13, "H": 13, "I": 12, "J": 22, "K": 60})
wp.freeze_panes = "C8"

LINHA: dict[str, int] = {}     # nome -> linha na aba Premissas
CEN_ROW: set[str] = set()
DOC = "docs/custos-estimados.txt (documento de custos da equipe)"
OFICIAL = "Tabela oficial da Anthropic (platform.claude.com/docs/en/about-claude/pricing), conferida em " + DATA_CONF
PROTO = "Protótipo v4: backend/app/agents/governanca.py (estimar_custo) e roteador"
DEMO = "Protótipo v4: histórico de 30 dias da demo (SINTÉTICO, gerado por app/seed/historico.py)"

# (nome, descrição, valor base | fórmula, overrides {col: valor}, unidade, fmt, status, fonte, nome_no_codigo, chave)
GRUPOS = [
    ("Investimento", [
        ("investimento_inicial", "Desenvolvimento + implantação, com contingência",
         "=%s!$D$14" % q(S_CAPEX), {}, "R$", BRL, "Documento da equipe", "Aba Investimento (CAPEX)", True, False),
        ("modulos_integracao", "Pacote de módulos de integração (conectores do catálogo)",
         "=%s!$E$24" % q(S_CAPEX), {}, "R$", BRL, "Documento da equipe", "Aba Investimento (CAPEX)", True, False),
        ("incluir_modulos", "Incluir os módulos de integração? (1 = sim, 0 = não)", 1, {}, "1/0", NUM, "Documento da equipe", DOC, True, False),
    ]),
    ("Operação", [
        ("hospedagem_mensal", "Hospedagem + domínio + n8n (teto da faixa R$ 2,8 a 6,9 mil)", 6900, {}, "R$/mês", BRL,
         "Documento da equipe", DOC + ". Estimativa de mercado; usamos o teto para não favorecer o resultado", True, False),
        ("sustentacao_mensal", "Time de sustentação", 16000, {}, "R$/mês", BRL, "Documento da equipe", DOC, True, False),
    ]),
    ("Uso", [
        ("usuarios", "Colaboradores com acesso", 6000, {}, "pessoas", NUM, "Documento da equipe", DOC + " (6.000 usuários)", True, False),
        ("adocao_alvo", "Fração que usa agentes ao fim da rampa", 0.25, {"F": 0.15, "G": 0.40}, "%", PCT,
         "Premissa a validar", "Premissa da equipe; o piloto mede. Decide o resultado (ver Sensibilidade)", True, True),
        ("meses_rampa", "Meses até atingir a adoção-alvo", 12, {"F": 18}, "meses", NUM, "Premissa a validar", "Premissa da equipe", True, True),
        ("tarefas_por_usuario_dia", "Execuções de agente por usuário ativo por dia útil", 1.0, {"G": 1.5}, "exec/dia", NUM1,
         "Premissa a validar", "Premissa da equipe", True, True),
        ("dias_uteis", "Dias úteis por mês", 22, {}, "dias", NUM, "Documento da equipe", DOC, True, False),
    ]),
    ("Valor", [
        ("minutos_por_tarefa", "Tempo da tarefa feita à mão (média)", 10, {"H": "=%s!$D$12" % q(S_BEN)}, "min", NUM1,
         "Premissa a validar", "Base: premissa da equipe. Base medido: média ponderada dos 3 agentes da demo (aba Benefícios)", True, True),
        ("minutos_revisao_humana", "Tempo que a pessoa ainda gasta conferindo o resultado", 2, {}, "min", NUM1,
         "Premissa a validar", "Premissa da equipe", True, False),
        ("custo_hora", "Custo da hora de trabalho (salário + encargos, média)", 45.0, {}, "R$/h", BRL2,
         "Premissa a validar", "Premissa da equipe", True, True),
        ("aproveitamento", "Fração do tempo liberado que vira ganho real", 0.5, {"F": 0.35}, "%", PCT,
         "Premissa a validar", "Premissa da equipe (metade do tempo liberado vira trabalho de valor)", True, True),
        ("custo_por_execucao", "Custo de tokens por execução de agente", 0.03, {"H": "=%s!$D$40" % q(S_TOK)}, "R$/exec", BRL4,
         "Premissa a validar", "Base: premissa conservadora da equipe. Base medido: modelo de agentes da aba Tokens", True, True),
    ]),
    ("Análise", [
        ("meses", "Horizonte da análise (até 60)", 36, {}, "meses", NUM, "Premissa da análise", "premissas.py", True, False),
        ("taxa_desconto_anual", "Taxa de desconto (custo de capital)", 0.12, {}, "% a.a.", PCT, "Premissa a validar",
         "premissas.py; validar com Finanças da Stone", True, False),
        ("taxa_erro_manual", "Retrabalho no processo manual", 0.08, {}, "%", PCT, "Premissa a validar",
         "premissas.py; usado só no indicador de erros (não entra no fluxo)", True, False),
    ]),
    ("Derivadas", [
        ("investimento_total", "Investimento total = inicial + módulos (se incluídos)",
         "={c}{investimento_inicial}+IF({c}{incluir_modulos}=1,{c}{modulos_integracao},0)", {}, "R$", BRL, "Fórmula", "calculadora.py", True, False),
        ("custo_fixo_mensal", "Custo fixo mensal = hospedagem + sustentação",
         "={c}{hospedagem_mensal}+{c}{sustentacao_mensal}", {}, "R$/mês", BRL, "Fórmula", "premissas.py", True, False),
        ("ganho_por_tarefa", "Ganho por tarefa = (minutos − conferência) / 60 × custo-hora × aproveitamento",
         "=MAX({c}{minutos_por_tarefa}-{c}{minutos_revisao_humana},0)/60*{c}{custo_hora}*{c}{aproveitamento}", {}, "R$", BRL4,
         "Fórmula", "premissas.py", True, False),
        ("taxa_mensal", "Taxa de desconto mensal equivalente", "=(1+{c}{taxa_desconto_anual})^(1/12)-1", {}, "% a.m.",
         '0.000%', "Fórmula", "calculadora.py", True, False),
    ]),
    ("Câmbio", [
        ("cotacao_dolar", "Dólar usado no modelo (igual ao protótipo)", 5.52, {}, "R$/US$", '0.0000', "Documento da equipe",
         DOC + "; backend/app/core/config.py COTACAO_DOLAR", False, False),
        ("cotacao_euro", "Euro", 6.12, {}, "R$/€", '0.0000', "Documento da equipe", DOC, False, False),
        ("ptax_conferida", "PTAX de venda em 13/11/2026 (referência, não usada nas contas)", 5.6518, {}, "R$/US$", '0.0000',
         "Referência", "Banco Central (ptax.bcb.gov.br), fechamento de 13/11/2026; tokens são ~1% a 4% do custo, o efeito é pequeno", False, False),
    ]),
    ("Preços (US$/milhão de tokens)", [
        ("haiku_entrada", "Claude Haiku 5.5: entrada (prompt até 100 mil tokens)", 0.10, {}, "US$/MTok", NUM2, "Tabela oficial", OFICIAL, False, False),
        ("haiku_saida", "Claude Haiku 5.5: saída", 0.50, {}, "US$/MTok", NUM2, "Tabela oficial", OFICIAL, False, False),
        ("haiku_cache", "Claude Haiku 5.5: leitura de cache", 0.01, {}, "US$/MTok", NUM2, "Premissa a validar",
         "Estimativa: 10% do preço de entrada (padrão da tabela); conferir", False, False),
        ("sonnet_entrada", "Claude Sonnet 5.5: entrada", 2.00, {}, "US$/MTok", NUM2, "Tabela oficial", OFICIAL, False, False),
        ("sonnet_saida", "Claude Sonnet 5.5: saída", 10.00, {}, "US$/MTok", NUM2, "Tabela oficial", OFICIAL, False, False),
        ("sonnet_cache", "Claude Sonnet 5.5: leitura de cache", 0.10, {}, "US$/MTok", NUM2, "Tabela oficial", OFICIAL, False, False),
    ]),
    ("Equipe (CAPEX)", [
        ("horas_mes", "Horas por pessoa por mês", 160, {}, "h", NUM, "Documento da equipe", "R$ 750/h × ~800 h = R$ 600 mil", False, False),
        ("meses_projeto", "Duração do desenvolvimento + implantação", 5, {}, "meses", NUM, "Documento da equipe", DOC, False, False),
        ("devs_qtd", "Desenvolvedores", 3, {}, "pessoas", NUM, "Documento da equipe", DOC, False, False),
        ("dev_hora", "Custo/hora do desenvolvedor (pleno de fintech)", 150, {}, "R$/h", BRL, "Documento da equipe", DOC, False, False),
        ("gp_qtd", "Gerente de projeto", 1, {}, "pessoas", NUM, "Documento da equipe", DOC, False, False),
        ("gp_hora", "Custo/hora do GP", 180, {}, "R$/h", BRL, "Documento da equipe", DOC, False, False),
        ("qa_qtd", "Analista de qualidade (QA)", 1, {}, "pessoas", NUM, "Documento da equipe", DOC, False, False),
        ("qa_hora", "Custo/hora do QA", 120, {}, "R$/h", BRL, "Documento da equipe", DOC, False, False),
        ("contingencia", "Contingência sobre o desenvolvimento", 0.15, {}, "%", PCT, "Documento da equipe", DOC, False, False),
        ("modulos_qtd", "Módulos de integração no pacote", 4, {}, "módulos", NUM, "Documento da equipe", DOC, False, False),
        ("modulo_min", "Custo de um módulo: mínimo da faixa", 50000, {}, "R$", BRL, "Documento da equipe", DOC, False, False),
        ("modulo_max", "Custo de um módulo: máximo da faixa", 100000, {}, "R$", BRL, "Documento da equipe", DOC, False, False),
        ("modulo_valor", "Custo de um módulo usado no modelo (meio da faixa)", 75000, {}, "R$", BRL, "Documento da equipe",
         DOC + " (pacote com 4 ≈ R$ 300 mil)", False, False),
        ("piloto_modulos", "Módulos entregues antes do piloto (Atendimento e Risco)", 2, {}, "módulos", NUM, "Premissa a validar",
         "Proposta de faseamento da equipe", False, False),
        ("piloto_meses", "Duração do piloto em 2 áreas", 3, {}, "meses", NUM, "Premissa a validar", "Proposta de go-to-market", False, False),
        ("piloto_usuarios", "Colaboradores das 2 áreas no piloto", 400, {}, "pessoas", NUM, "Premissa a validar",
         "Ordem de grandeza; confirmar com Atendimento e Risco", False, False),
    ]),
    ("Operação (detalhe)", [
        ("hospedagem_min", "Hospedagem + domínio + n8n: piso da faixa", 2800, {}, "R$/mês", BRL, "Documento da equipe", DOC, False, False),
        ("observabilidade_mensal", "Observabilidade externa (APM/logs) além da nativa", 0, {}, "R$/mês", BRL, "Premissa a validar",
         "No protótipo, Saúde e Alertas são nativos. Ferramenta externa seria custo adicional (não incluído)", False, False),
    ]),
    ("Tokens (a): Q&A do documento", [
        ("perguntas_dia", "Perguntas por usuário por dia útil", 5, {}, "perg/dia", NUM, "Documento da equipe", DOC, False, False),
        ("pct_base", "Respondidas pela base aprovada (sem modelo)", 0.40, {}, "%", PCT, "Documento da equipe", DOC, False, False),
        ("pct_haiku", "Respondidas pelo Haiku", 0.48, {}, "%", PCT, "Documento da equipe", DOC, False, False),
        ("pct_sonnet", "Respondidas pelo Sonnet", 0.12, {}, "%", PCT, "Documento da equipe", DOC, False, False),
        ("qa_haiku_in", "Tokens de entrada por pergunta no Haiku", 1500, {}, "tokens", NUM, "Premissa da equipe",
         "Simulador do v3 (v3-extensao/funil/config.py)", False, False),
        ("qa_haiku_out", "Tokens de saída por pergunta no Haiku", 500, {}, "tokens", NUM, "Premissa da equipe", "Simulador do v3", False, False),
        ("qa_sonnet_in", "Tokens de entrada por pergunta no Sonnet", 3000, {}, "tokens", NUM, "Premissa da equipe", "Simulador do v3", False, False),
        ("qa_sonnet_out", "Tokens de saída por pergunta no Sonnet", 1000, {}, "tokens", NUM, "Premissa da equipe", "Simulador do v3", False, False),
        ("tokens_doc_brl", "Custo mensal de tokens declarado no documento", 8500, {}, "R$/mês", BRL, "Documento da equipe", DOC, False, False),
        ("tokens_doc_min", "Faixa do documento: mínimo", 4300, {}, "R$/mês", BRL, "Documento da equipe", DOC, False, False),
        ("tokens_doc_max", "Faixa do documento: máximo", 21000, {}, "R$/mês", BRL, "Documento da equipe", DOC, False, False),
    ]),
    ("Tokens (b): agentes do v4", [
        ("tk_sistema", "Tokens de instruções do sistema por chamada", 450, {}, "tokens", NUM, "Protótipo (estimativa)", PROTO, False, False),
        ("tk_por_dependencia", "Tokens de contexto por passo anterior usado", 600, {}, "tokens", NUM, "Protótipo (estimativa)", PROTO, False, False),
        ("tk_por_ferramenta", "Tokens por definição de ferramenta", 180, {}, "tokens", NUM, "Protótipo (estimativa)", PROTO, False, False),
        ("tk_resultado_ferramenta", "Tokens do resultado de uma ferramenta", 500, {}, "tokens", NUM, "Protótipo (estimativa)", PROTO, False, False),
        ("tk_chamada_ferramenta", "Tokens de saída ao pedir uma ferramenta", 120, {}, "tokens", NUM, "Protótipo (estimativa)", PROTO, False, False),
        ("tk_saida", "Tokens da resposta final do passo", 350, {}, "tokens", NUM, "Protótipo (estimativa)", PROTO, False, False),
        ("cache_fracao", "Fração do prompt fixo lida do cache (cenário com cache de prompt)", 0.8, {}, "%", PCT,
         "Premissa a validar", "Ilustrativo: o cliente do protótipo marca o prompt fixo para cache; medir com a chave real", False, False),
        ("vol_triagem", "Execuções concluídas: Triagem de chargebacks (30 dias)", 165, {}, "exec", NUM, "Histórico sintético da demo", DEMO, False, False),
        ("vol_duvidas", "Execuções concluídas: Resposta a dúvidas de lojistas (30 dias)", 420, {}, "exec", NUM, "Histórico sintético da demo", DEMO, False, False),
        ("vol_ferias", "Execuções concluídas: Orientação de férias (30 dias)", 224, {}, "exec", NUM, "Histórico sintético da demo", DEMO, False, False),
    ]),
    ("Benefícios (detalhe)", [
        ("min_triagem", "Minutos à mão: Triagem de chargebacks", 25, {}, "min", NUM1, "Premissa a validar",
         "Declarado no blueprint do agente (Estúdio); o piloto mede", False, False),
        ("min_duvidas", "Minutos à mão: Resposta a dúvidas de lojistas", 8, {}, "min", NUM1, "Premissa a validar", "Blueprint do agente", False, False),
        ("min_ferias", "Minutos à mão: Orientação de férias", 10, {}, "min", NUM1, "Premissa a validar", "Blueprint do agente", False, False),
        ("taxa_escalada", "Execuções que escalaram para humano (agente)", 0.0593, {}, "%", PCT, "Histórico sintético da demo",
         DEMO + ": 51 de 860", False, False),
        ("ai_eng_hora", "Custo/hora de um AI Engineer", 180, {}, "R$/h", BRL, "Premissa a validar",
         "Ordem de grandeza (sênior de fintech); validar com Pessoas", False, False),
        ("ai_eng_horas_agente", "Horas de AI Engineer por agente sob medida", 160, {}, "h", NUM, "Premissa a validar",
         "Premissa: ~1 mês de um engenheiro por agente", False, False),
        ("agentes_por_ano", "Agentes novos por ano que iriam para a fila da Engenharia", 24, {}, "agentes", NUM, "Premissa a validar",
         "Premissa: 2 por mês na empresa toda", False, False),
    ]),
    ("Construir × comprar", [
        ("copilot_usd_credito", "Copilot Studio: US$ por crédito (pacote de US$ 200 = 25 mil créditos)", 0.008, {}, "US$", USD4,
         "Pesquisa de preço público", "microsoft.com/en-us/microsoft-365-copilot/pricing/copilot-studio, consultado em " + DATA_CONF, False, False),
        ("copilot_creditos_exec", "Copilot Studio: créditos por execução de agente", 12, {}, "créditos", NUM, "Premissa a validar",
         "2 respostas generativas (2 cada) + 2 ações de agente (5 cada) por execução média; tabela em learn.microsoft.com "
         "(requirements-messages-management), consultada em " + DATA_CONF, False, False),
        ("zapier_usd_atividade", "Zapier Agents: US$ por atividade (Pro: ~US$ 33,33/mês por 1.500)", 0.0222, {}, "US$", USD4,
         "Pesquisa de preço público", "zapier.com/pricing (seção Agents), consultado em " + DATA_CONF + ". Enterprise sob consulta: extrapolação", False, False),
        ("zapier_atividades_exec", "Zapier Agents: atividades por execução", 4, {}, "atividades", NUM, "Premissa a validar",
         "Gatilho + 2 ações + 1 resposta", False, False),
        ("n8n_eur_mes", "n8n Business (self-hosted, anual): € por mês", 667, {}, "€/mês", EUR, "Pesquisa de preço público",
         "n8n.io/pricing, consultado em " + DATA_CONF, False, False),
        ("n8n_execs_incluidas", "n8n Business: execuções incluídas por mês", 40000, {}, "exec", NUM, "Pesquisa de preço público",
         "n8n.io/pricing, consultado em " + DATA_CONF, False, False),
        ("n8n_eur_bloco", "n8n: € por bloco extra de execuções", 4000, {}, "€", EUR, "Pesquisa de preço público",
         "Reportado por terceiros (cloudzero.com/blog/n8n-pricing, consultado em " + DATA_CONF + "); conferir com a n8n", False, False),
        ("n8n_execs_bloco", "n8n: execuções por bloco extra", 300000, {}, "exec", NUM, "Pesquisa de preço público", "Idem", False, False),
        ("comprar_implantacao", "Comprar SaaS (Copilot, Zapier): configuração, governança e treinamento (fora a integração)", 200000, {}, "R$", BRL,
         "Premissa a validar", "Premissa: SSO, ambientes, políticas de DLP e trilha de auditoria sobre a ferramenta comprada", False, False),
        ("n8n_fracao_construcao", "n8n: fração do desenvolvimento do StoneFalcon que ainda seria preciso construir", 0.7, {}, "%", PCT,
         "Premissa a validar", "O n8n dá o motor de fluxos; Estúdio no-code, catálogo com permissões, guardrails e auditoria teriam de ser feitos", False, False),
    ]),
]

linha = LIN0
pend_formulas = []
for grupo, itens in GRUPOS:
    secao(wp, linha, grupo, 11)
    linha += 1
    for (nome, desc, base, over, unid, fmt, status, fonte, cenario, chave) in itens:
        LINHA[nome] = linha
        cel(wp, "B%d" % linha, desc)
        cel(wp, "C%d" % linha, nome if (cenario or nome.startswith("cotacao")) else "—", Font(name=F, size=9, color="46564F"))
        cel(wp, "I%d" % linha, unid)
        cel(wp, "J%d" % linha, status)
        cel(wp, "K%d" % linha, fonte, alin=Alignment(wrap_text=False))
        if cenario:
            CEN_ROW.add(nome)
            pend_formulas.append((nome, base, over, fmt, chave))
            cel(wp, "D%d" % linha, "=INDEX(E%d:H%d,MATCH(cenario_ativo,$E$7:$H$7,0))" % (linha, linha), f_calc_b, fmt)
            nomear(nome, S_PREM, "$D$%d" % linha)
        else:
            cel(wp, "D%d" % linha, base, f_in, fmt)
            nomear(nome, S_PREM, "$D$%d" % linha)
        for c in "BCDEFGHIJK":
            wp["%s%d" % (c, linha)].border = borda
        linha += 1
    linha += 1

for nome, base, over, fmt, chave in pend_formulas:
    r = LINHA[nome]
    for col in COLS:
        refs = {k: v for k, v in LINHA.items()}
        if isinstance(base, str) and "{c}" in base:
            v = base.format(c=col, **refs)
            fonte = f_calc
        elif col in over:
            v = over[col]
            fonte = f_link if isinstance(v, str) else f_in
        elif col == "E":
            v = base
            fonte = f_link if isinstance(base, str) else f_in
        else:
            v = "=$E%d" % r
            fonte = f_calc
        c = cel(wp, "%s%d" % (col, r), v, fonte, fmt)
        if col in over:
            c.fill = p_chave
    if chave:
        wp["E%d" % r].fill = p_chave

# =====================================================================
# 3. Investimento (CAPEX)
# =====================================================================
wc = wb.create_sheet(S_CAPEX)
titulo(wc, "Investimento (CAPEX)", "Fonte: " + DOC + ". Valores derivados das premissas de equipe; conectores mapeados ao catálogo do protótipo.")
larguras(wc, {"A": 34, "B": 12, "C": 14, "D": 16, "E": 16, "F": 16, "G": 60})
cabecalho(wc, 4, ["Equipe", "Pessoas", "R$/hora", "Horas no projeto", "Custo", "", "Observação"])
equipe = [("Desenvolvedores", "devs_qtd", "dev_hora"), ("Gerente de projeto", "gp_qtd", "gp_hora"), ("QA", "qa_qtd", "qa_hora")]
for i, (rot, qn, hn) in enumerate(equipe):
    r = 5 + i
    cel(wc, "A%d" % r, rot)
    cel(wc, "B%d" % r, "=" + qn, f_link, NUM)
    cel(wc, "C%d" % r, "=" + hn, f_link, BRL)
    cel(wc, "D%d" % r, "=horas_mes*meses_projeto", f_calc, NUM)
    cel(wc, "E%d" % r, "=B%d*C%d*D%d" % (r, r, r), f_calc, BRL)
cel(wc, "G5", "Pleno de fintech: Dev R$ 150/h, GP R$ 180/h, QA R$ 120/h (documento da equipe)", f_sub)
cel(wc, "A9", "Custo da equipe por hora (todas as pessoas)", f_neg)
cel(wc, "C9", "=SUMPRODUCT(B5:B7,C5:C7)", f_calc, BRL)
cel(wc, "G9", "Conferência: R$ 750/h × 800 h = R$ 600 mil", f_sub)
cel(wc, "A11", "Desenvolvimento + implantação (sem contingência)", f_neg)
cel(wc, "D11", "=SUM(E5:E7)", f_calc_b, BRL)
cel(wc, "A12", "Contingência")
cel(wc, "C12", "=contingencia", f_link, PCT)
cel(wc, "D12", "=D11*C12", f_calc, BRL)
cel(wc, "A14", "Investimento inicial (vai para a premissa investimento_inicial)", f_neg)
cel(wc, "D14", "=D11+D12", f_calc_b, BRL, p_kpi)

cabecalho(wc, 17, ["Módulo de integração", "Classificação", "Mínimo", "Máximo", "Usado no modelo", "", "Ferramentas do catálogo atendidas"])
modulos = [
    ("1. Cadastro de lojistas", "Interna", "consultar_lojista"),
    ("2. Transações, contestações e repasses", "Confidencial e restrita", "listar_transacoes, listar_chargebacks, bloquear_repasse (ação sensível)"),
    ("3. Chamados e notificações", "Interna", "abrir_chamado, enviar_notificacao"),
    ("4. Pessoas (RH) e políticas internas", "Interna e confidencial", "consultar_colaborador, buscar_politica"),
]
for i, (nome_m, cls, ferr) in enumerate(modulos):
    r = 18 + i
    cel(wc, "A%d" % r, nome_m)
    cel(wc, "B%d" % r, cls)
    cel(wc, "C%d" % r, "=modulo_min", f_link, BRL)
    cel(wc, "D%d" % r, "=modulo_max", f_link, BRL)
    cel(wc, "E%d" % r, "=modulo_valor", f_link, BRL)
    cel(wc, "G%d" % r, ferr)
cel(wc, "A22", "Módulos considerados (premissa modulos_qtd)")
cel(wc, "E22", "=modulos_qtd", f_link, NUM)
cel(wc, "A24", "Pacote de módulos (vai para a premissa modulos_integracao)", f_neg)
cel(wc, "C24", "=modulos_qtd*modulo_min", f_calc, BRL)
cel(wc, "D24", "=modulos_qtd*modulo_max", f_calc, BRL)
cel(wc, "E24", "=modulos_qtd*modulo_valor", f_calc_b, BRL, p_kpi)
cel(wc, "G24", "Faixa do documento: R$ 50 a 100 mil por módulo; pacote com 4 ≈ R$ 300 mil", f_sub)

cel(wc, "A27", "Investimento total do cenário em uso", f_neg)
cel(wc, "E27", "=investimento_total", f_link, BRL, p_kpi)

secao(wc, 30, "Faseamento proposto: piloto antes da escala", 7)
cabecalho(wc, 31, ["Tranche", "", "", "", "Valor", "", "O que libera a próxima"])
cel(wc, "A32", "1. Plataforma + 2 conectores + piloto em 2 áreas")
cel(wc, "E32", "=investimento_inicial+piloto_modulos*modulo_valor+piloto_meses*custo_fixo_mensal", f_calc_b, BRL)
cel(wc, "G32", "Metas de saída do piloto atingidas (adoção, minutos medidos, escaladas, zero vazamento)")
cel(wc, "A33", "2. Conectores restantes + escala por ondas")
cel(wc, "E33", "=IF(incluir_modulos=1,(modulos_qtd-piloto_modulos)*modulo_valor,0)", f_calc, BRL)
cel(wc, "G33", "Expansão por área com CoE de IA e embaixadores")
cel(wc, "A34", "Total (antes da operação contínua)", f_neg)
cel(wc, "E34", "=E32+E33", f_calc_b, BRL)
cel(wc, "A35", "Nota: o fluxo de caixa (como a calculadora do protótipo) põe todo o investimento no mês 0 e o benefício a partir do mês 1.", f_sub)

# =====================================================================
# 4. Operação (OPEX)
# =====================================================================
wo = wb.create_sheet(S_OPEX)
titulo(wo, "Operação (OPEX)", "Custos fixos mensais. Fonte: " + DOC + ". O n8n serve só às integrações (aviso do documento).")
larguras(wo, {"A": 50, "B": 16, "C": 16, "D": 4, "E": 62})
cabecalho(wo, 4, ["Item", "Piso da faixa", "Usado no modelo", "", "Observação"])
cel(wo, "A5", "Hospedagem + domínio + n8n")
cel(wo, "B5", "=hospedagem_min", f_link, BRL)
cel(wo, "C5", "=hospedagem_mensal", f_link, BRL)
cel(wo, "E5", "Estimativa de mercado; o modelo usa o teto (R$ 6,9 mil)")
cel(wo, "A6", "Time de sustentação")
cel(wo, "B6", "=sustentacao_mensal", f_link, BRL)
cel(wo, "C6", "=sustentacao_mensal", f_link, BRL)
cel(wo, "E6", "Mantém conectores, catálogo, revisões de segurança e plantão")
cel(wo, "A7", "Observabilidade externa (APM/logs)")
cel(wo, "B7", "=observabilidade_mensal", f_link, BRL)
cel(wo, "C7", "=observabilidade_mensal", f_link, BRL)
cel(wo, "E7", "Saúde, alertas e auditoria são nativos; ferramenta externa não incluída (premissa em 0)")
cel(wo, "A9", "Total mensal SEM time de sustentação", f_neg)
cel(wo, "B9", "=B5+B7", f_calc, BRL)
cel(wo, "C9", "=C5+C7", f_calc, BRL)
cel(wo, "A10", "Total mensal COM time de sustentação", f_neg)
cel(wo, "B10", "=B5+B6+B7", f_calc_b, BRL)
cel(wo, "C10", "=C5+C6+C7", f_calc_b, BRL, p_kpi)
cel(wo, "E10", "É o custo_fixo_mensal da calculadora (hospedagem + sustentação)")
cel(wo, "A11", "Conferência com a premissa custo_fixo_mensal (deve ser 0)")
cel(wo, "C11", "=C10-observabilidade_mensal-custo_fixo_mensal", f_calc, BRL)
cel(wo, "A13", "Custo fixo por ano (com sustentação)")
cel(wo, "C13", "=C10*12", f_calc, BRL)
cel(wo, "A14", "Custo fixo no horizonte da análise")
cel(wo, "C14", "=custo_fixo_mensal*MIN(meses,60)", f_calc, BRL)
secao(wo, 16, "Custo variável (tokens) no cenário em uso", 5)
cel(wo, "A17", "Execuções por mês com a adoção-alvo atingida")
cel(wo, "C17", "=usuarios*adocao_alvo*tarefas_por_usuario_dia*dias_uteis", f_calc, NUM)
cel(wo, "A18", "Custo de tokens por mês com a adoção-alvo atingida")
cel(wo, "C18", "=C17*custo_por_execucao", f_calc, BRL)
cel(wo, "A19", "Tokens como parcela do custo mensal total (fixo + tokens)")
cel(wo, "C19", "=IFERROR(C18/(C18+custo_fixo_mensal),0)", f_calc, PCT)
cel(wo, "E19", "Mesmo no regime pleno, os tokens são uma parcela pequena do custo")

# =====================================================================
# 6. Benefícios (antes de Tokens para a referência D12)
# =====================================================================
wbn = wb.create_sheet(S_BEN)
titulo(wbn, "Benefícios por caso de uso",
       "Ganho por tarefa = (minutos à mão − conferência) ÷ 60 × custo-hora × aproveitamento. Só execuções concluídas geram ganho.")
larguras(wbn, {"A": 38, "B": 16, "C": 12, "D": 12, "E": 14, "F": 14, "G": 14, "H": 54})
cabecalho(wbn, 4, ["Agente (demo)", "Área", "Minutos à mão", "Conferência", "Ganho por tarefa", "Execuções concluídas (30 d)",
                   "Peso no volume", "Observação"])
agentes_b = [("Triagem de chargebacks", "Prevenção a Fraudes", "min_triagem", "vol_triagem", "Usa o Sonnet na análise; ação sensível com confirmação"),
             ("Resposta a dúvidas de lojistas", "Atendimento", "min_duvidas", "vol_duvidas", "Só Haiku"),
             ("Orientação de férias", "Pessoas (RH)", "min_ferias", "vol_ferias", "Só Haiku")]
for i, (n, a, mn, vn, obs) in enumerate(agentes_b):
    r = 5 + i
    cel(wbn, "A%d" % r, n)
    cel(wbn, "B%d" % r, a)
    cel(wbn, "C%d" % r, "=" + mn, f_link, NUM1)
    cel(wbn, "D%d" % r, "=minutos_revisao_humana", f_link, NUM1)
    cel(wbn, "E%d" % r, "=MAX(C%d-D%d,0)/60*custo_hora*aproveitamento" % (r, r), f_calc, BRL2)
    cel(wbn, "F%d" % r, "=" + vn, f_link, NUM)
    cel(wbn, "G%d" % r, "=F%d/SUM($F$5:$F$7)" % r, f_calc, PCT)
    cel(wbn, "H%d" % r, obs)
cel(wbn, "A9", "Extrapolação: média da plataforma (premissa do cenário)", f_neg)
cel(wbn, "C9", "=minutos_por_tarefa", f_link, NUM1)
cel(wbn, "D9", "=minutos_revisao_humana", f_link, NUM1)
cel(wbn, "E9", "=ganho_por_tarefa", f_link, BRL2)
cel(wbn, "H9", "Vale para todos os agentes que a empresa criar, não só os 3 da demo")
cel(wbn, "A12", "Média ponderada dos 3 agentes da demo (minutos à mão)", f_neg)
cel(wbn, "D12", "=SUMPRODUCT(C5:C7,F5:F7)/SUM(F5:F7)", f_calc_b, NUM1, p_kpi)
cel(wbn, "H12", "Alimenta minutos_por_tarefa no cenário Base medido. O painel do protótipo mostra 12,0 min")
cel(wbn, "A13", "Ganho médio ponderado por tarefa")
cel(wbn, "D13", "=SUMPRODUCT(E5:E7,F5:F7)/SUM(F5:F7)", f_calc, BRL2)

secao(wbn, 15, "Benefício mensal no cenário em uso (entra no fluxo de caixa)", 8)
cel(wbn, "A16", "Execuções por mês com a adoção-alvo atingida")
cel(wbn, "D16", "=usuarios*adocao_alvo*tarefas_por_usuario_dia*dias_uteis", f_calc, NUM)
cel(wbn, "A17", "Horas liberadas por mês")
cel(wbn, "D17", "=D16*MAX(minutos_por_tarefa-minutos_revisao_humana,0)/60", f_calc, NUM)
cel(wbn, "A18", "Benefício por mês (horas × custo-hora × aproveitamento)")
cel(wbn, "D18", "=D16*ganho_por_tarefa", f_calc_b, BRL)

secao(wbn, 21, "Ganhos que NÃO entram no fluxo (conservadorismo): mostrar ao board como potencial", 8)
cabecalho(wbn, 22, ["Ganho adicional", "", "", "Taxa / base", "Por mês", "Por ano", "", "Como medir no piloto"])
cel(wbn, "A23", "Retrabalho evitado (erro manual − escalada do agente)")
cel(wbn, "D23", "=MAX(taxa_erro_manual-taxa_escalada,0)", f_calc, PCT)
cel(wbn, "E23", "=D16*D23*minutos_por_tarefa/60*custo_hora*aproveitamento", f_calc, BRL)
cel(wbn, "F23", "=E23*12", f_calc, BRL)
cel(wbn, "H23", "Comparar a taxa de retrabalho manual (8%, premissa) com a de escalada medida")
cel(wbn, "A24", "Custo evitado de AI Engineer (agentes sob medida)")
cel(wbn, "D24", "=ai_eng_hora*ai_eng_horas_agente", f_calc, BRL)
cel(wbn, "E24", "=F24/12", f_calc, BRL)
cel(wbn, "F24", "=D24*agentes_por_ano", f_calc, BRL)
cel(wbn, "H24", "Contar quantos pedidos de agente saíram da fila da Engenharia")
cel(wbn, "A25", "Total potencial fora do fluxo", f_neg)
cel(wbn, "E25", "=E23+E24", f_calc_b, BRL)
cel(wbn, "F25", "=F23+F24", f_calc_b, BRL)
cel(wbn, "A27", "A taxa de escalada vem do histórico SINTÉTICO da demo, não de medição; o piloto a substitui.", f_sub)

# =====================================================================
# 5. Tokens
# =====================================================================
wt = wb.create_sheet(S_TOK, index=3)
titulo(wt, "Tokens: dois modelos lado a lado",
       "(a) reconcilia o documento da equipe (Q&A); (b) modela os agentes do v4 passo a passo, com e sem o roteador.")
larguras(wt, {"A": 40, "B": 14, "C": 13, "D": 14, "E": 11, "F": 11, "G": 13, "H": 10, "I": 14, "J": 14, "K": 14, "L": 40})
secao(wt, 4, "(a) Q&A do documento: 5 perguntas por dia, mix 40% base / 48% Haiku / 12% Sonnet", 12)
cabecalho(wt, 5, ["Camada", "Perguntas/mês", "Tokens entrada", "Tokens saída", "", "", "US$/mês", "", "R$/mês", "Parcela do custo"])
cel(wt, "A6", "Base aprovada (sem modelo)")
cel(wt, "B6", "=usuarios*perguntas_dia*dias_uteis*pct_base", f_calc, NUM)
cel(wt, "G6", 0, f_calc, USD2)
cel(wt, "A7", "Claude Haiku 5.5")
cel(wt, "B7", "=usuarios*perguntas_dia*dias_uteis*pct_haiku", f_calc, NUM)
cel(wt, "C7", "=qa_haiku_in", f_link, NUM)
cel(wt, "D7", "=qa_haiku_out", f_link, NUM)
cel(wt, "G7", "=B7*(C7*haiku_entrada+D7*haiku_saida)/1000000", f_calc, USD2)
cel(wt, "A8", "Claude Sonnet 5.5")
cel(wt, "B8", "=usuarios*perguntas_dia*dias_uteis*pct_sonnet", f_calc, NUM)
cel(wt, "C8", "=qa_sonnet_in", f_link, NUM)
cel(wt, "D8", "=qa_sonnet_out", f_link, NUM)
cel(wt, "G8", "=B8*(C8*sonnet_entrada+D8*sonnet_saida)/1000000", f_calc, USD2)
for r in (6, 7, 8):
    cel(wt, "I%d" % r, "=G%d*cotacao_dolar" % r, f_calc, BRL)
    cel(wt, "J%d" % r, "=IFERROR(G%d/$G$9,0)" % r, f_calc, PCT)
cel(wt, "A9", "Total recalculado", f_neg)
cel(wt, "B9", "=SUM(B6:B8)", f_calc_b, NUM)
cel(wt, "G9", "=SUM(G6:G8)", f_calc_b, USD2)
cel(wt, "I9", "=SUM(I6:I8)", f_calc_b, BRL, p_kpi)
cel(wt, "A11", "Valor declarado no documento")
cel(wt, "I11", "=tokens_doc_brl", f_link, BRL)
cel(wt, "A12", "Diferença (documento ÷ recalculado − 1)")
cel(wt, "I12", "=I11/I9-1", f_calc, PCT)
cel(wt, "A13", "Câmbio que reproduz o documento (R$ por US$)")
cel(wt, "I13", "=I11/G9", f_calc, '0.00')
cel(wt, "A14", "Recalculado convertendo pela cotação do EURO")
cel(wt, "I14", "=G9*cotacao_euro", f_calc_b, BRL)
cel(wt, "L11", "Leitura: o recalculado dá ≈ R$ 7,7 mil. O documento (R$ 8,5 mil) é reproduzido ao converter "
               "US$ pela cotação do euro (6,12): provável troca de moeda. O Sonnet faz 12% das perguntas e ~91% do custo.",
    f_sub, alin=quebra)
wt.merge_cells("L11:L16")

secao(wt, 18, "(b) Agentes do v4: custo por execução, passo a passo (tamanhos do protótipo; roteador escolhe o modelo)", 12)
cabecalho(wt, 19, ["Agente · passo", "Modelo pedido", "Modelo do roteador", "Passos anteriores", "Ferramentas", "Voltas",
                   "Tokens entrada", "", "Com roteador (US$)", "Tudo no Sonnet (US$)", "Com cache (US$)", "Por que este modelo"])
passos = [
    ("Triagem de chargebacks · análise", "auto", "Sonnet", 2, 1, "triagem", "Complexidade 0,68 ≥ 0,60: análise de risco"),
    ("Triagem de chargebacks · ação", "rápido", "Haiku", 1, 2, "triagem", "Blueprint pediu o modelo rápido"),
    ("Dúvidas de lojistas · resposta", "rápido", "Haiku", 2, 0, "duvidas", "Blueprint pediu o modelo rápido"),
    ("Orientação de férias · resposta", "rápido", "Haiku", 2, 0, "ferias", "Blueprint pediu o modelo rápido"),
]
P0 = 20
for i, (n, ped, mod, dep, fer, ag, motivo) in enumerate(passos):
    r = P0 + i
    cel(wt, "A%d" % r, n)
    cel(wt, "B%d" % r, ped)
    cel(wt, "C%d" % r, mod, f_in)
    cel(wt, "D%d" % r, dep, f_in, NUM)
    cel(wt, "E%d" % r, fer, f_in, NUM)
    cel(wt, "F%d" % r, "=IF(E%d>0,2,1)" % r, f_calc, NUM)
    cel(wt, "G%d" % r, "=tk_sistema+D%d*tk_por_dependencia+E%d*tk_por_ferramenta" % (r, r), f_calc, NUM)
    cel(wt, "H%d" % r, ag, Font(name=F, size=8, color="A0A0A0"))
    # custo de um passo: 1 volta = entrada + saída final; 2 voltas = (entrada + pedido da ferramenta) + (entrada + resultado + saída final)
    def custo(pin, pout, pcache=None):
        if pcache is None:
            return ("IF(F{r}=2,(G{r}*{pin}+tk_chamada_ferramenta*{pout}+(G{r}+tk_resultado_ferramenta+tk_chamada_ferramenta)*{pin}"
                    "+tk_saida*{pout}),G{r}*{pin}+tk_saida*{pout})/1000000").format(r=r, pin=pin, pout=pout)
        fixo = "(tk_sistema+E{r}*tk_por_ferramenta)*cache_fracao".format(r=r)
        return ("(F{r}*(({fx})*{pc}-({fx})*{pin})"
                "+IF(F{r}=2,(G{r}*{pin}+tk_chamada_ferramenta*{pout}+(G{r}+tk_resultado_ferramenta+tk_chamada_ferramenta)*{pin}"
                "+tk_saida*{pout}),G{r}*{pin}+tk_saida*{pout}))/1000000").format(r=r, pin=pin, pout=pout, pc=pcache, fx=fixo)
    pin = 'IF($C{r}="Sonnet",sonnet_entrada,haiku_entrada)'.format(r=r)
    pout = 'IF($C{r}="Sonnet",sonnet_saida,haiku_saida)'.format(r=r)
    pc = 'IF($C{r}="Sonnet",sonnet_cache,haiku_cache)'.format(r=r)
    cel(wt, "I%d" % r, "=" + custo(pin, pout), f_calc, '0.000000')
    cel(wt, "J%d" % r, "=" + custo("sonnet_entrada", "sonnet_saida"), f_calc, '0.000000')
    cel(wt, "K%d" % r, "=" + custo(pin, pout, pc), f_calc, '0.000000')
    cel(wt, "L%d" % r, motivo)
cel(wt, "A25", "Os passos de ferramenta (consultas) não chamam modelo e custam R$ 0. Modelo do roteador: saída de app/llm/roteador.py.", f_sub)

cabecalho(wt, 27, ["Por agente (R$ por execução)", "Com roteador", "Tudo no Sonnet", "Com cache", "Economia do roteador",
                   "Peso no volume", "", "", "", "", "", ""])
ags = [("Triagem de chargebacks", "triagem", "vol_triagem"), ("Resposta a dúvidas de lojistas", "duvidas", "vol_duvidas"),
       ("Orientação de férias", "ferias", "vol_ferias")]
rng = lambda col: "$%s$%d:$%s$%d" % (col, P0, col, P0 + len(passos) - 1)
for i, (n, ag, vn) in enumerate(ags):
    r = 28 + i
    cel(wt, "A%d" % r, n)
    cel(wt, "B%d" % r, '=SUMIF(%s,"%s",%s)*cotacao_dolar' % (rng("H"), ag, rng("I")), f_calc, BRL4)
    cel(wt, "C%d" % r, '=SUMIF(%s,"%s",%s)*cotacao_dolar' % (rng("H"), ag, rng("J")), f_calc, BRL4)
    cel(wt, "D%d" % r, '=SUMIF(%s,"%s",%s)*cotacao_dolar' % (rng("H"), ag, rng("K")), f_calc, BRL4)
    cel(wt, "E%d" % r, "=IFERROR(1-B%d/C%d,0)" % (r, r), f_calc, PCT)
    cel(wt, "F%d" % r, "=%s/(vol_triagem+vol_duvidas+vol_ferias)" % vn, f_calc, PCT)
cel(wt, "A31", "Média ponderada pelo volume", f_neg)
for c in "BCD":
    cel(wt, "%s31" % c, "=SUMPRODUCT(%s28:%s30,$F$28:$F$30)" % (c, c), f_calc_b, BRL4)
cel(wt, "E31", "=IFERROR(1-B31/C31,0)", f_calc_b, PCT, p_kpi)
cel(wt, "L28", "Conferência: o Estúdio do protótipo estima R$ 0,0764 (triagem) e R$ 0,0019 (dúvidas e férias) por execução.",
    f_sub, alin=quebra)
wt.merge_cells("L28:L31")

secao(wt, 33, "Resultado do modelo (b)", 12)
cel(wt, "A34", "Custo por execução: premissa do cenário (custo_por_execucao)")
cel(wt, "D34", "=custo_por_execucao", f_link, BRL4)
cel(wt, "A35", "Economia do roteador no mix de agentes da demo")
cel(wt, "D35", "=E31", f_calc, PCT)
cel(wt, "L35", "O painel do protótipo mostra ~79% sobre o histórico SINTÉTICO da demo; este é o valor estrutural.", f_sub, alin=quebra)
cel(wt, "A36", "Economia adicional do cache de prompt (sobre o custo com roteador)")
cel(wt, "D36", "=IFERROR(1-D31/B31,0)", f_calc, PCT)
cel(wt, "A37", "Custo de tokens/mês com a adoção-alvo atingida (cenário em uso)")
cel(wt, "D37", "=usuarios*adocao_alvo*tarefas_por_usuario_dia*dias_uteis*custo_por_execucao", f_calc, BRL)
cel(wt, "A38", "Parcela dos tokens no custo total do horizonte (cenário em uso)")
cel(wt, "D38", "=%s!$B$11" % q(S_FLUXO), f_link, PCT)
cel(wt, "A40", "Custo por execução MODELADO (vai para o cenário Base medido)", f_neg)
cel(wt, "D40", "=B31", f_calc_b, BRL4, p_kpi)
cel(wt, "L40", "A premissa da equipe (R$ 0,03) fica ~1,7× acima do modelado: margem para passos e voltas extras.", f_sub, alin=quebra)

# =====================================================================
# 7. Fluxo de caixa
# =====================================================================
wf = wb.create_sheet(S_FLUXO, index=5)
titulo(wf, "Fluxo de caixa mensal (cenário em uso)",
       "Mesmas fórmulas de backend/app/finance/calculadora.py: investimento no mês 0, adoção em rampa linear, benefício só de tarefas concluídas.")
larguras(wf, {"A": 34, "B": 16, "C": 11, "D": 13, "E": 13, "F": 13, "G": 14, "H": 14, "I": 15, "J": 15, "K": 16, "L": 15})
cel(wf, "A4", "Cenário em uso", f_neg)
cel(wf, "B4", "=cenario_ativo", f_link)
kpis = [
    ("VPL", "=SUM(L16:L76)", BRL),
    ("TIR mensal", '=IFERROR(IRR(J16:J76,0.01),IFERROR(IRR(J16:J76,-0.05),"—"))', '0.00%'),
    ("TIR anual", '=IF(ISNUMBER(B6),(1+B6)^12-1,"—")', PCT),
    ("Payback (mês)", '=IF(K76>=0,COUNTIF(K17:K76,"<0")+1,"não se paga")', NUM),
    ("ROI no horizonte", "=IFERROR((B12-B10)/B10,0)", PCT),
    ("Custo total (investimento + fixo + tokens)", "=investimento_total+SUM(G17:G76)+SUM(H17:H76)", BRL),
    ("Participação dos tokens no custo", "=IFERROR(SUM(G17:G76)/B10,0)", PCT),
    ("Benefício total", "=SUM(I17:I76)", BRL),
]
# B5 VPL · B6 TIR mensal · B7 TIR anual · B8 payback · B9 ROI · B10 custo total · B11 tokens % · B12 benefício
for i, (rot, f_, fmt) in enumerate(kpis):
    r = 5 + i
    cel(wf, "A%d" % r, rot, f_neg)
    cel(wf, "B%d" % r, f_, f_calc_b, fmt, p_kpi)
cabecalho(wf, 15, ["Mês", "Dentro do horizonte", "Adoção", "Usuários ativos", "Execuções", "Horas liberadas", "Custo de tokens",
                   "Custo fixo", "Benefício", "Fluxo do mês", "Acumulado", "Fluxo descontado"])
wf.freeze_panes = "B16"
cel(wf, "A16", 0, f_txt, NUM)
cel(wf, "J16", "=-investimento_total", f_calc, BRL)
cel(wf, "K16", "=J16", f_calc, BRL)
cel(wf, "L16", "=J16", f_calc, BRL)
for m in range(1, 61):
    r = 16 + m
    cel(wf, "A%d" % r, m, f_txt, NUM)
    cel(wf, "B%d" % r, "=IF(A%d<=meses,1,0)" % r, f_calc, NUM)
    cel(wf, "C%d" % r, "=B%d*adocao_alvo*MIN(1,A%d/meses_rampa)" % (r, r), f_calc, PCT)
    cel(wf, "D%d" % r, "=usuarios*C%d" % r, f_calc, NUM)
    cel(wf, "E%d" % r, "=D%d*tarefas_por_usuario_dia*dias_uteis" % r, f_calc, NUM)
    cel(wf, "F%d" % r, "=E%d*MAX(minutos_por_tarefa-minutos_revisao_humana,0)/60" % r, f_calc, NUM)
    cel(wf, "G%d" % r, "=E%d*custo_por_execucao" % r, f_calc, BRL)
    cel(wf, "H%d" % r, "=B%d*custo_fixo_mensal" % r, f_calc, BRL)
    cel(wf, "I%d" % r, "=E%d*ganho_por_tarefa" % r, f_calc, BRL)
    cel(wf, "J%d" % r, "=I%d-G%d-H%d" % (r, r, r), f_calc, BRL)
    cel(wf, "K%d" % r, "=K%d+J%d" % (r - 1, r), f_calc, BRL)
    cel(wf, "L%d" % r, "=J%d/(1+taxa_mensal)^A%d" % (r, r), f_calc, BRL)

# =====================================================================
# Motor (auxiliar): cada coluna é um caso completo de 60 meses
# =====================================================================
wm = wb.create_sheet(S_MOTOR)
titulo(wm, "Motor de cenários (auxiliar)", "Cada coluna recalcula o fluxo completo de um caso. Usado por Cenários, Sensibilidade e Resumo. Não editar.")
larguras(wm, {"A": 30})
PARAM = ["usuarios", "adocao_alvo", "meses_rampa", "tarefas_por_usuario_dia", "dias_uteis", "minutos_por_tarefa",
         "minutos_revisao_humana", "custo_hora", "aproveitamento", "custo_por_execucao", "investimento_total",
         "custo_fixo_mensal", "taxa_desconto_anual", "meses"]
PR = {nome: 5 + i for i, nome in enumerate(PARAM)}      # linhas 5..18
R_GANHO, R_TAXAM = 19, 20
R_VPL, R_TIRM, R_TIRA, R_PAY, R_ACUMF, R_EXEC, R_TOK, R_FIXO, R_CUSTO, R_BEN, R_ROI, R_TOKPCT = range(22, 34)
R_F0 = 36            # fluxo mês 0..60 -> linhas 36..96
R_A0 = 98            # acumulado mês 0..60 -> linhas 98..158
cel(wm, "A3", "Caso", f_neg)
cel(wm, "A4", "Grupo", f_neg)
for nome, r in PR.items():
    cel(wm, "A%d" % r, nome)
cel(wm, "A%d" % R_GANHO, "ganho_por_tarefa")
cel(wm, "A%d" % R_TAXAM, "taxa_mensal")
for r, rot in zip(range(R_VPL, R_TOKPCT + 1), ["VPL", "TIR mensal", "TIR anual", "Payback (mês)", "Acumulado no fim",
                                               "Execuções no horizonte", "Custo de tokens", "Custo fixo", "Custo total",
                                               "Benefício total", "ROI", "Participação dos tokens"]):
    cel(wm, "A%d" % r, rot, f_neg)
cel(wm, "A%d" % (R_F0 - 1), "Fluxo do mês (mês na coluna A)", f_neg)
cel(wm, "A%d" % (R_A0 - 1), "Acumulado (mês na coluna A)", f_neg)
for m in range(61):
    cel(wm, "A%d" % (R_F0 + m), m, f_txt, NUM)
    cel(wm, "A%d" % (R_A0 + m), m, f_txt, NUM)
MESES_RNG = "$A$%d:$A$%d" % (R_F0 + 1, R_F0 + 60)

CASOS: list[tuple[str, str, dict]] = []   # (nome, grupo, {param: fórmula})
for nome_c, col in zip(CENARIOS, COLS):
    CASOS.append((nome_c, "Cenário", {p: "=%s!$%s$%d" % (S_PREM, col, LINHA[p]) for p in PARAM}))
COL_CASO = {}


def col_caso(i):
    return L(2 + i)


def escrever_caso(i, nome_c, grupo, params):
    c = col_caso(i)
    COL_CASO[nome_c] = c
    wm.column_dimensions[c].width = 15
    cel(wm, "%s3" % c, nome_c, f_neg, alin=Alignment(wrap_text=True))
    cel(wm, "%s4" % c, grupo, f_sub)
    for p, r in PR.items():
        fmt = {"adocao_alvo": PCT, "aproveitamento": PCT, "taxa_desconto_anual": PCT, "custo_por_execucao": BRL4,
               "investimento_total": BRL, "custo_fixo_mensal": BRL, "custo_hora": BRL2}.get(p, NUM2)
        cel(wm, "%s%d" % (c, r), params[p], f_link if "!" in params[p] else f_calc, fmt)
    P = {p: "%s$%d" % (c, r) for p, r in PR.items()}
    cel(wm, "%s%d" % (c, R_GANHO), "=MAX({m}-{rv},0)/60*{ch}*{ap}".format(m=P["minutos_por_tarefa"], rv=P["minutos_revisao_humana"],
                                                                      ch=P["custo_hora"], ap=P["aproveitamento"]), f_calc, BRL4)
    cel(wm, "%s%d" % (c, R_TAXAM), "=(1+%s)^(1/12)-1" % P["taxa_desconto_anual"], f_calc, '0.000%')
    g, tm = "%s$%d" % (c, R_GANHO), "%s$%d" % (c, R_TAXAM)
    cel(wm, "%s%d" % (c, R_F0), "=-%s" % P["investimento_total"], f_calc, BRL)
    cel(wm, "%s%d" % (c, R_A0), "=%s%d" % (c, R_F0), f_calc, BRL)
    for m in range(1, 61):
        rf, ra = R_F0 + m, R_A0 + m
        cel(wm, "%s%d" % (c, rf),
            "=IF($A{rf}<={me},{u}*{a}*MIN(1,$A{rf}/{rp})*{t}*{d}*({g}-{cpe})-{fx},0)".format(
                rf=rf, me=P["meses"], u=P["usuarios"], a=P["adocao_alvo"], rp=P["meses_rampa"], t=P["tarefas_por_usuario_dia"],
                d=P["dias_uteis"], g=g, cpe=P["custo_por_execucao"], fx=P["custo_fixo_mensal"]), f_calc, BRL)
        cel(wm, "%s%d" % (c, ra), "=%s%d+%s%d" % (c, ra - 1, c, rf), f_calc, BRL)
    fl = "%s%d:%s%d" % (c, R_F0, c, R_F0 + 60)
    ac = "%s%d:%s%d" % (c, R_A0 + 1, c, R_A0 + 60)
    cel(wm, "%s%d" % (c, R_VPL), "=%s%d+NPV(%s,%s%d:%s%d)" % (c, R_F0, tm, c, R_F0 + 1, c, R_F0 + 60), f_calc_b, BRL)
    cel(wm, "%s%d" % (c, R_TIRM), '=IFERROR(IRR(%s,0.01),IFERROR(IRR(%s,-0.05),"—"))' % (fl, fl), f_calc, '0.00%')
    cel(wm, "%s%d" % (c, R_TIRA), '=IF(ISNUMBER(%s%d),(1+%s%d)^12-1,"—")' % (c, R_TIRM, c, R_TIRM), f_calc_b, PCT)
    cel(wm, "%s%d" % (c, R_PAY), '=IF(%s%d>=0,COUNTIF(%s,"<0")+1,"não se paga")' % (c, R_A0 + 60, ac), f_calc_b, NUM)
    cel(wm, "%s%d" % (c, R_ACUMF), "=%s%d" % (c, R_A0 + 60), f_calc, BRL)
    sramp = "SUMPRODUCT(({ms}<={me})*(({ms}/{rp}<1)*({ms}/{rp})+({ms}/{rp}>=1)))".format(ms=MESES_RNG, me=P["meses"], rp=P["meses_rampa"])
    cel(wm, "%s%d" % (c, R_EXEC), "={u}*{a}*{t}*{d}*{s}".format(u=P["usuarios"], a=P["adocao_alvo"], t=P["tarefas_por_usuario_dia"],
                                                             d=P["dias_uteis"], s=sramp), f_calc, NUM)
    cel(wm, "%s%d" % (c, R_TOK), "=%s%d*%s" % (c, R_EXEC, P["custo_por_execucao"]), f_calc, BRL)
    cel(wm, "%s%d" % (c, R_FIXO), "=%s*MIN(%s,60)" % (P["custo_fixo_mensal"], P["meses"]), f_calc, BRL)
    cel(wm, "%s%d" % (c, R_CUSTO), "=%s+%s%d+%s%d" % (P["investimento_total"], c, R_TOK, c, R_FIXO), f_calc, BRL)
    cel(wm, "%s%d" % (c, R_BEN), "=%s%d*%s" % (c, R_EXEC, g), f_calc, BRL)
    cel(wm, "%s%d" % (c, R_ROI), "=IFERROR((%s%d-%s%d)/%s%d,0)" % (c, R_BEN, c, R_CUSTO, c, R_CUSTO), f_calc, PCT)
    cel(wm, "%s%d" % (c, R_TOKPCT), "=IFERROR(%s%d/%s%d,0)" % (c, R_TOK, c, R_CUSTO), f_calc, PCT)


for i, (n, g_, p_) in enumerate(CASOS):
    escrever_caso(i, n, g_, p_)
BASE = COL_CASO["Base"]
bref = lambda p: "=%s$%d" % (BASE, PR[p])

# ---------- Cenários (precisa das células de equilíbrio antes dos casos de equilíbrio) ----------
wcn = wb.create_sheet(S_CEN, index=6)
titulo(wcn, "Cenários e ponto de equilíbrio",
       "Cada cenário recalcula o fluxo completo (aba Motor). Edite as colunas dos cenários na aba Premissas.")
larguras(wcn, {"A": 50, "B": 16, "C": 16, "D": 16, "E": 16, "F": 4, "G": 60})
cabecalho(wcn, 4, ["Premissas que mudam", *CENARIOS, "", "Leitura"])
mostra = [("Adoção-alvo", "adocao_alvo", PCT), ("Meses de rampa", "meses_rampa", NUM), ("Execuções por usuário por dia", "tarefas_por_usuario_dia", NUM1),
          ("Minutos por tarefa à mão", "minutos_por_tarefa", NUM1), ("Aproveitamento do tempo liberado", "aproveitamento", PCT),
          ("Custo de tokens por execução", "custo_por_execucao", BRL4)]
for i, (rot, p, fmt) in enumerate(mostra):
    r = 5 + i
    cel(wcn, "A%d" % r, rot)
    for j, n in enumerate(CENARIOS):
        cel(wcn, "%s%d" % (L(2 + j), r), "=%s!%s$%d" % (S_MOTOR, COL_CASO[n], PR[p]), f_link, fmt)
cabecalho(wcn, 12, ["Resultado em 36 meses", *CENARIOS, "", ""])
res = [("Payback (mês)", R_PAY, NUM), ("VPL", R_VPL, BRL), ("TIR anual", R_TIRA, PCT), ("ROI no horizonte", R_ROI, PCT),
       ("Custo total", R_CUSTO, BRL), ("Benefício total", R_BEN, BRL), ("Acumulado no fim do horizonte", R_ACUMF, BRL),
       ("Participação dos tokens no custo", R_TOKPCT, PCT)]
for i, (rot, rr, fmt) in enumerate(res):
    r = 13 + i
    cel(wcn, "A%d" % r, rot, f_neg)
    for j, n in enumerate(CENARIOS):
        cel(wcn, "%s%d" % (L(2 + j), r), "=%s!%s$%d" % (S_MOTOR, COL_CASO[n], rr), f_link, fmt, p_kpi if i < 3 else None)
cel(wcn, "G13", "Conservador não se paga no horizonte: por isso o piloto com metas de saída", f_sub)
cel(wcn, "G20", "Tokens: 1% a 4% do custo total. O retorno depende de adoção e valor por tarefa", f_sub)

cabecalho(wcn, 22, ["Composição do custo total", *CENARIOS, "", ""])
comp = [("Investimento", "=%s!{c}$%d" % (S_MOTOR, PR["investimento_total"])), ("Operação (custo fixo)", "=%s!{c}$%d" % (S_MOTOR, R_FIXO)),
        ("Tokens", "=%s!{c}$%d" % (S_MOTOR, R_TOK))]
for i, (rot, f_) in enumerate(comp):
    r = 23 + i
    cel(wcn, "A%d" % r, rot)
    for j, n in enumerate(CENARIOS):
        cel(wcn, "%s%d" % (L(2 + j), r), f_.format(c=COL_CASO[n]), f_link, BRL)

secao(wcn, 28, "Ponto de equilíbrio (demais premissas do cenário Base)", 7)
m = lambda p: "%s!$%s$%d" % (S_MOTOR, BASE, PR[p])
ms = "%s!%s" % (S_MOTOR, MESES_RNG)
me = "MIN(%s,60)" % m("meses")
rp = m("meses_rampa")
tm_ = "%s!$%s$%d" % (S_MOTOR, BASE, R_TAXAM)
ramp = "(({ms}/{rp}<1)*({ms}/{rp})+({ms}/{rp}>=1))".format(ms=ms, rp=rp)
cel(wcn, "A29", "Soma da rampa no horizonte (meses-equivalentes de adoção plena)")
cel(wcn, "B29", "=SUMPRODUCT(({ms}<={me})*{rm})".format(ms=ms, me=me, rm=ramp), f_calc, NUM2)
cel(wcn, "A30", "Idem, descontada")
cel(wcn, "B30", "=SUMPRODUCT(({ms}<={me})*{rm}/(1+{tm})^{ms})".format(ms=ms, me=me, rm=ramp, tm=tm_), f_calc, NUM2)
cel(wcn, "A31", "Fator de anuidade dos custos fixos (descontado)")
cel(wcn, "B31", "=SUMPRODUCT(({ms}<={me})/(1+{tm})^{ms})".format(ms=ms, me=me, tm=tm_), f_calc, NUM2)
cel(wcn, "A32", "Margem por execução (ganho − tokens), cenário Base")
cel(wcn, "B32", "=%s!$%s$%d-%s" % (S_MOTOR, BASE, R_GANHO, m("custo_por_execucao")), f_calc, BRL4)
volume = "{u}*{t}*{d}".format(u=m("usuarios"), t=m("tarefas_por_usuario_dia"), d=m("dias_uteis"))
cabecalho(wcn, 34, ["Para o projeto se pagar…", "Acumulado ≥ 0 no fim", "VPL ≥ 0", "Base hoje", "", "", "Leitura"])
cel(wcn, "A35", "Adoção mínima (com as demais premissas do Base)", f_neg)
cel(wcn, "B35", '=IF(B32>0,({inv}+{me}*{fx})/({v}*B32*B29),"—")'.format(inv=m("investimento_total"), me=me, fx=m("custo_fixo_mensal"), v=volume),
    f_calc_b, PCT, p_kpi)
cel(wcn, "C35", '=IF(B32>0,({inv}+{fx}*B31)/({v}*B32*B30),"—")'.format(inv=m("investimento_total"), fx=m("custo_fixo_mensal"), v=volume),
    f_calc_b, PCT, p_kpi)
cel(wcn, "D35", "=" + m("adocao_alvo"), f_link, PCT)
cel(wcn, "G35", "Abaixo disso, o projeto não recupera o investimento no horizonte", f_sub)
ganho_min_acum = "({inv}+{me}*{fx})/({v}*{a}*B29)+{c}".format(inv=m("investimento_total"), me=me, fx=m("custo_fixo_mensal"), v=volume,
                                                            a=m("adocao_alvo"), c=m("custo_por_execucao"))
ganho_min_vpl = "({inv}+{fx}*B31)/({v}*{a}*B30)+{c}".format(inv=m("investimento_total"), fx=m("custo_fixo_mensal"), v=volume,
                                                          a=m("adocao_alvo"), c=m("custo_por_execucao"))
conv = "*60/({ch}*{ap})+{rv}".format(ch=m("custo_hora"), ap=m("aproveitamento"), rv=m("minutos_revisao_humana"))
cel(wcn, "A36", "Minutos mínimos por tarefa à mão (com as demais premissas do Base)", f_neg)
cel(wcn, "B36", "=(" + ganho_min_acum + ")" + conv, f_calc_b, NUM1, p_kpi)
cel(wcn, "C36", "=(" + ganho_min_vpl + ")" + conv, f_calc_b, NUM1, p_kpi)
cel(wcn, "D36", "=" + m("minutos_por_tarefa"), f_link, NUM1)
cel(wcn, "G36", "Tempo à mão que a tarefa média precisa ter para o projeto se pagar", f_sub)
cel(wcn, "A37", "Usuários ativos no regime pleno (adoção mínima × usuários)")
cel(wcn, "B37", '=IFERROR(B35*%s,"—")' % m("usuarios"), f_calc, NUM)
cel(wcn, "C37", '=IFERROR(C35*%s,"—")' % m("usuarios"), f_calc, NUM)
cel(wcn, "D37", "=%s*%s" % (m("adocao_alvo"), m("usuarios")), f_calc, NUM)
cel(wcn, "A39", "Conferência: acumulado no fim com a adoção mínima (deve dar ≈ 0)")
cel(wcn, "A40", "Conferência: acumulado no fim com os minutos mínimos (deve dar ≈ 0)")

# casos de equilíbrio no Motor (conferem a fórmula fechada)
eq_a = {p: bref(p) for p in PARAM}
eq_a["adocao_alvo"] = "=%s!$B$35" % q(S_CEN)
eq_m = {p: bref(p) for p in PARAM}
eq_m["minutos_por_tarefa"] = "=%s!$B$36" % q(S_CEN)
escrever_caso(4, "Equilíbrio: adoção", "Conferência", eq_a)
escrever_caso(5, "Equilíbrio: minutos", "Conferência", eq_m)
cel(wcn, "B39", "=%s!%s$%d" % (S_MOTOR, COL_CASO["Equilíbrio: adoção"], R_ACUMF), f_link, BRL)
cel(wcn, "B40", "=%s!%s$%d" % (S_MOTOR, COL_CASO["Equilíbrio: minutos"], R_ACUMF), f_link, BRL)

# ---------- Sensibilidade: ±delta em cada premissa (casos no Motor) ----------
ws_ = wb.create_sheet(S_SENS, index=7)
titulo(ws_, "Sensibilidade do VPL (tornado)", "Cada premissa do cenário Base varia para baixo e para cima; as demais ficam no Base.")
larguras(ws_, {"A": 40, "B": 14, "C": 16, "D": 16, "E": 16, "F": 16, "G": 16, "H": 6, "I": 4, "J": 40, "K": 16, "L": 16, "M": 16})
cel(ws_, "A4", "Variação aplicada (±)", f_neg)
cel(ws_, "B4", 0.2, f_in, PCT, p_chave)
nomear("sens_delta", S_SENS, "$B$4")
cel(ws_, "A5", "VPL do cenário Base", f_neg)
cel(ws_, "B5", "=%s!%s$%d" % (S_MOTOR, BASE, R_VPL), f_link, BRL)
SENS = [("Adoção-alvo", "adocao_alvo"), ("Minutos por tarefa à mão", "minutos_por_tarefa"), ("Custo da hora de trabalho", "custo_hora"),
        ("Aproveitamento do tempo liberado", "aproveitamento"), ("Execuções por usuário por dia", "tarefas_por_usuario_dia"),
        ("Colaboradores com acesso", "usuarios"), ("Minutos de conferência humana", "minutos_revisao_humana"),
        ("Meses de rampa", "meses_rampa"), ("Investimento total", "investimento_total"), ("Custo fixo mensal", "custo_fixo_mensal"),
        ("Taxa de desconto", "taxa_desconto_anual"), ("Custo de tokens por execução", "custo_por_execucao")]
cabecalho(ws_, 7, ["Premissa", "Valor no Base", "VPL com −", "VPL com +", "Δ VPL (−)", "Δ VPL (+)", "Amplitude", "Ordem"])
idx = 6
for i, (rot, p) in enumerate(SENS):
    r = 8 + i
    for sinal, nome_s in ((-1, "−"), (1, "+")):
        params = {pp: bref(pp) for pp in PARAM}
        params[p] = "=%s$%d*(1%ssens_delta)" % (BASE, PR[p], "-" if sinal < 0 else "+")
        escrever_caso(idx, "%s %s" % (p, nome_s), "Sensibilidade", params)
        col = COL_CASO["%s %s" % (p, nome_s)]
        cel(ws_, "%s%d" % ("C" if sinal < 0 else "D", r), "=%s!%s$%d" % (S_MOTOR, col, R_VPL), f_link, BRL)
        idx += 1
    cel(ws_, "A%d" % r, rot)
    cel(ws_, "B%d" % r, "=%s!%s$%d" % (S_MOTOR, BASE, PR[p]), f_link, BRL4 if p == "custo_por_execucao" else NUM2)
    cel(ws_, "E%d" % r, "=C%d-$B$5" % r, f_calc, BRL)
    cel(ws_, "F%d" % r, "=D%d-$B$5" % r, f_calc, BRL)
    cel(ws_, "G%d" % r, "=ABS(F%d-E%d)+ROW()/1000000" % (r, r), f_calc, BRL)
    cel(ws_, "H%d" % r, "=RANK(G%d,$G$8:$G$%d)" % (r, 7 + len(SENS)), f_calc, NUM)
NS = len(SENS)
cabecalho(ws_, 7, ["Ordenado por impacto", "Δ VPL (−)", "Δ VPL (+)", "Amplitude"], col0=10)
for k in range(1, NS + 1):
    r = 7 + k
    cel(ws_, "J%d" % r, "=INDEX($A$8:$A$%d,MATCH(%d,$H$8:$H$%d,0))" % (7 + NS, k, 7 + NS), f_calc)
    cel(ws_, "K%d" % r, "=INDEX($E$8:$E$%d,MATCH(%d,$H$8:$H$%d,0))" % (7 + NS, k, 7 + NS), f_calc, BRL)
    cel(ws_, "L%d" % r, "=INDEX($F$8:$F$%d,MATCH(%d,$H$8:$H$%d,0))" % (7 + NS, k, 7 + NS), f_calc, BRL)
    cel(ws_, "M%d" % r, "=ABS(L%d-K%d)" % (r, r), f_calc, BRL)
cel(ws_, "A%d" % (9 + NS), "Leitura: adoção, minutos por tarefa e custo-hora lideram; o preço dos tokens fica no fim.", f_sub)

# ---------- Construir × comprar ----------
wx = wb.create_sheet(S_CXC, index=8)
titulo(wx, "Construir × comprar (36 meses, mesmo volume do cenário em uso)",
       "Preços públicos consultados em " + DATA_CONF + " (links na aba Premissas). Integração com sistemas internos é necessária nas duas opções.")
larguras(wx, {"A": 44, "B": 18, "C": 18, "D": 18, "E": 18, "F": 4, "G": 58})
OP = ["StoneFalcon (construir)", "Microsoft Copilot Studio", "Zapier Agents", "n8n Business + modelos"]
cabecalho(wx, 4, ["Custo no horizonte (R$)", *OP, "", "Como foi calculado"])
cel(wx, "A5", "Execuções no horizonte (cenário em uso)")
for c in "BCDE":
    cel(wx, "%s5" % c, "=SUM(%s!$E$17:$E$76)" % q(S_FLUXO), f_link, NUM)
cel(wx, "A6", "Custo da plataforma/licença por execução")
cel(wx, "B6", "=custo_por_execucao", f_link, BRL4)
cel(wx, "C6", "=copilot_creditos_exec*copilot_usd_credito*cotacao_dolar", f_calc, BRL4)
cel(wx, "D6", "=zapier_atividades_exec*zapier_usd_atividade*cotacao_dolar", f_calc, BRL4)
cel(wx, "E6", "=custo_por_execucao", f_link, BRL4)
cel(wx, "G6", "StoneFalcon e n8n pagam só os tokens; Copilot e Zapier cobram por crédito/atividade (modelo incluso)", f_sub)
cel(wx, "A7", "Uso variável (execuções × custo por execução)")
for c in "BCDE":
    cel(wx, "%s7" % c, "=%s5*%s6" % (c, c), f_calc, BRL)
cel(wx, "A8", "Assinatura fixa da ferramenta")
cel(wx, "B8", 0, f_calc, BRL)
cel(wx, "C8", 0, f_calc, BRL)
cel(wx, "D8", 0, f_calc, BRL)
cel(wx, "E8", "=SUMPRODUCT(%s!$B$17:$B$76*(n8n_eur_mes*cotacao_euro+CEILING(((%s!$E$17:$E$76>n8n_execs_incluidas)*(%s!$E$17:$E$76-n8n_execs_incluidas))/n8n_execs_bloco,1)*n8n_eur_bloco*cotacao_euro))"
    % (q(S_FLUXO), q(S_FLUXO), q(S_FLUXO)), f_calc, BRL)
cel(wx, "G8", "n8n: € 667/mês (40 mil execuções) + blocos de 300 mil a € 4 mil quando excede", f_sub)
cel(wx, "A9", "Desenvolvimento/configuração e governança")
cel(wx, "B9", "=investimento_inicial", f_link, BRL)
for c in "CD":
    cel(wx, "%s9" % c, "=comprar_implantacao", f_link, BRL)
cel(wx, "E9", "=investimento_inicial*n8n_fracao_construcao", f_calc, BRL)
cel(wx, "G9", "Comprar ainda exige SSO, DLP, políticas e trilha de auditoria (premissa a validar)", f_sub)
cel(wx, "A10", "Integração com sistemas internos (4 conectores)")
for c in "BCDE":
    cel(wx, "%s10" % c, "=IF(incluir_modulos=1,modulos_integracao,0)", f_link, BRL)
cel(wx, "A11", "Hospedagem própria")
cel(wx, "B11", "=hospedagem_mensal*MIN(meses,60)", f_calc, BRL)
cel(wx, "C11", 0, f_calc, BRL)
cel(wx, "D11", 0, f_calc, BRL)
cel(wx, "E11", "=hospedagem_mensal*MIN(meses,60)", f_calc, BRL)
cel(wx, "G11", "SaaS (Copilot, Zapier) não tem hospedagem própria; n8n Business é self-hosted", f_sub)
cel(wx, "A12", "Sustentação (time que administra)")
for c in "BCDE":
    cel(wx, "%s12" % c, "=sustentacao_mensal*MIN(meses,60)", f_calc, BRL)
cel(wx, "A13", "Custo total no horizonte", f_neg)
for c in "BCDE":
    cel(wx, "%s13" % c, "=SUM(%s7:%s12)" % (c, c), f_calc_b, BRL, p_kpi)
cel(wx, "A14", "Diferença para o StoneFalcon")
for c in "CDE":
    cel(wx, "%s14" % c, "=%s13-$B$13" % c, f_calc, BRL)
cel(wx, "A15", "Conferência: StoneFalcon = custo total do fluxo (deve dar 0)")
cel(wx, "B15", "=B13-%s!$B$10" % q(S_FLUXO), f_calc, BRL)
cel(wx, "A16", "Execuções no horizonte em que construir empata com esta opção", f_neg)
for c in "CD":
    cel(wx, "%s16" % c, '=IF(%s6>$B$6,(($B$9+$B$11)-(%s9+%s11))/(%s6-$B$6),"—")' % (c, c, c, c), f_calc_b, NUM)
cel(wx, "A17", "… em múltiplos do volume do cenário em uso")
for c in "CD":
    cel(wx, "%s17" % c, '=IFERROR(%s16/%s5,"—")' % (c, c), f_calc_b, '0.0"×"')
cel(wx, "G16", "Acima desse volume, construir sai mais barato; o custo por execução comprado é 15 a 30× maior", f_sub)

cabecalho(wx, 19, ["Critério (tabela do desafio e além)", *OP, "", ""])
quali = [
    ("Quem constrói", "Qualquer colaborador, sob a infraestrutura oficial da Stone", "Colaborador no ecossistema Microsoft",
     "Colaborador isolado (risco de shadow IT)", "Perfil técnico (fluxos em nós)"),
    ("Governança", "Catálogo governado, revisão em quatro olhos, pausa de emergência, trilha encadeada por hash",
     "Políticas do tenant (Power Platform)", "Limitada; controles de conta", "Depende do que a equipe montar"),
    ("Escala e integração", "Conectores nativos aos sistemas internos com as permissões de quem disparou",
     "Conectores Microsoft; internos sob medida", "Apps SaaS; internos sob medida", "Muito flexível, exige engenharia"),
    ("Segurança e compliance", "Guardrails silenciosos (mascaramento, isolamento de instrução embutida), dados ficam na Stone",
     "DLP da Microsoft; dados no tenant", "Dados passam pela Zapier (EUA)", "Self-hosted; guardrails por conta própria"),
    ("Custo por execução", "Tokens com roteador por passo (Haiku/Sonnet)", "Créditos por resposta/ação", "Atividades por ação",
     "Execução + tokens"),
    ("Dependência de fornecedor", "Baixa (troca de modelo no roteador)", "Alta", "Alta", "Média"),
]
for i, linha_q in enumerate(quali):
    r = 20 + i
    for j, v in enumerate(linha_q):
        cel(wx, "%s%d" % (L(1 + j), r), v, f_neg if j == 0 else f_txt, alin=quebra)
    wx.row_dimensions[r].height = 42
cel(wx, "A27", "Leitura: no volume do Base, comprar SaaS custa um pouco menos em 36 meses, porque evita o desenvolvimento. "
               "Mas o custo por execução é 15 a 30× maior: com ~1,5× o volume do Base, construir fica mais barato. E comprar não elimina "
               "integração nem governança, cria dependência e tira os dados da Stone. A decisão é estratégica, não só de custo.", f_sub)

# ---------- Resumo para slides ----------
wr = wb.create_sheet(S_RES, index=9)
titulo(wr, "Resumo para slides (fonte única da apresentação)",
       "Os slides só copiam números desta aba. Tudo aqui é fórmula. Coluna D diz de onde vem cada número.")
larguras(wr, {"A": 6, "B": 54, "C": 18, "D": 50})
cabecalho(wr, 4, ["#", "Número", "Valor", "Origem"])
MC = lambda n, rr: "=%s!%s$%d" % (S_MOTOR, COL_CASO[n], rr)
numeros = [
    ("investimento_inicial", "Investimento inicial (desenvolvimento + implantação + 15%)", "=investimento_inicial", BRL, "Investimento (CAPEX)!D14"),
    ("modulos", "Módulos de integração (4 conectores)", "=modulos_integracao", BRL, "Investimento (CAPEX)!E24"),
    ("investimento_total", "Investimento total", "=%s!$%s$%d" % (S_MOTOR, BASE, PR["investimento_total"]), BRL, "Motor (Base)"),
    ("custo_fixo", "Operação mensal (hospedagem + sustentação)", "=%s!$%s$%d" % (S_MOTOR, BASE, PR["custo_fixo_mensal"]), BRL, "Operação (OPEX)!C10"),
    ("cpe_premissa", "Custo de tokens por execução: premissa do Base", "=%s!$%s$%d" % (S_MOTOR, BASE, PR["custo_por_execucao"]), BRL4, "Premissas"),
    ("cpe_modelado", "Custo de tokens por execução: modelado (agentes da demo)", "=%s!$D$40" % q(S_TOK), BRL4, "Tokens!D40"),
    ("tokens_min", "Tokens no custo total: menor entre os cenários",
     "=MIN(%s)" % ",".join("%s!%s$%d" % (S_MOTOR, COL_CASO[n], R_TOKPCT) for n in CENARIOS), PCT, "Cenários (linha 20)"),
    ("tokens_max", "Tokens no custo total: maior entre os cenários",
     "=MAX(%s)" % ",".join("%s!%s$%d" % (S_MOTOR, COL_CASO[n], R_TOKPCT) for n in CENARIOS), PCT, "Cenários (linha 20)"),
    ("economia_roteador", "Economia do roteador (mix de agentes da demo)", "=%s!$E$31" % q(S_TOK), PCT, "Tokens!E31"),
    ("payback_base", "Payback do cenário Base (mês)", MC("Base", R_PAY), NUM, "Cenários!B13"),
    ("vpl_base", "VPL do cenário Base (36 meses, 12% a.a.)", MC("Base", R_VPL), BRL, "Cenários!B14"),
    ("tir_base", "TIR anual do cenário Base", MC("Base", R_TIRA), PCT, "Cenários!B15"),
    ("roi_base", "ROI do cenário Base no horizonte", MC("Base", R_ROI), PCT, "Cenários!B16"),
    ("payback_medido", "Payback do Base medido (mês)", MC("Base medido", R_PAY), NUM, "Cenários!E13"),
    ("vpl_medido", "VPL do Base medido", MC("Base medido", R_VPL), BRL, "Cenários!E14"),
    ("vpl_conservador", "VPL do Conservador", MC("Conservador", R_VPL), BRL, "Cenários!C14"),
    ("payback_conservador", "Payback do Conservador", MC("Conservador", R_PAY), NUM, "Cenários!C13"),
    ("vpl_otimista", "VPL do Otimista", MC("Otimista", R_VPL), BRL, "Cenários!D14"),
    ("payback_otimista", "Payback do Otimista (mês)", MC("Otimista", R_PAY), NUM, "Cenários!D13"),
    ("adocao_minima", "Adoção mínima para se pagar em 36 meses (acumulado ≥ 0)", "=%s!$B$35" % q(S_CEN), PCT, "Cenários!B35"),
    ("adocao_minima_vpl", "Adoção mínima para VPL ≥ 0", "=%s!$C$35" % q(S_CEN), PCT, "Cenários!C35"),
    ("minutos_minimos", "Minutos mínimos por tarefa para se pagar em 36 meses", "=%s!$B$36" % q(S_CEN), NUM1, "Cenários!B36"),
    ("custo_36m_stonefalcon", "Construir: custo em 36 meses", "=%s!$B$13" % q(S_CXC), BRL, "Construir × comprar!B13"),
    ("custo_36m_copilot", "Comprar (Copilot Studio): custo em 36 meses", "=%s!$C$13" % q(S_CXC), BRL, "Construir × comprar!C13"),
    ("empate_copilot_x", "Volume em que construir empata com o Copilot (× o Base)", "=%s!$C$17" % q(S_CXC), '0.0"×"', "Construir × comprar!C17"),
    ("cpe_copilot", "Copilot Studio: custo por execução", "=%s!$C$6" % q(S_CXC), BRL4, "Construir × comprar!C6"),
    ("piloto_tranche1", "Pedido: tranche 1 (plataforma + 2 conectores + piloto)", "=%s!$E$32" % q(S_CAPEX), BRL, "Investimento (CAPEX)!E32"),
    ("piloto_meses", "Duração do piloto (meses)", "=piloto_meses", NUM, "Premissas"),
    ("escalada_demo", "Taxa de escalada para humano (histórico sintético)", "=taxa_escalada", PCT, "Premissas"),
    ("minutos_demo", "Minutos à mão, média ponderada dos 3 agentes", "=%s!$D$12" % q(S_BEN), NUM1, "Benefícios!D12"),
]
RES_ROW = {}
for i, (chave_n, rot, f_, fmt, orig) in enumerate(numeros):
    r = 5 + i
    RES_ROW[chave_n] = r
    cel(wr, "A%d" % r, chave_n, Font(name=F, size=8, color="76847D"))
    cel(wr, "B%d" % r, rot)
    cel(wr, "C%d" % r, f_, f_link, fmt)
    cel(wr, "D%d" % r, orig, f_sub)
    nomear("res_" + chave_n, S_RES, "$C$%d" % r)
fim_num = 5 + len(numeros)

# dados dos 4 gráficos
G1 = fim_num + 2
secao(wr, G1, "Gráfico 1: resultado acumulado por cenário (R$), meses 0 a 36", 4)
cabecalho(wr, G1 + 1, ["Mês", *CENARIOS], col0=1)
wr.column_dimensions["E"].width = 16
for mm in range(37):
    r = G1 + 2 + mm
    cel(wr, "A%d" % r, mm, f_txt, NUM)
    for j, n in enumerate(CENARIOS):
        cel(wr, "%s%d" % (L(2 + j), r), "=%s!%s%d" % (S_MOTOR, COL_CASO[n], R_A0 + mm), f_link, BRL)
G2 = G1 + 2 + 37 + 1
secao(wr, G2, "Gráfico 2: composição do custo total no horizonte (R$)", 4)
cabecalho(wr, G2 + 1, ["Componente", *CENARIOS], col0=1)
for i, rot in enumerate(["Investimento", "Operação", "Tokens"]):
    r = G2 + 2 + i
    cel(wr, "A%d" % r, rot)
    for j in range(4):
        cel(wr, "%s%d" % (L(2 + j), r), "=%s!%s%d" % (q(S_CEN), L(2 + j), 23 + i), f_link, BRL)
G3 = G2 + 6
secao(wr, G3, "Gráfico 3: tornado do VPL (Δ em relação ao Base, R$)", 4)
cabecalho(wr, G3 + 1, ["Premissa", "Δ VPL (−)", "Δ VPL (+)"], col0=1)
for k in range(NS):
    r = G3 + 2 + k
    cel(wr, "A%d" % r, "=%s!J%d" % (S_SENS, 8 + k), f_link)
    cel(wr, "B%d" % r, "=%s!K%d" % (S_SENS, 8 + k), f_link, BRL)
    cel(wr, "C%d" % r, "=%s!L%d" % (S_SENS, 8 + k), f_link, BRL)
G4 = G3 + 2 + NS + 1
secao(wr, G4, "Gráfico 4: custo de tokens por execução, com e sem roteador (R$)", 4)
cabecalho(wr, G4 + 1, ["Agente", "Com roteador", "Tudo no Sonnet"], col0=1)
for i in range(4):
    r = G4 + 2 + i
    cel(wr, "A%d" % r, "=%s!A%d" % (S_TOK, 28 + i), f_link)
    cel(wr, "B%d" % r, "=%s!B%d" % (S_TOK, 28 + i), f_link, BRL4)
    cel(wr, "C%d" % r, "=%s!C%d" % (S_TOK, 28 + i), f_link, BRL4)
for nome_g, ref in (("g1", "$A$%d:$E$%d" % (G1 + 1, G1 + 38)), ("g2", "$A$%d:$E$%d" % (G2 + 1, G2 + 4)),
                    ("g3", "$A$%d:$C$%d" % (G3 + 1, G3 + 1 + NS)), ("g4", "$A$%d:$C$%d" % (G4 + 1, G4 + 5))):
    nomear("res_" + nome_g, S_RES, ref)


# ---------- gráficos nativos ----------
def grafico_acumulado(ws, ancora, aba_dados, linha_cab, col_mes=1):
    ch = LineChart()
    ch.title = "Resultado acumulado em 36 meses por cenário (R$)"
    ch.y_axis.title = "R$"
    ch.x_axis.title = "Mês"
    ch.height, ch.width = 9, 18
    dados = Reference(aba_dados, min_col=col_mes + 1, max_col=col_mes + 4, min_row=linha_cab, max_row=linha_cab + 37)
    ch.add_data(dados, titles_from_data=True)
    ch.set_categories(Reference(aba_dados, min_col=col_mes, min_row=linha_cab + 1, max_row=linha_cab + 37))
    cores = [VERDE, "B3261E", ROSA, "275EC4"]
    for s, cor in zip(ch.series, cores):
        s.graphicalProperties.line.solidFill = cor
        s.graphicalProperties.line.width = 22000
        s.smooth = False
    ch.y_axis.number_format = '#,##0'
    ch.x_axis.tickLblSkip = 6
    ws.add_chart(fechar_grafico(ch), ancora)


def grafico_composicao(ws, ancora, aba, linha_cab):
    ch = BarChart()
    ch.type, ch.grouping, ch.overlap = "col", "stacked", 100
    ch.title = "Composição do custo total no horizonte (R$)"
    ch.height, ch.width = 8, 14
    dados = Reference(aba, min_col=1, max_col=5, min_row=linha_cab + 1, max_row=linha_cab + 3)
    ch.add_data(dados, titles_from_data=True, from_rows=True)
    ch.set_categories(Reference(aba, min_col=2, max_col=5, min_row=linha_cab))
    for s, cor in zip(ch.series, [VERDE_ESC, "76847D", ROSA]):
        s.graphicalProperties.solidFill = cor
    ch.y_axis.number_format = '#,##0'
    ws.add_chart(fechar_grafico(ch), ancora)


def grafico_tornado(ws, ancora, aba, linha_cab, n, col0=1):
    ch = BarChart()
    ch.type, ch.grouping, ch.overlap, ch.gapWidth = "bar", "clustered", 100, 40
    ch.title = "Sensibilidade do VPL (±20% em cada premissa)"
    ch.height, ch.width = 9, 16
    dados = Reference(aba, min_col=col0 + 1, max_col=col0 + 2, min_row=linha_cab, max_row=linha_cab + n)
    ch.add_data(dados, titles_from_data=True)
    ch.set_categories(Reference(aba, min_col=col0, min_row=linha_cab + 1, max_row=linha_cab + n))
    for s, cor in zip(ch.series, ["B3261E", VERDE]):
        s.graphicalProperties.solidFill = cor
    ch.x_axis.scaling.orientation = "maxMin"
    ch.y_axis.number_format = '#,##0'
    ws.add_chart(fechar_grafico(ch), ancora)


def grafico_roteador(ws, ancora, aba, linha_cab):
    ch = BarChart()
    ch.type, ch.grouping = "col", "clustered"
    ch.title = "Custo de tokens por execução (R$): com e sem roteador"
    ch.height, ch.width = 8, 16
    dados = Reference(aba, min_col=2, max_col=3, min_row=linha_cab, max_row=linha_cab + 4)
    ch.add_data(dados, titles_from_data=True)
    ch.set_categories(Reference(aba, min_col=1, min_row=linha_cab + 1, max_row=linha_cab + 4))
    for s, cor in zip(ch.series, [VERDE, "76847D"]):
        s.graphicalProperties.solidFill = cor
    ch.y_axis.number_format = '0.00'
    ws.add_chart(fechar_grafico(ch), ancora)


grafico_acumulado(wr, "G4", wr, G1 + 1)
grafico_composicao(wr, "G24", wr, G2 + 1)
grafico_tornado(wr, "G42", wr, G3 + 1, NS)
grafico_roteador(wr, "G62", wr, G4 + 1)
grafico_acumulado(wcn, "A43", wr, G1 + 1)
grafico_composicao(wcn, "G22", wcn, 22)
grafico_tornado(ws_, "J%d" % (10 + NS), ws_, 7, NS, col0=10)
grafico_roteador(wt, "A43", wr, G4 + 1)

# =====================================================================
# 1. Leia-me
# =====================================================================
wl = wb.create_sheet("Leia-me", index=0)
titulo(wl, "StoneFalcon: análise financeira (F8)", "Plataforma institucional de agentes de IA. Protótipo acadêmico (UFSC / StoneLab); não é um produto da Stone.")
larguras(wl, {"A": 28, "B": 110})
blocos = [
    ("Objetivo", "Mostrar quanto custa, quando se paga e o que move o resultado do StoneFalcon, com premissas rastreáveis. "
                 "A apresentação (F9) só copia números da aba 'Resumo para slides'."),
    ("Como usar", "1) Escolha o cenário em uso na célula D4 da aba Premissas. 2) Edite só as células em azul da aba Premissas. "
                  "3) Todas as abas recalculam. Os cenários lado a lado (aba Cenários) usam as colunas E a H da aba Premissas."),
    ("Legenda de cores", "Azul = premissa editável · preto = fórmula · verde = vem de outra aba · fundo amarelo = premissa-chave "
                         "ou o que muda no cenário · fundo rosa = resultado principal."),
    ("Status das premissas", "Documento da equipe (docs/custos-estimados.txt) · Tabela oficial (preços da Anthropic) · "
                             "Premissa a validar (o piloto mede) · Protótipo (estimativa do código) · Histórico sintético da demo · "
                             "Pesquisa de preço público (com link e data)."),
    ("Consistência", "As fórmulas do fluxo são as de backend/app/finance/calculadora.py. O script entregaveis/gerador/"
                     "testar_consistencia.py compara este arquivo recalculado com calculadora.projetar() nos cenários, "
                     "mês a mês, com tolerância de R$ 1."),
    ("Data de conferência", DATA_CONF + ". Antes de apresentar: conferir preços da Anthropic, câmbio (PTAX de 13/11/2026 = R$ 5,6518; "
                            "o modelo usa R$ 5,52 como o protótipo), faixas do n8n e da hospedagem e os preços de mercado."),
    ("Reconciliação de tokens", "Com as premissas do próprio documento, o custo de Q&A dá ≈ R$ 7,7 mil/mês (US$ 1.394). O valor do "
                                "documento (R$ 8,5 mil) aparece ao converter pela cotação do euro (6,12): provável troca de moeda. "
                                "Ver aba Tokens."),
    ("Limites honestos", "1) O histórico de 30 dias do protótipo é SINTÉTICO (gerado para a demo), não medição: o cenário 'Base medido' "
                         "usa os tamanhos e o roteador do código, não tráfego real. 2) Como a calculadora, o fluxo põe o investimento "
                         "no mês 0 e o benefício desde o mês 1; os 5 meses de construção atrasariam o payback. 3) Retrabalho evitado e "
                         "custo evitado de AI Engineer ficam fora do fluxo (aba Benefícios). 4) Preços de mercado mudam: conferir."),
    ("Abas", "Leia-me · Premissas · Investimento (CAPEX) · Operação (OPEX) · Tokens · Benefícios · Fluxo de caixa · Cenários · "
             "Sensibilidade · Construir × comprar · Resumo para slides · Motor (auxiliar: um fluxo completo por coluna)."),
    ("Nome da aba de resumo", "O plano pedia 'Resumo p/ slides'; o Excel não aceita '/' em nome de aba, por isso 'Resumo para slides'."),
    ("Uso de IA", "Planilha gerada por script (entregaveis/gerador/gerar_excel.py) escrito com o Claude (Anthropic), a pedido da equipe."),
]
for i, (k, v) in enumerate(blocos):
    r = 4 + i
    cel(wl, "A%d" % r, k, f_sec, alin=Alignment(vertical="top"))
    cel(wl, "B%d" % r, v, f_txt, alin=quebra)
    wl.row_dimensions[r].height = 44
cel(wl, "A17", "Exemplo de edição", f_sec)
cel(wl, "B17", "Na aba Premissas, mude adocao_alvo do Base (célula E da linha 'Fração que usa agentes') de 25% para 20% e veja "
               "Cenários, Sensibilidade e Resumo mudarem.", f_txt, alin=quebra)
wl.row_dimensions[17].height = 30

# ordem final das abas
ordem = ["Leia-me", S_PREM, S_CAPEX, S_OPEX, S_TOK, S_BEN, S_FLUXO, S_CEN, S_SENS, S_CXC, S_RES, S_MOTOR]
wb._sheets = [wb[n] for n in ordem]
for ws in wb.worksheets:
    ws.sheet_properties.tabColor = {S_RES: ROSA, S_PREM: VERDE, S_MOTOR: "A0A0A0"}.get(ws.title, "0B6342")
wb.active = 0
wb.calculation.fullCalcOnLoad = True
SAIDA.parent.mkdir(parents=True, exist_ok=True)
wb.save(SAIDA)
print("ok", SAIDA)
