# Plano: processos de demonstração no lugar dos agentes legados e alertas tratáveis por persona

Base: `main` em `d7b7beb` (v8 + roda do login, versão 8.0.0). Um ticket = um commit (ou um PR por ticket).

## Contexto

- **Agente legado = agente de vários passos** (formato da v7). A v8 recusa agente novo com mais de um passo (422); os
  antigos rodam só leitura e oferecem "Converter em processo". O banco da demo já nasce sem legados (só trabalhadores de
  um passo), mas o formato antigo ainda aparece no código: os 6 padrões da galeria do Estúdio (2 a 5 passos), o endpoint
  `agentes-exemplo`, as linhas de base de ROI da medição dos roteiros e o exemplo do prompt do Estúdio.
- **Personas sem processo próprio:** Lucas e Helena (o "Registro de incidente de sistema" é do Thiago).
- **Alertas:** as regras só avaliam agentes. Execução de processo não tem `agente_id`, então processo com falha ou lento
  não alerta, e o orçamento do processo nunca abre alerta. A demo começa sem alerta, de propósito. Tratamento hoje:
  "Marcar como lido", link para o agente e fechamento automático.
- **Versão:** está certa (v8). A pasta v7 está em `baf350f` (7.0.0); `ce64181 v8 (#4)` é o squash dos 15 tickets da
  branch `v8` (árvore idêntica a `origin/v8`); `d7b7beb (#5)` é a correção da roda + docs (árvore idêntica a
  `docs/roda-login-docs`) e não subiu a versão. Este plano fecha como **8.1.0**.

## Resumo

| # | Ticket | Bloqueado por | Status |
|---|---|---|---|
| 01 | Prefatoração: uma fonte única da demo por persona | — | ready-for-agent |
| 02 | Galeria v8 do Estúdio no lugar dos padrões legados | 01 | ready-for-agent |
| 03 | Processo de demonstração do Lucas | 01 | ready-for-agent |
| 04 | Processo de demonstração da Helena | 01 | ready-for-agent |
| 05 | Alertas entendem processos | — | ready-for-agent |
| 06 | Alertas de demonstração por persona no estado inicial | 03, 04, 05 | ready-for-agent |
| 07 | Assumir o alerta | 05 | ready-for-agent |
| 08 | Ação de tratamento por regra | 06, 07 | ready-for-agent |
| 09 | Versão 8.1.0, docs e roteiros | 02, 08 | ready-for-agent |

Fronteira inicial: **01** e **05**.

---

# 01: Prefatoração: uma fonte única da demo por persona

**O que construir:** o estado inicial, os roteiros guiados e o Estúdio passam a ler um único catálogo "persona →
trabalhador + processo" (hoje as definições estão espalhadas entre os processos da demo, os padrões do Estúdio e os
agentes de exemplo). Os blueprints de vários passos saem do código da aplicação e viram fixtures só dos testes, que
continuam cobrindo o caminho legado (recusa 422, só leitura, "Converter em processo"). Nenhuma mudança visível.

**Bloqueado por:** nenhum (pode começar já).

**Status:** ready-for-agent

- [ ] Um catálogo por persona com chave estável, usado pelo seed, pelos roteiros e pelo Estúdio.
- [ ] Nenhum módulo da aplicação importa blueprint de vários passos; eles existem só como fixture de teste.
- [ ] Os testes de contrato legado (recusa, só leitura, conversão) continuam verdes usando a fixture.
- [ ] Banco semeado antes e depois é equivalente (mesmos agentes, processos, arquivos e histórico).
- [ ] `pytest` e `npm run build` verdes.

# 02: Galeria v8 do Estúdio no lugar dos padrões legados

**O que construir:** a galeria do Estúdio deixa de oferecer os 6 padrões de vários passos e oferece padrões
"trabalhador + processo" por persona. Escolher um padrão abre o trabalhador no Estúdio e o processo pronto para montar,
sem o aviso "legado". No modo simulado o Estúdio continua escolhendo o padrão mais parecido com a descrição; no modo real
o exemplo do prompt é um trabalhador de um passo. O endpoint `agentes-exemplo` sai e as linhas de base de ROI da medição
vêm dos processos.

**Bloqueado por:** 01

**Status:** ready-for-agent

- [ ] Nenhum padrão da galeria tem mais de um passo; nenhum dispara o aviso "legado".
- [ ] Um padrão para cada persona que cria (Marina, Rafael, Carla, Thiago), mais os de Lucas e Helena quando 03 e 04 entrarem.
- [ ] Descrições de exemplo de cada padrão ainda caem no padrão certo no modo simulado (teste por padrão).
- [ ] `agentes-exemplo` removido da API e de quem o chamava; medição dos roteiros com os mesmos números AS IS × TO BE.
- [ ] Roteiros de Marina, Rafael, Carla, Thiago e o pitch passam de ponta a ponta.

# 03: Processo de demonstração do Lucas

**O que construir:** o Lucas (Engenharia) passa a ter um processo próprio no estado inicial, por exemplo "Triagem de
incidente de sistema": dados (registro de incidentes e estado do sistema) → agente trabalhador "Analista de incidentes"
→ condição (incidente crítico?) → chamado na fila da Engenharia / saída. Aparece em Processos, na galeria, no Mapa de IA
e em Finanças, com histórico sintético coerente.

**Bloqueado por:** 01

**Status:** ready-for-agent

- [ ] Trabalhador (um passo) e processo publicados pelo ciclo de vida real, com dono Lucas e auditoria íntegra.
- [ ] Executável pelo Lucas em ≤ 3 cliques no modo simulado; quem não tem a área ou o nível é barrado e auditado.
- [ ] Aparece no Mapa de IA (camada processos) e em Finanças por processo, com histórico de 30 dias.
- [ ] "Reiniciar a demo" o recria.

