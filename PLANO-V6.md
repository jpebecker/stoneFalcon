# StoneFalcon v6 — Plano em tickets

> Plano aprovado em 17/11/2026. Parte do estado entregue na v5 (commit `eb75c38` da `main`; o plano da v5 saiu do repositório nesta versão). Cada ticket é uma fatia vertical: back, front e teste juntos, demonstrável sozinho.

## 1. O que muda e por quê

A v5 deixou toda a plataforma aberta para todos os perfis: qualquer persona vê o painel executivo, os seis roteiros e as perguntas da banca. Isso funciona para quem apresenta, mas contradiz a história de governança que o próprio produto conta (papéis, níveis de acesso, quatro olhos). A v6 faz a interface obedecer ao perfil e acrescenta uma resposta visível à pergunta "e a integração com as ferramentas que a empresa já usa?".

1. **Avatares reais.** As iniciais coloridas viram fotos das personas.
2. **Acesso por perfil.** Painel executivo, Roteiros (todos) e Perguntas da Ferramenta passam a ser exclusivos da Helena Castro (Gestora do CoE de IA). Os demais perfis só iniciam o próprio roteiro, pelo Início.
3. **Marketplace de plugins.** Uma aba, para todos os perfis, que simula um marketplace de plugins homologados de ferramentas externas. Um plugin integrado vira ferramenta no Catálogo e passo no Estúdio, e tem uma página com a visão consolidada dele.

## 2. Decisões já tomadas

| # | Decisão | Escolha |
|---|---|---|
| 1 | Roteiros que trocam de perfil no meio (Rafael → Lucas na revisão → Helena na auditoria; Lucas → Marina) | **Mantém a troca.** O roteiro só é visível e iniciável pelo dono, mas os passos de quatro olhos continuam trocando de perfil, porque são a prova de governança. A outra persona não vê o roteiro na própria interface. |
| 2 | Passo final "Perguntas da banca" nos roteiros dos outros perfis | **Removido.** Esses roteiros terminam no cartão AS IS × TO BE. As perguntas de cada persona continuam existindo, só na aba da Helena, filtradas por persona. |
| 3 | Enquadramento do marketplace de plugins | **Integrado ao Catálogo.** Marketplace é a camada de aquisição; Catálogo é a camada de governança. Plugin que toca dado confidencial ou restrito passa pela aprovação do Lucas. |
| 4 | Nomes dos plugins | **Ferramentas reais, sem logo oficial.** Ícones genéricos por categoria e selo "simulado" em toda tela de plugin, como no resto do protótipo. |

## 3. Matriz de acesso por aba

| Aba | Helena Castro (CoE de IA) | Demais perfis |
|---|---|---|
| Início | sim, com o card do próprio roteiro | sim, com o card do próprio roteiro |
| Roteiros | sim, **todos** os roteiros | **não** (a aba some) |
| Painel executivo | sim | **não** |
| Perguntas da Ferramenta *(antes "Perguntas da banca")* | sim, com o atalho Alt + B | **não** (o atalho também não funciona) |
| Plugins *(nova)* | sim | sim |
| Demais abas (Estúdio, Agentes, Revisões, Execuções, Saúde, Finanças, Ferramentas, Auditoria) | como na v5 | como na v5 |

**Regra de ouro:** esconder a aba não basta. Cada restrição vale em três lugares: o menu, a rota no front (endereço digitado volta ao Início) e a API (responde 403). A fonte da verdade é uma só, no back, e o front só a lê.

## 4. Validação da ideia do marketplace de plugins

**Vale a pena.** A banca vai perguntar como a plataforma conversa com os sistemas que a Stone já usa, e hoje a resposta é só o Catálogo, que a Engenharia mantém conector por conector. O marketplace mostra o outro lado: as áreas encontram uma integração pronta e homologada, e a governança continua no mesmo lugar.

