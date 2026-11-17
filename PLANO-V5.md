# StoneFalcon v5 — Plano de refatoração

> Rascunho para aprovação do grupo. Os números de tempo e custo marcados **(hipótese)** precisam ser validados antes do pitch.

## 1. O que muda e por quê

A v4 mostra que a plataforma *funciona* (runtime, guardrails, auditoria, custos), mas a demonstração depende de quem apresenta saber onde clicar e de inventar entradas na hora. As respostas simuladas ("Dados considerados: …") não convencem a banca, a extensão é uma moldura crua da plataforma e a entrada de dados pede códigos técnicos (`lojista_id`, `colaborador_id`).

A v5 organiza o produto em torno de **personas e processos reais**, e cada história vira uma **rota pré-determinada** que pode ser demonstrada do mesmo jeito sempre:

1. **Conhecer a persona**: cargo, área, rotina e dor.
2. **Processo AS IS**: como a tarefa é feita hoje, passo a passo, com tempo, erros e retrabalho.
3. **Processo TO BE**: o mesmo processo assistido por um agente, com ganho mensurável nos 5 critérios da banca (tempo, custo, produtividade, erros, ROI).
4. **Jornada completa**: a persona cria o agente, a governança o aprova, a persona o usa (na plataforma e na extensão) e o resultado aparece medido.
5. **Rota no sistema**: um roteiro guiado reproduz essa jornada, com entradas e respostas pré-determinadas.
6. **Perguntas e respostas do pitch**: perguntas prováveis da banca para cada persona, com a resposta e a tela que serve de prova.

### Princípios

- **Demonstração determinística.** O mesmo roteiro produz sempre o mesmo resultado, com ou sem chave da API. No modo real, o roteiro ainda pode usar o modelo, mas tem resposta de reserva.
- **Linguagem de usuário.** Ninguém digita códigos técnicos. Entidades (lojista, colaborador, chamado) são escolhidas por nome ou preenchidas pelo contexto.
- **Valor mensurável na tela.** Todo roteiro termina mostrando o AS IS × TO BE em números, ligado ao painel executivo.
- **Nada do núcleo é jogado fora.** Runtime, guardrails, ciclo de vida, auditoria, saúde e finanças da v4 continuam e passam a ser o palco dos roteiros.

## 2. Personas (proposta: 6 perfis)

As 5 personas da v4 continuam. Proponho uma 6ª (Operações/Logística), porque o desafio cita logística explicitamente e porque o modelo "Pedido de troca de maquininha" já existe no Estúdio.

| Persona | Cargo · área | Papel na demonstração | Dor principal |
|---|---|---|---|
| **Marina Duarte** | Analista de atendimento · Atendimento | cria e usa (no-code) | responde as mesmas dúvidas de lojistas consultando 3 sistemas |
| **Rafael Lima** | Analista de risco · Prevenção a Fraudes | cria e usa, com ação sensível | triagem manual de chargebacks; risco de bloquear errado |
| **Carla Nogueira** | Business partner · Pessoas (RH) | cria e usa, com dado confidencial | perguntas repetidas sobre férias e benefícios |
| **Thiago Moreira** *(nova)* | Analista de operações · Logística | cria e usa, com fluxo em paralelo | troca de maquininha exige cadastro + estoque + chamado |
| **Lucas Prado** | Engenheiro de segurança · Engenharia | governa | não tem headcount para construir um agente por time |
| **Helena Castro** | Gestora do CoE de IA | gere | precisa provar ROI e controlar custo da IA |

### 2.1 Processos AS IS → TO BE por persona

Os tempos AS IS partem do `minutos_manual` que já existe nos agentes de exemplo. Todos são **(hipótese)**.

**Marina: resposta a dúvidas de lojistas**
- AS IS (≈ 8 min, hipótese): lê o chamado → abre o cadastro no backoffice → procura a política na wiki → redige → revisa o tom → responde. Erros típicos: política desatualizada, prazo prometido fora da regra.
- TO BE (≈ 1,5 min, incluindo a conferência humana): seleciona o texto do chamado na extensão → o agente consulta o cadastro e a política em paralelo → devolve a resposta pronta citando a regra → Marina confere e copia.
- Valor medido: tempo por tarefa, respostas por dia, retrabalho por política errada e custo por resposta (Haiku).

**Rafael: triagem de chargebacks**
- AS IS (≈ 25 min, hipótese): exporta contestações → cruza com o cadastro → consulta a política de risco → decide → abre o chamado → pede o bloqueio por e-mail.
- TO BE (≈ 4 min): informa o lojista → cadastro e contestações rodam juntos → análise com Sonnet (o roteador explica por quê) → chamado aberto → a retenção **pausa pedindo a confirmação de Rafael**.
- Valor medido: tempo, lojistas triados por dia, falsos bloqueios evitados e custo por triagem. A confirmação humana e a auditoria aparecem como prova de governança.

