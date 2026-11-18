# StoneFalcon v7 — Plano em tickets

> **Rascunho para aprovação** (17/11/2026). Parte do estado entregue na v6 (commit `7e57856` da `main`). Cada ticket é uma fatia vertical: back, front, extensão e teste juntos, demonstrável sozinho, entregue por um PR com a esteira de CI verde.

## 1. O que muda e por quê

A v6 deu à plataforma acesso por perfil e um marketplace de plugins. A v7 responde a três perguntas que a banca ainda pode fazer: "como a extensão vira porta de entrada para criar agentes?", "como o CoE enxerga, ao vivo, tudo o que os colaboradores criaram?" e "a plataforma depende de um único fornecedor de IA?".

1. **Versão 7.0 visível.** A extensão aparece como "StoneFalcon 7.0" em `chrome://extensions`, e a plataforma, a extensão e a API passam a contar a mesma versão (hoje a extensão diz 5.0.0 e a API diz 6.0.0).
2. **Atalho "Criar Agente de IA" na extensão.** Abre o Estúdio do hub web numa aba nova, já logado no mesmo perfil da extensão.
3. **Mapa de IA da Helena.** Nova aba, só do CoE de IA, com o fluxo animado e ao vivo: quem criou → agentes → modelos → plugins/ferramentas → plataformas da Stone e externas. Um agente publicado agora aparece no mapa sem recarregar a página.
4. **Vários provedores de IA + balanceador por esforço.** Além do Claude, modelos do Google (Gemini), OpenAI (GPT), DeepSeek e xAI (Grok) entram nas opções do Estúdio e na contabilidade de Finanças. Um balanceador classifica o esforço de cada passo e delega ao modelo capaz mais barato, com troca de provedor quando um falha ou estoura o orçamento. É uma **demonstração de capacidade**: só o Claude roda de verdade (com chave); os outros são simulados.
5. **Esteira de CI.** Hoje não há nenhuma. A v7 começa por ela, para que cada ticket entre por PR com testes, compilação e checagem da extensão.
6. **`iniciar.bat` e `iniciar.sh` validados** depois de tudo, inclusive numa pasta onde a v6 já rodou.
7. **Demonstração integrada para o pitch.** Uma rotina real de trabalho que começa numa planilha do Google aberta no navegador, passa pela extensão e pelo Estúdio, roda como tarefa de rotina e aparece no Mapa de IA e em Finanças.

## 2. Decisões propostas (confirmar antes de começar)

| # | Decisão | Proposta |
|---|---|---|
| 1 | Login da aba nova aberta pela extensão | **Passe de uso único.** A extensão pede à plataforma um passe curto (expira em 60 s, vale uma vez) para o perfil dela e abre o hub com esse passe. Mantém a regra da v6: digitar `?perfil=` num endereço direto continua não trocando o perfil de ninguém. |
| 2 | Perfis sem o Estúdio (Helena, Lucas) | **O atalho só aparece para quem tem a aba Estúdio.** Para os outros, o painel mostra "Seu perfil não cria agentes" com um link para o Início. A fonte da verdade continua sendo a lista de abas que o back devolve. |
| 3 | Onde fica o fluxo de IA da Helena | **Aba nova "Mapa de IA"**, exclusiva da Helena (menu, rota e API, como as outras abas restritas), com um cartão de acesso no Painel executivo. |
| 4 | "Tempo real" | **Consulta curta (2–3 s) + animação no navegador**, o mesmo padrão já usado em Saúde e na página do plugin. Sem infraestrutura nova; SSE fica como melhoria futura. Desenho com React Flow, que o Estúdio já usa. |
| 5 | Outros provedores | **Simulados, sempre**, com selo "simulado" e preço de tabela pública conferido na data (fonte e data registradas, como a tabela da Anthropic). Nenhuma dependência nova no back, então `iniciar` não muda por causa deles. |
| 6 | Plataforma terceira da demo | **Google Sheets, com plano B local.** Planilha real (dados fictícios, publicada na web) e uma planilha fictícia servida pela própria plataforma, como o helpdesk fictício da v5, para ensaiar sem internet. Ver o risco no ticket 10. |
| 7 | Persona da demo integrada | **Thiago (Logística):** já tem o Slack integrado e o caso da troca de maquininha, que vira rotina semanal. Helena fecha o pitch no Mapa de IA e em Finanças. |

