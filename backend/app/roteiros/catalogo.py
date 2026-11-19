"""Roteiros de demonstração: uma jornada pré-determinada por persona.

Cada roteiro conta a mesma história, do mesmo jeito sempre:
  persona e processo AS IS -> processo TO BE -> criar/testar/publicar/usar -> valor medido.
(O roteiro da Helena termina nas Perguntas da Ferramenta, que só a aba dela mostra.)

Os tempos AS IS partem do `minutos_manual` dos agentes de exemplo e são HIPÓTESES até um piloto
com a área (cada um está marcado). O que é medido na execução (tempo do agente e custo em tokens)
vem das execuções reais do roteiro; a conferência humana é premissa.

Cada passo diz ao front: quem é a pessoa (`perfil`), em que tela estamos (`rota`), o que fazer (`acao`),
o que o apresentador pode dizer (`fala`) e o que já vem preenchido (`preenche`). Na rota, `{agente:Nome}` ou `{processo:Nome}`
é resolvido pelo front para o agente com esse nome.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Passo:
    id: str
    titulo: str
    perfil: str
    rota: str
    acao: str
    fala: str
    preenche: dict = field(default_factory=dict)
    externa: bool = False      # abre fora do app (ex.: o helpdesk fictício)

    def publico(self) -> dict:
        return {"id": self.id, "titulo": self.titulo, "perfil": self.perfil, "rota": self.rota, "acao": self.acao,
                "fala": self.fala, "preenche": self.preenche, "externa": self.externa}


@dataclass(frozen=True)
class Roteiro:
    id: str
    persona: str
    titulo: str
    processo: str
    resumo: str
    as_is: dict            # {minutos, passos[], dor, erros[], hipotese}
    to_be: dict            # {passos[], conferencia_min, nota}
    valor: list[str]       # o que será medido
    passos: tuple[Passo, ...]
    agente_nome: str | None = None      # agente que a persona cria/usa no roteiro
    sem: frozenset = frozenset()        # agentes da semente que a persona cria ao vivo
    preparar: str | None = None         # gancho que deixa o estado exato do roteiro
    duracao_min: int = 4
    apresentacao: bool = False          # roteiro do pitch: só o CoE vê na lista (a persona entra por ele)

    def publico(self) -> dict:
        return {"id": self.id, "persona": self.persona, "apresentacao": self.apresentacao, "titulo": self.titulo, "processo": self.processo,
                "resumo": self.resumo, "as_is": self.as_is, "to_be": self.to_be, "valor": self.valor,
                "agente_nome": self.agente_nome, "duracao_min": self.duracao_min,
                "passos": [p.publico() for p in self.passos]}


def _min(v: float) -> str:
    return ("%.1f" % v).replace(".", ",")


def _ctx(persona: str, texto: str, fala: str) -> Passo:
    return Passo("contexto", "Conhecer a persona e o processo de hoje", persona, "/roteiro/" + persona,
                 "Apresente a persona e leia o processo AS IS: passos, tempo e erros típicos.", fala)


def _medir(persona: str, fala: str) -> Passo:
    return Passo("medir", "Medir: AS IS × TO BE", persona, "/roteiro/%s?etapa=resultado" % persona,
                 "Abra o cartão com o tempo e o custo da execução real e o ganho projetado.", fala)


def _perguntas(persona: str) -> Passo:
    return Passo("perguntas", "Perguntas da Ferramenta", persona, "/perguntas?persona=" + persona,
                 "Mostre as perguntas prováveis sobre a ferramenta e a tela que serve de prova.",
                 "Estas são as perguntas que mais esperamos; cada resposta tem a tela de prova ao lado.")


LUCAS = Roteiro(
    id="lucas", persona="lucas", titulo="Lucas governa sem headcount para cada time",
    processo="Governança do catálogo e dos agentes", agente_nome=None, sem=frozenset(), preparar="versao_em_revisao",
    resumo="Revisão de segurança (quatro olhos), sistema fora do ar, alerta, pausa de emergência e normalização.",
    as_is={"minutos": 0, "hipotese": True,
           "dor": "Cada time pede um agente e a Engenharia constrói: semanas de fila e shadow IT quando trava.",
           "passos": ["O time pede um agente", "A Engenharia constrói", "Semanas de fila", "Shadow IT quando a fila trava"],
           "erros": ["Agente sem revisão rodando fora do radar"]},
    to_be={"conferencia_min": 0,
           "passos": ["Mantém o catálogo de ferramentas uma vez", "Revisa só os processos e agentes de risco alto",
                      "Recebe o alerta quando um sistema cai", "Pausa um agente com um clique"],
           "nota": "Sem código novo por agente."},
    valor=["Agentes e processos publicados sem código novo", "Tempo de revisão", "Incidentes detectados pelo alerta"],
    passos=(
        _ctx("lucas", "", "O Lucas não tem headcount para construir um agente por time. Ele governa o catálogo."),
        Passo("revisao", "Revisar o agente de risco alto", "lucas", "/revisoes",
              "Leia o que mudou na versão e aprove com o parecer preenchido.",
              "Ele revisa só o que importa: o que mudou, quais ferramentas e quais riscos.",
              {"parecer": "Mudança restrita ao aviso por Slack, sem novas ferramentas sensíveis. Retenção continua com confirmação humana. Aprovado."}),
        Passo("falha", "Simular um sistema fora do ar", "lucas", "/ferramentas",
              "Em “Consultar cadastro do lojista”, simule fora do ar.",
              "Um sistema integrado cai. Nenhum agente precisa ser editado."),
        Passo("usar", "Um processo sofre com a falha", "marina", "/processos/{processo:Resposta a dúvidas de lojistas}",
              "Execute com a dúvida preenchida: a execução escala para humano, com o motivo.",
              "O processo não inventa: escala no bloco que depende do sistema, com o motivo registrado.",
              {"entrada": {"lojista_id": "L1001", "pergunta": "Em quanto tempo o estorno cai para o cliente?"}}),
        Passo("alerta", "O alerta chega", "lucas", "/alertas",
              "Mostre o alerta crítico no sino e na tela de alertas.",
              "O dono do agente e a Engenharia recebem o alerta sozinhos."),
        Passo("pausar", "Pausa de emergência", "lucas", "/processos/{processo:Resposta a dúvidas de lojistas}",
              "Clique em “Pausar” e informe o motivo: um clique.",
              "A pausa também barra ações já pendentes."),
        Passo("normalizar", "Normalizar o sistema", "lucas", "/ferramentas",
              "Volte o sistema ao normal: o alerta fecha sozinho.",
              "Quando o sistema volta, o alerta fecha sozinho e o processo pode ser retomado."),
        _medir("lucas", "Agentes e processos publicados sem código novo e incidentes detectados pelo alerta."),
    ), duracao_min=5)

HELENA = Roteiro(
    id="helena", persona="helena", titulo="Helena prova o retorno e controla o custo da IA",
    processo="Gestão do CoE de IA", agente_nome=None, sem=frozenset(),
    resumo="Painel com os 5 critérios da banca, economia do roteador, orçamento e a calculadora ligada aos processos.",
    as_is={"minutos": 0, "hipotese": True,
           "dor": "Não sabe quanto a IA custa nem quanto devolve; cada time usa uma ferramenta diferente.",
           "passos": ["Pergunta custo a cada time", "Soma planilhas", "Não consegue provar o retorno"],
           "erros": ["Custo de IA invisível", "Ferramentas duplicadas"]},
    to_be={"conferencia_min": 0,
           "passos": ["Painel com os 5 critérios da banca", "AS IS × TO BE por processo", "Economia do roteador",
                      "Orçamento com corte", "Calculadora de ROI"],
           "nota": "Números do histórico de demonstração são cenário, não medição."},
    valor=["ROI", "Payback", "Custo por área", "Economia do roteador"],
    passos=(
        _ctx("helena", "", "A Helena precisa provar o retorno da IA e manter o custo sob controle."),
        Passo("painel", "Painel executivo", "helena", "/painel",
              "Mostre os 5 critérios da banca: tempo, custo, produtividade, erros e ROI.",
              "Os cinco critérios do desafio, medidos nas execuções."),
        Passo("financas", "Finanças e economia do roteador", "helena", "/financas",
              "Mostre a economia do roteador e o gráfico por modelo.",
              "O roteador manda o trabalho simples para o Haiku e só usa o Sonnet quando precisa."),
        Passo("calculadora", "Calculadora ligada aos processos", "helena", "/financas/calculadora",
              "Carregue os números de um processo e mude a adoção.",
              "A calculadora parte dos processos dos roteiros: mude a adoção e veja payback, VPL e TIR."),
        _medir("helena", "Consolidado dos quatro processos, com a origem de cada número."),
        _perguntas("helena"),
    ), duracao_min=4)

_PLANILHA = "local:pedidos-troca"
_AGENTE_PLANILHA = "{processo:Troca de maquininha pela planilha}"

PITCH = Roteiro(
    id="pitch", persona="thiago", titulo="Pitch v7: da planilha do Thiago ao Mapa de IA da Helena",
    processo="Troca de maquininha por planilha (rotina semanal)", agente_nome="Troca de maquininha pela planilha",
    sem=frozenset(), preparar="pitch", apresentacao=True,
    resumo="Uma planilha aberta no navegador vira agente pela extensão, ganha rotina semanal, aparece ao vivo no Mapa de IA e "
           "mostra vários provedores de IA, a queda de um deles e o gasto por provedor em Finanças.",
    as_is={"minutos": 12, "hipotese": True,
           "dor": "Os pedidos de troca chegam numa planilha; alguém copia cada linha para cadastro, regra, estoque, chamado e aviso.",
           "passos": ["Abre a planilha de pedidos", "Copia o lojista e o modelo da linha", "Confere cadastro, regra e estoque",
                      "Abre o chamado na logística", "Avisa o lojista e o canal", "Repete toda segunda-feira"],
           "erros": ["Linha esquecida na planilha", "Troca fora da regra", "Modelo sem estoque descoberto tarde"]},
    to_be={"conferencia_min": 1.9,
           "passos": ["A extensão cria o agente a partir da planilha aberta", "O balanceador escolhe o modelo de cada passo",
                      "A rotina roda toda segunda às 9h, em nome do Thiago", "O Mapa de IA mostra tudo ao vivo para o CoE"],
           "nota": "Conferência humana de ≈ %s min por pedido (hipótese); a rotina tira o disparo manual." % _min(1.9)},
    valor=["Tempo por troca", "Rotina semanal sem disparo manual", "Gasto por provedor de IA"],
    passos=(
        Passo("contexto", "A dor: cada time cria IA sozinho", "helena", "/roteiro/pitch",
              "Apresente o problema do CoE: não enxerga o que os times criam, quanto custa nem de qual fornecedor depende.",
              "A Helena não vê o que os times estão criando, quanto custa nem de que fornecedor de IA depende. Hoje, um pedido de troca "
              "de maquininha mora numa planilha e alguém copia linha por linha. Vamos ver isso mudar em oito minutos."),
        Passo("planilha", "Abrir a planilha de pedidos", "thiago", "/demo/planilha",
              "Mostre a planilha “Pedidos de troca de maquininha” no navegador (dados fictícios; abre em outra aba).",
              "Esta é a planilha do Thiago, aberta no navegador. No Google Sheets a grade não é texto selecionável: a extensão lê o "
              "endereço da planilha, não as células. Aqui, a versão local para ensaiar sem internet.", externa=True),
        Passo("criar", "Criar o agente pela extensão", "thiago", "/estudio",
              "No painel da extensão: “Criar Agente de IA a partir desta planilha”. Aqui o Estúdio já abre com a fonte; clique em “Montar meu agente”.",
              "[v7: atalho na extensão] Um clique na extensão e o Estúdio abre no mesmo perfil, com a planilha como fonte. O Thiago não digita nada: "
              "ler a planilha, validar cadastro, regra e estoque, abrir o chamado e avisar o lojista.",
              {"descricao": "Ler a planilha de pedidos de troca de maquininha e tratar o primeiro pedido pendente: conferir cadastro, "
                            "regra de troca e estoque, abrir o chamado na logística e avisar o lojista. Levo uns 12 minutos.",
               "fonte": {"tipo": "planilha", "url": _PLANILHA}}),
        Passo("testar", "Testar no sandbox e ver o balanceador", "thiago", "/estudio",
              "Rode o teste e abra “Como o agente decidiu” num passo com IA: nível de esforço, candidatos e motivo.",
              "[v7: vários provedores e balanceador] Cada passo com IA recebe um nível de esforço e vai ao modelo mais barato que dá conta, "
              "de qualquer provedor. Só o Claude roda de verdade; os outros são simulados, com o selo na tela.",
              {"entrada": {"planilha": _PLANILHA}}),
        Passo("publicar", "Publicar", "thiago", "/estudio",
              "Clique em “Publicar”: risco médio, vai ao ar direto.",
              "Escrita em outro sistema é risco médio: publica direto, com guardrails e auditoria."),
        Passo("rotina", "Agendar a rotina semanal", "thiago", "/processos/" + _AGENTE_PLANILHA,
              "Agende toda segunda às 9h (já preenchido) e clique em “Rodar agora”: a primeira execução leva o selo “rotina”.",
              "[v7: tarefa de rotina] O agente agora roda sozinho toda segunda às 9h, em nome do Thiago, com as mesmas permissões, guardrails "
              "e orçamento. Para ver agora, “Rodar agora”.",
              {"frequencia": "semanal", "dia_semana": 0, "hora": "09:00", "entrada": {"planilha": _PLANILHA}}),
        Passo("mapa", "Mapa de IA: o agente apareceu sozinho", "helena", "/mapa",
              "No Mapa de IA, o agente novo já está no mapa. Avance o relógio da demo (+1 semana) e veja o pulso percorrer o caminho.",
              "[v7: Mapa de IA ao vivo] Para a Helena, o agente do Thiago apareceu sozinho: quem criou, os modelos por provedor, o Slack e o "
              "estoque. O pulso é a rotina rodando: planilha, modelos, ferramentas e plataformas."),
        Passo("queda", "Simular a queda de um provedor", "helena", "/saude",
              "Em Saúde, clique em “Simular queda” no Claude e depois em “Simular carga”: veja a distribuição por provedor e o custo.",
              "[v7: queda de provedor] A Helena derruba o provedor principal. O balanceador delega a outro provedor capaz, abre o alerta e a "
              "carga de teste mostra a distribuição e o custo mudando. Sem depender de um fornecedor só."),
        Passo("financas", "Finanças por provedor", "helena", "/financas",
              "Mostre o gasto por provedor e por modelo e o comparativo “e se tudo rodasse em um só modelo”.",
              "[v7: contabilidade multimodelo] O gasto vem das execuções: por provedor, por modelo e o comparativo de quanto custaria rodar tudo "
              "em um só."),
        Passo("medir", "Medir: AS IS × TO BE com a rotina", "helena", "/roteiro/pitch?etapa=resultado",
              "Abra o cartão AS IS × TO BE do Thiago: a rotina semanal conta no ganho.",
              "Fechamos no cartão do Thiago: tempo medido do agente, a rotina semanal sem ninguém disparar e a origem de cada número."),
    ), duracao_min=9)

from .criadores import CARLA, MARINA, RAFAEL, THIAGO  # noqa: E402  (v8: os quatro criadores têm roteiro próprio)

ROTEIROS: dict[str, Roteiro] = {r.id: r for r in (MARINA, RAFAEL, CARLA, THIAGO, LUCAS, HELENA, PITCH)}