**Como se encaixa no que já existe:**
- **Plugin** = pacote homologado de uma ferramenta externa. Traz uma ou mais ferramentas (leitura ou escrita), com classificação da informação, áreas que podem usar e se exige aprovação humana: exatamente o contrato que o Catálogo já tem.
- **Integrar** um plugin registra essas ferramentas no Catálogo, com a origem "plugin X". A partir daí elas aparecem como passo no Estúdio e rodam no runtime como qualquer conector (dados fictícios, latência simulada).
- **Quem integra:** criadores (para a própria área) e a Engenharia integram plugins de classificação pública ou interna direto. Plugin confidencial ou restrito vira pedido para o Lucas (quatro olhos), na mesma fila de Revisões. Quem não tem esses papéis navega e vê os plugins da própria área.
- **Página consolidada:** cada plugin integrado tem uma página com uma "janela" simulada do sistema externo (ex.: fila de chamados do Zendesk, quadro do Jira) e os números da integração: agentes que usam, chamadas no mês, custo, latência e saúde. Os dados respeitam o nível de acesso de quem olha.

**Vitrine inicial (8 plugins, todos simulados):**

| Plugin | Categoria | Ferramentas que traz | Classificação | Áreas |
|---|---|---|---|---|
| Zendesk | Helpdesk | ler chamado, responder chamado | interna | Atendimento |
| Salesforce | CRM | consultar conta do lojista, registrar interação | confidencial | Atendimento, Prevenção a Fraudes |
| Slack | Chat corporativo | enviar mensagem em canal | interna | todas |
| Jira | Gestão de trabalho | abrir item, consultar status | interna | Engenharia, Logística |
| Google Drive | Documentos | buscar documento de política | interna | todas |
| ServiceNow | Chamados de TI | abrir incidente | interna | Engenharia |
| SAP SuccessFactors | RH | consultar saldo de férias | confidencial *(era restrita; ver §8)* | Pessoas (RH) |
| Datadog | Observabilidade | consultar alerta de sistema | interna | Engenharia |

**Riscos e como o plano lida com eles:**
- *Dois conceitos parecidos (plugin × ferramenta) confundem a banca.* O plugin nunca é executado: só as ferramentas que ele traz. A tela diz isso em uma frase.
- *Escopo crescer.* Só 3 plugins ganham "janela" própria do sistema externo (Zendesk, Slack, Jira); os outros mostram só os números da integração.
- *Marca de terceiros.* Nomes reais, sem logo oficial, e o aviso de protótipo acadêmico que já existe no rodapé.

## 5. Tickets (fatias verticais)

O rastreador de tickets não está configurado no projeto. A lista fica consolidada aqui; se o grupo quiser, cada ticket vira um arquivo em `.scratch/stonefalcon-v6/issues/`.

| # | Ticket | Fase | Bloqueado por |
|---|---|---|---|
| 01 | Painel executivo só da Helena (mapa de abas por perfil) | 1 · Acesso | — |
| 02 | Perguntas da Ferramenta: renomear e restringir à Helena | 1 · Acesso | 01 |
| 03 | Roteiros isolados por perfil | 1 · Acesso | 01 |
| 04 | Fotos das personas no lugar das iniciais | 2 · Avatares | — |
| 05 | Vitrine de plugins homologados | 3 · Plugins | 01 |
| 06 | Integrar plugin de risco baixo | 3 · Plugins | 05 |
| 07 | Integração governada de plugin sensível | 3 · Plugins | 06 |
| 08 | Página consolidada do plugin integrado | 3 · Plugins | 06 |
| 09 | Plugin dentro de um roteiro | 3 · Plugins | 02, 03, 06, 08 |
| 10 | Ensaio geral v6 | Fechamento | 04, 07, 09 |

**Ordem de trabalho:** 01 e 04 começam juntos. Depois do 01, os tickets 02, 03 e 05 correm em paralelo. O 06 abre a frente de plugins; 07 e 08 correm em paralelo depois dele. O 09 junta acesso e plugins, e o 10 fecha.

---

### 01: Painel executivo só da Helena (mapa de abas por perfil)