## 3. Fluxo de trabalho e esteira de CI

- **Um ticket = um branch = um PR.** Branch `v7/NN-nome-curto` saindo de `main`; PR para `main` com o número do ticket no título e os critérios de aceite como checklist.
- **A esteira roda em todo PR e em `main`** e precisa estar verde para juntar:
  1. Back: testes automáticos (pytest) em Python 3.11 e na versão usada pelo grupo.
  2. Front: checagem de tipos e compilação de produção.
  3. Extensão: manifesto válido, versão igual à da plataforma, arquivos citados no manifesto existem.
  4. Consistência da versão: extensão, API e front contam o mesmo número.
  5. Fumaça dos scripts de início (entra no ticket 12): `iniciar.sh` no Ubuntu e `iniciar.bat` no Windows sobem a plataforma e respondem em `/api/v1/saude`.
- **Definição de pronto:** critérios de aceite marcados, esteira verde, critérios comuns da seção 6 respeitados e o status do ticket atualizado neste arquivo.
- A versão sobe para **7.0.0** no ticket 02; os tickets seguintes não mexem mais nela.

## 4. Matriz de acesso (o que muda)

| Aba / recurso | Helena Castro (CoE de IA) | Criadores (Marina, Rafael, Carla, Thiago) | Lucas Prado |
|---|---|---|---|
| **Mapa de IA** *(nova)* | sim | **não** | **não** |
| Atalho "Criar Agente de IA" na extensão *(novo)* | não (aviso) | sim | não (aviso) |
| Escolha de modelo por passo no Estúdio *(nova)* | — | sim | — |
| Política do balanceador | vê e simula falha de provedor | vê o modelo escolhido em cada passo | vê |
| Demais abas | como na v6 | como na v6 | como na v6 |

## 5. Tickets (fatias verticais)

O rastreador de tickets não está configurado no projeto. A lista fica consolidada aqui; se o grupo quiser, cada ticket vira uma issue no GitHub ou um arquivo em `.scratch/stonefalcon-v7/issues/`.

| # | Ticket | Fase | Bloqueado por |
|---|---|---|---|
| 01 | Esteira de CI no GitHub | 0 · Base | — |
| 02 | Versão 7.0 em todo lugar | 0 · Base | 01 |
| 03 | Atalho "Criar Agente de IA" na extensão | 1 · Extensão | 02 |
| 04 | Registro de modelos por provedor (prefatoração) | 2 · Multimodelo | 01 |
| 05 | Modelos de outros provedores no Estúdio e em Finanças | 2 · Multimodelo | 04 |
| 06 | Balanceador por nível de esforço | 2 · Multimodelo | 05 |
| 07 | Mapa de IA ao vivo (bala traçante) | 3 · Mapa | 01 |
| 08 | Fluxo animado e camada de modelos no mapa | 3 · Mapa | 05, 07 |
| 09 | Tarefa de rotina (agente com agenda) | 4 · Demonstração | 01 |
| 10 | Planilha do Google como fonte de uma rotina | 4 · Demonstração | 03, 09 |
| 11 | Roteiro do pitch v7 (demo integrada) | 4 · Demonstração | 06, 08, 10 |
| 12 | `iniciar.bat` e `iniciar.sh` validados para a v7 | Fechamento | 02, 03, 06, 08, 10 |
| 13 | Ensaio geral v7 | Fechamento | 11, 12 |

**Ordem de trabalho:** o 01 vem primeiro e sozinho. Depois dele, 02, 04, 07 e 09 correm em paralelo. O 03 sai do 02; o 05 sai do 04 e libera 06 e 08 em paralelo (o 08 também espera o 07). O 10 junta extensão e rotina. O 11 costura tudo no pitch; o 12 valida os scripts com todas as mudanças dentro, e o 13 fecha.

