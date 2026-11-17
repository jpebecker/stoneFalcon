"""Perguntas prováveis da banca, por persona e por tema, com a resposta curta e a tela que serve de prova.

`prova.perfil` é a pessoa com quem abrir a tela; `prova.rota` é a tela; `prova.roteiro`/`prova.passo` levam
ao passo do roteiro em que a prova aparece. Respostas curtas, para falar em até 30 segundos.
"""
from ..finance.premissas import Premissas
from .catalogo import ROTEIROS

_PR = Premissas()


def _conf(rid: str) -> str:
    return ("%.1f" % ROTEIROS[rid].to_be["conferencia_min"]).replace(".", ",")


TEMAS = {
    "seguranca": "Segurança e privacidade",
    "custo": "Custo e ROI",
    "escala": "Escala e governança",
    "diferencial": "Por que não um low-code genérico",
    "processo": "Processo e valor",
}


def _q(id, persona, tema, pergunta, resposta, perfil, rota, rotulo, roteiro=None, passo=None):
    return {"id": id, "persona": persona, "tema": tema, "pergunta": pergunta, "resposta": resposta,
            "prova": {"perfil": perfil, "rota": rota, "rotulo": rotulo, "roteiro": roteiro or persona, "passo": passo}}


PERGUNTAS = [
    # ---- Marina
    _q("marina-1", "marina", "processo", "Quanto tempo a Marina realmente economiza?",
       "O AS IS de %d min é hipótese que vamos validar com a área; o TO BE usa o tempo medido do agente mais %s min de conferência humana. "
       "O cartão diz qual número é medido e qual é hipótese." % (ROTEIROS["marina"].as_is["minutos"], _conf("marina")),
       "marina", "/roteiro/marina?etapa=resultado", "Cartão AS IS × TO BE", passo="medir"),
    _q("marina-2", "marina", "seguranca", "O que o modelo vê do lojista?",
       "Nada de dado pessoal: CPF, CNPJ, e-mail e telefone viram marcadores antes de qualquer modelo. A linha do tempo da execução mostra o que foi mascarado.",
       "marina", "/estudio", "Linha do tempo do sandbox com marcadores", passo="testar"),
    _q("marina-3", "marina", "diferencial", "A Marina precisa de alguém da TI para criar o agente?",
       "Não. Ela descreve o processo em português e o Estúdio monta passos, ferramentas, risco e custo. Risco baixo publica na hora.",
       "marina", "/estudio", "Estúdio: descrição virando agente", passo="criar"),
    _q("marina-4", "marina", "seguranca", "E se o texto do chamado tiver uma instrução maliciosa?",
       "Conteúdo de sistemas externos é tratado como informação, nunca como instrução: a plataforma isola o texto suspeito e registra o evento.",
       "marina", "/demo/helpdesk?chamado=4816&perfil=marina", "Helpdesk: chamado com instrução embutida", passo="extensao"),
    _q("marina-5", "marina", "custo", "Quanto custa cada resposta?",
       "Centavos: o passo de redação usa o Haiku, e o custo real aparece em cada execução.",
       "marina", "/execucoes", "Lista de execuções com custo", passo="usar"),
    # ---- Rafael
    _q("rafael-1", "rafael", "seguranca", "O agente pode bloquear um lojista sozinho?",
       "Não. A retenção de repasse é ação sensível: a execução para e só continua depois da confirmação do analista, registrada na auditoria.",
       "rafael", "/agentes/{agente:Triagem de chargebacks}", "Execução parada pedindo confirmação", passo="usar"),
    _q("rafael-2", "rafael", "seguranca", "Como provar quem aprovou a retenção?",
       "A trilha de auditoria é encadeada por hash: ninguém altera um evento sem quebrar a cadeia, e o selo mostra isso.",
       "helena", "/auditoria", "Auditoria: cadeia íntegra e evento de confirmação", passo="auditoria"),
    _q("rafael-3", "rafael", "custo", "Por que usar o modelo mais caro na análise?",
       "O roteador escolhe por tarefa e explica por quê: a análise de risco pesa vários fatores e sobe para o Sonnet; o resto fica no Haiku.",
       "rafael", "/agentes/{agente:Triagem de chargebacks}", "Passo da análise: por que este modelo", passo="usar"),
    _q("rafael-4", "rafael", "escala", "Um agente de risco alto vai ao ar sem revisão?",
       "Nunca. Agente de risco alto vai para a Segurança, que aprova com parecer; a pausa de emergência também barra ações pendentes.",
       "lucas", "/revisoes", "Fila de revisão da Segurança", passo="revisao"),
    _q("rafael-5", "rafael", "processo", "Quantos lojistas ele tria por dia agora?",
       "O AS IS de %d min por lojista é hipótese; o TO BE mede o tempo do agente e inclui a confirmação humana. A produtividade vem dessa diferença." % ROTEIROS["rafael"].as_is["minutos"],
       "rafael", "/roteiro/rafael?etapa=resultado", "Cartão AS IS × TO BE", passo="medir"),
    # ---- Carla
    _q("carla-1", "carla", "seguranca", "O modelo vê o CPF dos colaboradores?",
       "Não. CPF e e-mail da ficha viram marcadores antes do modelo; só o sistema interno que tem classificação suficiente recebe o dado real.",
       "carla", "/estudio", "Sandbox: ficha com marcadores", passo="testar"),
    _q("carla-2", "carla", "seguranca", "Isso está de acordo com a LGPD?",
       "O protótipo aplica minimização (só marcadores no modelo), controle de acesso por área e trilha de auditoria. A conformidade formal depende de DLP real e do jurídico em produção.",
       "lucas", "/auditoria", "Evento de RH sem dado pessoal", passo="auditoria"),
    _q("carla-3", "carla", "escala", "Outra área pode usar o agente de RH?",
       "Não por padrão: a ferramenta de ficha é restrita à área de Pessoas, e o agente só roda com as permissões de quem o dispara.",
       "marina", "/ferramentas", "Catálogo: quem pode usar cada ferramenta"),
    _q("carla-4", "carla", "processo", "O que a Carla deixa de fazer?",
       "As perguntas repetidas de férias e benefícios; ela passa a tratar só as exceções.",
       "carla", "/roteiro/carla?etapa=resultado", "Cartão AS IS × TO BE", passo="medir"),
    # ---- Thiago
    _q("thiago-1", "thiago", "diferencial", "O que a plataforma faz que uma automação comum não faz?",
       "Passos em paralelo, ferramentas governadas por permissão e classificação, risco calculado e auditoria nativos. O Thiago só descreve o processo.",
       "thiago", "/estudio", "Canvas com passos paralelos", passo="testar"),
    _q("thiago-2", "thiago", "escala", "Como entra um sistema novo, como o estoque?",
       "A Engenharia registra o conector uma vez no catálogo, com classificação e áreas; qualquer criador autorizado passa a usá-lo, sem código por agente.",
       "lucas", "/ferramentas", "Catálogo com a ferramenta de estoque"),
    _q("thiago-3", "thiago", "processo", "E se o estoque estiver baixo?",
       "O agente consulta o estoque junto com o cadastro e a regra, e já avisa no chamado que o estoque está baixo para oferecer um modelo equivalente.",
       "thiago", "/agentes/{agente:Troca de maquininha com estoque}", "Resposta do agente com estoque baixo", passo="usar"),
    _q("thiago-4", "thiago", "custo", "Isso fica caro com muitas trocas?",
       "O cadastro, a regra e o estoque são consultas diretas, sem IA e sem custo de modelo; só a redação do chamado e do aviso usa o Haiku.",
       "thiago", "/roteiro/thiago?etapa=resultado", "Custo por troca medido", passo="medir"),
    # ---- Lucas
    _q("lucas-1", "lucas", "escala", "Como governar centenas de agentes sem aumentar o time?",
       "Engenharia governa o catálogo e as revisões de risco alto, não cada agente. Agente de risco baixo vai ao ar sozinho dentro dos guardrails.",
       "lucas", "/revisoes", "Fila de revisão só com risco alto", passo="revisao"),
    _q("lucas-2", "lucas", "escala", "O que acontece quando um sistema integrado cai?",
       "O agente escala para humano com o motivo, o alerta chega ao dono e à Engenharia, e a nota de saúde cai. Quando o sistema volta, o alerta fecha sozinho.",
       "lucas", "/alertas", "Alerta crítico aberto", passo="alerta"),
    _q("lucas-3", "lucas", "seguranca", "Dá para parar um agente na hora?",
       "Sim, com um clique. A pausa de emergência também barra ações que já estavam pendentes de confirmação.",
       "lucas", "/agentes/{agente:Resposta a dúvidas de lojistas}", "Botão Pausar", passo="pausar"),
    _q("lucas-4", "lucas", "diferencial", "Por que não deixar cada time usar um low-code genérico?",
       "Porque cada ferramenta paralela vira shadow IT sem permissão por classificação, sem mascaramento e sem trilha. Aqui isso é nativo e invisível.",
       "helena", "/auditoria", "Auditoria de todos os agentes", passo=None),
    # ---- Helena
    _q("helena-1", "helena", "custo", "Qual o retorno e em quanto tempo?",
       "O painel mostra ROI e payback; a calculadora deixa a banca mudar adoção e premissas. Os números de histórico são cenário e estão sinalizados.",
       "helena", "/painel", "Painel executivo: ROI e payback", passo="painel"),
    _q("helena-2", "helena", "custo", "Quanto o roteador economiza?",
       "O trabalho simples vai ao Haiku e o Sonnet só entra quando precisa; o percentual exato do período aparece em Finanças (no histórico de demonstração, que é cenário).",
       "helena", "/financas", "Finanças: economia do roteador", passo="financas"),
    _q("helena-3", "helena", "custo", "E se o custo da IA explodir?",
       "Cada agente tem orçamento mensal com corte automático e alerta de uso; cada execução tem limite de custo e de chamadas.",
       "helena", "/financas", "Orçamento por agente", passo="financas"),
    _q("helena-4", "helena", "processo", "Os números são reais?",
       "Cada número diz se é medido na execução, premissa ou hipótese. O AS IS vem de hipóteses a validar com a área em um piloto.",
       "helena", "/roteiro/helena?etapa=resultado", "Consolidado com a origem de cada número", passo="medir"),
    _q("helena-5", "helena", "escala", "Isso escala para %s colaboradores?" % format(_PR.usuarios, ",").replace(",", "."),
       "A calculadora usa o documento de custos da equipe (investimento, módulos e sustentação), %d colaboradores e rampa de adoção de %d meses; em produção, Postgres e SSO." % (_PR.usuarios, _PR.meses_rampa),
       "helena", "/financas/calculadora", "Calculadora com 6.000 colaboradores", passo="calculadora"),
]


def listar(persona: str | None = None, tema: str | None = None) -> list[dict]:
    return [q for q in PERGUNTAS if (not persona or q["persona"] == persona) and (not tema or q["tema"] == tema)]
