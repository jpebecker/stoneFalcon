"""Catálogo da demonstração: persona -> agente trabalhador + processo (v8). Conteúdo fictício. FONTE ÚNICA.

O estado inicial (`seed/demo.py`), os roteiros guiados (`roteiros/criadores.py`, `roteiros/medicao.py`) e a galeria do
Estúdio (`studio/modelos_prontos.py`) leem este catálogo; nenhum outro módulo define trabalhador ou processo de demonstração.
(O formato antigo, de vários passos, existe só como fixture dos testes: `backend/tests/legado.py`.)

Princípio: o trabalhador lê e raciocina; quem age em outros sistemas (abrir chamado, reter repasse, avisar) é um bloco do
processo, onde a aprovação humana e a condição ficam à vista.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..agents.blueprint import Blueprint

LOJISTA = {"id": "lojista_id", "rotulo": "Lojista", "tipo": "lojista", "ajuda": "Escolha o lojista pelo nome."}


@dataclass(frozen=True)
class Demo:
    """Uma entrada do catálogo: o trabalhador e o processo de uma persona, com o que a demo precisa saber deles."""
    chave: str                  # estável: "duvida", "triagem", "ferias", "troca"
    persona: str                # quem cria (e dona do processo)
    roteiro: str                # roteiro guiado que o realiza
    area: str
    nome_agente: str
    nome_processo: str
    orcamento: float            # orçamento mensal do processo, definido pela Helena
    nota: str                   # nota da primeira versão
    padrao: str                 # id do padrão na galeria do Estúdio
    exemplos: tuple[str, ...]   # como uma pessoa descreveria o processo (o primeiro rotula o padrão)
    parecer: str | None = None  # parecer da Segurança (só o que passa pela revisão de risco alto)


DEMOS: dict[str, Demo] = {d.chave: d for d in (
    Demo("duvida", "marina", "marina", "atendimento", "Redator de respostas a lojistas", "Resposta a dúvidas de lojistas", 120.0,
         "Primeira versão, a partir das perguntas mais comuns da fila.", "duvida_lojista", (
             "Responder dúvidas de lojistas sobre estorno, prazo e maquininha usando a política oficial",
             "Montar a resposta para o lojista que pergunta sobre o prazo de estorno",
             "Os lojistas mandam perguntas e eu procuro a regra na base para responder")),
    Demo("triagem", "rafael", "rafael", "risco", "Analista de risco de chargebacks", "Triagem de chargebacks", 300.0,
         "Triagem diária de contestações.", "triagem_chargeback", (
             "Toda manhã confiro os lojistas com chargeback e decido se abro chamado ou bloqueio o repasse",
             "Analisar contestações de vendas de um lojista e avaliar risco de fraude",
             "Quero um agente que olhe as vendas contestadas e me diga se é fraude"),
         parecer="Retenção de repasse protegida por confirmação humana; acesso restrito à área de risco. Aprovado."),
    Demo("ferias", "carla", "carla", "pessoas", "Orientador de férias e benefícios", "Orientação de férias", 80.0,
         "Dúvidas de férias e benefícios.", "ferias_colaborador", (
             "Colaboradores perguntam quantos dias de férias têm e como pedir, eu olho a ficha e a política",
             "Responder dúvidas de RH sobre férias e benefícios com base na ficha do colaborador",
             "Consultar saldo de férias e explicar a regra para o colaborador")),
    Demo("troca", "thiago", "thiago", "logistica", "Analista de trocas de maquininha", "Troca de maquininha com estoque", 100.0,
         "Troca de maquininha com cadastro, regra e estoque em paralelo.", "troca_maquininha_estoque", (
             "Quando o lojista pede troca de maquininha eu confiro o cadastro, a regra de troca e o estoque do modelo ao mesmo tempo, abro o chamado na logística e aviso o canal",
             "Troca de equipamento com conferência de estoque, chamado na logística e aviso ao lojista",
             "Conferir cadastro, regra de troca e estoque da maquininha antes de abrir o chamado",
             "Quando o lojista diz que a maquininha quebrou eu confiro o cadastro e abro chamado de troca na logística",
             "Maquininha com defeito: verificar o cliente e pedir a troca")),
)}

CHAVES = tuple(DEMOS)
# visões por chave, para quem só precisa de um atributo
ROTEIRO = {c: d.roteiro for c, d in DEMOS.items()}
NOME_PROCESSO = {c: d.nome_processo for c, d in DEMOS.items()}
NOME_AGENTE = {c: d.nome_agente for c, d in DEMOS.items()}
AREA = {c: d.area for c, d in DEMOS.items()}


def por_persona(persona: str) -> list[Demo]:
    """O que a persona tem na demo (um trabalhador + um processo por entrada)."""
    return [d for d in DEMOS.values() if d.persona == persona]


def por_padrao(padrao_id: str) -> Demo | None:
    return next((d for d in DEMOS.values() if d.padrao == padrao_id), None)


def _trabalhador(chave: str, objetivo: str, instrucoes: str, ferramentas: list[str], instrucao: str, modelo: str) -> Blueprint:
    return Blueprint.model_validate({
        "nome": NOME_AGENTE[chave], "objetivo": objetivo, "area": AREA[chave], "instrucoes": instrucoes, "campos": [], "minutos_manual": 0,
        "passos": [{"id": "trabalho", "titulo": NOME_AGENTE[chave], "tipo": "agente", "modelo": modelo,
                    "ferramentas": ferramentas, "instrucao": instrucao}]})


TRABALHADORES: dict[str, Blueprint] = {
    "duvida": _trabalhador(
        "duvida", "Escrever a resposta a uma dúvida de lojista usando o cadastro e a política oficial.",
        "Tom cordial e direto. Não prometa prazos fora da política.", ["consultar_lojista", "buscar_politica"],
        "Escreva a resposta ao lojista em até 5 frases, usando a política encontrada e o plano dele.", "rapido"),
    "triagem": _trabalhador(
        "triagem", "Avaliar o risco de fraude de um lojista com base no cadastro e nas contestações recentes.",
        "Nunca decida sozinho sobre bloqueios: o processo propõe e espera a confirmação do analista. Cite os números que sustentam a conclusão.",
        ["buscar_politica"],
        "Compare o perfil do lojista com as contestações da semana, consulte a política de risco e avalie se há sinais de fraude. "
        "Explique os sinais encontrados e o nível de risco.", "auto"),
    "ferias": _trabalhador(
        "ferias", "Responder dúvidas de férias e benefícios usando a ficha do colaborador e a política de RH.",
        "Não exponha dados de outros colaboradores. Linguagem acolhedora.", ["consultar_colaborador", "buscar_politica"],
        "Responda à pergunta usando o saldo e os benefícios da ficha e a política encontrada.", "rapido"),
    "troca": _trabalhador(
        "troca", "Avaliar um pedido de troca de maquininha com o cadastro, a regra de troca e o estoque do modelo.",
        "Confirme o modelo e o endereço antes de abrir o chamado. Se o estoque estiver baixo, diga isso.",
        ["consultar_lojista", "buscar_politica", "consultar_estoque"],
        "Com o cadastro, a regra de troca e o estoque, escreva um resumo do pedido para o chamado: modelo, relato, estoque e prazo de envio.", "rapido"),
}


def _b(id: str, tipo: str, titulo: str, depende_de: list[str] | None = None, **campos) -> dict:
    return {"id": id, "tipo": tipo, "titulo": titulo, "depende_de": depende_de or [], **campos}


def processo(chave: str, agente: str, slack: bool = False, por_nome: bool = False) -> dict[str, Any]:
    """O fluxo de blocos de `chave`. `agente` é o id do trabalhador (ou o NOME, com `por_nome`: a tela do roteiro resolve o id).
    Com `slack`, o aviso do processo de trocas usa o plugin do Slack (o roteiro do Thiago o integra antes)."""
    chave_agente = {"agente_nome": agente} if por_nome else {"agente_id": agente}
    base = {"nome": NOME_PROCESSO[chave], "area": AREA[chave], "roteiro_id": ROTEIRO[chave], "limites": {"max_custo_brl": 2.0, "max_chamadas_modelo": 20}}
    if chave == "duvida":
        return {**base, "objetivo": "Montar uma resposta para a dúvida de um lojista, usando o cadastro dele e a política oficial.", "minutos_manual": 8,
                "campos": [LOJISTA, {"id": "pergunta", "rotulo": "Dúvida do lojista", "tipo": "texto_longo",
                                     "exemplo": "Em quanto tempo o estorno cai para o cliente?", "ajuda": "Cole o texto do chamado ou selecione-o na página (extensão)."}],
                "blocos": [
                    _b("cadastro", "dados", "Consultar cadastro do lojista", ferramenta="consultar_lojista", entrada={"lojista_id": "{{entrada.lojista_id}}"}),
                    _b("politica", "dados", "Buscar a política aplicável", ferramenta="buscar_politica",
                       entrada={"area": "atendimento", "consulta": "{{entrada.pergunta}}"}),
                    _b("resposta", "agente", "Redigir a resposta ao lojista", ["cadastro", "politica"], **chave_agente)]}
    if chave == "triagem":
        return {**base, "objetivo": "Analisar lojistas com contestações recentes, avaliar o risco e propor a ação adequada.", "minutos_manual": 25,
                "campos": [LOJISTA],
                "blocos": [
                    _b("cadastro", "dados", "Consultar cadastro do lojista", ferramenta="consultar_lojista", entrada={"lojista_id": "{{entrada.lojista_id}}"}),
                    _b("contestacoes", "dados", "Levantar contestações da semana", ferramenta="listar_chargebacks",
                       entrada={"lojista_id": "{{entrada.lojista_id}}", "dias": 7}),
                    _b("analise", "agente", "Avaliar o risco do caso", ["cadastro", "contestacoes"], **chave_agente),
                    _b("risco_alto", "condicao", "O risco é alto?", ["analise"],
                       regra={"fonte": "passos.analise.saida", "operador": "contem", "valor": "Risco ALTO"}),
                    _b("chamado", "plugin", "Abrir chamado na fila de risco", ["risco_alto"], ferramenta="abrir_chamado",
                       ramo={"condicao": "risco_alto", "valor": "sim"},
                       entrada={"fila": "risco", "titulo": "Triagem de chargebacks: {{passos.cadastro.saida.nome}}", "descricao": "{{passos.analise.saida}}"}),
                    _b("retencao", "plugin", "Reter os repasses (pede a sua confirmação)", ["chamado"], ferramenta="bloquear_repasse",
                       entrada={"lojista_id": "{{entrada.lojista_id}}", "motivo": "{{passos.analise.saida}}"}),
                    _b("sem_risco", "saida", "Sem risco alto: seguir o acompanhamento", ["risco_alto"], ramo={"condicao": "risco_alto", "valor": "nao"},
                       texto="Sem sinais de risco alto neste lojista: nenhuma retenção de repasse. Segue o acompanhamento de rotina.")]}
    if chave == "ferias":
        return {**base, "objetivo": "Responder dúvidas de férias e benefícios usando a ficha do colaborador e a política de RH.", "minutos_manual": 10,
                "campos": [{"id": "colaborador_id", "rotulo": "Colaborador", "tipo": "colaborador", "ajuda": "Você mesmo, ou outra pessoa se o seu perfil permitir."},
                           {"id": "pergunta", "rotulo": "Dúvida sobre férias ou benefícios", "tipo": "texto_longo", "exemplo": "Quantos dias de férias eu tenho e como peço?"}],
                "blocos": [
                    _b("ficha", "dados", "Consultar ficha do colaborador", ferramenta="consultar_colaborador", entrada={"colaborador_id": "{{entrada.colaborador_id}}"}),
                    _b("politica", "dados", "Buscar a política de RH", ferramenta="buscar_politica", entrada={"area": "rh", "consulta": "{{entrada.pergunta}}"}),
                    _b("resposta", "agente", "Responder ao colaborador", ["ficha", "politica"], **chave_agente)]}
    aviso = (_b("canal", "plugin", "Avisar o canal da logística no Slack", ["chamado"], ferramenta="slack_enviar_mensagem",
                entrada={"canal": "#logistica", "mensagem": "Troca de {{entrada.modelo}}: {{passos.analise.saida}}"}) if slack else
             _b("canal", "saida", "Avisar o canal da logística", ["chamado"], ferramenta="enviar_notificacao",
                entrada={"canal": "slack", "destino": "#logistica", "mensagem": "Troca de {{entrada.modelo}}: {{passos.analise.saida}}"}))
    return {**base, "objetivo": "Conferir cadastro, regra de troca e estoque do modelo em paralelo, abrir o chamado na logística e avisar o canal.", "minutos_manual": 12,
            "campos": [LOJISTA, {"id": "modelo", "rotulo": "Modelo da maquininha", "tipo": "opcao",
                                 "opcoes": ["Maquininha Mini", "Maquininha Pro", "Maquininha Smart"], "exemplo": "Maquininha Smart"},
                       {"id": "relato", "rotulo": "Relato do defeito", "tipo": "texto_longo", "exemplo": "A tela ficou preta e a maquininha não liga mais."}],
            "blocos": [
                _b("cadastro", "dados", "Consultar cadastro do lojista", ferramenta="consultar_lojista", entrada={"lojista_id": "{{entrada.lojista_id}}"}),
                _b("regra", "dados", "Buscar a regra de troca", ferramenta="buscar_politica",
                   entrada={"area": "logistica", "consulta": "Qual a regra para trocar a maquininha com defeito?"}),
                _b("estoque", "dados", "Conferir o estoque do modelo", ferramenta="consultar_estoque", entrada={"modelo": "{{entrada.modelo}}"}),
                _b("analise", "agente", "Resumir o pedido de troca", ["cadastro", "regra", "estoque"], **chave_agente),
                _b("chamado", "plugin", "Abrir chamado na logística", ["analise"], ferramenta="abrir_chamado",
                   entrada={"fila": "logistica", "titulo": "Troca de {{entrada.modelo}}", "descricao": "{{passos.analise.saida}}"}),
                aviso]}


def fluxo(chave: str, slack: bool = False) -> Blueprint:
    """O processo de `chave` compilado SEM banco, com o trabalhador do catálogo: a base das estimativas de custo e tempo
    dos roteiros enquanto a pessoa ainda não criou o processo."""
    from ..processos.blueprint import ProcessoBlueprint
    from ..processos.compilar import compilar
    return compilar(None, ProcessoBlueprint.model_validate(processo(chave, chave, slack=slack)), trabalhadores=TRABALHADORES)