# 04: Processo de demonstração da Helena

**O que construir:** a Helena (CoE de IA) passa a ter um processo próprio, por exemplo "Revisão mensal do custo de IA":
dados (resumo de Finanças / arquivo de finanças) → agente "Analista de custo de IA" → condição (acima do orçamento?) →
aviso. Mesma visibilidade do 03.

**Bloqueado por:** 01

**Status:** ready-for-agent

- [ ] Trabalhador e processo publicados pelo ciclo real, dono Helena, auditoria íntegra.
- [ ] Executável pela Helena em ≤ 3 cliques; resultado cita números das execuções.
- [ ] Aparece no Mapa de IA e em Finanças, com histórico de 30 dias.
- [ ] "Reiniciar a demo" o recria.

# 05: Alertas entendem processos

**O que construir:** as regras de alerta passam a avaliar processos publicados ou pausados: muitas execuções escaladas
(falhando), latência acima da habitual (lento), orçamento do processo a 80% / 100% e sistema integrado com problema
usado por um bloco do processo. O alerta vai ao dono do processo (e à Engenharia, no caso de sistema) e leva a
"Abrir o processo". Os alertas de agente que roda sozinho continuam como estão.

**Bloqueado por:** nenhum (pode começar já).

**Status:** ready-for-agent

- [ ] Processo com ≥ 30% das últimas execuções escaladas abre "falhando"; volta ao normal e o alerta fecha sozinho.
- [ ] Orçamento do processo a 80% abre atenção; a 100% abre crítico e as novas execuções são bloqueadas como hoje.
- [ ] Sistema fora usado por um bloco do processo alerta o dono do processo e a Engenharia, sem duplicar por trabalhador.
- [ ] Tela de Alertas e o sino mostram o alerta de processo com link "Abrir o processo"; Saúde conta o alerta na nota.
- [ ] Abertura e fechamento ficam na trilha.

# 06: Alertas de demonstração por persona no estado inicial

**O que construir:** cada uma das seis personas entra na demo com pelo menos um alerta aberto ligado ao seu papel,
produzido pelas regras reais (histórico e estado de sistema moldados), não por linhas falsas. Sugestão: Marina — sistema
lento no FAQ/cadastro; Rafael — triagem falhando; Carla — orçamento a 80%; Thiago — estoque ou Slack lento; Lucas —
sistema fora (com o processo dele); Helena — queda de provedor ou orçamento consolidado. "Reiniciar a demo" restaura;
os roteiros guiados continuam começando limpos.

**Bloqueado por:** 03, 04, 05

**Status:** ready-for-agent

- [ ] Logo após semear, cada persona vê ≥ 1 alerta não lido no sino, coerente com o próprio perfil.
- [ ] Nenhum alerta é inserido direto: todos nascem de `avaliar` sobre o estado semeado.
- [ ] "Reiniciar a demo" volta ao mesmo conjunto de alertas.
- [ ] Iniciar um roteiro guiado zera esses alertas e o roteiro do Lucas (sistema fora → alerta → pausa) segue igual.
- [ ] O histórico continua marcado como demonstração nas telas.

# 07: Assumir o alerta

**O que construir:** quem recebe um alerta pode **assumi-lo** com uma nota curta. O alerta mostra "em tratamento · por X"
para todos os destinatários, com a nota e a hora; dá para devolver. Tudo vai para a trilha. O fechamento continua
automático quando a condição some.

**Bloqueado por:** 05

**Status:** ready-for-agent

- [ ] Só destinatário (ou a Helena, que vê todos) assume; os demais recebem 404/403.
- [ ] Estado "em tratamento" visível na tela de Alertas, no filtro e no detalhe de Saúde.
- [ ] Assumir e devolver ficam na auditoria com quem, quando e a nota.
- [ ] Alerta resolvido sozinho guarda quem estava tratando.

# 08: Ação de tratamento por regra

**O que construir:** cada alerta oferece a ação que resolve o caso dele, respeitando o perfil: pausar o processo ou
agente (falhando, sistema fora), revisar o orçamento (Helena), abrir o sistema em Saúde (sistema lento/fora, Engenharia),
restaurar o provedor (queda de provedor, Helena). Executar a ação assume o alerta automaticamente e registra na trilha.

**Bloqueado por:** 06, 07

**Status:** ready-for-agent

- [ ] Cada regra tem uma ação primária; quem não pode executá-la não vê o botão.
- [ ] A ação usa as mesmas funções das telas atuais (pausa de emergência, orçamento, sistema, provedor).
- [ ] Depois da ação o alerta fica "em tratamento" e fecha sozinho quando a condição some.
- [ ] Para cada persona, o alerta semeado no 06 tem uma ação que ela consegue concluir em ≤ 3 cliques.

# 09: Versão 8.1.0, docs e roteiros

**O que construir:** a plataforma passa a contar 8.1.0 em todo lugar; LEIA-ME, ENSAIO-GERAL e os documentos de
`docs/` descrevem os processos de Lucas e Helena, a galeria v8 e o tratamento de alertas; os links quebrados pela
mudança dos documentos para `docs/` são corrigidos; o roteiro de cada persona ganha o passo "veja e trate o seu alerta".

**Bloqueado por:** 02, 08

**Status:** ready-for-agent

- [ ] `scripts/verifica_versao.py` verde com 8.1.0 (API, front, extensão, pyproject).
- [ ] Nenhum link para `PLAN-V8.md` ou documentos da raiz que não existem mais.
- [ ] "Novidades da 8.1" no LEIA-ME; matriz de acesso atualizada com assumir e tratar alerta.
- [ ] Os seis roteiros têm o passo de alerta e passam de ponta a ponta no modo simulado.
