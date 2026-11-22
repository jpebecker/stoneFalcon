# Ensaio geral e roteiro do pitch (8 a 10 minutos)

Este arquivo (ticket 10 da v6, antes o 16 da v5) diz o que conferir antes de apresentar, como ensaiar e o que falar. **Na v6, quem apresenta Roteiros, Painel executivo e Perguntas da Ferramenta é a Helena**: as outras personas só iniciam o próprio roteiro pelo Início.

## 1. Teste automático dos roteiros (seis personas + o pitch v8)

```bash
cd backend && uv run pytest -q tests/test_roteiros.py tests/test_acesso.py tests/test_plugins.py
```

O teste percorre Marina, Rafael, Carla, Thiago, Lucas e Helena do início ao fim **pela API**, com as mesmas entradas que o roteiro mostra na tela, sem chave da API e sem internet. Para cada roteiro ele confere o agente montado, o teste no sandbox, a publicação (direta ou com revisão), a execução, o cartão AS IS × TO BE (cada número com a origem: medido, estimado, premissa ou hipótese) e de 3 a 5 Perguntas da Ferramenta por persona (só a Helena as lê). `test_acesso.py` confere a matriz de acesso para os seis perfis e `test_plugins.py` o marketplace. Também confere o reinício por roteiro, a busca por nome (lojista e colaborador), a sugestão da extensão e o helpdesk fictício. O conjunto todo: `uv run pytest -q` (698 testes). O pitch v8 tem teste próprio (`tests/test_pitch.py`) e a matriz de acesso da v7 está em `tests/test_matriz_v7.py`.

## 2. Checklist antes de apresentar

**Na véspera**
- [ ] Preços e dólar conferidos (`COTACAO_DOLAR` em `backend/app/core/config.py` e a tabela de preços em `backend/app/llm/precos.py`). O LEIA-ME diz a data da última conferência.
- [ ] `uv run pytest -q` passando (698 testes) e `npm run build` feito em `frontend` (o servidor serve `frontend/dist`).
- [ ] Decidir o modo: **simulado** (sem chave, resultado idêntico sempre, recomendado para o palco) ou **modelos reais** (chave em `backend/.env`, limite de gasto mensal definido). No modo real, se o serviço do modelo falhar (rede, limite), o passo usa a resposta pré-determinada e a tela mostra **“resposta de reserva”** (desligue com `STONEFALCON_RESERVA=0`); erro de chave ou de modelo escala em vez de fingir.
- [ ] Extensão carregada no Chrome (`chrome://extensions` → Modo do desenvolvedor → Carregar sem compactação → `extensao`) e conexão testada nas opções. Sem a extensão, a página `/demo/helpdesk` abre o mesmo painel sozinha (plano B).

**No dia**
- [ ] `iniciar.bat` (ou `sh iniciar.sh`) e abrir `http://localhost:8765`. O selo no topo diz o modo.
- [ ] Zoom do navegador em 100 a 110%, painel de roteiro visível na base, uma aba só para a plataforma e outra para o helpdesk.
- [ ] **Reiniciar apaga o banco, inclusive a auditoria.** No modo demonstração (padrão) qualquer perfil reinicia pelo roteiro; fora do palco, defina `STONEFALCON_DEMO=0` e só o CoE reinicia.
- [ ] Não precisa “reiniciar a demo”: **cada roteiro reinicia a plataforma no estado exato dele** ao ser iniciado (e o botão “Reiniciar” da barra faz isso de novo no meio). “Reiniciar a demo” (Início da Helena) volta ao estado geral.
- [ ] Rodar o roteiro da Marina uma vez inteiro antes de entrar, e reiniciar.
- [ ] **Apresente como Helena** (ela vê todos os roteiros): Alt + B abre as Perguntas da Ferramenta de qualquer tela, só para ela. Iniciar o roteiro de uma persona pela aba Roteiros troca para essa persona sozinho.

## 3. Roteiro do pitch (9 a 10 minutos)

Cada linha é um roteiro iniciado pela tela “Quem é você hoje?” (botão **Iniciar roteiro**). A barra na base mostra o passo e a **fala sugerida**.

