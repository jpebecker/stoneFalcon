# Ensaio geral e roteiro do pitch (8 a 10 minutos)

Este arquivo é o ticket 16 do [PLANO-V5](PLANO-V5.md): o que conferir antes de apresentar, como ensaiar e o que falar.

## 1. Teste automático dos seis roteiros

```bash
cd backend && uv run pytest -q tests/test_roteiros.py
```

O teste percorre Marina, Rafael, Carla, Thiago, Lucas e Helena do início ao fim **pela API**, com as mesmas entradas que o roteiro mostra na tela, sem chave da API e sem internet. Para cada roteiro ele confere o agente montado, o teste no sandbox, a publicação (direta ou com revisão), a execução, o cartão AS IS × TO BE (cada número com a origem: medido, estimado, premissa ou hipótese) e de 3 a 5 perguntas da banca. Também confere o reinício por roteiro, a busca por nome (lojista e colaborador), a sugestão da extensão e o helpdesk fictício. O conjunto todo: `uv run pytest -q` (180 testes).

## 2. Checklist antes de apresentar

**Na véspera**
- [ ] Preços e dólar conferidos (`COTACAO_DOLAR` em `backend/app/core/config.py` e a tabela de preços em `backend/app/llm/precos.py`). O LEIA-ME diz a data da última conferência.
- [ ] `uv run pytest -q` passando (180 testes) e `npm run build` feito em `frontend` (o servidor serve `frontend/dist`).
- [ ] Decidir o modo: **simulado** (sem chave, resultado idêntico sempre, recomendado para o palco) ou **modelos reais** (chave em `backend/.env`, limite de gasto mensal definido). No modo real, se o serviço do modelo falhar (rede, limite), o passo usa a resposta pré-determinada e a tela mostra **“resposta de reserva”** (desligue com `STONEFALCON_RESERVA=0`); erro de chave ou de modelo escala em vez de fingir.
- [ ] Extensão carregada no Chrome (`chrome://extensions` → Modo do desenvolvedor → Carregar sem compactação → `extensao`) e conexão testada nas opções. Sem a extensão, a página `/demo/helpdesk` abre o mesmo painel sozinha (plano B).

**No dia**
- [ ] `iniciar.bat` (ou `sh iniciar.sh`) e abrir `http://localhost:8765`. O selo no topo diz o modo.
- [ ] Zoom do navegador em 100 a 110%, painel de roteiro visível na base, uma aba só para a plataforma e outra para o helpdesk.
- [ ] **Reiniciar apaga o banco, inclusive a auditoria.** No modo demonstração (padrão) qualquer perfil reinicia pelo roteiro; fora do palco, defina `STONEFALCON_DEMO=0` e só o CoE reinicia.
- [ ] Não precisa “reiniciar a demo”: **cada roteiro reinicia a plataforma no estado exato dele** ao ser iniciado (e o botão “Reiniciar” da barra faz isso de novo no meio). “Reiniciar a demo” (Início da Helena) volta ao estado geral.
- [ ] Rodar o roteiro da Marina uma vez inteiro antes de entrar, e reiniciar.
- [ ] Alt + B abre as perguntas da banca de qualquer tela.

## 3. Roteiro do pitch (9 a 10 minutos)

Cada linha é um roteiro iniciado pela tela “Quem é você hoje?” (botão **Iniciar roteiro**). A barra na base mostra o passo e a **fala sugerida**.

| Tempo | Persona e roteiro | O que mostrar | Mensagem |
|---|---|---|---|
| 0:00 | Abertura | Tela “Quem é você hoje?” | Seis pessoas, seis jornadas: criam, governam, medem. Tudo fictício, tudo reproduzível. |
| 0:30 | **Marina** (2:30) | AS IS (8 min, hipótese) → Estúdio descreve o processo → sandbox com dado mascarado → publica sem fila → usa no helpdesk pela extensão → cartão AS IS × TO BE | Sem código, sem fila de Engenharia; o ganho é medido e cada número diz se é medido ou hipótese. |
| 3:00 | **Rafael** (3:00) | Teste sem risco → “Enviar para revisão” → Lucas aprova (troca de perfil sozinha) → execução com o lojista suspeito: passos paralelos, Sonnet explicado, **pausa pedindo confirmação** → auditoria | Ação sensível nunca é automática; quem confirmou e quando fica na trilha encadeada. |
| 6:00 | **Lucas** (1:30) | Sistema fora do ar → execução escala com motivo → alerta no sino → **Pausar** → normalizar e o alerta fecha | Governança sem headcount por time: catálogo uma vez, revisão só do risco alto. |
| 7:30 | **Helena** (2:00) | AS IS × TO BE consolidado → painel dos 5 critérios → economia do roteador → calculadora partindo de um processo | Retorno, custo e payback com premissas à vista. |
| 9:30 | Fechamento | Alt + B → duas perguntas da banca com “Mostrar na tela” | Cada resposta tem a tela de prova. |

**Carla e Thiago** entram como cartão AS IS × TO BE (30 s cada, `/roteiro/carla` e `/roteiro/thiago`) e ficam disponíveis para perguntas: Carla prova que o CPF não chega ao modelo; Thiago mostra três consultas em paralelo e o estoque baixo no chamado. Se sobrar tempo, rode o roteiro completo de um deles no lugar do Lucas.

Se a duração do pitch for menor, corte nesta ordem: Lucas, Helena (fica só o painel), Rafael (fica até a pausa para confirmação). A Marina é a bala traçante e não sai.

## 4. Plano B

| Problema | O que fazer |
|---|---|
| A extensão não está instalada ou o Chrome bloqueou | Abra `/demo/helpdesk?chamado=4812&perfil=marina`: selecionar o texto mostra “Perguntar ao StoneFalcon” e abre o mesmo painel dentro da página. |
| A API da Anthropic falhou (modo real) | O passo usa a resposta de reserva e mostra o aviso; ou volte ao modo simulado removendo a chave do `.env`. |
| O roteiro ficou num estado estranho | **Reiniciar** na barra (apaga o que foi criado no roteiro e volta ao passo 1). |
| O servidor não responde | `iniciar.bat` de novo; o banco recria o estado inicial sozinho. |
| Pergunta fora do roteiro | Alt + B, filtre por persona ou tema. |

## 5. O que o ensaio não cobre

- A extensão no Chrome e no Edge **não foi exercitada nesta máquina por teste automático**: os arquivos foram checados (sintaxe e manifesto), e o painel foi testado no helpdesk fictício. Carregue-a uma vez antes de apresentar.
- Chamadas à API real da Anthropic (não havia chave).
- Os tempos AS IS continuam hipóteses: validar com pessoas da área é a pendência número um antes do pitch.