**Carla: orientação de férias e benefícios**
- AS IS (≈ 10 min, hipótese): recebe a pergunta → abre a ficha do colaborador → consulta a política de RH → responde.
- TO BE (≈ 1 min): o colaborador pergunta → o agente usa a ficha (dado confidencial que nunca chega ao modelo sem máscara) → resposta com a regra.
- Valor medido: tempo, perguntas resolvidas sem a Carla e zero dado pessoal no log (auditoria).

**Thiago: troca de maquininha** *(nova)*
- AS IS (≈ 12 min, hipótese): confere o cadastro → confere a regra de troca → verifica estoque → abre o chamado na logística → avisa o lojista.
- TO BE (≈ 2 min): agente com passos em paralelo (cadastro + regra + estoque) → chamado aberto → aviso pronto.
- Valor medido: tempo, trocas processadas por dia e erros de troca fora da regra.

**Lucas: governança sem headcount**
- AS IS: cada time pede um agente → Engenharia constrói → semanas de fila. Shadow IT quando a fila trava.
- TO BE: o Lucas mantém o **catálogo** de ferramentas uma vez e revisa só os agentes de risco alto (quatro olhos). Quando um sistema cai, o alerta chega, e ele pausa um agente com um clique.
- Valor medido: agentes publicados sem código novo, tempo de revisão e incidentes detectados pelo alerta.

**Helena: gestão do CoE**
- AS IS: não sabe quanto a IA custa nem quanto devolve, e cada time usa uma ferramenta diferente.
- TO BE: painel com os 5 critérios da banca, AS IS × TO BE por processo, economia do roteador, orçamento com corte e calculadora de ROI.
- Valor medido: ROI, payback, custo por área e economia do roteador.

### 2.2 Jornada padrão de cada roteiro

Cada persona criadora (Marina, Rafael, Carla e Thiago) percorre a mesma espinha, e Lucas e Helena entram como contrapartes:

1. **Contexto**: cartão AS IS da persona (passos, tempo, dor).
2. **Criar**: no Estúdio, descreve o processo com o texto do roteiro → o agente é montado → explicação simples, risco e custo estimado.
3. **Testar**: sandbox com uma entrada do roteiro, escolhida por nome.
4. **Publicar**: risco baixo publica direto. Risco alto vai para a revisão do Lucas, e o roteiro troca de perfil sozinho.
5. **Usar**: a persona usa o agente no dia a dia, pela plataforma e pela extensão sobre uma página fictícia (helpdesk ou CRM).
6. **Medir**: cartão TO BE com o tempo e o custo da execução real e o ganho projetado no painel da Helena.
7. **Perguntas da banca**: 3 a 5 perguntas prováveis, com a resposta e o botão "mostrar na tela".

## 3. Mudanças por frente

### A. Roteiros guiados (modo apresentação)
- Catálogo de roteiros (persona → processo → passos), cada passo com tela, ação esperada, entrada pré-definida e fala sugerida do apresentador.
- Barra do roteiro na plataforma: "Passo 3 de 7 · Publicar o agente", com avançar, voltar, reiniciar o roteiro e trocar de perfil automaticamente.
- "Reiniciar a demo" passa a reiniciar **por roteiro** e deixa o estado exato de que aquele roteiro precisa.

### B. Base de respostas pré-determinadas
- **Para os agentes:** o simulador passa a responder com textos realistas por agente e entrada, por exemplo "O lojista Eletrônicos Relâmpago teve 10 contestações (R$ 86 mil) em 7 dias, 5× a média…", no lugar de "resposta simulada. Dados considerados".
- **Para o pitch:** base de perguntas e respostas da banca por persona e por tema (segurança, custo, escala, por que não low-code genérico), cada uma ligada à evidência na tela.

### C. Usuários e entradas mais amigáveis
- **Entrar:** a tela vira "Quem é você hoje?", com cartões de persona (avatar, cargo, o que a pessoa faz na plataforma e o roteiro dela). A troca de perfil fica num menu no avatar, sem voltar à tela inicial.
- **Fim do "colaborador ID":** cada persona passa a ter a própria matrícula. Campos do tipo "colaborador" já vêm com "Eu mesmo", e a pessoa pode buscar outro colaborador por nome, se tiver permissão.
- **Lojistas por nome:** campo com busca ("Padaria Pão Dourado · L1001"). O código aparece como detalhe, não como pergunta.
- **Campos com rótulo e ajuda:** os campos de entrada do agente deixam de ser `lojista_id` e passam a ter rótulo, tipo e exemplo. O Estúdio gera os rótulos.

