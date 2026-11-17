"""Galeria de padrões de agente.

Servem a dois propósitos:
  - no modo simulado, o Estúdio escolhe o padrão mais parecido com a descrição;
  - no modo real, são exemplos que orientam o modelo a gerar blueprints no mesmo estilo.
Os "exemplos" são formas como um colaborador descreveria o processo.
"""
from ..seed.agentes_exemplo import DUVIDA_LOJISTA, TRIAGEM_CHARGEBACK

PADROES = [
    {
        "id": "triagem_chargeback",
        "titulo": "Triagem de contestações",
        "area": "risco",
        "exemplos": [
            "Toda manhã confiro os lojistas com chargeback e decido se abro chamado ou bloqueio o repasse",
            "Analisar contestações de vendas de um lojista e avaliar risco de fraude",
            "Quero um agente que olhe as vendas contestadas e me diga se é fraude",
        ],
        "blueprint": TRIAGEM_CHARGEBACK.model_dump(),
    },
    {
        "id": "duvida_lojista",
        "titulo": "Resposta a dúvidas de lojistas",
        "area": "atendimento",
        "exemplos": [
            "Responder dúvidas de lojistas sobre estorno, prazo e maquininha usando a política oficial",
            "Montar a resposta para o lojista que pergunta sobre o prazo de estorno",
            "Os lojistas mandam perguntas e eu procuro a regra na base para responder",
        ],
        "blueprint": DUVIDA_LOJISTA.model_dump(),
    },
    {
        "id": "troca_maquininha",
        "titulo": "Pedido de troca de maquininha",
        "area": "atendimento",
        "exemplos": [
            "Quando o lojista diz que a maquininha quebrou eu confiro o cadastro e abro chamado de troca na logística",
            "Abrir chamado de troca de equipamento com defeito",
            "Maquininha com defeito: verificar o cliente e pedir a troca",
        ],
        "blueprint": {
            "nome": "Troca de maquininha", "area": "atendimento", "minutos_manual": 12,
            "objetivo": "Conferir o cadastro do lojista e abrir o chamado de troca de equipamento na logística.",
            "instrucoes": "Confirme o endereço cadastrado antes de abrir o chamado.",
            "campos": [
                {"id": "lojista_id", "rotulo": "Lojista", "tipo": "lojista", "ajuda": "Escolha o lojista pelo nome."},
                {"id": "relato", "rotulo": "Relato do defeito", "tipo": "texto_longo",
                 "exemplo": "A maquininha parou de ligar depois de cair no chão."}],
            "passos": [
                {"id": "cadastro", "titulo": "Consultar cadastro do lojista", "tipo": "ferramenta",
                 "ferramenta": "consultar_lojista", "entrada": {"lojista_id": "{{entrada.lojista_id}}"}},
                {"id": "politica", "titulo": "Buscar a regra de troca", "tipo": "ferramenta",
                 "ferramenta": "buscar_politica",
                 "entrada": {"area": "atendimento", "consulta": "Como o lojista solicita a troca da maquininha?"}},
                {"id": "chamado", "titulo": "Abrir chamado na logística", "tipo": "agente", "modelo": "rapido",
                 "depende_de": ["cadastro", "politica"], "ferramentas": ["abrir_chamado"],
                 "instrucao": "Abra um chamado na fila logistica com o relato do lojista e confirme o protocolo."},
            ],
        },
    },
    {
        "id": "troca_maquininha_estoque",
        "titulo": "Troca de maquininha com conferência de estoque",
        "area": "logistica",
        "exemplos": [
            "Quando o lojista pede troca de maquininha eu confiro o cadastro, a regra de troca e o estoque do modelo ao mesmo tempo, abro o chamado na logística e aviso o lojista",
            "Troca de equipamento com conferência de estoque, chamado na logística e aviso ao lojista",
            "Conferir cadastro, regra de troca e estoque da maquininha antes de abrir o chamado",
        ],
        "blueprint": {
            "nome": "Troca de maquininha com estoque", "area": "logistica", "minutos_manual": 12,
            "objetivo": "Conferir cadastro, regra de troca e estoque do modelo em paralelo, abrir o chamado na logística e avisar o lojista.",
            "instrucoes": "Confirme o modelo e o endereço antes de abrir o chamado. Se o estoque estiver baixo, diga isso no chamado.",
            "campos": [
                {"id": "lojista_id", "rotulo": "Lojista", "tipo": "lojista", "ajuda": "Escolha o lojista pelo nome."},
                {"id": "modelo", "rotulo": "Modelo da maquininha", "tipo": "opcao",
                 "opcoes": ["Maquininha Mini", "Maquininha Pro", "Maquininha Smart"], "exemplo": "Maquininha Smart"},
                {"id": "relato", "rotulo": "Relato do defeito", "tipo": "texto_longo",
                 "exemplo": "A tela ficou preta e a maquininha não liga mais."}],
            "passos": [
                {"id": "cadastro", "titulo": "Consultar cadastro do lojista", "tipo": "ferramenta",
                 "ferramenta": "consultar_lojista", "entrada": {"lojista_id": "{{entrada.lojista_id}}"}},
                {"id": "regra", "titulo": "Buscar a regra de troca", "tipo": "ferramenta",
                 "ferramenta": "buscar_politica",
                 "entrada": {"area": "logistica", "consulta": "Qual a regra para trocar a maquininha com defeito?"}},
                {"id": "estoque", "titulo": "Conferir o estoque do modelo", "tipo": "ferramenta",
                 "ferramenta": "consultar_estoque", "entrada": {"modelo": "{{entrada.modelo}}"}},
                {"id": "chamado", "titulo": "Abrir chamado na logística", "tipo": "agente", "modelo": "rapido",
                 "depende_de": ["cadastro", "regra", "estoque"], "ferramentas": ["abrir_chamado"],
                 "instrucao": "Abra um chamado na fila logistica com o modelo, o relato do lojista e a situação do estoque, e confirme o protocolo."},
                {"id": "aviso", "titulo": "Avisar o lojista", "tipo": "agente", "modelo": "rapido",
                 "depende_de": ["chamado", "cadastro"], "ferramentas": ["enviar_notificacao"],
                 "instrucao": "Escreva um aviso curto ao lojista com o protocolo do chamado e o prazo de envio, e envie por e-mail."},
            ],
        },
    },
    {
        "id": "ferias_colaborador",
        "titulo": "Orientação de férias e benefícios",
        "area": "pessoas",
        "exemplos": [
            "Colaboradores perguntam quantos dias de férias têm e como pedir, eu olho a ficha e a política",
            "Responder dúvidas de RH sobre férias e benefícios com base na ficha do colaborador",
            "Consultar saldo de férias e explicar a regra para o colaborador",
        ],
        "blueprint": {
            "nome": "Orientação de férias", "area": "pessoas", "minutos_manual": 10,
            "objetivo": "Responder dúvidas de férias e benefícios usando a ficha do colaborador e a política de RH.",
            "instrucoes": "Não exponha dados de outros colaboradores. Linguagem acolhedora.",
            "campos": [
                {"id": "colaborador_id", "rotulo": "Colaborador", "tipo": "colaborador",
                 "ajuda": "Você mesmo, ou outra pessoa se o seu perfil permitir."},
                {"id": "pergunta", "rotulo": "Dúvida sobre férias ou benefícios", "tipo": "texto_longo",
                 "exemplo": "Quantos dias de férias eu tenho e como peço?"}],
            "passos": [
                {"id": "ficha", "titulo": "Consultar ficha do colaborador", "tipo": "ferramenta",
                 "ferramenta": "consultar_colaborador", "entrada": {"colaborador_id": "{{entrada.colaborador_id}}"}},
                {"id": "politica", "titulo": "Buscar a política de RH", "tipo": "ferramenta",
                 "ferramenta": "buscar_politica", "entrada": {"area": "rh", "consulta": "{{entrada.pergunta}}"}},
                {"id": "resposta", "titulo": "Responder ao colaborador", "tipo": "agente", "modelo": "rapido",
                 "depende_de": ["ficha", "politica"],
                 "instrucao": "Responda à pergunta usando o saldo e os benefícios da ficha e a política encontrada."},
            ],
        },
    },
    {
        "id": "aviso_time",
        "titulo": "Resumo e aviso ao time",
        "area": "*",
        "exemplos": [
            "Juntar a informação da política e mandar um aviso no Slack do time",
            "Enviar um comunicado por e-mail com a regra atualizada",
            "Avisar o time sobre um procedimento",
        ],
        "blueprint": {
            "nome": "Aviso ao time", "area": "*", "minutos_manual": 15,
            "objetivo": "Buscar a orientação oficial sobre um tema e enviar um aviso claro ao time.",
            "instrucoes": "Mensagens curtas, com o que muda e a partir de quando.",
            "campos": [
                {"id": "tema", "rotulo": "Tema do aviso", "tipo": "texto", "exemplo": "Novo prazo de estorno"},
                {"id": "destino", "rotulo": "Para quem avisar", "tipo": "texto", "exemplo": "#time-atendimento",
                 "ajuda": "Canal (#nome) ou e-mail."}],
            "passos": [
                {"id": "politica", "titulo": "Buscar a orientação oficial", "tipo": "agente", "modelo": "rapido",
                 "ferramentas": ["buscar_politica"],
                 "instrucao": "Encontre a política sobre o tema informado na base da área mais adequada."},
                {"id": "aviso", "titulo": "Enviar o aviso", "tipo": "agente", "modelo": "rapido",
                 "depende_de": ["politica"], "ferramentas": ["enviar_notificacao"],
                 "instrucao": "Escreva um aviso de até 4 frases e envie para o destino informado."},
            ],
        },
    },
]


def por_id(padrao_id: str) -> dict | None:
    return next((p for p in PADROES if p["id"] == padrao_id), None)