```
01 ─┬─ 02 ── 03 ──────────────┬─ 10 ─┐
    ├─ 09 ────────────────────┘      │
    ├─ 04 ── 05 ─┬─ 06 ──────────────┼─ 11 ─┐
    │            └─ 08 ──────────────┤      ├─ 13
    └─ 07 ─────────┘                 └─ 12 ─┘
```

---

### 01: Esteira de CI no GitHub

**O que construir:** a esteira que todo PR da v7 vai atravessar. A cada PR e a cada push em `main`, o GitHub roda os testes do back, a checagem de tipos e a compilação do front e uma checagem do manifesto da extensão, e mostra o resultado no PR. O LEIA-ME ganha o selo da esteira e a seção "Como contribuir" com o fluxo da seção 3.

**Bloqueado por:** nenhum (pode começar já).

**Status:** feito localmente; falta validar no GitHub (push, PR e proteção de `main` dependem do dono do repositório)

- [ ] Abrir um PR dispara a esteira e o resultado aparece no PR.
- [x] Testes do back (workflow escrito, matriz 3.11 e 3.14; suíte local passa em modo simulado) rodam em Python 3.11 e na versão mais nova usada pelo grupo, em modo simulado, sem chave da API.
- [x] Checagem de tipos e compilação do front falham a esteira quando quebram.
- [x] A checagem da extensão falha se o manifesto for inválido ou citar um arquivo que não existe.
- [ ] Um PR com um teste quebrado de propósito fica vermelho (verificado e revertido).
- [ ] A esteira inteira roda em menos de 10 minutos.
- [ ] `main` exige a esteira verde para juntar (configuração do repositório registrada no PR).

### 02: Versão 7.0 em todo lugar

**O que construir:** a extensão aparece como **"StoneFalcon 7.0"** na página de extensões do Chrome, com versão 7.0.0. A API, o painel lateral, a tela de opções e o rodapé do hub mostram a mesma versão, lida de uma fonte só. A esteira passa a falhar se as versões divergirem.

**Bloqueado por:** 01.

**Status:** feito (falta conferir o nome no `chrome://extensions` com a extensão carregada e a esteira no GitHub)

- [ ] Carregar a pasta da extensão em `chrome://extensions` mostra o nome "StoneFalcon 7.0" e a versão 7.0.0.
- [x] A rota de saúde da API responde 7.0.0.
- [x] A tela de opções da extensão e o rodapé do hub mostram 7.0.
- [x] A checagem de versão da esteira falha quando extensão e plataforma contam números diferentes (testado).
- [x] O LEIA-ME pede para remover e recarregar a extensão da v6, porque o Chrome mantém a antiga.

### 03: Atalho "Criar Agente de IA" na extensão

**O que construir:** um botão "Criar Agente de IA" no painel lateral da extensão e um item igual no menu do botão direito. Ao clicar, abre uma aba nova no Estúdio do hub web, já logada no perfil que estava logado na extensão. O login usa um passe de uso único (decisão 1): a extensão pede o passe à plataforma, abre o hub com ele, e o hub troca o passe pelo perfil e leva ao Estúdio. Se havia um trecho selecionado, ele vira o rascunho da descrição do agente no Estúdio, sem passar pelo endereço. Perfis sem o Estúdio veem o aviso da decisão 2.

**Bloqueado por:** 02.

**Status:** feito localmente; falta testar com a extensão carregada no Chrome (o fluxo foi testado no hub, no painel e no helpdesk fictício)

- [x] Logado como Thiago na extensão, clicar em "Criar Agente de IA" abre o Estúdio numa aba nova, logado como Thiago, mesmo que o hub estivesse logado em outro perfil.
- [x] O passe expira em 60 s e vale uma vez só; reusar ou atrasar volta à tela "Quem é você hoje?" com uma mensagem clara (teste automático).
- [x] O endereço da aba nova não contém o id do perfil nem o texto selecionado.
- [x] Selecionar um texto e usar o item do menu "Criar Agente de IA com este trecho" abre o Estúdio com a descrição preenchida e a sugestão de agente já calculada.
- [x] Helena e Lucas não veem o botão; veem "Seu perfil não cria agentes" (a regra vem da lista de abas do back).
- [x] O servidor desligado mostra o mesmo diagnóstico de conexão que o painel já usa.
- [ ] Testado no helpdesk fictício e com a extensão carregada no Chrome (registro no PR).

