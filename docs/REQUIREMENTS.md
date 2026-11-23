# StoneFalcon — Requisitos

O que a plataforma precisa fazer e respeitar (estado da v8). Como ela é montada: [ARCHITECTURE.md](ARCHITECTURE.md). Linguagem visual: [DESIGN.md](DESIGN.md). Como trabalhar no repositório: [AGENTS.md](AGENTS.md).

> Protótipo acadêmico (UFSC) para o desafio StoneLab. Não é um produto da Stone. Pessoas, áreas e dados são fictícios.

**Propósito.** Qualquer colaborador descreve um processo em português e recebe um agente pronto, ligado só às ferramentas que o seu papel permite, com guardrails, monitoramento e custo sob controle. Engenharia e Segurança governam o catálogo, não cada agente.

## 1. Personas e papéis

Seis pessoas fictícias, entradas pelo login simulado (tela “Quem é você hoje?”). A fonte é `backend/app/core/identidade.py`.

| Persona | Área | Cargo | Nível de acesso | Papéis |
|---|---|---|---|---|
| Marina Duarte | Atendimento | Analista de atendimento | interna | criador, curador |
| Rafael Lima | Prevenção a Fraudes | Analista de risco | restrita | criador, curador |
| Carla Nogueira | Pessoas (RH) | Business partner de RH | confidencial | criador, curador, consulta de colaboradores |
| Thiago Moreira | Logística | Analista de operações | interna | criador, curador |
| Lucas Prado | Engenharia de Plataforma | Engenheiro de segurança | confidencial | criador, revisor de segurança, engenharia |
| Helena Castro | CoE de IA | Gestora do CoE de IA | interna | criador, gestor de IA, analista de IA |

Todos têm também o papel `usuario` (executa o que foi publicado e a que tem acesso).

| Papel | O que permite |
|---|---|
| `criador` | Cria e mantém agentes e processos da própria área, só com ferramentas que ele mesmo pode usar. |
| `curador` | Aprova respostas para a base de conhecimento da área. |
| `revisor_seguranca` | Aprova a publicação de versões de risco alto e de plugins confidenciais ou restritos. |
| `engenharia` | Registra conectores no catálogo e integra plugins. |
| `consulta_colaboradores` | Busca outros colaboradores por nome (RH). |
| `gestor_ia` | Vê custos, retorno, saúde e auditoria de toda a empresa; reinicia a demonstração. |
| `ai_analyst` | Decide os pedidos “Crie o seu plugin”. |

**Nível de acesso** (`publica < interna < confidencial < restrita`) é um eixo separado dos papéis: diz até que classificação de *dado* a pessoa toca.

## 2. Matriz de acesso por aba

Decidida no back (`ABAS` em `identidade.py`); o front só lê (`abas` em `/api/v1/eu`). Endereço digitado sem permissão volta ao Início; a API responde 403.

| Aba | Marina | Rafael | Carla | Thiago | Lucas | Helena |
|---|:-:|:-:|:-:|:-:|:-:|:-:|
| Início | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ |
| Roteiros (todos) | | | | | | ✔ |
| Painel executivo | | | | | | ✔ |
| Perguntas da Ferramenta (Alt + B) | | | | | | ✔ |
| Mapa de IA | | | | | | ✔ |
| Plugins | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ |
| Estúdio | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ |
| Agentes | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ |
| Processos | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ |
| Revisões | | | | | ✔ | |
| Execuções | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ |
| Saúde | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ |
| Finanças | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ |
| Ferramentas | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ |
| Auditoria | | | | | ✔ | ✔ |

Regras além das abas:

- **Processos:** todos veem; só criadores da área criam e editam; executar exige a área e o nível. Na 8.1 o Lucas e a Helena também são criadores (cada um tem o seu processo na demo); ninguém aprova o próprio risco alto.
- **Alertas:** vê o alerta quem é destinatário (dono, Engenharia no caso de sistema) e a Helena, que vê todos; **assumir** é só de quem vê (os demais recebem 404); **devolver** é de quem assumiu ou da Helena; a **ação** da regra só aparece para quem pode executá-la (pausar: quem opera o processo; revisar o orçamento: o dono ou a Helena; restaurar o provedor: a Helena; abrir o sistema em Saúde ou o processo lento: quem recebe o alerta; alerta assumido por outra pessoa: só a Helena).
- **Arquivos e Planilhas:** ler e escrever exige a **área e o nível** do arquivo; escrita em arquivo confidencial ou restrito espera a confirmação de uma pessoa.
- **Crie o seu plugin:** só criadores e Engenharia (os demais recebem 403).
- **Decidir pedido de plugin:** Helena; Lucas quando o dado é confidencial ou restrito; ninguém decide o próprio pedido.

