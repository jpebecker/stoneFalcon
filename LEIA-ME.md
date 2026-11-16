# StoneFalcon

**A fábrica governada de agentes de IA.** Qualquer colaborador descreve um processo em português e recebe um agente pronto, ligado só às ferramentas que o seu papel permite, com guardrails, monitoramento e custo sob controle. Engenharia e Segurança governam o catálogo, não cada agente.

> **Stone** (empresa patrocinadora) + **Falcon** (grupo PinkFalcon de empreendedorismo).
> Protótipo acadêmico (UFSC) para o desafio StoneLab. **Não é um produto da Stone.** Pessoas, áreas, lojistas e políticas são fictícios.

## Ligar no computador

Precisa do **Python 3.11+** e, só na primeira vez, do **Node.js LTS** (para compilar as telas).

- **Windows:** dois cliques em `iniciar.bat`.
- **Mac/Linux:** `sh iniciar.sh`.

Abre em **http://localhost:8765**. Sem configuração nenhuma roda em **modo simulado**: sem chave, sem custo e sem internet. Runtime, guardrails, auditoria, alertas e custos funcionam como no modo real; só o texto produzido pelos modelos é de exemplo, e tokens e custos são estimados com a mesma régua.

### Modelos de verdade
1. Crie uma chave em https://platform.claude.com e **defina um limite de gasto mensal**.
2. Copie `backend/.env.exemplo` para `backend/.env` e preencha `ANTHROPIC_API_KEY`.
3. Ligue de novo. O selo no topo muda para **Modelos reais**.

Nunca coloque a chave no código, na extensão ou no Git (`.env` está no `.gitignore`).

### Desenvolvimento
```bash
cd backend && uv sync && uv run uvicorn app.main:app --reload --port 8765
cd frontend && npm install && npm run dev        # http://localhost:5173 (repassa /api ao backend)
cd backend && uv run pytest -q                   # 154 testes, sem chave nem internet
```

### Extensão (Chrome/Edge)
`chrome://extensions` → Modo do desenvolvedor → **Carregar sem compactação** → pasta `extensao`. Aparece um botão no canto das páginas: ele abre os agentes da plataforma no painel lateral levando o texto selecionado. O botão direito sobre um texto faz o mesmo. A extensão não tem lógica nem chave: roda tudo na plataforma, com as permissões de quem está logado.

## O que o desafio pede e onde está

| Requisito (contexto-desafio.pdf) | Como o StoneFalcon atende | Onde |
|---|---|---|
| Onboarding guiado | Descrição em português → agente montado (passos, ferramentas, modelo, risco, custo), explicado em linguagem simples, editável no canvas e testável no sandbox | Estúdio · `app/studio` |
| Integração segura de ferramentas | Catálogo governado; cada ferramenta tem classificação (pública → restrita) e áreas; roda com as permissões de **quem disparou** o agente; ações sensíveis pedem confirmação humana | Ferramentas · `app/tools` |
| Guardrails nativos e silenciosos | CPF, CNPJ, cartão, e-mail, telefone e segredos viram marcadores antes de qualquer modelo; o sistema interno recebe o dado real **só se a classificação dele cobrir a do sistema de onde o dado veio** (dado confidencial não vaza para uma ferramenta interna); saída limpa; conteúdo externo com cara de instrução é isolado | `app/guardrails`, `app/runtime` |
| Saúde e observabilidade | Métricas por agente e por sistema integrado, nota de saúde, 5 regras de alerta ao dono (falhas, lentidão, sistema fora, sistema lento, orçamento) que fecham sozinhas | Saúde, Alertas · `app/observability` |
| Rastreabilidade e ciclo de vida | Rascunho → revisão → publicado ⇄ pausado → depreciado; versões imutáveis com diff; revisão da Segurança (quatro olhos) para risco alto; pausa de emergência também barra ações já pendentes; trilha encadeada por hash | Agentes, Revisões, Auditoria · `app/agents`, `app/audit` |
| Gestão financeira | Custo por execução/agente/área/modelo, economia do roteador, retorno por agente, orçamento mensal com corte, calculadora (VPL, TIR, payback) | Finanças, Calculadora · `app/finance` |
| Agente: decisão, ferramentas, sequência/paralelo, raciocínio | Grafo de passos (paralelos rodam juntos), loop pensar → agir → observar com tool use, limites de passos e de custo, escalada segura para humano | `app/runtime` |
| Critérios de avaliação (tempo, custo, produtividade, erros, ROI) | Painel executivo com os 5, medidos nas execuções | Painel executivo |