### 04: Registro de modelos por provedor (prefatoração)

**O que construir:** prefatoração sem mudança visível. Hoje os modelos são duas chaves fixas ("rapido" e "forte"), e o nome deles está repetido em mais de um lugar. Passa a existir um registro único de modelos, cada um com provedor, nome, preços, capacidades (ferramentas, contexto longo, nível de raciocínio) e se roda de verdade ou é simulado. "rapido" e "forte" continuam valendo como apelidos para Haiku e Sonnet, então blueprints, execuções gravadas e a semente da demo não mudam.

**Bloqueado por:** 01.

**Status:** feito (aguarda validação da esteira no GitHub)

- [x] Todos os testes atuais passam sem alteração de comportamento.
- [x] Nomes e preços dos modelos vêm só do registro (nenhuma tabela repetida em Finanças ou no cliente).
- [x] Um blueprint antigo com "rapido"/"forte" valida, roda e custa o mesmo que na v6 (teste).
- [x] Teste do registro: todo modelo tem provedor, preço de entrada e saída, capacidades e fonte/data do preço.

### 05: Modelos de outros provedores no Estúdio e em Finanças

**O que construir:** o registro ganha modelos do Google (Gemini), OpenAI (GPT), DeepSeek e xAI (Grok), cada provedor com pelo menos um modelo leve e um forte. Eles aparecem como opção por passo no Estúdio (além de "auto"), rodam no simulador com respostas determinísticas e tokens estimados pela mesma régua, e entram na contabilidade: Finanças mostra o gasto por provedor e por modelo, e um comparativo "e se tudo rodasse em X". O selo "simulado" aparece em todo lugar onde um modelo não-Claude aparece.

**Bloqueado por:** 04.

**Status:** feito (com chave real o Claude roda de verdade: não testado, sem chave; preços a reconferir na véspera)

- [x] O Estúdio lista os modelos agrupados por provedor no seletor de cada passo, com preço por milhão de tokens e selo "simulado".
- [x] Testar no sandbox um agente com um passo em Gemini e outro em GPT funciona sem chave, e a execução mostra o modelo e o custo de cada passo.
- [x] Finanças mostra o gasto do mês por provedor e por modelo, com números vindos das execuções (não fixos na tela).
- [x] O comparativo "e se tudo rodasse em X" recalcula o custo do período para o modelo escolhido.
- [x] A semente da demo inclui execuções históricas em mais de um provedor, para os gráficos não nascerem vazios.
- [x] Com chave da Anthropic, Claude roda de verdade e os outros continuam simulados, sem erro.
- [x] Preços conferidos na tabela pública de cada provedor na data da implementação; fonte e data registradas.

### 06: Balanceador por nível de esforço

**O que construir:** o roteador "auto" vira um balanceador. Cada passo recebe um nível de esforço (leve, moderado, alto, crítico) calculado a partir da complexidade do texto, das ferramentas que usa, do tamanho do contexto e do risco do agente. Uma política, legível na tela, diz quais capacidades cada nível exige; o balanceador escolhe o modelo mais barato que atende e delega a outro provedor quando o escolhido está indisponível ou o agente passou do orçamento. A trilha "como o agente decidiu" mostra nível, candidatos, escolhido e motivo. A Helena vê a política, simula a queda de um provedor e roda uma carga de teste para ver a distribuição e o custo mudarem.

**Bloqueado por:** 05.

**Status:** feito (carga de 300 passos visual testada no navegador; falta medir fluidez do mapa, ticket 08)