### D. Extensão copiloto v5
Hoje ela é um botão genérico e uma moldura (iframe) da tela de agentes, sem identidade visual nem estados.
- **Painel lateral redesenhado** como copiloto de chat: cabeçalho com a pessoa logada e o status da conexão, sugestão de agente a partir do trecho selecionado, campos já preenchidos com o que foi detectado no trecho (lojista, CNPJ, nome), passos ao vivo, confirmação inline e histórico da sessão.
- **Botão flutuante** discreto, que aparece só quando há texto selecionado, com o atalho "Perguntar ao StoneFalcon".
- **Menu de contexto por agente**, por exemplo "Responder com: Dúvidas de lojistas".
- **Primeira execução e conexão:** tela de boas-vindas, teste de conexão com diagnóstico claro e escolha de perfil.
- **Visual:** a mesma identidade da plataforma (paleta pedra/falcão, tipografia), tema escuro, ícones refeitos e estados de carregando, erro e vazio.
- **Página de demonstração** servida pela plataforma (um helpdesk fictício com chamados de lojistas) para os roteiros usarem a extensão sem depender de sites externos.

## 4. Tickets (fatias verticais)

O rastreador de tickets não está configurado no projeto (`/setup-matt-pocock-skills` não foi rodado). Depois que o grupo aprovar esta lista, cada ticket vira um arquivo em `.scratch/stonefalcon-v5/issues/`.

| # | Ticket | Bloqueado por | O que entrega (de ponta a ponta) |
|---|---|---|---|
| 01 | Campos de entrada com rótulo e tipo (expandir) | — | Agentes aceitam campos com rótulo, tipo (lojista, colaborador, texto) e exemplo, ao lado do formato antigo. Os agentes de exemplo e o Estúdio passam a gerar o novo formato, e nada quebra. |
| 02 | Personas v5 e "Quem é você hoje?" | — | 6 personas com matrícula, avatar e descrição. Nova tela de entrada e menu de troca de perfil no avatar. Thiago incluído, com papéis e área de Logística. |
| 03 | Escolher lojista e colaborador por nome | 01, 02 | No sandbox do Estúdio, na execução de agentes e na tela da extensão, a pessoa busca o lojista por nome e o colaborador vem como "Eu mesmo". Nenhum campo pede código. |
| 04 | Respostas pré-determinadas dos agentes | — | O simulador responde com textos realistas por agente e entrada, e o modo real usa esses textos como reserva. Os 3 agentes atuais são cobertos. |
| 05 | Roteiro da Marina (bala traçante) | 02, 03, 04 | Primeira rota completa: cartão AS IS → criar no Estúdio → testar → publicar → usar → cartão TO BE com tempo e custo medidos. Inclui a barra do roteiro, o reinício por roteiro e 3 a 5 perguntas da banca. |
| 06 | Roteiro do Rafael | 05 | Chargeback com execução paralela, roteador explicando o Sonnet, pausa para confirmação e trilha de auditoria. Perguntas da banca sobre ação sensível. |
| 07 | Roteiro da Carla | 05 | Férias e benefícios com dado confidencial mascarado e prova na auditoria. Perguntas sobre LGPD e vazamento. |
| 08 | Roteiro do Thiago | 05 | Nova ferramenta fictícia de estoque, agente de troca de maquininha com 3 passos em paralelo, chamado e aviso. Perguntas sobre integração com sistemas. |
| 09 | Roteiro do Lucas | 05 | Revisão de segurança (quatro olhos) de um agente de risco alto vindo de outro roteiro, sistema fora do ar → alerta → pausa de emergência → normalização. Perguntas sobre governança e escala sem headcount. |
| 10 | Roteiro da Helena e AS IS × TO BE consolidado | 06, 07, 08, 09 | Painel com o AS IS × TO BE de todos os processos, os 5 critérios, a economia do roteador e a calculadora ligada aos processos dos roteiros. Perguntas sobre ROI e custo. |
| 11 | Modo apresentador e base de perguntas da banca | 05 | Tela de perguntas por persona e por tema, cada uma com a resposta curta e o botão "mostrar na tela", que leva ao passo do roteiro. Atalho para abrir no meio da demo. |
| 12 | Extensão: painel copiloto | 03, 04 | O painel lateral vira chat: sugere o agente pelo trecho, preenche campos detectados, mostra passos ao vivo e a confirmação inline. Tem estados de conexão, erro e vazio. |
| 13 | Extensão: botão, menu, boas-vindas e visual | 12 | Botão flutuante só com seleção, menu de contexto por agente, tela de boas-vindas e conexão, ícones novos e tema escuro. |
| 14 | Página de demonstração para a extensão | 12, 05 | Helpdesk fictício servido pela plataforma. Os roteiros da Marina e do Rafael ganham o passo "usar pela extensão" sobre essa página. |
| 15 | Campos de entrada: remover o formato antigo (contrair) | 03, 06, 07, 08, 09 | Nenhum agente nem tela usa mais os campos sem rótulo, e o formato antigo é removido. |
| 16 | Ensaio geral | 10, 11, 13, 14, 15 | Teste automático que percorre os 6 roteiros do início ao fim, checklist de apresentação (cotação, chave, reinício) e roteiro de 8 a 10 minutos para o pitch. |