## 3. Requisitos funcionais

### 3.1 Entrada e navegação

- **RF-01** A pessoa escolhe um dos seis perfis na tela de entrada. Em tela larga, por uma roda de fotos; em tela estreita, por cartões.
- **RF-02** Entrar sempre abre o Início da persona, qualquer que seja a tela em que a pessoa anterior estava ao sair.
- **RF-03** O menu mostra só as abas a que o perfil tem acesso, em Início mais quatro grupos sanfonados (Construir, Acompanhar, Gestão e valor, Apresentação): um grupo aberto por vez, o grupo da página atual abre sozinho, grupo sem aba permitida some e grupo com uma aba é um link simples. Nenhuma aba fica fora do alcance em 1366 × 768 (o menu rola por dentro em janelas mais baixas).
- **RF-04** A pessoa troca de perfil ou sai pelo menu do avatar; trocar abre o Início.
- **RF-05** A tela de entrada tem a opção de iniciar o roteiro guiado do perfil.
- **RF-06** Todo texto da interface está em português do Brasil, em linguagem simples.

### 3.2 Agentes

- **RF-10** Descrever um processo em português e receber um agente montado (passos, ferramentas, modelo, risco e custo estimado), explicado em linguagem simples (Estúdio).
- **RF-11** Editar o agente num canvas e testá-lo num sandbox antes de publicar.
- **RF-12** O agente faz uma única tarefa de IA. Um agente novo com mais de um passo é recusado, com mensagem apontando para os Processos.
- **RF-13** Ciclo de vida: rascunho → revisão → publicado ⇄ pausado → depreciado. A versão publicada é imutável; editar gera nova versão em rascunho, com diff entre versões.
- **RF-14** Toda versão de risco alto passa pela revisão da Segurança, feita por alguém que não é o autor.
- **RF-15** Segurança e CoE pausam qualquer agente na hora (botão de emergência), inclusive barrando ações já pendentes.
- **RF-16** Agentes antigos de vários passos continuam rodando, em leitura, e podem ser convertidos em processo.
- **RF-17** A galeria do Estúdio oferece padrões “trabalhador + processo” por persona (Marina, Rafael, Carla, Thiago, Lucas e Helena); escolher um abre o trabalhador de um passo e o processo pronto para montar. Os padrões vêm do catálogo único da demo (`seed/catalogo.py`).

### 3.3 Processos

- **RF-20** Montar um processo por blocos, sem código: dados, agente, plugin/ação, aprovação, condição e saída, num canvas.
- **RF-21** As saídas de um bloco entram em outros por seleção em lista, sem digitar referências.
- **RF-22** O processo tem dono, versões imutáveis e o mesmo ciclo de vida do agente, com revisão da Segurança no risco alto.
- **RF-23** Ação sensível dentro do processo pausa a execução até uma pessoa confirmar.
- **RF-24** O processo mostra o custo estimado e valida o fluxo antes de publicar.
- **RF-25** Se um agente do processo está pausado, depreciado ou sem acesso, o passo escala com o motivo em vez de falhar em silêncio.

### 3.4 Execução e ferramentas

- **RF-30** Executar um agente ou processo publicado a que a pessoa tem acesso, na plataforma ou pela extensão.
- **RF-31** Passos independentes rodam em paralelo; os dependentes, em sequência.
- **RF-32** Cada ferramenta tem classificação (pública → restrita) e áreas. Roda com as permissões de **quem disparou**; um agente criado por alguém com mais acesso nunca vira porta dos fundos.
- **RF-33** Ação sensível espera a confirmação humana; a execução pode ser retomada depois da decisão.
- **RF-34** Limites por execução (custo, chamadas de modelo, iterações por passo). Falha que o agente não contorna vira **escalada** para um humano, com o motivo.
- **RF-35** O balanceador escolhe, por passo, o modelo mais barato que atende, delega a outro provedor quando um cai e explica a decisão (“como o agente decidiu”).
- **RF-36** Rotinas: agendar um agente ou processo publicado (“toda segunda às 9h”) com entrada fixa; roda em nome de quem agendou, com as mesmas permissões e limites.

### 3.5 Plugins