| Tempo | Persona e roteiro | O que mostrar | Mensagem |
|---|---|---|---|
| 0:00 | Abertura | Tela “Quem é você hoje?” | Seis pessoas, seis jornadas: criam, governam, medem. Tudo fictício, tudo reproduzível. |
| 0:30 | **Marina** (2:30) | AS IS (8 min, hipótese) → Estúdio descreve o processo → sandbox com dado mascarado → publica sem fila → usa no helpdesk pela extensão → cartão AS IS × TO BE | Sem código, sem fila de Engenharia; o ganho é medido e cada número diz se é medido ou hipótese. |
| 3:00 | **Rafael** (3:00) | Teste sem risco → “Enviar para revisão” → Lucas aprova (troca de perfil sozinha) → execução com o lojista suspeito: passos paralelos, Sonnet explicado, **pausa pedindo confirmação** → auditoria | Ação sensível nunca é automática; quem confirmou e quando fica na trilha encadeada. |
| 6:00 | **Lucas** (1:30) | Sistema fora do ar → execução escala com motivo → alerta no sino → **assumir** e **Pausar** (a ação do alerta) → normalizar e o alerta fecha | Governança sem headcount por time: catálogo uma vez, revisão só do risco alto. |
| 7:30 | **Helena** (2:00) | AS IS × TO BE consolidado → painel dos 5 critérios → economia do roteador → calculadora partindo de um processo | Retorno, custo e payback com premissas à vista. |
| 9:30 | **Plugins** (1:00, opcional) | Thiago: aba Plugins → integrar o Slack (interno, direto) → agente avisa o #logistica → página do Slack com a mensagem. Carla: SAP vira pedido para o Lucas | Marketplace é a aquisição, Catálogo é a governança: sensível passa pelos quatro olhos. |
| 10:30 | Fechamento | Alt + B (Helena) → duas Perguntas da Ferramenta com “Mostrar na tela” | Cada resposta tem a tela de prova. |

**Carla e Thiago** entram como cartão AS IS × TO BE (30 s cada, `/roteiro/carla` e `/roteiro/thiago`, abertos pela Helena) e ficam disponíveis para perguntas: Carla prova que o CPF não chega ao modelo; Thiago mostra três consultas em paralelo e o estoque baixo no chamado. Se sobrar tempo, rode o roteiro completo de um deles no lugar do Lucas.

Se a duração do pitch for menor, corte nesta ordem: Plugins, Lucas, Helena (fica só o painel), Rafael (fica até a pausa para confirmação). A Marina é a bala traçante e não sai.

## 3b. Pitch v8: do seletor ao plugin criado pela equipe (≈ 10 minutos)

Na aba **Roteiros** (como Helena) o cartão **Pitch v8** (selo “pitch”) inicia o roteiro `pitch`: ele reinicia a plataforma (com o plugin Arquivos e Planilhas
integrado e o Google Sheets e o Slack integrados pelo Thiago) e **troca de perfil sozinho** (Helena → Thiago → Helena → Lucas → Helena). Nada é digitado e não
precisa de chave nem de internet. A fala de cada passo marca com **[v8: …]** (ou **[v7: …]**) onde cada recurso aparece.

| Tempo | Perfil | Tela | Recurso | Plano B |
|---|---|---|---|---|
| 0:00 | Helena | Contexto do pitch | a dor: o CoE não enxerga o que os times criam | — |
| 0:40 | Helena | Tela de entrada | **seletor radial** (mouse, setas e Enter) | em tela estreita vira grade de cartões; “Reiniciar” da barra volta |
| 1:20 | Thiago | Estúdio com a planilha como fonte | **agente trabalhador** (uma tarefa só) | a planilha **já é a local** (sem internet) |
| 2:20 | Thiago | “Transformar em processo” e publicar | **processo de blocos** (dados em paralelo, agente, chamado, aviso) | sem a extensão, o Estúdio abre pelo roteiro |
| 3:20 | Thiago | Sandbox do processo: “Como o agente decidiu” | balanceador (v7) | o simulador responde igual sempre |
| 4:00 | Thiago | Página do processo: **Rotina** + Rodar agora | tarefa de rotina | o relógio da demo (+1 semana) dispara sem esperar |
| 4:45 | Thiago | Plugins → **Arquivos e Planilhas** | **plugin de verdade**: prévia, classificação, download | os arquivos já vêm semeados |
| 5:30 | Thiago | Plugins → **Crie o seu plugin** (pedido já preenchido) | rascunho genérico + comprar × construir | o rascunho é determinístico (igual sem chave) |
| 6:30 | Helena | Plugins → pedido do Thiago | **analista de IA** aprova com parecer | o parecer já vem preenchido |
| 7:15 | Lucas | Plugins → pedido (dado confidencial) | **quatro olhos**: aval da Segurança; plugin “interno · conceitual” publicado | idem |
| 7:45 | Helena | **Mapa de IA** | camada de processos com pulso | a linha do tempo ao lado mostra a execução com o selo “rotina” |
| 8:40 | Helena | Finanças | custo e ROI **por processo**, agentes por dentro, **Exportar para planilha** | histórico de demonstração já tem vários provedores |
| 9:30 | Helena | Cartão AS IS × TO BE do Thiago | a rotina semanal conta no ganho | — |

