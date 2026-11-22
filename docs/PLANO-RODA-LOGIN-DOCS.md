# StoneFalcon — Plano: roda seletora, entrada no Início e documentos do repositório

> Parte do estado entregue na v8 (`main`). Cada ticket é uma fatia vertical, demonstrável sozinha, entregue como um PR com a esteira de CI verde. Este arquivo é a fonte única da execução: siga a ordem da seção 4 e marque as caixas aqui conforme avança.

## 1. O que muda e por quê

1. **Roda seletora de personas mais limpa.** Hoje, em repouso, as seis fatias mostram foto, uma sombra escura sobre todas e o primeiro nome com contorno; o miolo traz uma instrução que cita as setas do teclado (que só respondem depois de focar uma fatia com Tab, então para quem lê parecem não funcionar). Ao passar o mouse, o miolo empilha nome, cargo, área, descrição longa, selos de papel, selo de acesso e o botão de roteiro. O redesenho deixa só as fotos em repouso e revela os detalhes aos poucos.
2. **Entrar sempre abre o Início da persona.** Ao sair, o perfil é limpo mas o endereço continua o mesmo; ao entrar com outra persona, ela abre na tela em que a anterior estava (se tiver acesso àquela aba). Entrar passa a levar sempre ao Início.
3. **Documentos do repositório.** `AGENTS.md`, `DESIGN.md`, `ARCHITECTURE.md` e `REQUIREMENTS.md` na raiz, para pessoas e agentes de código entenderem o projeto sem ler a história das versões.

## 2. Princípios de design aplicados (Apple HIG)

| Princípio | Diretriz | Como aparece na roda |
|---|---|---|
| Simplicidade | `design-principles.md › Simplicity`: "Include just what's necessary." | Em repouso, só as fotos. O nome não se repete na fatia: o miolo já o mostra. |
| Revelação progressiva | `layout.md › Visual hierarchy`: "Use progressive disclosure to make layouts cleaner and easier to interact with." | Detalhes só com mouse ou foco, e em menor quantidade que hoje. |
| Movimento com propósito | `motion.md`: "Add motion purposefully… Aim for brevity and precision in feedback animations." | Mantém a ampliação da fatia ativa; o escurecimento só existe nas vizinhas de uma fatia ativa. Movimento reduzido segue respeitado. |
| Acessibilidade | `accessibility.md`: "Let people use the keyboard alone to navigate and interact with your app." / "Convey information with more than color alone." | O teclado continua funcionando (só deixa de ser anunciado); nome no rótulo acessível de cada fatia; iniciais quando a foto falha. |

## 3. Decisões

| # | Decisão | Escolha |
|---|---|---|
| 1 | Teclado na roda | Remove a menção às teclas do texto; a navegação por Tab + setas + Enter continua existindo. |
| 2 | Selos de papel | Saem do miolo da roda; continuam nos cartões da tela estreita. |
| 3 | Idioma dos quatro documentos | Português do Brasil, como o `LEIA-ME.md`. |
| 4 | Versão | Não muda neste plano (segue 8.0.0). |

## 4. Tickets

| # | Ticket | Bloqueado por |
|---|---|---|
| 01 | Roda em repouso só com fotos | — |
| 02 | Miolo da roda enxuto ao passar o mouse | 01 |
| 03 | Entrar sempre abre o Início da persona | — |
| 04 | ARCHITECTURE.md | — |
| 05 | REQUIREMENTS.md | — |
| 06 | DESIGN.md | 01, 02 |
| 07 | AGENTS.md | 04, 05, 06 |

Fronteira inicial: 01, 03, 04 e 05 podem começar em paralelo.

---

### 01: Roda em repouso só com fotos

**O que construir:** ao abrir a tela "Quem é você hoje?" sem nada selecionado, a roda mostra apenas as seis fotos de perfil, limpas, sem nomes e sem a sombra escura. O miolo mantém a instrução de seleção, sem referência a teclas: "Quem é você hoje?" + "Passe o mouse sobre uma foto para ver quem é. Clique para entrar."

**Bloqueado por:** nenhum (pode começar já).

**Status:** feito (falta a evidência no PR)

- [x] Em repouso, nenhuma fatia exibe nome ou texto sobreposto; apenas a foto (ou as iniciais, quando a foto falha).
- [x] Em repouso, as fotos aparecem sem a camada escura.
- [x] O miolo em repouso não menciona setas nem teclado.
- [x] Cada fatia mantém o rótulo acessível com nome, cargo e área.
- [x] Tab, setas e Enter continuam funcionando na roda.
- [ ] Checagem de tipos e build passam; captura de tela da roda em repouso no PR.

### 02: Miolo da roda enxuto ao passar o mouse

**O que construir:** ao passar o mouse (ou focar) uma fatia, ela se amplia, as vizinhas escurecem levemente e o miolo mostra só o essencial: nome, cargo · área, descrição em até duas linhas, um selo de nível de acesso e o botão "Iniciar roteiro guiado" (quando a persona tem roteiro). Ao sair da roda, volta ao estado de repouso do ticket 01 sem piscar.