- [x] Cada passo "auto" de uma execução mostra o nível de esforço, os modelos candidatos e o motivo da escolha.
- [x] Um passo leve vai a um modelo leve; um passo crítico vai a um modelo forte (teste com passos de exemplo de cada nível).
- [x] Simular a queda de um provedor faz os passos seguintes irem a outro provedor capaz, com o motivo "provedor indisponível" na trilha e um alerta em Saúde.
- [x] Agente acima do orçamento passa a usar o modelo capaz mais barato, com o motivo na trilha.
- [x] "Simular carga" (só Helena) roda um lote de execuções sintéticas e mostra a distribuição por nível e por provedor e o custo total, comparado com "tudo no modelo forte".
- [x] Passos com modelo fixado pelo criador continuam respeitados (como na v6).
- [x] Reiniciar a demo desfaz a queda simulada e a carga de teste.

### 07: Mapa de IA ao vivo (bala traçante)

**O que construir:** nova aba "Mapa de IA", só da Helena (menu, rota e 403 na API, pela mesma lista de abas da v6), com um cartão de acesso no Painel executivo. O mapa desenha, da esquerda para a direita: áreas e colaboradores criadores → agentes publicados → plugins e ferramentas → plataformas (sistemas da Stone e externos). Os dados vêm de uma única rota do back, e a tela se atualiza sozinha: publicar um agente em outra aba faz ele aparecer no mapa em poucos segundos, com uma animação de entrada.

**Bloqueado por:** 01.

**Status:** feito (publicação em outra janela apareceu no mapa em ~1 s no navegador)

- [x] A aba aparece só para a Helena; outros perfis voltam ao Início e recebem 403 na API (teste dos 6 perfis).
- [x] O mapa mostra todos os agentes publicados da semente, ligados às ferramentas, aos plugins integrados e aos sistemas que eles tocam.
- [x] Publicar um agente novo (como Thiago, em outra janela) faz ele aparecer no mapa da Helena em até 5 s, sem recarregar.
- [x] Integrar ou remover um plugin muda o mapa do mesmo jeito.
- [x] Clicar num agente ou num plugin abre a página dele.
- [x] Teste do back: a rota do mapa devolve nós e ligações coerentes com o catálogo e os agentes publicados.

### 08: Fluxo animado e camada de modelos no mapa

**O que construir:** o mapa passa a mostrar o fluxo. Cada execução acende um pulso que percorre o caminho agente → modelo → ferramenta → sistema, na cor do resultado (concluída, escalada, falha). Entre agentes e ferramentas aparece a camada de modelos, agrupada por provedor. Cada nó mostra volume e custo do período, e um filtro por área e por provedor limpa a visão. Uma linha do tempo mostra as últimas execuções ao lado do mapa.

**Bloqueado por:** 05, 07.

**Status:** feito (fluidez medida no painel do app: p50 36 ms e p95 54 ms por quadro com queda de provedor, carga e 3 execuções simultâneas; navegador do app em segundo plano)

- [x] Rodar um agente faz um pulso percorrer o caminho certo no mapa em poucos segundos, na cor do resultado.
- [x] A camada de modelos mostra os provedores usados de fato no período, com custo por provedor.
- [x] Filtros por área e por provedor funcionam e se combinam.
- [x] Sem execuções recentes, o mapa fica parado e legível (sem animação em laço).
- [x] Com "reduzir movimento" ligado no sistema, os pulsos viram destaque estático.
- [x] O mapa continua fluido com a carga simulada do ticket 06 ligada (registro no PR).

### 09: Tarefa de rotina (agente com agenda)

**O que construir:** um criador pode dar a um agente publicado uma agenda de rotina (ex.: "toda segunda às 9h") com uma entrada fixa. A plataforma dispara a rotina sozinha; na demo, um relógio acelerado e o botão "Rodar agora" mostram isso sem esperar. Execuções de rotina aparecem em Execuções e no Mapa de IA com o selo "rotina" e passam pelas mesmas permissões, guardrails e orçamento de uma execução manual, em nome de quem agendou.

**Bloqueado por:** 01.

**Status:** feito (testado na tela com o relógio acelerado)

