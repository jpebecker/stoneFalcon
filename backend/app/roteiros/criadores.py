"""Roteiros v8 das quatro pessoas que criam: criar o agente trabalhador -> montar o processo -> testar -> publicar -> usar.

O fluxo de blocos de cada processo vem de seed/catalogo.py (o mesmo do estado inicial da demo); aqui ele vai no `preenche`
do passo "montar" com o NOME do agente, que a tela troca pelo id do agente que a pessoa acabou de criar.
"""
from __future__ import annotations

from ..seed.catalogo import NOME_AGENTE, NOME_PROCESSO, processo
from .catalogo import Passo, Roteiro, _ctx, _medir, _min


def _criar(persona: str, chave: str, descricao: str, fala: str) -> Passo:
    return Passo("criar", "Criar o agente trabalhador", persona, "/estudio",
                 "Clique em “Montar meu agente”: o texto vem preenchido. O Estúdio monta UM agente, que faz uma tarefa. Confira o nome e clique em “Publicar”.",
                 fala, {"descricao": descricao, "nome_agente": NOME_AGENTE[chave]}, alvo="acao-montar")


def _montar(persona: str, chave: str, fala: str, acao: str, slack: bool = False) -> Passo:
    return Passo("montar", "Montar o processo", persona, "/processos/novo", acao, fala,
                 {"processo": processo(chave, NOME_AGENTE[chave], slack=slack, por_nome=True)})


def _alerta(persona: str, acao: str, fala: str) -> Passo:
    """O passo "veja e trate o seu alerta" de cada roteiro: o cenário nasce de uma regra real (a tela chama o endpoint do cenário)."""
    return Passo("alerta", "Veja e trate o seu alerta", persona, "/alertas", acao, fala, {"cenario_alerta": True}, alvo="acao-alerta")


def _processo(chave: str) -> str:
    return "{processo:%s}" % NOME_PROCESSO[chave]


MARINA = Roteiro(
    id="marina", persona="marina", titulo="Marina responde lojistas sem consultar três sistemas",
    processo="Resposta a dúvidas de lojistas", agente_nome=NOME_AGENTE["duvida"], sem=frozenset({"duvida"}),
    resumo="Um agente trabalhador, um processo de blocos, uso na plataforma e na extensão, com o ganho de tempo medido.",
    as_is={"minutos": 8, "hipotese": True,
           "dor": "Responde as mesmas dúvidas consultando três sistemas.",
           "passos": ["Lê o chamado do lojista", "Abre o cadastro no backoffice", "Procura a política na wiki",
                      "Redige a resposta", "Revisa o tom", "Responde"],
           "erros": ["Política desatualizada na wiki", "Prazo prometido fora da regra"]},
    to_be={"conferencia_min": 1.3,
           "passos": ["Seleciona o texto do chamado (extensão)", "O processo consulta cadastro e política em paralelo",
                      "O agente redige a resposta citando a regra", "Marina confere e copia"],
           "nota": "Conferência humana de ≈ %s min (hipótese) somada ao tempo medido do processo." % _min(1.3)},
    valor=["Tempo por tarefa", "Respostas por dia", "Retrabalho por política errada", "Custo por resposta (Haiku)"],
    passos=(
        _ctx("marina", "", "A Marina responde dezenas de dúvidas por dia, e cada uma pede três sistemas. É daí que sai o tempo."),
        _criar("marina", "duvida", "Quando um lojista pergunta algo no chamado, eu abro o cadastro dele, procuro a regra na política "
               "de atendimento e escrevo a resposta com o tom certo. Levo uns 8 minutos por chamado.",
               "Ela conta o processo como contaria a um colega novo. O Estúdio monta o trabalhador: um agente que lê e escreve. Sem código."),
        _montar("marina", "duvida", "O processo é o fluxo da Marina: cadastro e política rodam juntos, e o agente escreve a resposta. O agente é o trabalhador; o processo é o fluxo.",
                "Abra o processo: os blocos já vêm montados com o seu agente. Confira e siga."),
        Passo("testar", "Testar o processo no sandbox", "marina", "/processos/novo",
              "Escolha o lojista pelo nome e rode o teste: a entrada já vem preenchida.",
              "Dados pessoais viram marcadores antes de qualquer modelo. A linha do tempo mostra cada bloco e o agente que rodou dentro dele.",
              {"entrada": {"lojista_id": "L1001", "pergunta": "Em quanto tempo o estorno cai para o cliente?"}}, alvo="acao-executar"),
        Passo("publicar", "Publicar o processo", "marina", "/processos/novo",
              "Clique em “Publicar”: risco baixo, vai ao ar na hora, sem fila.",
              "Risco baixo publica direto: os guardrails da plataforma já cobrem este processo.", alvo="acao-publicar"),
        Passo("usar", "Usar o processo na plataforma", "marina", "/processos/" + _processo("duvida"),
              "Execute com o lojista e a dúvida já preenchidos.",
              "Cadastro e política rodam juntos; o texto final cita a regra.",
              {"entrada": {"lojista_id": "L1002", "pergunta": "Qual o prazo de estorno de uma venda no débito?"}}, alvo="acao-executar"),
        Passo("extensao", "Usar pela extensão no helpdesk", "marina", "/demo/helpdesk?chamado=4812&perfil=marina",
              "No helpdesk, selecione o texto do chamado e clique em “Perguntar ao StoneFalcon”.",
              "O mesmo processo, agora dentro da ferramenta onde ela já trabalha.", externa=True),
        _alerta("marina", "O processo ficou mais lento que o normal: assuma o alerta e abra o processo pela ação do alerta.",
                "Ela não configurou nada: a plataforma comparou as últimas execuções com as de sempre e avisou a dona do processo. "
                "Assumir mostra a todos quem está cuidando."),
        _medir("marina", "O tempo e o custo desta execução são medidos; o AS IS é hipótese, e dizemos qual é qual."),
    ), duracao_min=6)

