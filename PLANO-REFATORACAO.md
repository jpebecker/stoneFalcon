# StoneFalcon v4: plano de refatoração

> **Status (15/11/2026):** protótipo F0–F7 concluído (ver `LEIA-ME.md`). Faltam F8 (análise financeira em Excel) e F9 (apresentação em PowerPoint).

> **Stone** (empresa patrocinadora) + **Falcon** (grupo PinkFalcon de empreendedorismo).
> Protótipo acadêmico (UFSC) para o desafio StoneLab. Pessoas, áreas e dados são fictícios.

## 1. Diagnóstico

### O que o desafio pede (docs/contexto-desafio.pdf)
Uma **Plataforma Agêntica Institucional no-code/low-code** em que um colaborador não técnico **cria, gerencia e sustenta** os próprios agentes. Os agentes devem ser capazes de:

| Capacidade do agente | Requisito funcional da plataforma |
|---|---|
| Decisão e contexto | Onboarding guiado: descrição do problema → estrutura de agente sugerida |
| Uso de ferramentas (APIs, sistemas internos) | Integração segura respeitando o papel do usuário |
| Execução complexa (sequência e paralelo) | Guardrails nativos e silenciosos |
| Loop de raciocínio | Saúde e observabilidade com alerta ao *owner* |
| Gestão de custo, ROI e manutenção | Ciclo de vida: Criação → Modificações → Execuções → Escaladas → Deprecação |
| | Gestão financeira: custos e calculadora de investimento/retorno |

O objetivo também cita **proposta de valor, arquitetura e go-to-market interno**. Critérios de avaliação (docs/criterios-avaliacao.jpeg): **tempo de execução, custo operacional, produtividade, taxa de erros, ROI**.

### O que o v3 é
Um **funil de perguntas e respostas com controle de custo**: base aprovada (R$ 0) → Haiku → Sonnet, com RBAC por área, guardrails por regex, auditoria encadeada por hash, aprovação humana que alimenta a base, painel de custos, simulador e extensão do Chrome. São cerca de 3,2 mil linhas, sem dependências, com 104 testes passando.

### Cobertura do v3 frente aos requisitos

| Requisito | v3 | Lacuna |
|---|---|---|
| Onboarding guiado | ❌ | Os 4 agentes estão fixos em `funil/config.py`; ninguém cria agente |
| Ferramentas / APIs | ❌ | Os agentes só geram texto; não acionam nenhum sistema |
| Sequência / paralelo | ❌ | Uma chamada por pergunta |
| Loop de raciocínio | ❌ | Não há ciclo pensar → agir → observar |
| Guardrails silenciosos | ✅ | Bom (CPF/CNPJ validados, Luhn, segredos); falta cobrir argumentos e retornos de ferramentas e *prompt injection* |
| Observabilidade + alertas | ⚠️ | Só `/saude`; não há métricas por agente nem alertas ao *owner* |
| Ciclo de vida | ⚠️ | A auditoria registra execuções e aprovações, mas o agente não tem versão, estado nem deprecação |
| Gestão financeira | ✅ | Custo por camada e simulador; falta orçamento e ROI **por agente** |
| UX / visual | ⚠️ | Um `app.js` de 650 linhas, em formato de chat; não transmite "plataforma" |
| Arquitetura | ⚠️ | `http.server` com rota `?r=`, JSON em arquivo ou Redis; não escala para o que precisamos |

**Conclusão:** a refatoração muda o **conceito** do produto. O v3 é *um agente de Q&A barato*; o v4 precisa ser *a fábrica governada de agentes*. O funil do v3 não se perde: vira o **roteador de modelos** usado em cada passo de cada agente, um diferencial de custo que ferramentas genéricas não oferecem.

## 2. Visão do v4

> **StoneFalcon: a fábrica de agentes da Stone.** Qualquer colaborador descreve um processo em português e recebe um agente pronto, já ligado às ferramentas que o seu papel permite, com guardrails, monitoramento e custo sob controle. Engenharia e Segurança governam o catálogo, não cada agente.

### O que vem do v3 e o que muda