## Roteiro de demonstração (≈ 4 minutos)

**Antes de gravar:** entre como **Helena** → Início → **Reiniciar a demo**. Isso deixa 3 agentes publicados e 30 dias de histórico gerado (sinalizado nas telas como cenário, não medição).

1. **Criar sem código (Marina, 50 s).** Estúdio → exemplo *Pedido de troca de maquininha* → **Montar meu agente**. Mostre o canvas (dois passos na mesma coluna rodam em paralelo), o risco médio e o custo por execução. Em *Testar no sandbox*, use `L1001` e um relato → linha do tempo com os dados mascarados. **Publicar**.
2. **Permissão por papel (Marina, 15 s).** Recomeçar e descrever *"toda manhã confiro os lojistas com chargeback e decido se bloqueio o repasse"* → o Estúdio avisa que tirou as ferramentas confidenciais e restritas, com o motivo.
3. **Agente com ação sensível (Rafael, 40 s).** Agentes → *Triagem de chargebacks* → executar com `L1003`. Os dois primeiros passos rodam juntos; a análise sobe para o modelo forte (abra o passo: *por que este modelo*). O agente abre o chamado e **para pedindo confirmação** para reter repasses → **Confirmar ação**. Com `L1001` (sem risco) ele nem propõe a retenção.
4. **Saúde e alerta (Lucas e Marina, 40 s).** Lucas → Ferramentas → *Consultar cadastro do lojista* → simular **fora do ar**. Marina → executa *Resposta a dúvidas de lojistas* → a execução **escala para humano** com o motivo; o **sino** acende com alerta crítico; Saúde mostra a nota caindo. Lucas normaliza → o alerta fecha sozinho.
5. **Governança (Lucas, 25 s).** Auditoria: selo **cadeia íntegra**, filtros por ciclo de vida, execuções e ferramentas; abra um evento para ver que só há marcadores no lugar dos dados pessoais.
6. **Gestão (Helena, 50 s).** Painel executivo: os 5 critérios da banca. Finanças: **economia do roteador** (~79%) e o gráfico por modelo; o Sonnet é a maior parte do custo. Calculadora: mude a adoção e veja payback, VPL e TIR.
7. **Extensão (10 s).** Em qualquer site, selecione um parágrafo → botão flutuante → o painel lateral abre com o trecho no agente.

Perfis (login simulado): **Marina** (Atendimento, cria agentes), **Rafael** (Prevenção a Fraudes, acesso restrito), **Carla** (Pessoas), **Lucas** (Engenharia: revisa segurança e mantém o catálogo), **Helena** (CoE de IA: vê custos, painel e auditoria de tudo).

## Arquitetura

```
 frontend (React + Vite + Tailwind + React Flow)        extensão (MV3)
                         │  /api/v1                         │
                         ▼                                  ▼
 backend FastAPI ── Estúdio ── Runtime (DAG + loop + roteador) ── Ciclo de vida ── Saúde ── Finanças
        │                │                 │
        │          Guardrails ──── Catálogo de ferramentas (mocks; em produção: webhooks n8n/APIs)
        ▼
 SQLite (protótipo) / Postgres (produção) · trilha de auditoria encadeada por hash
        ▲
 Claude Haiku 5.5 / Sonnet 5.5 (ou simulador determinístico)
```

