"""Arquivos e processos do estado inicial da demo para o plugin Arquivos e Planilhas (o REAL). Dados fictícios.

Cada persona tem um uso de verdade (v8/11): um arquivo semeado e um processo que usa um bloco do plugin.
O plugin nasce integrado, para os processos da demo já poderem usá-lo.

  Marina  lê o FAQ do atendimento para responder lojistas
  Rafael  lê a lista de chargebacks e registra a decisão da triagem (restrita: pede confirmação)
  Carla   lê a tabela de benefícios (confidencial: CPF e e-mail protegidos)
  Thiago  lê os pedidos de troca pendentes e marca o pedido tratado
  Lucas   mantém o registro de incidentes, onde um processo anota quando um sistema cai
  Helena  exporta o resumo de Finanças para uma planilha (botão na página de Finanças)
"""
from __future__ import annotations

from sqlmodel import Session

from ..core.identidade import PERSONAS, Classificacao
from ..plugins import arquivos
from ..plugins import servico as plugins

I, C, R = int(Classificacao.INTERNA), int(Classificacao.CONFIDENCIAL), int(Classificacao.RESTRITA)


def _tabela(colunas: list[str], linhas: list[tuple]) -> tuple[list[str], list[dict]]:
    return colunas, [dict(zip(colunas, l)) for l in linhas]


FAQ_C, FAQ_L = _tabela(["assunto", "pergunta", "resposta", "prazo"], [
    ("Estorno", "Em quanto tempo o estorno cai para o cliente?", "O estorno de venda no crédito aparece na fatura em até 2 faturas; no débito, em até 5 dias úteis.", "5 dias úteis"),
    ("Estorno", "Posso estornar uma venda de outro mês?", "Sim, até 90 dias da data da venda, pelo aplicativo ou pelo atendimento.", "90 dias"),
    ("Taxas", "Como a taxa de antecipação é calculada?", "A taxa de antecipação depende do prazo e do plano do lojista; a simulação aparece antes de confirmar.", "imediato"),
    ("Maquininha", "Minha maquininha não liga, o que faço?", "Conecte o carregador original por 30 minutos; se não ligar, abra a troca pelo atendimento.", "2 dias úteis"),
    ("Maquininha", "Como troco o modelo da minha maquininha?", "A troca por defeito é gratuita até 12 meses depois da entrega; a troca de modelo tem custo do plano.", "3 dias úteis"),
    ("Repasse", "Quando recebo o repasse das vendas?", "O repasse acontece no dia útil seguinte para o débito e conforme o plano para o crédito.", "1 dia útil"),
    ("Contestação", "O que é uma contestação?", "É quando o portador do cartão não reconhece a compra; o lojista tem 10 dias para enviar a defesa.", "10 dias"),
    ("Conta", "Como altero os dados do meu cadastro?", "No aplicativo, em Conta > Dados cadastrais; mudança de CNPJ pede documento pelo atendimento.", "1 dia útil"),
])
BENEFICIOS_C, BENEFICIOS_L = _tabela(["matricula", "nome", "cpf", "email", "beneficio", "valor_mensal"], [
    ("C501", "Bruno Tavares", "529.982.247-25", "bruno.tavares@exemplo.com.br", "VR", 900),
    ("C501", "Bruno Tavares", "529.982.247-25", "bruno.tavares@exemplo.com.br", "Plano de saúde", 650),
    ("C502", "Aline Souza", "111.444.777-35", "aline.souza@exemplo.com.br", "VR", 900),
    ("C502", "Aline Souza", "111.444.777-35", "aline.souza@exemplo.com.br", "Auxílio creche", 400),
])
CHARGEBACKS_C, CHARGEBACKS_L = _tabela(["lojista_id", "lojista", "decisao", "contestacoes_semana", "valor_total"], [
    ("L1001", "Ótica Visão Clara", "sem ação", 1, 320),
    ("L1002", "Padaria Pão Dourado", "acompanhar", 2, 540),
    ("L1003", "Eletrônicos Relâmpago", "pendente", 10, 210000),
])
PEDIDOS_C, PEDIDOS_L = _tabela(["codigo", "lojista_id", "modelo", "relato", "status"], [
    ("P-101", "L1001", "Maquininha Pro", "Tela trincada", "tratado"),
    ("P-102", "L1002", "Maquininha Mini", "Não carrega", "pendente"),
    ("P-103", "L1003", "Maquininha Smart", "Tela preta", "pendente"),
    ("P-104", "L1001", "Maquininha Pro", "Teclado falhando", "pendente"),
])
INCIDENTES_C, INCIDENTES_L = _tabela(["sistema", "descricao", "severidade"], [
    ("Cadastro de lojistas", "Tempo esgotado nas consultas por 12 minutos; a fila de chamados cresceu.", "alta"),
    ("Mensageria interna", "Avisos por e-mail atrasaram; o reenvio automático resolveu.", "media"),
])
FINANCAS_C, FINANCAS_L = _tabela(["processo", "execucoes", "custo_brl", "ganho_brl"], [
    ("Resposta a dúvidas de lojistas", 452, 31.4, 1248.0),
    ("Triagem de chargebacks", 177, 28.9, 1530.0),
])