RAFAEL = Roteiro(
    id="rafael", persona="rafael", titulo="Rafael tria chargebacks sem bloquear o lojista errado",
    processo="Triagem de chargebacks", agente_nome=NOME_AGENTE["triagem"], sem=frozenset({"triagem"}),
    resumo="Processo com bloco em paralelo, condição de risco, pausa para confirmação humana e auditoria.",
    as_is={"minutos": 25, "hipotese": True,
           "dor": "Triagem manual de contestações, com risco de bloquear a pessoa errada.",
           "passos": ["Exporta as contestações", "Cruza com o cadastro", "Consulta a política de risco", "Decide",
                      "Abre o chamado", "Pede o bloqueio por e-mail"],
           "erros": ["Bloqueio indevido de lojista bom", "Contestação esquecida na exportação"]},
    to_be={"conferencia_min": 3.9,
           "passos": ["Informa o lojista", "Cadastro e contestações rodam juntos", "O agente analisa o risco (o roteador explica o modelo)",
                      "Se o risco é alto: chamado aberto", "A retenção pausa e pede a confirmação do Rafael"],
           "nota": "Inclui a confirmação humana obrigatória (≈ %s min, hipótese)." % _min(3.9)},
    valor=["Tempo por triagem", "Lojistas triados por dia", "Falsos bloqueios evitados", "Custo por triagem"],
    passos=(
        _ctx("rafael", "", "O Rafael tem acesso restrito e uma ação que não pode errar: reter o repasse de um lojista."),
        _criar("rafael", "triagem", "Todo dia olho as contestações de um lojista, cruzo com o cadastro e com a política de risco e decido "
               "se abro chamado ou bloqueio o repasse. Levo uns 25 minutos por lojista.",
               "Ele descreve o que faz hoje; o Estúdio monta o trabalhador que avalia o risco. Quem age em outro sistema é o processo."),
        _montar("rafael", "triagem", "No processo, a ação sensível fica à vista: só se o risco for alto o fluxo abre o chamado e propõe reter o repasse, e a retenção pede a confirmação dele.",
                "Abra o processo: cadastro e contestações em paralelo, o agente, a condição de risco e a retenção."),
        Passo("testar", "Testar com um lojista sem risco", "rafael", "/processos/novo",
              "Rode o teste com o lojista sem contestações: a condição segue o caminho “não” e nada é proposto.",
              "Mesmo processo, outro lojista: sem sinal de risco, o ramo da retenção aparece como pulado.",
              {"entrada": {"lojista_id": "L1001"}}, alvo="acao-executar"),
        Passo("publicar", "Enviar o processo para a revisão da Segurança", "rafael", "/processos/novo",
              "Clique em “Enviar para revisão”: risco alto não vai direto ao ar.",
              "O processo toca dado restrito e uma ação sensível. Por isso passa pelos quatro olhos.", alvo="acao-publicar"),
        Passo("revisao", "Revisão de segurança (Lucas)", "lucas", "/revisoes",
              "O Lucas lê o que mudou e aprova com o parecer preenchido.",
              "O Lucas não constrói processos: ele aprova só os de risco alto.",
              {"parecer": "Retenção de repasse protegida por confirmação humana; acesso restrito à área de risco. Aprovado."}, alvo="acao-aprovar"),
        Passo("usar", "Executar com o lojista suspeito", "rafael", "/processos/" + _processo("triagem"),
              "Execute com o lojista de risco alto e confirme a retenção quando o processo parar.",
              "Cadastro e contestações rodam juntos; o agente analisa e o roteador explica o modelo. "
              "A retenção só acontece depois da confirmação do Rafael.",
              {"entrada": {"lojista_id": "L1003"}}, alvo="acao-executar"),
        Passo("extensao", "Usar pela extensão no helpdesk", "rafael", "/demo/helpdesk?chamado=4815&perfil=rafael",
              "No helpdesk, selecione o texto do chamado do lojista e peça a triagem pela extensão.",
              "A mesma triagem, a partir do chamado que chegou da Operação.", externa=True),
        Passo("auditoria", "Provar na trilha de auditoria", "helena", "/auditoria",
              "Mostre o selo de cadeia íntegra e abra a confirmação da retenção.",
              "Quem confirmou, quando e com que dado: tudo na trilha encadeada por hash."),
        _alerta("rafael", "A triagem está falhando: assuma o alerta e pause o processo pela ação do alerta, com o motivo.",
                "4 das últimas 10 execuções escalaram: o alerta chega ao dono do processo, e a pausa de emergência fica a um clique."),
        _medir("rafael", "Tempo, custo e a confirmação humana aparecem medidos."),
    ), duracao_min=8)