**O que construir:** a bala traçante do controle de acesso por aba. O back passa a dizer, junto com os dados da pessoa logada, quais abas ela pode ver; o menu, as rotas do front e a API obedecem a essa lista. A primeira aba restrita é o Painel executivo: só a Helena o vê. Os atalhos para o painel em outras telas (cartão de resultado do roteiro, Início) só aparecem para ela.

**Bloqueado por:** nenhum (pode começar já).

**Status:** done

- [x] Os dados da pessoa logada trazem a lista de abas permitidas, calculada no back a partir dos papéis (uma fonte de verdade só).
- [x] Logado como qualquer perfil que não a Helena, a aba "Painel executivo" não aparece no menu.
- [x] Digitar o endereço do painel com outro perfil volta ao Início, sem tela quebrada.
- [x] Os indicadores exclusivos do painel respondem 403 para quem não é a Helena; o que Finanças e Calculadora usam continua aberto a quem já tinha acesso.
- [x] Os links "Painel executivo" do cartão AS IS × TO BE só aparecem para a Helena.
- [x] Teste automático cobre os 6 perfis: Helena vê e acessa; os outros 5 não veem e recebem 403.

### 02: Perguntas da Ferramenta: renomear e restringir à Helena

**O que construir:** "Perguntas da banca" passa a se chamar "Perguntas da Ferramenta" em toda a interface (menu, título, atalho, botões) e vira exclusiva da Helena. O atalho Alt + B só funciona para ela. O passo final "Perguntas da banca" sai dos roteiros dos outros perfis, que passam a terminar no cartão AS IS × TO BE. O conteúdo das perguntas não muda: todas as personas continuam cobertas, filtráveis por persona na aba da Helena, e o "Mostrar na tela" continua levando ao passo do roteiro com o perfil certo.

**Bloqueado por:** 01.

**Status:** done

- [x] Nenhuma tela mostra mais o texto "Perguntas da banca"; o nome é "Perguntas da Ferramenta".
- [x] A aba, a rota e a API das perguntas só respondem para a Helena (menu, redirecionamento e 403, como no 01).
- [x] Alt + B não faz nada para os outros perfis.
- [x] Os roteiros de Marina, Rafael, Carla, Thiago e Lucas terminam no passo "Medir: AS IS × TO BE"; o da Helena mantém o passo de perguntas.
- [x] O botão "Perguntas" do cartão de resultado só aparece para a Helena.
- [x] "Mostrar na tela" a partir da aba da Helena continua abrindo a prova certa, inclusive em passos de outras personas.
- [x] Testes de roteiros atualizados para a nova contagem de passos.

### 03: Roteiros isolados por perfil

**O que construir:** cada persona só enxerga o próprio roteiro. A aba "Roteiros" passa a ser exclusiva da Helena, que vê e inicia todos. Os outros perfis iniciam o próprio roteiro pelo card "Seu roteiro guiado" no Início, e a página AS IS × TO BE de outra persona não abre para eles. A troca automática de perfil continua nos passos de quatro olhos: durante um roteiro ativo, a persona do passo (ex.: Lucas na revisão do roteiro do Rafael) consegue carregar o roteiro para a barra funcionar, mas ele não aparece na interface dela.

**Bloqueado por:** 01.

**Status:** done

- [x] A aba "Roteiros" só aparece para a Helena e lista os 6 roteiros; para os outros, a rota volta ao Início.
- [x] A listagem de roteiros na API devolve só o roteiro do próprio perfil (todos para a Helena).
- [x] Detalhe, reinício e resultado de um roteiro respondem só ao dono, às personas que participam de algum passo dele e à Helena; os demais recebem 403.
- [x] A página AS IS × TO BE de outra persona volta ao Início para quem não é dono nem a Helena.
- [x] O roteiro do Rafael roda do início ao fim com a troca para Lucas e Helena, sem erro de acesso; idem Lucas → Marina (o do Thiago não troca de perfil, ver §8).
- [x] O consolidado AS IS × TO BE continua disponível para a Calculadora de Finanças.
- [x] Teste automático: matriz persona × roteiro com o acesso esperado.