# (nome, dono, classificação, áreas, colunas, linhas)
ARQUIVOS = [
    ("faq-atendimento.csv", "marina", I, ["atendimento", "logistica"], FAQ_C, FAQ_L),
    ("chargebacks-triagem.csv", "rafael", R, ["risco"], CHARGEBACKS_C, CHARGEBACKS_L),
    ("beneficios-rh.csv", "carla", C, ["pessoas"], BENEFICIOS_C, BENEFICIOS_L),
    ("pedidos-troca.csv", "thiago", I, ["logistica", "atendimento"], PEDIDOS_C, PEDIDOS_L),
    ("registro-incidentes.csv", "lucas", I, ["engenharia", "logistica"], INCIDENTES_C, INCIDENTES_L),
    ("financas-resumo-inicial.csv", "helena", I, ["gestao"], FINANCAS_C, FINANCAS_L),
]

_LOJ = {"id": "lojista_id", "rotulo": "Lojista", "tipo": "lojista", "ajuda": "Escolha o lojista pelo nome."}


def _b(id: str, tipo: str, titulo: str, depende_de: list[str] | None = None, **campos) -> dict:
    return {"id": id, "tipo": tipo, "titulo": titulo, "depende_de": depende_de or [], **campos}


def _base(nome: str, objetivo: str, area: str, minutos: int) -> dict:
    return {"nome": nome, "objetivo": objetivo, "area": area, "minutos_manual": minutos,
            "limites": {"max_custo_brl": 2.0, "max_chamadas_modelo": 20}}