CARLA = Roteiro(
    id="carla", persona="carla", titulo="Carla orienta férias e benefícios sem expor dado pessoal",
    processo="Orientação de férias e benefícios", agente_nome=NOME_AGENTE["ferias"], sem=frozenset({"ferias"}),
    resumo="Dado confidencial mascarado antes do modelo, num processo de blocos, e prova na auditoria.",
    as_is={"minutos": 10, "hipotese": True,
           "dor": "Perguntas repetidas sobre férias e benefícios.",
           "passos": ["Recebe a pergunta", "Abre a ficha do colaborador", "Consulta a política de RH", "Responde"],
           "erros": ["Saldo de férias lido da planilha errada", "Regra de benefício desatualizada"]},
    to_be={"conferencia_min": 0.9,
           "passos": ["O colaborador pergunta", "O processo usa a ficha (dado mascarado para o modelo)", "O agente responde com a regra"],
           "nota": "Conferência humana de ≈ %s min (hipótese)." % _min(0.9)},
    valor=["Tempo por pergunta", "Perguntas resolvidas sem a Carla", "Zero dado pessoal no log (auditoria)"],
    passos=(
        _ctx("carla", "", "A Carla lida com dado confidencial todos os dias: CPF, e-mail e saldo de cada colaborador."),
        _criar("carla", "ferias", "Os colaboradores perguntam quantos dias de férias têm e como pedir; eu olho a ficha do colaborador "
               "e a política de RH e respondo. Gasto uns 10 minutos por pergunta.",
               "O Estúdio já escolhe a ferramenta de RH, que só a área de Pessoas pode usar."),
        _montar("carla", "ferias", "Ficha e política rodam juntas; o agente responde sem nunca ver o dado pessoal.",
                "Abra o processo: os blocos já vêm montados com o seu agente."),
        Passo("testar", "Testar com o colaborador escolhido por nome", "carla", "/processos/novo",
              "Escolha o colaborador pelo nome e rode o teste.",
              "O CPF e o e-mail da ficha viram marcadores: o modelo nunca vê o dado real.",
              {"entrada": {"colaborador_id": "C501", "pergunta": "Quantos dias de férias eu tenho e como peço?"}}, alvo="acao-executar"),
        Passo("publicar", "Publicar o processo", "carla", "/processos/novo",
              "Clique em “Publicar”: leitura confidencial é risco médio e vai ao ar direto.",
              "Leitura confidencial é risco médio: publica direto, com o acesso limitado à área.", alvo="acao-publicar"),
        Passo("usar", "Usar o processo", "carla", "/processos/" + _processo("ferias"),
              "Execute com o colaborador e a pergunta já preenchidos.",
              "A resposta vem com o saldo da ficha e a regra da política, sem dado pessoal no texto.",
              {"entrada": {"colaborador_id": "C501", "pergunta": "Quantos dias de férias eu tenho e como peço?"}}, alvo="acao-executar"),
        Passo("auditoria", "Provar que nada vazou", "lucas", "/auditoria",
              "Abra o evento da ferramenta de RH: só há marcadores no lugar do CPF e do e-mail.",
              "A auditoria registra o que foi mascarado, nunca o dado em si."),
        _alerta("carla", "O processo chegou a 88% do orçamento do mês: assuma o alerta e revise o orçamento pela ação do alerta.",
                "O orçamento tem alerta a 80% e corte a 100%: a Carla age antes de o processo parar."),
        _medir("carla", "O ganho vem sem abrir mão da privacidade."),
    ), duracao_min=5)

