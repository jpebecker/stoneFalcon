"""Campos que cada ferramenta devolve, em português: a tela de processos oferece a lista ("o plano do lojista"),
ninguém digita `{{passos.cadastro.saida.plano}}`. Ferramenta fora da lista só oferece o resultado completo."""

CAMPOS_SAIDA: dict[str, dict[str, str]] = {
    "consultar_lojista": {"nome": "Nome do lojista", "cidade": "Cidade", "segmento": "Segmento", "plano": "Plano",
                          "faturamento_mensal": "Faturamento mensal", "maquininha": "Maquininha", "email": "E-mail"},
    "listar_transacoes": {"quantidade": "Quantidade de vendas", "total": "Valor total das vendas"},
    "listar_chargebacks": {"quantidade": "Quantidade de contestações", "valor_total": "Valor total contestado"},
    "buscar_politica": {"resultados": "Políticas encontradas"},
    "consultar_colaborador": {"nome": "Nome", "area": "Área", "saldo_ferias_dias": "Saldo de férias (dias)", "admissao": "Data de admissão"},
    "consultar_estoque": {"disponivel": "Unidades disponíveis", "centro": "Centro de distribuição", "prazo_envio_dias": "Prazo de envio (dias)"},
    "abrir_chamado": {"chamado_id": "Número do chamado", "status": "Situação", "fila": "Fila"},
    "enviar_notificacao": {"notificacao_id": "Número do aviso", "status": "Situação"},
    "zendesk_ler_chamado": {"chamado_id": "Número do chamado", "assunto": "Assunto", "solicitante": "Solicitante", "lojista_id": "Lojista",
                            "prioridade": "Prioridade", "status": "Situação", "mensagem": "Mensagem"},
    "sap_consultar_saldo_ferias": {"nome": "Nome", "saldo_ferias_dias": "Saldo de férias (dias)", "admissao": "Data de admissão"},
    "jira_consultar_status": {"titulo": "Título", "status": "Situação"},
}


def campos(ferramenta: str) -> dict[str, str]:
    return CAMPOS_SAIDA.get(ferramenta, {})