| Peça do v3 | Destino no v4 |
|---|---|
| Funil base → Haiku → Sonnet | **Roteador de modelos** por passo do agente, com cache semântico aprovado |
| `guardrails.py` | **Camada de guardrails** aplicada a entrada, saída, argumentos e retornos de ferramentas |
| Auditoria encadeada por hash | **Trilha de ciclo de vida** que cobre todos os eventos do agente |
| Aprovação humana → base | **Base de conhecimento** do agente com curadoria pela área dona |
| RBAC por área | **RBAC por papel** em ferramentas e agentes (criar, usar, revisar) |
| Painel e simulador | **Finanças**: custo e ROI por agente, orçamento e calculadora |
| Extensão Chrome | Cliente leve que executa agentes publicados sobre a página aberta |
| Modo simulado | **Mantido**: a demo roda sem chave e sem internet |
| Personas (Marina, Lucas, Carla, Rafael, Helena) | Mantidas, com papéis novos (criadora, revisor de segurança, CoE) |

## 3. Arquitetura

```
 frontend (React + Vite + TS)          extensão (MV3)
   Estúdio · Agentes · Execuções ─┐        │
   Governança · Saúde · Finanças  │        │
                                  ▼        ▼
                 backend FastAPI (/api/v1, OpenAPI)
 ┌──────────────┬───────────────┬───────────────┬──────────────┐
 │ Estúdio      │ Runtime       │ Governança    │ Observação   │
 │ (onboarding: │ ReAct loop +  │ RBAC, ciclo   │ métricas,    │
 │ blueprint)   │ fluxo DAG     │ de vida,      │ health check,│
 │              │ seq/paralelo  │ revisão,      │ alertas ao   │
 │              │ + roteador    │ auditoria     │ owner        │
 └──────┬───────┴──────┬────────┴───────┬───────┴──────┬───────┘
        │       Guardrails (entrada · saída · ferramentas)
        ▼              ▼                ▼              ▼
   Claude API     Catálogo de      SQLite (dev) /   Finanças
   ou simulado    ferramentas      Postgres (prod)  (custo, ROI,
                  (mocks internos)                  orçamento)
```

**Stack:** Python 3.12+, FastAPI, SQLModel/SQLite, SDK `anthropic` (tool use nativo), `pytest`. No front: React 18, Vite, TypeScript, Tailwind, React Flow (canvas do fluxo), Recharts e TanStack Query. Para subir: um script `iniciar` (Windows e Mac/Linux) e `docker compose up` como alternativa.

### Estrutura de pastas
```
v4-final/stoneFalcon/
├─ backend/app/
│  ├─ core/         config, db, auth simulado (SSO de mentira), relógio
│  ├─ guardrails/   porta do v3 + ferramentas + prompt injection
│  ├─ audit/        trilha encadeada por hash (porta do v3)
│  ├─ llm/          cliente Claude, modo simulado, roteador (funil do v3), preços
│  ├─ tools/        catálogo, classificação de sensibilidade, mocks de APIs internas
│  ├─ agents/       modelo Agente/Versão, ciclo de vida, revisão
│  ├─ studio/       onboarding guiado → blueprint
│  ├─ runtime/      loop ReAct, executor de DAG, limites de passos e custo, escalada humana
│  ├─ observability/ métricas, health checks, regras de alerta, caixa de notificações
│  ├─ finance/      custo por execução, orçamento, ROI, calculadora
│  └─ api/          rotas por módulo
├─ backend/tests/
├─ frontend/src/{pages,components,api,styles}
├─ extensao/
├─ seed/            agentes, ferramentas e histórico de demonstração
├─ entregaveis/     analise-financeira.xlsx · apresentacao.pptx
└─ iniciar.bat / iniciar.sh / docker-compose.yml / LEIA-ME.md
```

## 4. Módulos (escopo funcional)

