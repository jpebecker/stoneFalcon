"""Base de conhecimento inicial dos agentes de exemplo (portada do v3).

Conteúdo INVENTADO para o protótipo. Não é política real da Stone.
"variacoes" são outras formas de fazer a mesma pergunta.
"""

BASE_INICIAL = {
    "rh": [
        {
            "pergunta": "Como solicito férias?",
            "variacoes": ["Como marcar férias?", "Quero tirar férias, como faço o pedido?"],
            "resposta": "Abra o pedido no portal de Pessoas, em Férias > Nova solicitação, com pelo menos 30 dias de antecedência. Sua liderança aprova pelo próprio portal e você recebe a confirmação por e-mail.",
        },
        {
            "pergunta": "Quando o vale-refeição é creditado?",
            "variacoes": ["Que dia cai o VR?", "Qual a data de crédito do vale alimentação?"],
            "resposta": "O crédito do vale-refeição e do vale-alimentação entra no último dia útil de cada mês, já valendo para o mês seguinte.",
        },
        {
            "pergunta": "Como funciona o auxílio home office?",
            "variacoes": ["Tenho direito ao auxílio home office?", "Quem recebe ajuda de custo para trabalho remoto?"],
            "resposta": "O auxílio home office é pago mensalmente junto com a folha para quem tem contrato remoto ou híbrido. Não é preciso solicitar: ele aparece no holerite.",
        },
        {
            "pergunta": "Como acesso meu holerite?",
            "variacoes": ["Onde vejo meu contracheque?", "Como baixar o demonstrativo de pagamento?"],
            "resposta": "O holerite fica no portal de Pessoas, em Pagamentos > Holerites. Ele é publicado até o dia do pagamento e pode ser baixado em PDF.",
        },
        {
            "pergunta": "Como incluo um dependente no plano de saúde?",
            "variacoes": ["Como colocar meu filho no convênio médico?", "Quero adicionar um dependente no plano de saúde"],
            "resposta": "Peça a inclusão no portal de Pessoas, em Benefícios > Plano de saúde > Dependentes, anexando o documento que comprova o vínculo. A inclusão vale a partir do mês seguinte.",
        },
        {
            "pergunta": "Como funciona o auxílio creche?",
            "variacoes": ["Tenho direito a auxílio creche?", "Como pedir o reembolso da creche?"],
            "resposta": "O auxílio creche atende filhos de até 5 anos e 11 meses. Envie o comprovante de matrícula e os recibos mensais pelo portal de Pessoas, em Benefícios > Auxílio creche.",
        },
    ],
    "ti": [
        {
            "pergunta": "Como redefino minha senha?",
            "variacoes": ["Esqueci minha senha, como troco?", "Como resetar a senha de rede?"],
            "resposta": "Acesse o portal de autoatendimento de TI, escolha Redefinir senha e confirme com o código enviado ao seu celular. A nova senha vale para e-mail, VPN e rede.",
        },
        {
            "pergunta": "Como configuro a VPN?",
            "variacoes": ["Como instalar a VPN no notebook?", "Preciso conectar na VPN, como faço?"],
            "resposta": "Instale o cliente de VPN pela loja interna de aplicativos, entre com seu e-mail corporativo e confirme no autenticador. Se pedir endereço do servidor, use o que aparece na página de TI.",
        },
        {
            "pergunta": "Como peço acesso a um sistema?",
            "variacoes": ["Como solicitar permissão em um sistema interno?", "Preciso de acesso a uma ferramenta, onde peço?"],
            "resposta": "Abra um chamado em Acessos > Nova solicitação informando o sistema e o motivo. O pedido vai para a sua liderança e depois para o dono do sistema.",
        },
        {
            "pergunta": "Meu notebook está lento, o que faço?",
            "variacoes": ["O computador está travando, como resolver?", "Notebook muito devagar"],
            "resposta": "Reinicie o equipamento e instale as atualizações pendentes. Se continuar lento, abra um chamado em Equipamentos para avaliarmos a troca ou o reparo.",
        },
        {
            "pergunta": "Como instalo um software novo?",
            "variacoes": ["Posso instalar um programa no notebook?", "Como baixar um aplicativo que não está na loja interna?"],
            "resposta": "Programas homologados ficam na loja interna de aplicativos. Para um software que não está lá, abra um chamado em Software > Homologação.",
        },
    ],
    "atendimento": [
        {
            "pergunta": "Qual o prazo de estorno de uma venda no cartão?",
            "variacoes": ["Em quanto tempo o estorno cai para o cliente?", "Quanto tempo demora a devolução no cartão de crédito?"],
            "resposta": "Depois que o lojista solicita o estorno, o valor volta para o cliente em até duas faturas no crédito e em até 7 dias úteis no débito. O lojista acompanha o pedido pelo aplicativo.",
        },
        {
            "pergunta": "Como o lojista solicita a troca da maquininha?",
            "variacoes": ["A maquininha quebrou, como trocar?", "Como pedir uma maquininha nova por defeito?"],
            "resposta": "Abra o pedido de troca no sistema de atendimento, em Logística > Troca de equipamento, com o número de série. A troca é agendada no endereço cadastrado do lojista.",
        },
        {
            "pergunta": "Como orientar o cliente sobre uma venda contestada?",
            "variacoes": ["O lojista recebeu um chargeback, o que ele faz?", "Como responder a uma contestação de venda?"],
            "resposta": "Oriente o lojista a enviar o comprovante da venda e a prova de entrega pelo aplicativo dentro do prazo indicado na notificação. Sem esses documentos, a contestação tende a ser aceita.",
        },
        {
            "pergunta": "Quais os canais de atendimento ao lojista?",
            "variacoes": ["Por onde o lojista fala com o suporte?", "Qual o contato do atendimento para clientes?"],
            "resposta": "O lojista é atendido pelo chat do aplicativo, por telefone e por mensagem. O chat do aplicativo é o canal com resposta mais rápida.",
        },
        {
            "pergunta": "Como o lojista pede mais bobina?",
            "variacoes": ["Acabou a bobina da maquininha, como solicitar?", "Onde pedir papel para a maquininha?"],
            "resposta": "O pedido de bobinas é feito pelo aplicativo, em Ajuda > Pedir bobinas. A entrega vai para o endereço cadastrado.",
        },
    ],
    "risco": [
        {
            "pergunta": "Qual o passo a passo ao receber uma denúncia de fraude?",
            "variacoes": ["O que fazer quando chega uma denúncia de fraude?", "Como tratar uma denúncia de golpe recebida de outra instituição?"],
            "resposta": "Registre a denúncia no sistema de casos, reúna o histórico da conta, verifique os sinais de alerta da lista padrão e, se houver indício, aplique o bloqueio preventivo e encaminhe para a investigação. A decisão final é sempre de um analista.",
        },
        {
            "pergunta": "Quais documentos pedir numa análise de cadastro suspeito?",
            "variacoes": ["Que documentos solicitar ao lojista em uma análise de risco?", "Lista de documentos para validar um cadastro suspeito"],
            "resposta": "Peça documento de identidade com foto do titular, comprovante de endereço do negócio, comprovante da atividade (nota fiscal ou contrato) e uma selfie com o documento.",
        },
        {
            "pergunta": "Quando devo escalar um caso para a coordenação?",
            "variacoes": ["Em que situação encaminho o caso para o coordenador?", "Critérios para escalar um caso de fraude"],
            "resposta": "Escale quando o valor envolvido passar do limite da sua alçada, quando houver suspeita de envolvimento interno ou quando o caso tiver ligação com outras contas já investigadas.",
        },
    ],
    "logistica": [
        {
            "pergunta": "Qual a regra para trocar a maquininha com defeito?",
            "variacoes": ["Como é a troca de maquininha quebrada?", "Quando posso trocar o equipamento do lojista?"],
            "resposta": "A troca por defeito é gratuita até 12 meses depois da entrega do equipamento, com o cadastro do lojista ativo. Abra o chamado na fila logistica com o modelo e o relato do defeito; o envio sai do centro de distribuição mais próximo.",
        },
        {
            "pergunta": "Em quanto tempo a maquininha nova chega?",
            "variacoes": ["Qual o prazo de entrega da troca?", "Quanto tempo leva para enviar o equipamento novo?"],
            "resposta": "O envio sai em até 3 dias úteis, conforme o estoque do modelo no centro de distribuição. O lojista recebe o código de rastreio por mensagem e devolve o equipamento antigo na mesma embalagem.",
        },
        {
            "pergunta": "O que fazer quando o modelo não tem estoque?",
            "variacoes": ["Sem estoque da maquininha, como proceder?", "Falta equipamento do modelo pedido"],
            "resposta": "Se o modelo estiver abaixo de 10 unidades, ofereça um modelo equivalente com o consentimento do lojista e registre no chamado. Sem alternativa, o chamado fica na fila de reposição.",
        },
    ],
}