**Bloqueado por:** 01.

**Status:** feito (falta a evidência no PR)

- [x] O miolo ativo mostra apenas: nome, cargo · área, descrição (máx. 2 linhas), selo de acesso e botão de roteiro.
- [x] Os selos de papel não aparecem no miolo; continuam nos cartões da tela estreita.
- [x] O escurecimento das vizinhas só existe enquanto uma fatia está ativa.
- [x] Dá para ir da fatia ao botão do miolo com o mouse sem o miolo voltar ao repouso.
- [x] Com movimento reduzido ligado, não há animação; foco do teclado segue visível.
- [ ] Checagem de tipos e build passam; capturas de tela (repouso, ativa, foco) no PR.

### 03: Entrar sempre abre o Início da persona

**O que construir:** escolher um perfil na tela de entrada (pela roda ou pelos cartões) sempre abre o Início daquela persona, qualquer que seja a tela em que a pessoa anterior estava ao sair.

**Bloqueado por:** nenhum (pode começar já).

**Status:** feito (falta a evidência no PR)

- [x] Estando em uma tela interna (ex.: Processos), "Sair para a tela inicial" e entrar com outra persona abre o Início.
- [x] O mesmo vale entrando pelos cartões da tela estreita.
- [x] Trocar de perfil pelo menu do avatar continua abrindo o Início.
- [x] Iniciar um roteiro guiado pela tela de entrada continua abrindo o primeiro passo do roteiro.
- [x] A entrada pela extensão e pelo helpdesk não muda.
- [ ] Checagem de tipos e build passam; roteiro manual da verificação descrito no PR.

### 04: ARCHITECTURE.md

**O que construir:** um documento na raiz que explica como o StoneFalcon é montado: back (API, runtime de agentes e processos, plugins, guardrails, auditoria encadeada por hash, alertas, custos), front (rotas, acesso por abas vindo do back, roteiros guiados), extensão copiloto, modo simulado versus modelos reais, banco e scripts de início e de CI.

**Bloqueado por:** nenhum (pode começar já).

**Status:** feito

- [x] Visão geral com um diagrama (texto ou Mermaid) dos componentes e de como conversam.
- [x] Fluxo de uma execução de processo, do gatilho à auditoria.
- [x] Onde o acesso por perfil é decidido e como o front só o lê.
- [x] Modo simulado: o que é real e o que é exemplo.
- [x] Tudo confere com o código atual (nenhum módulo inventado).

### 05: REQUIREMENTS.md

**O que construir:** um documento na raiz com o que a plataforma precisa fazer e respeitar: as seis personas e seus papéis, a matriz de acesso por aba, requisitos funcionais por área (agentes, processos, plugins, roteiros, finanças, auditoria, extensão), requisitos não funcionais e os critérios comuns de todo ticket.

**Bloqueado por:** nenhum (pode começar já).

**Status:** feito

- [x] Personas e matriz de acesso iguais às que o back entrega hoje.
- [x] Requisitos funcionais numerados, em linguagem de usuário.
- [x] Requisitos não funcionais: funciona offline em modo simulado, português do Brasil, dados fictícios, auditoria, restauração da demonstração.
- [x] Critérios comuns de todo ticket (herdados do plano da v8).

### 06: DESIGN.md

**O que construir:** um documento na raiz com a linguagem visual do StoneFalcon: tokens de cor e tipografia, componentes recorrentes (caixa, selo, botões), padrões de tela, a roda seletora já redesenhada e os princípios da HIG adotados (seção 2 deste plano), incluindo regras de acessibilidade e movimento.

**Bloqueado por:** 01, 02.

**Status:** feito

- [x] Tokens de cor (claro e escuro, se houver) e fontes, com seus papéis.
- [x] Componentes recorrentes com quando usar cada um.
- [x] Seção da roda: estados de repouso, ativa e foco, e o que cada um mostra.
- [x] Regras de acessibilidade e movimento que todo ticket de tela deve seguir.

### 07: AGENTS.md

**O que construir:** um guia na raiz para agentes de código (e pessoas novas) trabalharem no repositório: como ligar, testar e verificar; um ticket = um branch = um PR; o que a CI checa; convenções (interface em português do Brasil, dados fictícios, acesso decidido pelo back, nada de chave no código); e links para ARCHITECTURE, REQUIREMENTS e DESIGN.

**Bloqueado por:** 04, 05, 06.

**Status:** feito

- [x] Comandos de desenvolvimento e de teste conferidos (rodam como descritos).
- [x] Fluxo de entrega e checagens da CI.
- [x] Convenções e proibições do projeto.
- [x] Links para os outros três documentos.

## 5. Critérios comuns (todo ticket)

- Texto de interface em português do Brasil, linguagem simples.
- Pessoas, áreas e dados seguem fictícios; nada apresentado como produto oficial da Stone.
- Tudo funciona em modo simulado, sem chave da API nem internet.
- Acesso decidido pelo back; o front só lê.
- O front não tem testes automatizados: critérios de tela se cumprem com checagem de tipos e build verdes mais verificação no navegador (captura no PR).