### 04: Fotos das personas no lugar das iniciais

**O que construir:** as 6 personas passam a ter foto. O avatar mostra a foto em todo lugar onde hoje mostra iniciais (menu da pessoa, troca de perfil, tela "Quem é você hoje?", barra do roteiro, painel da extensão e página de helpdesk). Se a foto não carregar, volta para as iniciais na cor da persona. Antes de usar, os nomes dos arquivos são conferidos com os nomes das personas: cada arquivo é renomeado para o id da persona, e a correspondência fica registrada no ticket.

**Bloqueado por:** nenhum (pode começar já). Depende das imagens, que **ainda não estão no repositório** (ver seção 7).

**Status:** done

- [x] Tabela de correspondência arquivo original → persona registrada no PR, com as 6 personas cobertas e nenhuma imagem sobrando.
- [x] Imagens quadradas, otimizadas para web (alvo de até 200 KB cada) e servidas pela própria plataforma (nada de endereço externo).
- [x] O avatar mostra a foto, com texto alternativo com o nome da pessoa, em todas as telas da plataforma e da extensão.
- [x] Sem a foto (arquivo ausente ou erro), aparecem as iniciais na cor da persona, sem layout quebrado.
- [x] Teste automático falha se alguma persona não tiver foto ou se houver foto que não corresponde a nenhuma persona.

### 05: Vitrine de plugins homologados

**O que construir:** nova aba "Plugins", para todos os perfis, que simula um marketplace de plugins homologados. Mostra os 8 plugins da vitrine inicial (seção 4) em cartões com categoria, ferramentas que o plugin traz, classificação da informação, áreas que podem usar e estado (disponível, integrado, aguardando aprovação). Há filtro por categoria e busca por nome, e um detalhe por plugin explicando o que ele faz e o que muda ao integrar. Ainda não integra nada.

**Bloqueado por:** 01 (a aba entra pelo mapa de abas).

**Status:** done

- [x] A aba "Plugins" aparece para os 6 perfis.
- [x] Os 8 plugins aparecem com nome real, ícone genérico da categoria e selo "simulado".
- [x] Filtro por categoria e busca por nome funcionam.
- [x] O detalhe do plugin lista as ferramentas que ele traz, com leitura/escrita, classificação e se exige confirmação humana.
- [x] Cada cartão diz se o plugin vale para a área da pessoa logada.
- [x] A vitrine vem de um catálogo no back, com teste que confere que cada ferramenta de plugin segue o mesmo contrato das ferramentas do Catálogo.

### 06: Integrar plugin de risco baixo

**O que construir:** um criador (para a própria área) ou a Engenharia integra um plugin de classificação pública ou interna com um clique. As ferramentas do plugin entram no Catálogo com a origem "plugin X", ficam disponíveis como passo no Estúdio e rodam no runtime com dados fictícios. A integração e a remoção ficam na auditoria. Reiniciar a demo ou o roteiro desfaz as integrações feitas.

**Bloqueado por:** 05.

**Status:** done

- [x] Logada como Marina, integrar o Zendesk muda o estado para "integrado" e as ferramentas dele aparecem no Catálogo com a origem do plugin.
- [x] No Estúdio, a Marina consegue usar uma ferramenta do Zendesk como passo de um agente e testar no sandbox com resposta realista.
- [x] Perfis sem papel de criador ou de Engenharia veem o botão "Pedir integração" no lugar de "Integrar" (o pedido só fica registrado).
- [x] Remover a integração tira as ferramentas do Catálogo; agentes que as usam ficam sinalizados, não quebram em silêncio.
- [x] Integração e remoção aparecem na trilha de auditoria.
- [x] Reiniciar a demo volta todos os plugins ao estado inicial.

### 07: Integração governada de plugin sensível

**O que construir:** integrar um plugin confidencial ou restrito (ex.: Salesforce, SAP SuccessFactors) não acontece direto: vira um pedido na fila de Revisões do Lucas, com o motivo, a área e as ferramentas envolvidas. O Lucas aprova ou recusa com parecer, e só então as ferramentas entram no Catálogo. Quem pediu vê o estado "aguardando aprovação" e recebe o resultado nos alertas.

