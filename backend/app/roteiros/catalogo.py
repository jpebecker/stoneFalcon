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
        Passo("alerta", "O alerta chega: veja e trate", "lucas", "/alertas",
              "Mostre o alerta crítico no sino e na tela de alertas: assuma com uma nota e use a ação do alerta.",
              "O dono do processo e a Engenharia recebem o alerta sozinhos; quem assume aparece como “em tratamento” para todos."),
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
        Passo("alerta", "Veja e trate o seu alerta", "helena", "/alertas",
              "O processo de revisão de custo chegou perto do orçamento: assuma o alerta e revise o orçamento pela ação do alerta.",
              "Ela vê os alertas de toda a empresa; a ação do alerta usa a mesma tela de orçamento, e o alerta fecha sozinho quando o custo volta ao normal.",
              {"cenario_alerta": True}),
        _medir("helena", "Consolidado dos quatro processos, com a origem de cada número."),
        _perguntas("helena"),
    ), duracao_min=4)

from .criadores import CARLA, MARINA, RAFAEL, THIAGO  # noqa: E402
from .pitch import PITCH  # noqa: E402  (v8: o pitch tem módulo próprio)  (v8: os quatro criadores têm roteiro próprio)

ROTEIROS: dict[str, Roteiro] = {r.id: r for r in (MARINA, RAFAEL, CARLA, THIAGO, LUCAS, HELENA, PITCH)}