1. **Estúdio (onboarding guiado).** A pessoa descreve o processo ("toda manhã confiro os chargebacks do dia e abro chamado para os acima de R$ 5 mil"). O Sonnet devolve um **blueprint**: objetivo, gatilho, entradas, passos (sequência e paralelo), ferramentas sugeridas (só as que o papel dela permite), pontos de aprovação humana, nível de risco e o **tempo atual da tarefa** (linha de base do ROI). Ela ajusta no canvas, testa num *sandbox* e envia para publicação. No modo simulado, o blueprint vem de modelos prontos escolhidos por semelhança de texto (o motor de semelhança do v3).
2. **Catálogo de ferramentas.** Conectores registrados pela Engenharia, cada um com classificação (pública, interna, confidencial, restrita), papéis permitidos e limites de chamada. Mocks: consultar lojista, transações, chargebacks, abrir chamado, base de políticas de RH, enviar e-mail ou Slack (simulado). Os mocks aceitam **falha injetável** para a demo de observabilidade. Na execução, a ferramenta roda com o **papel de quem disparou** o agente, não com o de quem o criou.
3. **Runtime.** Loop ReAct sobre o tool use da Claude (pensar → chamar ferramenta → observar → decidir), com limite de passos, de tempo e de custo por execução. Um executor de DAG roda passos em sequência e em paralelo (`asyncio.gather`). Há um nó de escalada humana. Em cada passo, o roteador escolhe a camada mais barata que resolve: cache aprovado → Haiku → Sonnet.
4. **Guardrails silenciosos.** Porta do v3, mais: mascaramento de argumentos e retornos de ferramentas, bloqueio de dado restrito saindo para ferramenta de menor classificação, heurística de *prompt injection* em conteúdo externo e política por classificação. O criador não configura nada.
5. **Ciclo de vida e governança.** Estados: Rascunho → Em revisão → Publicado → Pausado → Depreciado. Toda alteração gera uma **versão** com diff. Agentes de risco alto (ferramentas confidenciais ou restritas) passam por revisão de Segurança (Lucas); os de risco baixo publicam sozinhos. Todos os eventos entram na trilha encadeada.
6. **Saúde e observabilidade.** Por agente: taxa de sucesso, latência p50/p95, custo, erro por ferramenta e escaladas. *Health checks* dos conectores. Regras de alerta (por exemplo, erro acima de X% em 1 h, latência degradada, ferramenta fora do ar, orçamento a 80%) que avisam o *owner* numa caixa de notificações. Cada agente tem um score de saúde.
7. **Finanças.** Custo por execução, agente, área e camada. Orçamento mensal com corte automático. ROI por agente (tempo de base × execuções × custo-hora − custo). Calculadora de investimento e retorno. Dashboard executivo com os **5 critérios da banca**.
8. **Extensão.** Lista os agentes publicados a que a pessoa tem acesso e roda um deles sobre o texto selecionado na página.

### Telas
Início (meus agentes e alertas) · Estúdio · Agente (fluxo, versões, execuções, saúde, custo) · Execução (passo a passo com o raciocínio e as chamadas de ferramenta) · Catálogo · Governança (fila de revisão e auditoria) · Saúde · Finanças · Dashboard executivo.

## 5. Fases de execução

| Fase | Entrega | Pronto quando |
|---|---|---|
| **F0 Fundação** | Monorepo, FastAPI, DB, auth simulado, porta de guardrails, auditoria e roteador | Os testes portados do v3 passam no backend novo |
| **F1 Ferramentas** | Catálogo, classificação, RBAC por papel, mocks com falha injetável | Uma ferramenta negada para o papel é bloqueada e auditada |
| **F2 Runtime** | ReAct + DAG seq/paralelo + limites + escalada + modo simulado | Um agente de 3 passos (2 em paralelo) roda ponta a ponta, real e simulado |
| **F3 Estúdio** | Descrição → blueprint → canvas → sandbox | A Marina cria um agente sem escrever código |
| **F4 Ciclo de vida** | Estados, versões, diff, revisão de segurança | Criar → editar → publicar → pausar → depreciar, tudo na trilha |
| **F5 Observabilidade** | Métricas, health checks, alertas, notificações | Injetar falha num mock gera alerta para o *owner* |
| **F6 Finanças** | Custo e ROI por agente, orçamento, calculadora, dashboard dos 5 critérios | Os números batem com as execuções registradas |
| **F7 Polimento** | UX/visual, seed de demo, extensão, LEIA-ME, roteiro de demo | Demo de 3 a 4 minutos sem chave e sem internet |
| **F8 Análise financeira** | `analise-financeira.xlsx` | Ver a seção 6 |
| **F9 Apresentação** | `apresentacao.pptx` | Ver a seção 7 |

F8 começa quando chegar o **documento de custos da equipe**. A ordem F0 → F2 é crítica; F5 e F6 podem andar em paralelo depois de F2.

## 6. Entregável 2: análise financeira (Excel)

### Base: docs/custos-estimados.txt (conferido em 15/11/2026)