**Ordem de trabalho:** 01, 02 e 04 começam juntos. Depois vem o 03 e então o 05, a bala traçante que valida o formato dos roteiros antes de replicá-lo. Os tickets 06 a 09 e o 12 podem correr em paralelo.

### Critérios de aceite comuns a todo roteiro
- Roda do início ao fim sem digitar nada além do que o roteiro mostra e sem chave da API.
- Termina com o AS IS × TO BE em números, e cada número diz se é medido na execução ou hipótese.
- Tem de 3 a 5 perguntas da banca, cada uma com a tela que serve de prova.
- Reiniciar o roteiro devolve exatamente o estado inicial.
- Os testes automáticos atuais continuam passando.

## 5. Decisões para o grupo

1. Entra a 6ª persona (Thiago, Logística) ou o grupo fica com 5?
2. Os tempos AS IS são hipóteses. Alguém do grupo consegue validá-los com pessoas da área ou com dados públicos?
3. A extensão continua mostrando a tela da plataforma por dentro (moldura) ou o painel passa a ser desenhado na própria extensão? A moldura é mais barata e mantém uma só tela; o painel próprio dá mais liberdade visual. **Recomendação:** manter a moldura e redesenhar a tela `/extensao`.
4. Qual a duração do pitch? Isso define se os 6 roteiros entram completos ou se alguns aparecem só como cartão AS IS × TO BE.

## 6. Status da execução

Executado em uma única passada, sem as decisões do grupo (seção 5): usei as recomendações do plano. **Se o grupo decidir diferente, o ajuste é pequeno**: a 6ª persona é um item em `PERSONAS` e `ROTEIROS`; a moldura da extensão foi mantida (recomendação 3).

| # | Ticket | Estado |
|---|---|---|
| 01 | Campos com rótulo e tipo | Feito (`Blueprint.campos`; o formato antigo continua sendo lido e convertido) |
| 02 | Personas v5 e “Quem é você hoje?” | Feito (6 personas, matrícula, avatar, menu no avatar) |
| 03 | Escolher lojista e colaborador por nome | Feito (sandbox, execução e extensão) |
| 04 | Respostas pré-determinadas | Feito (`runtime/respostas.py`; reserva no modo real) |
| 05 | Roteiro da Marina | Feito, testado na interface |
| 06 | Roteiro do Rafael | Feito, testado na interface |
| 07 | Roteiro da Carla | Feito, testado pelo ensaio via API |
| 08 | Roteiro do Thiago | Feito, testado pelo ensaio via API (ferramenta de estoque nova) |
| 09 | Roteiro do Lucas | Feito, testado na interface até o catálogo |
| 10 | Roteiro da Helena e consolidado | Feito (consolidado, calculadora partindo dos processos) |
| 11 | Modo apresentador e perguntas da banca | Feito (`/banca`, Alt + B, “Mostrar na tela”) |
| 12 | Extensão: painel copiloto | Feito, testado dentro do helpdesk |
| 13 | Extensão: botão, menu, boas-vindas, visual | Feito; **não exercitado no Chrome** (só checagem de sintaxe e manifesto) |
| 14 | Página de demonstração para a extensão | Feito (`/demo/helpdesk`, com painel de reserva sem a extensão) |
| 15 | Remover o formato antigo dos campos | Feito nas telas, nos exemplos e no que se grava; a leitura de versões antigas fica de propósito |
| 16 | Ensaio geral | Feito: `tests/test_roteiros.py`, [ENSAIO-GERAL.md](ENSAIO-GERAL.md) |

**Pendências que dependem do grupo:** validar os tempos AS IS com pessoas da área (hoje são hipóteses marcadas na tela), carregar a extensão no Chrome uma vez e fechar a duração do pitch (o roteiro sugerido é de 9 a 10 minutos).
