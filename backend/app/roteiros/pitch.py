"""Roteiro do pitch v8 (8 a 10 minutos, tudo em modo simulado): seletor radial -> agente -> processo -> plugin real -> "Crie o seu plugin"
aprovado pela Helena e pela Segurança -> Mapa de IA e Finanças por processo -> cartão AS IS x TO BE.

Importado ao fim de `catalogo.py` (como `criadores.py`); a Helena é quem apresenta, e a persona da tarefa medida é o Thiago.
"""
from __future__ import annotations

from .catalogo import Passo, Roteiro, _ctx, _medir, _min

_PLANILHA = "local:pedidos-troca"
_PROCESSO_PLANILHA = "{processo:Troca de maquininha pela planilha}"

PEDIDO_PLUGIN = {
    "ferramenta_mercado": "Agenda Corporativa Exemplo",
    "descricao_publica": ("A Agenda Corporativa Exemplo permite marcar reuniões, reservar salas e ver o calendário da equipe. Envia convite aos "
                          "participantes, cancela e remarca compromissos e mostra a disponibilidade de cada sala em cada horário."),
    "finalidade": "Reservar a sala de treinamento da logística e marcar a troca de turno das equipes de campo.",
    "areas": ["logistica"], "classificacao": "confidencial",
}

PITCH = Roteiro(
    id="pitch", persona="thiago", titulo="Pitch v8: do seletor ao plugin criado pela própria equipe",
    processo="Troca de maquininha por planilha (rotina semanal)", agente_nome="Troca de maquininha pela planilha", sem=frozenset(),
    preparar="pitch", apresentacao=True,
    resumo="A Helena abre o seletor, o Thiago cria um agente e um processo que usam o plugin Arquivos e Planilhas (de verdade), pede um plugin "
           "novo que a Helena e a Segurança aprovam, e o CoE enxerga tudo no Mapa de IA e em Finanças por processo.",
    as_is={"minutos": 12, "hipotese": True,
           "dor": "Os pedidos de troca chegam numa planilha; alguém copia cada linha para cadastro, regra, estoque, chamado e aviso.",
           "passos": ["Abre a planilha de pedidos", "Copia o lojista e o modelo da linha", "Confere cadastro, regra e estoque",
                      "Abre o chamado na logística", "Avisa o lojista e o canal", "Repete toda segunda-feira"],
           "erros": ["Linha esquecida na planilha", "Troca fora da regra", "Modelo sem estoque descoberto tarde"]},
    to_be={"conferencia_min": 1.9,
           "passos": ["Um agente trabalhador lê e resume o pedido", "Um processo de blocos confere em paralelo, abre o chamado e avisa o canal",
                      "O plugin Arquivos e Planilhas lê e marca a planilha", "A rotina roda toda segunda às 9h, em nome do Thiago"],
           "nota": "Conferência humana de ≈ %s min por pedido (hipótese); a rotina tira o disparo manual." % _min(1.9)},
    valor=["Tempo por troca", "Rotina semanal sem disparo manual", "Plugin novo sem fila de Engenharia"],
    passos=(
        Passo("contexto", "A dor: cada time cria IA sozinho", "helena", "/roteiro/pitch",
              "Apresente o problema do CoE: não enxerga o que os times criam, quanto custa nem do que depende.",
              "A Helena não vê o que os times criam, quanto custa nem de que depende. Em oito minutos: um agente, um processo, um plugin de verdade "
              "e um plugin novo pedido pela própria equipe."),
        Passo("seletor", "Entrar pelo seletor radial", "helena", "/",
              "Na tela de entrada, mostre o seletor radial: seis pessoas, cada uma com o seu papel. Passe o mouse, use as setas e escolha o Thiago.",
              "[v8: seletor radial] Cada pessoa vê só o que o papel dela permite. Vamos entrar como Thiago, da Logística."),
        Passo("criar", "Criar o agente trabalhador pela planilha", "thiago", "/estudio",
              "Clique em “Montar meu agente”: o Estúdio abre com a planilha como fonte e monta UM agente, que lê e raciocina.",
              "[v8: agente trabalhador] O agente faz uma tarefa só: ler o pedido e escrever o resumo. Quem age em outros sistemas é o processo.",
              {"descricao": "Ler a planilha de pedidos de troca de maquininha e tratar o primeiro pedido pendente: conferir cadastro, "
                            "regra de troca e estoque, abrir o chamado na logística e avisar o lojista. Levo uns 12 minutos.",
               "fonte": {"tipo": "planilha", "url": _PLANILHA}, "nome_agente": "Analista de trocas de maquininha"}),
        Passo("processo", "Transformar em processo e publicar", "thiago", "/estudio",
              "Clique em “Transformar em processo”, confira os blocos (em paralelo, com o aviso ao canal) e publique.",
              "[v8: processos] O processo é o fluxo de blocos: dados em paralelo, o agente, o chamado e o aviso. A aprovação humana e as ações ficam à vista."),
        Passo("testar", "Testar o processo e ver o balanceador", "thiago", "/processos/novo",
              "Rode o teste e abra “Como o agente decidiu” no bloco do agente: nível de esforço, candidatos e motivo.",
              "[v7: balanceador] O balanceador manda cada bloco com IA ao modelo mais barato que dá conta, de qualquer provedor. Só o Claude roda de verdade; "
              "os outros são simulados e têm selo.",
              {"entrada": {"planilha": _PLANILHA}}),
        Passo("rotina", "Agendar a rotina semanal do processo", "thiago", "/processos/" + _PROCESSO_PLANILHA,
              "Agende toda segunda às 9h (já preenchido) e clique em “Rodar agora”: a primeira execução leva o selo “rotina”.",
              "[v7: rotina] O processo agora roda sozinho toda segunda às 9h, em nome do Thiago, com as mesmas permissões, guardrails e orçamento.",
              {"frequencia": "semanal", "dia_semana": 0, "hora": "09:00", "entrada": {"planilha": _PLANILHA}}),
        Passo("arquivos", "O plugin que funciona de verdade", "thiago", "/plugins/arquivos",
              "Abra o plugin Arquivos e Planilhas: a prévia da planilha de pedidos, a classificação e as áreas. Baixe o arquivo.",
              "[v8: plugin real] Este plugin não é simulado: o Thiago envia um CSV ou Excel, escolhe a classificação e quem usa, e agentes e processos leem "
              "e escrevem nele. CPF e e-mail viram marcadores antes de qualquer modelo, e escrita em arquivo confidencial espera uma pessoa."),
        Passo("criarplugin", "Pedir um plugin novo: “Crie o seu plugin”", "thiago", "/plugins/criar",
              "O pedido já vem preenchido (descrição pública de uma ferramenta de agenda). Gere o rascunho, confira os números e envie.",
              "[v8: crie o seu plugin] Em vez de esperar a fila da Engenharia, o Thiago cola a descrição pública de uma ferramenta de mercado. A plataforma "
              "rascunha um plugin interno, genérico e sem marca, e calcula comprar contra construir.",
              {"plugin": PEDIDO_PLUGIN}),
        Passo("aprovar", "A analista de IA decide", "helena", "/plugins",
              "Abra o pedido do Thiago: o texto pedido ao lado da especificação e dos números. Aprove com o parecer já preenchido.",
              "[v8: analista de IA] A Helena lê a especificação ao lado do pedido e aprova. Como o dado é confidencial, o pedido segue para a Segurança.",
              {"parecer": "Atende à necessidade da logística, evita a licença externa e o escopo está claro. Aprovado."}),
        Passo("seguranca", "A Segurança dá o aval do dado sensível", "lucas", "/plugins",
              "O Lucas abre o pedido e aprova com o parecer preenchido. O plugin entra no marketplace como “interno · conceitual”.",
              "[v8: quatro olhos] Dado confidencial pede o aval da Segurança, e ninguém decide o próprio pedido. Aprovado, o plugin nasce no marketplace, "
              "com ferramentas simuladas que seguem a especificação.",
              {"parecer": "Escrita protegida por confirmação humana e acesso limitado à Logística. Aprovado."}),
        Passo("mapa", "Mapa de IA: tudo apareceu sozinho", "helena", "/mapa",
              "No Mapa de IA, veja a camada de processos: criador, processo, agentes, modelos, plugins e plataformas. Rode o processo e veja o pulso.",
              "[v8: mapa por processo] Para a Helena, o processo do Thiago apareceu sozinho, com o agente dentro dele, os modelos por provedor e os plugins, "
              "inclusive o de verdade. Cada execução acende um pulso pelo caminho."),
        Passo("financas", "Finanças por processo", "helena", "/financas",
              "Mostre o custo e o retorno por processo, abra os agentes dentro de um deles e exporte a tabela para uma planilha.",
              "[v8: finanças por processo] O gasto vem das execuções: por processo, com os agentes por dentro, por provedor e por modelo. O botão exporta "
              "a tabela para uma planilha do próprio plugin."),
        _medir("helena", "Fechamos no cartão do Thiago: tempo medido do processo, a rotina semanal sem ninguém disparar e a origem de cada número."),
    ), duracao_min=10)