THIAGO = Roteiro(
    id="thiago", persona="thiago", titulo="Thiago troca maquininhas com cadastro, regra e estoque em paralelo",
    processo="Troca de maquininha", agente_nome=NOME_AGENTE["troca"], sem=frozenset({"troca"}),
    resumo="Blocos em paralelo, o plugin do Slack integrado, chamado na logística e aviso ao canal, num processo de blocos.",
    as_is={"minutos": 12, "hipotese": True,
           "dor": "A troca exige cadastro, estoque e chamado em sistemas diferentes.",
           "passos": ["Confere o cadastro", "Confere a regra de troca", "Verifica o estoque", "Abre o chamado na logística",
                      "Avisa o lojista", "Avisa o canal da logística no Slack"],
           "erros": ["Troca fora da regra", "Modelo sem estoque descoberto tarde"]},
    to_be={"conferencia_min": 1.9,
           "passos": ["Cadastro, regra e estoque rodam juntos", "O agente resume o pedido", "Chamado aberto na logística",
                      "Aviso publicado no canal #logistica (plugin do Slack)"],
           "nota": "Conferência humana de ≈ %s min (hipótese)." % _min(1.9)},
    valor=["Tempo por troca", "Trocas processadas por dia", "Erros de troca fora da regra"],
    passos=(
        _ctx("thiago", "", "O Thiago faz a ponte entre atendimento e logística; a troca de uma maquininha passa por três sistemas."),
        Passo("integrar", "Integrar o plugin do Slack", "thiago", "/plugins/slack",
              "Abra o plugin do Slack e clique em “Integrar”: risco baixo, entra na hora.",
              "Marketplace é a aquisição, Catálogo é a governança: o Slack é interno, então o criador integra sozinho e a "
              "ferramenta passa a aparecer no Catálogo, com a origem “plugin Slack”.", alvo="acao-integrar"),
        _criar("thiago", "troca", "Quando o lojista pede troca de maquininha eu confiro o cadastro, a regra de troca e o estoque do modelo "
               "ao mesmo tempo, abro o chamado na logística, aviso o lojista e aviso o canal da logística no Slack. Levo uns 12 minutos.",
               "A ferramenta de estoque entrou no catálogo uma vez; o Slack acabou de entrar pelo marketplace. O Thiago só descreve."),
        _montar("thiago", "troca", "Três blocos de dados na mesma coluna rodam ao mesmo tempo: o tempo é o do mais lento, não a soma. O aviso ao canal é um bloco do plugin do Slack.",
                "Abra o processo: cadastro, regra e estoque em paralelo, o agente, o chamado e o aviso no Slack.", slack=True),
        Passo("testar", "Testar no sandbox", "thiago", "/processos/novo",
              "Escolha o lojista e o modelo e rode o teste: os três primeiros blocos rodam juntos.",
              "Três blocos na mesma coluna rodam ao mesmo tempo: o tempo é o do mais lento, não a soma.",
              {"entrada": {"lojista_id": "L1002", "modelo": "Maquininha Pro", "relato": "A tela ficou preta e a maquininha não liga mais."}}, alvo="acao-executar"),
        Passo("publicar", "Publicar o processo", "thiago", "/processos/novo",
              "Clique em “Publicar”: risco médio, vai ao ar direto.",
              "Escrita em outro sistema é risco médio: publica direto.", alvo="acao-publicar"),
        Passo("usar", "Usar o processo com estoque baixo", "thiago", "/processos/" + _processo("troca"),
              "Execute com o modelo de estoque baixo: o chamado já sai avisando.",
              "O estoque do modelo Smart está baixo e o agente diz isso no resumo do chamado.",
              {"entrada": {"lojista_id": "L1003", "modelo": "Maquininha Smart", "relato": "A tela ficou preta e a maquininha não liga mais."}}, alvo="acao-executar"),
        Passo("canal", "Ver o aviso no canal do Slack", "thiago", "/plugins/slack",
              "Abra a página do Slack: a mensagem do processo aparece no canal #logistica.",
              "A página consolidada do plugin mostra quem usa, quantas chamadas, o custo e a janela do canal, "
              "com a mensagem que o processo acabou de publicar."),
        _alerta("thiago", "O estoque ficou lento: assuma o alerta e abra o sistema em Saúde.",
                "O processo de trocas consulta o estoque do modelo; o alerta leva direto ao sistema que atrasa o processo."),
        _medir("thiago", "Três consultas em paralelo, o chamado aberto e o canal da logística avisado sem ninguém digitar."),
    ), duracao_min=6)