Atenção: **só o Claude roda de verdade; os outros provedores são simulados** (selo “simulado” em toda tela) e, entre os plugins, **só o Arquivos e Planilhas é de verdade**
(os plugins criados por pedido são “interno · conceitual”). O teste automático do roteiro é `tests/test_pitch.py` (e `tests/test_plugin_interno.py` para as aprovações).
O tempo acima é uma **estimativa por contagem de palavras e cliques** (a fala corrida soma menos de 5 min), ainda não cronometrada ao vivo.

### Checklist do fluxo v8 (antes de apresentar)
- [ ] `uv run pytest -q` verde e `npm run build` feito; versão **8.2.0** em `/api/v1/saude` e na extensão (`StoneFalcon 8.2`).
- [ ] Reiniciar a demo e conferir: o seletor radial abre com seis pessoas; Plugins mostra “Arquivos e Planilhas” com o selo **real**; Processos lista onze processos (a Helena e o Lucas têm o seu) e o sino de cada pessoa já traz um alerta.
- [ ] Ensaiar uma vez, como Thiago: agente → processo → rotina → Arquivos e Planilhas (prévia e download) → “Crie o seu plugin”; depois, como Helena e Lucas, as duas aprovações.
- [ ] Em Finanças (Helena): custo por processo, a lista dos agentes dentro de um processo e **Exportar para planilha** (o arquivo novo aparece no plugin).
- [ ] **8.1, alertas:** como qualquer persona, abrir Alertas: o alerta do perfil já está lá (processo de dúvidas lento, triagem falhando, orçamento a 88%, estoque lento, transações fora para a Engenharia, custo a 88%); **Assumir** com uma nota e ver “em tratamento · por” em Saúde; usar a **ação** do alerta (pausar, abrir o processo, revisar o orçamento ou abrir o sistema em Saúde). Cada roteiro guiado traz o passo “veja e trate o seu alerta” e começa **sem** alertas.
- [ ] **8.2, o falcão:** entrar pela roda e ver o voo de boas-vindas até a marca do menu; como Marina, **Executar** um agente (o falcão paira ao lado de “Executando…” e voa até a aba Execuções, que acende por um instante); publicar no Estúdio (voa até Agentes); abrir uma lista vazia (Revisões, sem pendências) e ver o falcão parado; com o sistema em “reduzir movimento”, conferir que ele só aparece parado. Em erro ou bloqueio, nenhum falcão.
- [ ] Perguntas da Ferramenta (Alt + B): as três novas do v8 (agentes × processos, o plugin é de verdade, como evitar clonar um fornecedor), cada uma com “Mostrar na tela”.
- [ ] Vindo da v7: remover a extensão antiga e carregar a pasta `extensao` de novo; o banco antigo abre sozinho (as tabelas e colunas novas são acrescentadas).

## 4. Plano B

| Problema | O que fazer |
|---|---|
| A extensão não está instalada ou o Chrome bloqueou | Abra `/demo/helpdesk?chamado=4812&perfil=marina`: selecionar o texto mostra “Perguntar ao StoneFalcon” e abre o mesmo painel dentro da página. |
| A API da Anthropic falhou (modo real) | O passo usa a resposta de reserva e mostra o aviso; ou volte ao modo simulado removendo a chave do `.env`. |
| O roteiro ficou num estado estranho | **Reiniciar** na barra (apaga o que foi criado no roteiro e volta ao passo 1). |
| O servidor não responde | `iniciar.bat` de novo; o banco recria o estado inicial sozinho. |
| Pergunta fora do roteiro | Alt + B (como Helena), filtre por persona ou tema. |

## 5. O que o ensaio não cobre

- Com a v6 o pitch passa de 10 min com a demonstração de plugins: o tempo de cada bloco ainda não foi cronometrado ao vivo (pendência 3 do plano da v6).

- A extensão no Chrome e no Edge **não foi exercitada nesta máquina por teste automático**: os arquivos foram checados (sintaxe e manifesto), e o painel foi testado no helpdesk fictício. Carregue-a uma vez antes de apresentar.
- Chamadas à API real da Anthropic (não havia chave).
- Os tempos AS IS continuam hipóteses: validar com pessoas da área é a pendência número um antes do pitch.