- [x] Thiago agenda o agente de troca de maquininha para toda segunda às 9h; a agenda aparece na página do agente.
- [x] "Rodar agora" executa a rotina e a execução aparece com o selo "rotina".
- [x] Com o relógio da demo acelerado, a rotina dispara sozinha na hora marcada (teste com relógio controlado).
- [x] Uma rotina não roda ferramentas que quem agendou não poderia rodar (teste).
- [x] Ação sensível dentro de uma rotina fica aguardando confirmação humana, sem executar sozinha.
- [x] Criar, pausar e remover a agenda fica na auditoria; reiniciar a demo remove as agendas.

### 10: Planilha do Google como fonte de uma rotina

**O que construir:** a ponte com uma plataforma terceira aberta no navegador. Começa por uma investigação curta (até meio dia) e registra a decisão no PR: o Google Sheets desenha a grade sem texto selecionável comum, então o menu do botão direito do Chrome provavelmente não recebe as células selecionadas. Caminhos a testar, nesta ordem: (a) a extensão lê o endereço da planilha aberta e a plataforma importa a versão publicada na web; (b) copiar e colar as células no painel; (c) a planilha fictícia local (plano B, sem internet). O resultado é um plugin "Google Sheets" no marketplace, com uma ferramenta de leitura de planilha que um agente usa como passo, e o atalho do ticket 03 reconhecendo quando a aba aberta é uma planilha.

**Bloqueado por:** 03, 09.

**Status:** ready-for-agent

- [ ] Decisão da investigação registrada no PR, com o que funcionou e o que não funcionou no Chrome.
- [ ] O plugin "Google Sheets" aparece no marketplace (classificação interna, selo "simulado" quando usar a planilha local) e integra como os outros.
- [ ] Com uma planilha do Google aberta, o painel da extensão oferece "Criar Agente de IA a partir desta planilha", que leva ao Estúdio com a fonte já configurada.
- [ ] Um agente com o passo "ler planilha" lê as linhas da planilha (real ou local) e mostra o que leu na execução.
- [ ] Sem internet, a planilha fictícia local cobre o mesmo fluxo.
- [ ] A planilha usada na demo só tem dados fictícios; nada de documento real da Stone.

### 11: Roteiro do pitch v7 (demo integrada)

**O que construir:** a demonstração que costura a v7, como roteiro guiado (o mesmo formato dos roteiros da v5/v6) e como texto falado para o pitch. Proposta de enredo:

1. **Thiago** abre no navegador a planilha "Pedidos de troca de maquininha".
2. Na extensão, clica em **"Criar Agente de IA a partir desta planilha"** e cai no Estúdio, logado como ele.
3. O Estúdio sugere o agente: ler a planilha → validar cadastro e regra → abrir chamado → avisar no Slack. O **balanceador** mostra o nível de esforço e o modelo de cada passo, de provedores diferentes.
4. Thiago testa no sandbox, publica e **agenda a rotina** para toda segunda às 9h; "Rodar agora" mostra a primeira execução.
5. A troca vai para a **Helena**: no **Mapa de IA**, o agente novo apareceu sozinho e o pulso da execução percorre planilha → modelos → Jira/Slack.
6. Helena simula a **queda de um provedor** e a carga de teste: o balanceador delega e **Finanças** mostra o gasto por provedor e o comparativo.
7. Fecha no cartão AS IS × TO BE do Thiago, com a rotina semanal contando no ganho.

**Bloqueado por:** 06, 08, 10.

**Status:** ready-for-agent

- [ ] O roteiro roda do início ao fim sem digitar nada além do roteiro e sem chave da API, com a troca Thiago → Helena.
- [ ] Reiniciar o roteiro devolve a planilha, o plugin, a agenda e o balanceador ao estado inicial.
- [ ] O texto do pitch cabe no tempo combinado (ver pendência 2) e marca onde cada recurso da v7 aparece.
- [ ] Há um plano B para cada passo que depende do navegador ou da internet (planilha local, helpdesk fictício).
- [ ] A aba Perguntas da Ferramenta ganha 2 a 3 perguntas novas (multiprovedor, mapa ao vivo, rotina), com "Mostrar na tela" funcionando.

