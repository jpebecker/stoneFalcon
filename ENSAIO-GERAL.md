# Ensaio geral e roteiro do pitch (8 a 10 minutos)

Este arquivo é o ticket 10 do [PLANO-V6](PLANO-V6.md) (antes, o ticket 16 da v5): o que conferir antes de apresentar, como ensaiar e o que falar. **Na v6, quem apresenta Roteiros, Painel executivo e Perguntas da Ferramenta é a Helena**: as outras personas só iniciam o próprio roteiro pelo Início.

## 1. Teste automático dos roteiros (seis personas + o pitch v7)

```bash
cd backend && uv run pytest -q tests/test_roteiros.py tests/test_acesso.py tests/test_plugins.py
```

O teste percorre Marina, Rafael, Carla, Thiago, Lucas e Helena do início ao fim **pela API**, com as mesmas entradas que o roteiro mostra na tela, sem chave da API e sem internet. Para cada roteiro ele confere o agente montado, o teste no sandbox, a publicação (direta ou com revisão), a execução, o cartão AS IS × TO BE (cada número com a origem: medido, estimado, premissa ou hipótese) e de 3 a 5 Perguntas da Ferramenta por persona (só a Helena as lê). `test_acesso.py` confere a matriz de acesso para os seis perfis e `test_plugins.py` o marketplace. Também confere o reinício por roteiro, a busca por nome (lojista e colaborador), a sugestão da extensão e o helpdesk fictício. O conjunto todo: `uv run pytest -q` (558 testes). O pitch v7 tem teste próprio (`tests/test_pitch.py`) e a matriz de acesso da v7 está em `tests/test_matriz_v7.py`.

## 2. Checklist antes de apresentar

**Na véspera**
- [ ] Preços e dólar conferidos (`COTACAO_DOLAR` em `backend/app/core/config.py` e a tabela de preços em `backend/app/llm/precos.py`). O LEIA-ME diz a data da última conferência.
- [ ] `uv run pytest -q` passando (558 testes) e `npm run build` feito em `frontend` (o servidor serve `frontend/dist`).
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
| 6:00 | **Lucas** (1:30) | Sistema fora do ar → execução escala com motivo → alerta no sino → **Pausar** → normalizar e o alerta fecha | Governança sem headcount por time: catálogo uma vez, revisão só do risco alto. |
| 7:30 | **Helena** (2:00) | AS IS × TO BE consolidado → painel dos 5 critérios → economia do roteador → calculadora partindo de um processo | Retorno, custo e payback com premissas à vista. |
| 9:30 | **Plugins** (1:00, opcional) | Thiago: aba Plugins → integrar o Slack (interno, direto) → agente avisa o #logistica → página do Slack com a mensagem. Carla: SAP vira pedido para o Lucas | Marketplace é a aquisição, Catálogo é a governança: sensível passa pelos quatro olhos. |
| 10:30 | Fechamento | Alt + B (Helena) → duas Perguntas da Ferramenta com “Mostrar na tela” | Cada resposta tem a tela de prova. |

**Carla e Thiago** entram como cartão AS IS × TO BE (30 s cada, `/roteiro/carla` e `/roteiro/thiago`, abertos pela Helena) e ficam disponíveis para perguntas: Carla prova que o CPF não chega ao modelo; Thiago mostra três consultas em paralelo e o estoque baixo no chamado. Se sobrar tempo, rode o roteiro completo de um deles no lugar do Lucas.

Se a duração do pitch for menor, corte nesta ordem: Plugins, Lucas, Helena (fica só o painel), Rafael (fica até a pausa para confirmação). A Marina é a bala traçante e não sai.

## 3b. Pitch v7: demonstração integrada (≈ 9 minutos)

Na aba **Roteiros** (como Helena) o cartão **Pitch v7** (selo “pitch”) inicia o roteiro `pitch`: ele reinicia a plataforma, deixa o Google Sheets e o Slack
já integrados pelo Thiago e **troca de perfil sozinho** (Helena → Thiago → Helena). Nada é digitado e não precisa de chave nem de internet. A fala de cada
passo marca com **[v7: …]** onde cada recurso novo aparece; a barra mostra a fala com o botão **Fala**.

| Tempo | Perfil | Tela | Recurso da v7 | Plano B |
|---|---|---|---|---|
| 0:00 | Helena | Contexto do pitch | a dor: o CoE não enxerga o que os times criam | — |
| 0:45 | Thiago | `/demo/planilha` (outra aba) | planilha aberta no navegador | a planilha **já é a local** (sem internet); no Google real, só o endereço da aba é lido |
| 1:30 | Thiago | Estúdio com a planilha como fonte | atalho **Criar Agente de IA** (extensão) | sem a extensão, a própria página da planilha abre o painel (botão “Abrir o StoneFalcon”) |
| 2:30 | Thiago | Sandbox: “Como o agente decidiu” | **vários provedores + balanceador** | o simulador responde igual sempre |
| 3:30 | Thiago | Publicar | — | — |
| 4:00 | Thiago | Página do agente: **Rotina** + Rodar agora | **tarefa de rotina** (toda segunda às 9h) | o relógio da demo (+1 semana) dispara sem esperar |
| 5:00 | Helena | **Mapa de IA** (+1 semana no relógio) | **mapa ao vivo** com pulso | se o pulso não aparecer, a linha do tempo ao lado mostra a execução com o selo “rotina” |
| 6:15 | Helena | Saúde: **Simular queda** no Claude + **Simular carga** | queda de provedor e balanceador | “Reiniciar” da barra desfaz |
| 7:30 | Helena | Finanças | gasto por provedor e “e se tudo rodasse em X” | histórico de demonstração já tem vários provedores |
| 8:15 | Helena | Cartão AS IS × TO BE do Thiago | a rotina semanal conta no ganho | — |

Atenção: **só o Claude roda de verdade; os outros provedores são simulados** (selo “simulado” em toda tela). O teste automático do roteiro é `tests/test_pitch.py`.
O tempo acima é uma **estimativa por contagem de palavras e cliques** (a fala corrida soma menos de 5 min), ainda não cronometrada ao vivo (pendência 2 do plano da v7). Capturas do pitch em `entregaveis/telas/` (14 a 19: atalho da extensão, Estúdio com vários provedores, trilha do balanceador, Mapa de IA, queda de provedor em Saúde e Finanças por provedor).

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