- **RF-40** Marketplace com 10 plugins homologados. O Arquivos e Planilhas funciona de verdade; os demais são simulados e identificados como tal.
- **RF-41** Plugin público ou interno é integrado na hora por criador da área ou Engenharia; confidencial ou restrito vira pedido na fila de Revisões, com parecer.
- **RF-42** Remover a integração tira as ferramentas do catálogo; agentes que as usam ficam sinalizados e escalam com o motivo.
- **RF-43** Arquivos e Planilhas: enviar CSV ou Excel (até 2 MB, 5.000 linhas e 30 colunas) com classificação (no máximo o nível de quem envia) e áreas; listar, ler com filtro, achar, acrescentar e atualizar linhas; cada escrita registra quem, qual agente ou processo e qual linha.
- **RF-44** Crie o seu plugin: a partir da descrição **pública** de uma ferramenta de mercado, a plataforma rascunha um plugin interno (nome e ícone genéricos, ferramentas, riscos, conta de comprar × construir); aprovado, entra no marketplace como interno e conceitual.

### 3.6 Roteiros guiados

- **RF-50** Cada persona tem um roteiro: a mesma jornada, do mesmo jeito sempre, com entradas pré-determinadas e sem chave da API.
- **RF-51** A barra do roteiro mostra o passo, a ação esperada e a fala sugerida; avançar troca de perfil sozinho e abre a tela do passo.
- **RF-52** Reiniciar devolve a plataforma ao estado exato do início do roteiro.
- **RF-53** O roteiro termina num cartão AS IS × TO BE nos cinco critérios (tempo, custo, produtividade, erros, ROI), e cada número diz de onde vem: medido, estimado, premissa ou hipótese.
- **RF-54** Perguntas da Ferramenta (só da Helena): perguntas por persona e tema, com resposta curta e botão “Mostrar na tela”.

### 3.7 Finanças e painel

- **RF-60** Custo por execução, agente, processo, área, provedor e modelo; economia do roteador; retorno por agente e por processo.
- **RF-61** Orçamento mensal com aviso a 80% e corte a 100%.
- **RF-62** Calculadora de investimento (fluxo de caixa mensal, VPL, TIR, payback) com premissas editáveis e fonte.
- **RF-63** Exportar o resumo financeiro para planilha (Helena).
- **RF-64** Painel executivo com os cinco critérios, medidos nas execuções; Mapa de IA ao vivo (quem criou → agentes → modelos → plugins → plataformas).

### 3.8 Saúde, alertas e auditoria

- **RF-70** Métricas e nota de saúde por agente, por sistema integrado e por provedor.
- **RF-71** Alertas automáticos ao responsável, sem configuração, para **agentes que rodam sozinhos e para processos**: falhando, lento, sistema fora, sistema lento, orçamento (80% atenção, 100% corte) e provedor fora. O alerta de processo vai ao dono, aos criadores das áreas com quem o processo é compartilhado (sem repetir ninguém) e, no caso de sistema, à Engenharia; mudar o compartilhamento atualiza os destinatários dos alertas abertos; vale uma vez por processo (não por trabalhador) e leva a “Abrir o processo”. Cada alerta abre uma vez e fecha sozinho quando a condição some; abertura e fechamento ficam na trilha.
- **RF-75** Tratar o alerta: quem o recebe pode **assumi-lo** com uma nota curta (“em tratamento · por X”, com nota e hora, para todos os destinatários) e **devolvê-lo**; o alerta resolvido sozinho guarda quem estava tratando. Assumir, devolver e a ação ficam na trilha.
- **RF-76** Cada regra de alerta tem uma **ação primária** que respeita o perfil e usa as mesmas funções das telas atuais (pausa de emergência, orçamento, abrir o sistema em Saúde, abrir o processo ou o agente lento, restaurar o provedor); executá-la assume o alerta. Em alerta assumido por outra pessoa, só o CoE de IA tem a ação, e ela o assume no lugar (a trilha guarda quem tratava antes); nada é executado antes de todas as checagens passarem.
- **RF-77b** Processo compartilhado: as áreas com quem ele é compartilhado veem o processo, o histórico e as execuções dele (nas duas pontas), podem executá-lo mas não editá-lo, e as duas pontas veem o selo “Compartilhado” com o sentido certo (“com Engenharia” para o dono, “de Logística · Thiago” para quem recebe). O dono, ou um criador da área dona, compartilha e para de compartilhar pela tela; a mudança vai para a trilha e vale na hora. O compartilhamento não estende o acesso aos arquivos que o processo lê.
- **RF-77** Estado inicial da demo: cada uma das seis personas entra com um alerta aberto não lido, um lido, um em tratamento (com nota) e um resolvido, todos produzidos pelas regras reais (estado de sistema, histórico, orçamento e provedor moldados; nenhum alerta é inserido direto), e um alerta no processo compartilhado entre Thiago e Lucas. Um banco semeado por uma versão antiga volta a esse estado ao subir (selo de versão do seed); um banco atual não é tocado. O Início mostra os alertas abertos da pessoa (até três, os mais graves primeiro). Os roteiros guiados começam sem alertas e trazem o passo “veja e trate o seu alerta”.
- **RF-72** Trilha de auditoria encadeada por hash cobrindo criação, modificação, revisão, execução, escalada, aprovação, plugins, rotinas e depreciação; alterar ou apagar uma linha quebra a cadeia e a verificação aponta onde.
- **RF-73** Guardrails silenciosos: CPF, CNPJ, cartão, e-mail, telefone e segredos viram marcadores antes de qualquer modelo e antes da auditoria; o dado real volta só na tela de quem perguntou, e só para sistema cuja classificação cobre a do dado.
- **RF-74** Conteúdo externo com cara de instrução (injeção) é sinalizado e entregue ao modelo como dado, não como ordem.