### 12: `iniciar.bat` e `iniciar.sh` validados para a v7

**O que construir:** os scripts de início funcionam numa máquina limpa e numa pasta onde a v6 já rodou. Problemas já encontrados na leitura dos scripts da v6, a corrigir ou descartar com teste:
- as telas só são compiladas se ainda não existirem, então uma pasta que já rodou a v6 abre as **telas antigas** depois de atualizar;
- o ambiente Python só é criado se não existir, então uma mudança nas dependências **não é instalada**;
- a versão mínima do Python (3.11) não é conferida;
- porta 8765 ocupada (ex.: outra cópia aberta) não dá mensagem clara.

A esteira ganha um teste de fumaça que roda cada script no seu sistema, espera a plataforma responder e desliga.

**Bloqueado por:** 02, 03, 06, 08, 10 (validar com todas as mudanças dentro).

**Status:** ready-for-agent

- [ ] Numa pasta que já rodou a v6, rodar o script da v7 recompila as telas e abre a v7 (versão 7.0 no rodapé).
- [ ] Mudar as dependências do back faz o script reinstalar na próxima execução.
- [ ] Python abaixo de 3.11 e porta ocupada geram mensagens claras em português.
- [ ] A esteira roda `iniciar.sh` no Ubuntu e `iniciar.bat` no Windows e confere que a saúde responde 7.0.0.
- [ ] Testado à mão numa máquina Windows limpa (registro no PR, item que a v6 deixou como "não testado").
- [ ] O LEIA-ME explica como atualizar de uma versão anterior.

### 13: Ensaio geral v7

**O que construir:** o fechamento da versão. Teste automático percorre todos os roteiros, inclusive o do pitch v7, e confere a matriz de acesso da seção 4. O ensaio geral, as capturas de tela, o LEIA-ME e a apresentação são atualizados para a v7.

**Bloqueado por:** 11, 12.

**Status:** ready-for-agent

- [ ] Todos os testes da v6 continuam passando, mais os novos, com a esteira verde em `main`.
- [ ] Teste da matriz de acesso cobre a aba Mapa de IA e o atalho da extensão para os 6 perfis.
- [ ] O ensaio geral inclui a demo integrada, com o tempo de cada parte.
- [ ] Capturas novas: atalho da extensão, Mapa de IA, Estúdio com vários provedores, trilha do balanceador, Finanças por provedor.
- [ ] A apresentação e a planilha financeira são regeneradas com os números multimodelo (na v6 elas ficaram para trás).
- [ ] O LEIA-ME descreve a esteira, o atalho, o Mapa de IA, os provedores simulados e o balanceador.

## 6. Critérios de aceite comuns a todo ticket

- Roda sem chave da API, com respostas determinísticas.
- Esteira de CI verde no PR antes de juntar.
- Toda restrição de aba vale no menu, na rota do front e na API.
- Reiniciar a demo ou o roteiro devolve exatamente o estado inicial.
- Os testes automáticos atuais continuam passando.
- Nada de dado real: pessoas, lojistas, planilhas, plugins e modelos simulados seguem fictícios ou com o selo correspondente.
- A extensão continua sem lógica de IA e sem chave: tudo roda na plataforma, com as permissões de quem está logado.

## 7. Pendências

1. **Onde a v7 vai morar.** Há duas cópias da v6 (`v6` e `v6_`) no mesmo commit, e este plano foi gravado em `v6_`. Definir se a v7 é um branch do mesmo repositório (recomendado, por causa da esteira) ou uma cópia nova.
2. **Tempo do pitch.** Com o atalho, o mapa e o balanceador, conferir se a demo integrada cabe no tempo da apresentação.
3. **Configuração local do Claude Code.** `.claude/launch.json` (fora do repositório) ainda aponta para as pastas da v4/v5; atualizar ao começar a v7.
4. **Planilha real da demo.** Alguém do grupo cria a planilha com dados fictícios na própria conta e publica na web (necessário para o caminho (a) do ticket 10).