| Pasta | Conteúdo |
|---|---|
| `backend/app/studio` | onboarding guiado: descrição → blueprint (Sonnet ou galeria de padrões) |
| `backend/app/runtime` | executa o grafo, loop de raciocínio, limites, escalada, aprovação e retomada |
| `backend/app/llm` | cliente Claude (cache de prompt, reserva em recusa), simulador, roteador, preços |
| `backend/app/tools` | catálogo, permissões, executor governado, sistemas fictícios |
| `backend/app/guardrails` | mascaramento (portado do v3) e detecção de instrução embutida |
| `backend/app/agents` | blueprint, risco e custo estimado, ciclo de vida, versões e diff |
| `backend/app/observability` | métricas, alertas, nota de saúde |
| `backend/app/finance` | premissas, resumo, ROI, calculadora, indicadores da banca |
| `backend/app/seed` | agentes de exemplo, demo inicial, histórico sintético |
| `frontend/src/pages` | uma tela por arquivo |

## Números e de onde vêm

- **Preços** (US$/milhão de tokens, tabela oficial da Anthropic, conferida em 15/11/2026): Haiku 5.5 a 0,10 / 0,50 (prompts até 100 mil tokens; acima, 0,50 / 2,50); Sonnet 5.5 a 2 / 10, leitura de cache 0,10. A leitura de cache do Haiku (0,01) é **estimativa** (10% da entrada). Confira na véspera.
- **Dólar:** R$ 5,52 (`docs/custos-estimados.txt`). Ajuste em `COTACAO_DOLAR`.
- **Investimento e operação:** `docs/custos-estimados.txt` — R$ 690 mil (com 15% de contingência), módulos de integração R$ 300 mil, R$ 6,9 mil/mês de hospedagem + R$ 16 mil/mês de sustentação.
- **Premissas nossas, a validar num piloto:** R$ 45/h, 50% do tempo liberado vira ganho real, 2 min de conferência humana por tarefa, 25% de adoção em 12 meses, 1 execução por usuário ativo por dia útil, 8% de retrabalho manual.
- O **histórico de demonstração** é gerado pelo próprio app (marcado `demo`), não é medição.

## O que foi testado e o que não foi

- **154 testes automáticos** (`uv run pytest -q`): semelhança de texto e guardrails portados do v3, catálogo e permissões, runtime (paralelismo real, aprovação, retomada com o dado real, limites, escalada), Estúdio, ciclo de vida e revisão, alertas, finanças e as rotas da API.
- **Testado no navegador:** todas as telas, o fluxo da Marina no Estúdio, publicar/versionar/diff, a demo de falha com alerta, finanças, calculadora e painel.
- **Não testado:** chamadas à API real da Anthropic (não havia chave neste ambiente; o formato segue o SDK oficial `anthropic` 2.8), a extensão nesta versão (portada do v3, que foi testada no Chrome), `iniciar.bat` numa máquina limpa e o Edge.

## Protótipo x produção

| No protótipo | Em produção |
|---|---|
| login simulado por personas | SSO da Stone (grupos → papéis e nível de acesso) |
| sistemas internos fictícios | conectores reais (APIs internas ou webhooks n8n), mesmo contrato |
| semelhança por radicais e sinônimos | embeddings |
| guardrails por expressões regulares | serviço de prevenção a vazamento (DLP) + classificador de injeção |
| SQLite, **um processo** (a sequência da auditoria é protegida por trava em memória) | Postgres com controle de acesso e retenção; sequência da trilha por trava no banco (`SELECT ... FOR UPDATE` ou sequência), para rodar com vários processos |
| trilha encadeada por hash | o mesmo, com os hashes diários publicados num cofre externo (WORM) |
| alertas no sino da plataforma | também por e-mail/Slack e plantão |
| mapa de marcadores pendentes em memória | cofre de segredos com expiração |

## Uso de IA

O código deste protótipo foi escrito com o Claude (Anthropic), a pedido da equipe. Registrem isso na declaração de uso de IA do trabalho.