**Bloqueado por:** 06.

**Status:** done

- [x] Logada como Carla, integrar o SAP SuccessFactors gera um pedido, e o plugin fica "aguardando aprovação".
- [x] O pedido aparece na tela de Revisões do Lucas, ao lado das revisões de agentes, com classificação e ferramentas.
- [x] Aprovar integra o plugin (mesmo efeito do 06); recusar volta o plugin para "disponível" com o parecer visível para quem pediu.
- [x] Quem pediu recebe alerta do resultado.
- [x] Ninguém aprova o próprio pedido (quatro olhos), testado.
- [x] Pedido, aprovação e recusa ficam na auditoria.

### 08: Página consolidada do plugin integrado

**O que construir:** a partir da aba Plugins, cada plugin integrado abre uma página com a visão consolidada dele: agentes que usam as ferramentas do plugin, chamadas no mês, custo, latência e saúde (ligados às telas de Saúde e Catálogo). Zendesk, Slack e Jira também ganham uma "janela" simulada do sistema externo (fila de chamados, canal com as mensagens enviadas pelos agentes, quadro de itens). Os dados mostrados respeitam o nível de acesso de quem olha.

**Bloqueado por:** 06.

**Status:** done

- [x] Plugins integrados têm o botão "Abrir"; os não integrados, não.
- [x] A página mostra agentes que usam o plugin, chamadas no mês, custo e saúde, com números vindos das execuções reais da demo (não fixos na tela).
- [x] Zendesk, Slack e Jira mostram a janela simulada do sistema externo, refletindo o que os agentes fizeram (ex.: a mensagem enviada aparece no canal do Slack).
- [x] Simular falha de uma ferramenta do plugin no Catálogo aparece como alerta de saúde na página do plugin.
- [x] Quem não tem nível para a classificação do plugin vê os números agregados, sem conteúdo do sistema externo.

### 09: Plugin dentro de um roteiro

**O que construir:** o marketplace aparece de ponta a ponta numa jornada. O roteiro do Thiago ganha os passos "integrar o Slack" e "avisar o canal de logística": o agente de troca de maquininha, depois de abrir o chamado, publica o aviso no canal, e a página consolidada do Slack mostra a mensagem. A aba Perguntas da Ferramenta ganha perguntas sobre integração com sistemas externos e governança de plugins, cada uma com a tela que serve de prova.

**Bloqueado por:** 02, 03, 06, 08.

**Status:** done

- [x] O roteiro do Thiago roda do início ao fim, sem digitar nada além do roteiro e sem chave da API, incluindo integrar o Slack e ver a mensagem no canal.
- [x] Reiniciar o roteiro do Thiago devolve o Slack a "disponível".
- [x] O cartão AS IS × TO BE do Thiago considera o aviso automático ao lojista/canal.
- [x] De 2 a 3 perguntas novas sobre plugins e integração, com "Mostrar na tela" funcionando.
- [x] Teste de roteiro atualizado.

### 10: Ensaio geral v6

**O que construir:** o fechamento da versão. Teste automático percorre os 6 roteiros com o isolamento por perfil ativo e confere a matriz de acesso da seção 3 para todas as personas. O ensaio geral, as capturas de tela dos entregáveis e a documentação de entrada são atualizados para a v6 (fotos, aba Plugins, nomes novos).

**Bloqueado por:** 04, 07, 09.

**Status:** done

- [x] Teste automático da matriz de acesso (abas × perfis) e dos 6 roteiros ponta a ponta passa.
- [x] Todos os testes da v5 continuam passando.
- [x] O roteiro de ensaio geral cita a Helena como quem apresenta Roteiros, Painel e Perguntas da Ferramenta, e inclui a demonstração de plugins.
- [x] As capturas de tela dos entregáveis são refeitas com as fotos e as abas novas.
- [x] O LEIA-ME descreve a matriz de acesso e a aba Plugins.