### 3.9 Extensão copiloto

- **RF-80** Botão flutuante sobre texto selecionado e menu do botão direito: “StoneFalcon → Responder com: *agente*”, com o que o perfil pode usar.
- **RF-81** Painel lateral que sugere o processo ou agente pelo trecho, preenche os campos detectados, mostra os passos e pede confirmação de ação sensível ali mesmo.
- **RF-82** A extensão não tem lógica nem chave: roda tudo na plataforma, com as permissões de quem está logado.
- **RF-83** Atalho “Criar Agente de IA” abre o Estúdio no mesmo perfil por passe de uso único (60 s, vale uma vez); quem não tem a aba Estúdio vê que o perfil não cria agentes.
- **RF-84** Helpdesk e planilha fictícios (`/demo/helpdesk`, `/demo/planilha`) permitem ensaiar sem instalar a extensão e sem internet.

## 4. Requisitos não funcionais

- **RNF-01 Offline em modo simulado.** Sem `ANTHROPIC_API_KEY`, tudo roda sem chave, sem custo e sem internet. Runtime, permissões, guardrails, auditoria, alertas e custos funcionam como no modo real; só o texto dos modelos é de exemplo, e tokens e custos são estimados com a mesma régua. O selo “Modo simulado” ou “Modelos reais” aparece no topo.
- **RNF-02 Português do Brasil.** Interface e documentação em português do Brasil.
- **RNF-03 Dados fictícios.** Pessoas, áreas, lojistas, políticas e sistemas são fictícios; nada é apresentado como produto oficial da Stone.
- **RNF-04 Acesso decidido pelo back.** O front e a extensão só leem; a API confere de novo.
- **RNF-05 Segredos fora do código.** Nenhuma chave no código, na extensão ou no Git (`backend/.env` está no `.gitignore`).
- **RNF-06 Auditoria íntegra.** Todo evento relevante é registrado e a cadeia é verificável; dados chegam à trilha já mascarados.
- **RNF-07 Restauração da demonstração.** Reiniciar volta ao estado inicial, geral ou o exato de um roteiro (apaga o banco, inclusive a auditoria). Fora de apresentações, `STONEFALCON_DEMO=0` restringe o reinício ao CoE.
- **RNF-08 Instalação simples.** `iniciar.bat` ou `sh iniciar.sh` sobem a plataforma com Python 3.11+ (e Node.js só para compilar as telas na primeira vez), com mensagens claras em português para Python antigo, Node ausente e porta ocupada.
- **RNF-09 Compatibilidade de dados.** Atualizar para uma versão nova mantém o banco; só entram tabelas e colunas.
- **RNF-10 Versão única.** API, front e extensão contam o mesmo número, conferido na CI.
- **RNF-11 Acessibilidade e movimento.** Uso só pelo teclado, informação que não dependa só de cor e respeito a “reduzir movimento” (detalhes em [DESIGN.md](DESIGN.md)).
- **RNF-12 Um processo só.** O protótipo roda sem vários processos do back (trava da auditoria e cache de plugins em memória).

## 5. Critérios comuns de todo ticket

Herdados do plano da v8 e válidos para qualquer entrega:

1. Texto de interface em português do Brasil, linguagem simples.
2. Pessoas, áreas e dados seguem fictícios; nada apresentado como produto oficial da Stone.
3. Tudo funciona em modo simulado, sem chave da API nem internet.
4. Acesso decidido pelo back; o front só lê.
5. O front não tem testes automatizados: critérios de tela se cumprem com checagem de tipos e compilação verdes mais verificação no navegador (captura de tela no PR).
6. A esteira de CI fica verde (back, front, extensão, versão e scripts de início).
7. Um ticket = um branch = um PR; os critérios de aceite do ticket são caixas marcáveis.
