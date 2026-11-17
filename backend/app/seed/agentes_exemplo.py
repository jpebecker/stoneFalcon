"""Agentes de exemplo da demo (no formato que o Estúdio gera). Conteúdo fictício."""
from ..agents.blueprint import Blueprint

TRIAGEM_CHARGEBACK = Blueprint.model_validate({
    "nome": "Triagem de chargebacks",
    "objetivo": "Analisar lojistas com contestações recentes, avaliar o risco e propor a ação adequada.",
    "area": "risco",
    "instrucoes": "Nunca decida sozinho sobre bloqueios: proponha e espere a confirmação do analista. "
                  "Cite os números que sustentam a conclusão.",
    "campos": [
        {"id": "lojista_id", "rotulo": "Lojista", "tipo": "lojista", "ajuda": "Escolha o lojista pelo nome."}],
    "minutos_manual": 25,
    "passos": [
        {"id": "cadastro", "titulo": "Consultar cadastro do lojista", "tipo": "ferramenta",
         "ferramenta": "consultar_lojista", "entrada": {"lojista_id": "{{entrada.lojista_id}}"}},
        {"id": "contestacoes", "titulo": "Levantar contestações da semana", "tipo": "ferramenta",
         "ferramenta": "listar_chargebacks", "entrada": {"lojista_id": "{{entrada.lojista_id}}", "dias": 7}},
        {"id": "analise", "titulo": "Avaliar o risco do caso", "tipo": "agente", "modelo": "auto",
         "depende_de": ["cadastro", "contestacoes"], "ferramentas": ["buscar_politica"],
         "instrucao": "Compare o perfil do lojista com as contestações da semana, consulte a política de risco "
                      "e avalie se há sinais de fraude. Explique os sinais encontrados e o nível de risco."},
        {"id": "acao", "titulo": "Encaminhar o caso", "tipo": "agente", "modelo": "rapido",
         "depende_de": ["analise"], "ferramentas": ["abrir_chamado", "bloquear_repasse"],
         "instrucao": "Com base na análise, abra um chamado na fila risco. Se o risco for alto, proponha "
                      "também a retenção preventiva dos repasses."},
    ],
})

DUVIDA_LOJISTA = Blueprint.model_validate({
    "nome": "Resposta a dúvidas de lojistas",
    "objetivo": "Montar uma resposta para a dúvida de um lojista, usando o cadastro dele e a política oficial.",
    "area": "atendimento",
    "instrucoes": "Tom cordial e direto. Não prometa prazos fora da política.",
    "campos": [
        {"id": "lojista_id", "rotulo": "Lojista", "tipo": "lojista", "ajuda": "Escolha o lojista pelo nome."},
        {"id": "pergunta", "rotulo": "Dúvida do lojista", "tipo": "texto_longo",
         "exemplo": "Em quanto tempo o estorno cai para o cliente?",
         "ajuda": "Cole o texto do chamado ou selecione-o na página (extensão)."}],
    "minutos_manual": 8,
    "passos": [
        {"id": "cadastro", "titulo": "Consultar cadastro do lojista", "tipo": "ferramenta",
         "ferramenta": "consultar_lojista", "entrada": {"lojista_id": "{{entrada.lojista_id}}"}},
        {"id": "politica", "titulo": "Buscar a política aplicável", "tipo": "ferramenta",
         "ferramenta": "buscar_politica", "entrada": {"area": "atendimento", "consulta": "{{entrada.pergunta}}"}},
        {"id": "resposta", "titulo": "Redigir a resposta ao lojista", "tipo": "agente", "modelo": "rapido",
         "depende_de": ["cadastro", "politica"],
         "instrucao": "Escreva a resposta ao lojista em até 5 frases, usando a política encontrada e o plano dele."},
    ],
})

EXEMPLOS = {"triagem_chargeback": TRIAGEM_CHARGEBACK, "duvida_lojista": DUVIDA_LOJISTA}