# um processo por persona, com um bloco "Arquivos e Planilhas" de verdade: (criador, compartilhar com, definição)
PROCESSOS = [
    ("marina", [], {
        **_base("Consulta ao FAQ de atendimento", "Achar no FAQ da equipe a resposta de um assunto, sem abrir três sistemas.", "atendimento", 6),
        "campos": [{"id": "assunto", "rotulo": "Assunto", "tipo": "opcao", "opcoes": ["Estorno", "Taxas", "Maquininha", "Repasse", "Contestação", "Conta"],
                    "exemplo": "Estorno"}],
        "blocos": [_b("faq", "dados", "Ler as respostas do FAQ para o assunto", ferramenta="arquivos_ler_linhas",
                      entrada={"arquivo": "faq-atendimento.csv", "coluna": "assunto", "valor": "{{entrada.assunto}}", "limite": 10})]}),
    ("rafael", [], {
        **_base("Registro da decisão de triagem", "Ver o lojista na lista de chargebacks e registrar a decisão da triagem.", "risco", 10),
        "campos": [_LOJ, {"id": "lojista", "rotulo": "Nome do lojista", "tipo": "texto", "exemplo": "Eletrônicos Relâmpago"},
                   {"id": "decisao", "rotulo": "Decisão", "tipo": "opcao", "opcoes": ["reter repasse", "acompanhar", "sem ação"], "exemplo": "reter repasse"}],
        "blocos": [_b("lista", "dados", "Ler a linha do lojista na lista", ferramenta="arquivos_buscar_linha",
                      entrada={"arquivo": "chargebacks-triagem.csv", "coluna": "lojista_id", "valor": "{{entrada.lojista_id}}"}),
                   _b("registro", "plugin", "Registrar a decisão (pede a sua confirmação)", ["lista"], ferramenta="arquivos_adicionar_linha",
                      entrada={"arquivo": "chargebacks-triagem.csv",
                               "valores": '{"lojista_id": "{{entrada.lojista_id}}", "lojista": "{{entrada.lojista}}", "decisao": "{{entrada.decisao}}"}'})]}),
    ("carla", [], {
        **_base("Consulta de benefícios do colaborador", "Ler os benefícios de um colaborador na tabela de RH, com CPF e e-mail protegidos.", "pessoas", 8),
        "campos": [{"id": "colaborador_id", "rotulo": "Colaborador", "tipo": "colaborador", "ajuda": "Você mesmo, ou outra pessoa se o seu perfil permitir."}],
        "blocos": [_b("beneficios", "dados", "Ler os benefícios do colaborador", ferramenta="arquivos_ler_linhas",
                      entrada={"arquivo": "beneficios-rh.csv", "coluna": "matricula", "valor": "{{entrada.colaborador_id}}", "limite": 10})]}),
    ("thiago", [], {
        **_base("Pedidos de troca pendentes", "Ver os pedidos de troca pendentes e marcar o pedido tratado na planilha.", "logistica", 7),
        "campos": [{"id": "codigo", "rotulo": "Código do pedido", "tipo": "texto", "exemplo": "P-102"}],
        "blocos": [_b("pendentes", "dados", "Ler os pedidos pendentes", ferramenta="arquivos_ler_linhas",
                      entrada={"arquivo": "pedidos-troca.csv", "coluna": "status", "valor": "pendente", "limite": 20}),
                   _b("marcar", "plugin", "Marcar o pedido como tratado", ["pendentes"], ferramenta="arquivos_atualizar_linha",
                      entrada={"arquivo": "pedidos-troca.csv", "coluna_chave": "codigo", "valor_chave": "{{entrada.codigo}}",
                               "valores": '{"status": "tratado"}'})]}),
    ("thiago", ["engenharia"], {
        **_base("Registro de incidente de sistema", "Quando um sistema cai, anotar o incidente no registro da engenharia.", "logistica", 5),
        "campos": [{"id": "sistema", "rotulo": "Sistema fora do ar", "tipo": "texto", "exemplo": "Cadastro de lojistas"},
                   {"id": "descricao", "rotulo": "O que aconteceu", "tipo": "texto_longo", "exemplo": "Consultas com tempo esgotado."},
                   {"id": "severidade", "rotulo": "Severidade", "tipo": "opcao", "opcoes": ["baixa", "media", "alta"], "exemplo": "alta"}],
        "blocos": [_b("registro", "plugin", "Anotar o incidente no registro", ferramenta="arquivos_adicionar_linha",
                      entrada={"arquivo": "registro-incidentes.csv",
                               "valores": '{"sistema": "{{entrada.sistema}}", "descricao": "{{entrada.descricao}}", "severidade": "{{entrada.severidade}}"}'})]}),
]


def preparar(s: Session) -> None:
    """Integra o plugin (como a Marina, que é criadora) e cria os arquivos da demo. Vem ANTES dos processos da demo, porque
    alguns (a triagem de incidentes do Lucas, a revisão de custo da Helena) já leem esses arquivos."""
    try:
        plugins.integrar(s, PERSONAS["marina"], arquivos.PLUGIN_ID, "Estado inicial da demonstração.")
    except plugins.ErroPlugin:
        pass
    for nome, dono, classificacao, areas, colunas, linhas in ARQUIVOS:
        arquivos.criar_pelo_sistema(s, PERSONAS[dono], nome, colunas, linhas, classificacao, areas, demo=True)


def semear(s: Session) -> None:
    """Cria os processos da demo que usam o plugin Arquivos e Planilhas (o plugin e os arquivos já vêm de `preparar`)."""
    from ..processos.blueprint import ProcessoBlueprint
    from ..processos.tipo import ciclo as ciclo_processos
    for criador, areas, definicao in PROCESSOS:
        pessoa = PERSONAS[criador]
        p = ciclo_processos.criar(s, pessoa, ProcessoBlueprint.model_validate(definicao), "Estado inicial: usa o plugin Arquivos e Planilhas.")
        p = ciclo_processos.publicar(s, pessoa, p.id)
        if areas:
            ciclo_processos.compartilhar(s, pessoa, p.id, areas)