| Item | Valor da equipe | Conferência |
|---|---|---|
| Desenvolvimento + implantação (3 devs, 1 GP e 1 QA por 5 meses) | R$ 600 mil, ou R$ 690 mil com 15% de contingência | ✅ R$ 750/h × ~800 h = R$ 600 mil |
| Módulos de integração | R$ 50 a 100 mil cada; pacote de 4 ≈ R$ 300 mil | No v4 eles viram os **conectores do catálogo** (ex.: lojistas, chamados, transações e chargebacks, RH) |
| Manutenção (hospedagem, domínio e n8n) | R$ 2,8 a 6,9 mil/mês, mais R$ 16 mil/mês com time de sustentação | Mantido |
| Tokens para 6.000 usuários | ≈ R$ 8,5 mil/mês (faixa de R$ 4,3 a 21 mil) | ⚠️ Recalculado com as premissas do próprio documento, dá **≈ R$ 7,7 mil/mês** (US$ 1.394). A diferença de ~10% pode ser o juiz da zona de dúvida ou margem; a planilha deixa isso explícito |
| Preços dos modelos | Haiku 5.5: US$ 0,10 / 0,50; Sonnet 5.5: US$ 2 / 10 por milhão de tokens | ✅ Batem com a tabela oficial da Anthropic. O Haiku custa 5× mais acima de 100 mil tokens de prompt |
| Dólar | R$ 5,52 | ⚠️ O documento diz que o config estava em 5,15, mas o v3 já usa 5,52. Fica como premissa editável na aba 1, com a cotação do dia |

### O que muda com agentes (o ponto mais importante)
O documento modela **perguntas** (uma chamada cada). Os agentes do v4 fazem **execuções com vários passos**: cada volta do ciclo de raciocínio reenvia o contexto e os resultados das ferramentas. A planilha troca, portanto, "perguntas/dia" por **execuções/dia × passos médios × tokens por passo**, separando Q&A (a carga do v3) de automações. Duas alavancas entram no modelo:
- **Cache de prompt**: no Sonnet 5.5, a leitura em cache custa US$ 0,10 contra US$ 2 de entrada normal, porque instruções e ferramentas do agente se repetem a cada passo.
- **Roteador por passo**: ele aplica a lição do documento (o Sonnet faz 12% das chamadas e gera 92% do custo) dentro dos fluxos, mandando ao Haiku os passos simples.

### n8n
Segue a recomendação do documento: o n8n serve **só às integrações**. No v4, cada conector do catálogo tem a mesma interface; no protótipo ele é um mock e, em produção, um webhook do n8n. O ciclo de raciocínio e o roteamento ficam no backend, então só as chamadas de ferramenta consomem execuções do n8n. Isso entra na planilha como premissa de execuções/mês por plano.

### Abas
Todas com fórmulas vivas (nada fixo no código):
1. **Premissas**: câmbio, preço por token (conferir na tabela oficial da Anthropic no dia), usuários, adoção por onda, mix de camadas, custo-hora, tempo por tarefa.
2. **Investimento (CAPEX)**: construção, implantação e contingência (base: documento da equipe).
3. **Operação (OPEX)**: infraestrutura, tokens por cenário, observabilidade e sustentação.
4. **Tokens**: execuções × passos × mix de camadas, com e sem roteador (a economia do funil).
5. **Benefícios**: por caso de uso, com horas economizadas, redução de retrabalho e erros, e agentes que deixam de exigir um AI Engineer.
6. **Fluxo de caixa de 36 meses**: VPL, TIR e *payback*.
7. **Sensibilidade**: cenários conservador, base e otimista, mais um tornado das premissas.
8. **Construir vs. comprar**: comparação qualitativa e de custo com ferramentas low-code de mercado (preços pesquisados e com fonte).

## 7. Entregável 3: apresentação (PowerPoint)

Cerca de 14 slides: dor (Operações × Engenharia/Segurança × custo) → por que institucional (tabela do desafio) → solução → demo (prints ou vídeo) → arquitetura → governança e guardrails → observabilidade → roteador de custo → finanças (VPL, *payback*, sensibilidade) → **go-to-market interno** (piloto em 2 áreas → ondas → CoE de IA e embaixadores por área) → KPIs (os 5 critérios) → riscos e mitigação → roadmap → pedido ao board.

## 8. Riscos e decisões em aberto
- **Documento de custos da equipe**: recebido (`docs/custos-estimados.txt`) e incorporado na seção 6.
- **Preços dos modelos**: conferidos em 15/11/2026; reconferir na véspera da apresentação.
- **Tokens com agentes**: o custo por execução será medido nas fases F2 a F6 (o roteador registra os tokens reais) e alimentará a planilha, em vez de ficar só na estimativa.
- **Hospedagem da demo**: local por padrão; nuvem (Render/Railway/Vercel) é opcional e fica para F7.
- **Escopo do canvas**: React Flow para visualizar e editar passos; sem editor de código livre (persona no-code).