## 6. Critérios de aceite comuns a todo ticket

- Roda sem chave da API, com respostas determinísticas.
- Toda restrição de aba vale no menu, na rota do front e na API.
- Reiniciar a demo ou o roteiro devolve exatamente o estado inicial.
- Os testes automáticos atuais continuam passando.
- Nada de dado real: pessoas, lojistas e plugins seguem fictícios ou simulados, com o selo correspondente.

## 7. Pendências

1. ~~**Imagens dos avatares.**~~ Resolvida: `avatares-stonefalcon.zip` recebido e aplicado (ver a tabela abaixo).
2. **Onde a v6 vai morar.** Este plano foi gravado no repositório da v5. Se a v6 for uma cópia separada, mover o arquivo junto.
3. **Pitch.** Com a Helena concentrando Roteiros, Painel e Perguntas, conferir se a ordem de apresentação do ensaio geral ainda cabe no tempo do pitch.

## 8. Registro da execução (branch `v6-acesso-e-plugins`)

**Ticket 04: correspondência arquivo original → persona.** Cada arquivo foi conferido pelo nome e pela imagem; todos viraram PNG quadrado de 320×320 (fundo transparente), 97 a 117 KB, em `backend/app/static/avatares/`.

| Arquivo original | Persona (id) | Arquivo final |
|---|---|---|
| `avatar-marinaDuarte.png` | Marina Duarte (`marina`) | `marina.png` |
| `avatar-rafaelLima.png` | Rafael Lima (`rafael`) | `rafael.png` |
| `avatar-carlaNogueira.png` | Carla Nogueira (`carla`) | `carla.png` |
| `avatar-thiagoMoreira.png` | Thiago Moreira (`thiago`) | `thiago.png` |
| `avatar-lucasPrado.png` | Lucas Prado (`lucas`) | `lucas.png` |
| `avatar-helenaCastro.png` | Helena Castro (`helena`) | `helena.png` |

6 personas cobertas, nenhuma imagem sobrando.

**Decisões de implementação e desvios do plano**
- Rota das Perguntas da Ferramenta: `/perguntas` (antes `/banca`); o passo final dos roteiros ficou com o id `perguntas`.
- O Painel executivo é protegido pela API `/financas/indicadores`; `/financas/resumo`, `/financas/premissas` e `/roteiros/consolidado` seguem abertos (Finanças e Calculadora).
- As ferramentas dos plugins ficam sempre registradas no código, mas só valem enquanto o plugin está integrado (`permissoes.avaliar`, aba Ferramentas e Saúde conferem). Assim, remover um plugin nunca invalida o grafo de um agente: ele é sinalizado e escala com o motivo.
- O roteiro do Thiago **não tinha** passo com o Lucas (a versão inicial da decisão 1 citava “Thiago → Lucas”; corrigida): o Slack é interno e o criador integra direto, então não há troca de perfil nele. Mantido assim; o teste de acesso cobre os participantes reais de cada roteiro.
- SAP SuccessFactors passou de restrito a **confidencial** (revisão da v6): restrito, ele ficava aprovado e inútil, porque ninguém de Pessoas tem nível restrito. Confidencial, continua sensível (passa pela aprovação do Lucas) e roda para a Carla depois de aprovado.
- Escrita de plugin em dado confidencial ou restrito exige confirmação humana (hoje: registrar interação no Salesforce), a mesma regra do catálogo da plataforma.
- Pedido feito pela própria Segurança (Lucas) é decidido pela **Helena** (CoE de IA): ninguém aprova o próprio pedido e não há segundo revisor na demo. Ela recebe um alerta e decide na página do plugin.
- A janela do sistema externo na página do plugin respeita nível **e** área (o CoE vê todas as áreas); de fora, só os números agregados.
- Capturas de tela: `entregaveis/telas` refeitas (9 existentes + 4 novas: Roteiros, Perguntas da Ferramenta, vitrine de plugins e página do Slack). A apresentação (`apresentacao.pptx`) e a planilha **não foram regeneradas**.
