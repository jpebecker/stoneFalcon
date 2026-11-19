# StoneFalcon

[![CI](https://github.com/jpebecker/stoneFalcon/actions/workflows/ci.yml/badge.svg)](https://github.com/jpebecker/stoneFalcon/actions/workflows/ci.yml)

**A fábrica governada de agentes de IA.** Qualquer colaborador descreve um processo em português e recebe um agente pronto, ligado só às ferramentas que o seu papel permite, com guardrails, monitoramento e custo sob controle. Engenharia e Segurança governam o catálogo, não cada agente.

> **Stone** (empresa patrocinadora) + **Falcon** (grupo PinkFalcon de empreendedorismo).
> Protótipo acadêmico (UFSC) para o desafio StoneLab. **Não é um produto da Stone.** Pessoas, áreas, lojistas e políticas são fictícios.

## Ligar no computador

Precisa do **Python 3.11+** e, só na primeira vez, do **Node.js LTS** (para compilar as telas).

- **Windows:** dois cliques em `iniciar.bat`.
- **Mac/Linux:** `sh iniciar.sh`.

**Atualizando de uma versão anterior (v7 ou antes):** é só rodar o script da versão nova na mesma pasta. Ele **recompila as telas** quando a versão ou o código delas mudou (por isso não abre mais as telas antigas) e **reinstala as dependências do back** quando o `backend/requirements.txt` mudou. O banco (`backend/dados`) continua valendo: a v8 só acrescenta tabelas e colunas. **Vindo da v7:** remova a extensão antiga em `chrome://extensions` e carregue a pasta `extensao` de novo (o Chrome guarda a versão antiga). Se o Chrome ainda mostrar a extensão antiga, remova-a em `chrome://extensions` e carregue a pasta `extensao` de novo.

Mensagens claras em português para o que costuma dar errado: **Python abaixo de 3.11**, **Node.js ausente** (só quando falta compilar as telas) e **porta ocupada** (outra cópia aberta; use `STONEFALCON_PORTA=8766`). Variáveis opcionais: `STONEFALCON_PORTA` (padrão 8765), `STONEFALCON_SEM_NAVEGADOR=1` e, no Windows, `STONEFALCON_SEM_PAUSA=1`.

Abre em **http://localhost:8765**. Sem configuração nenhuma roda em **modo simulado**: sem chave, sem custo e sem internet. Runtime, guardrails, auditoria, alertas e custos funcionam como no modo real; só o texto produzido pelos modelos é de exemplo, e tokens e custos são estimados com a mesma régua.

### Modelos de verdade
1. Crie uma chave em https://platform.claude.com e **defina um limite de gasto mensal**.
2. Copie `backend/.env.exemplo` para `backend/.env` e preencha `ANTHROPIC_API_KEY`.
3. Ligue de novo. O selo no topo muda para **Modelos reais**.

Nunca coloque a chave no código, na extensão ou no Git (`.env` está no `.gitignore`).

### Desenvolvimento
```bash
cd backend && uv sync && uv run uvicorn app.main:app --reload --port 8765   # um processo só (sem --workers): os plugins integrados ficam num cache em memória
cd frontend && npm install && npm run dev        # http://localhost:5173 (repassa /api ao backend)
cd backend && uv run pytest -q                   # 558 testes, sem chave nem internet
```

### Extensão copiloto (Chrome/Edge)
> **Vinha da v7 (ou anterior)?** Remova a extensão antiga em `chrome://extensions` e carregue a pasta `extensao` de novo: o Chrome guarda a versão antiga até isso. Depois da troca, a página de extensões mostra **StoneFalcon 8.0** (versão 8.0.0).

`chrome://extensions` → Modo do desenvolvedor → **Carregar sem compactação** → pasta `extensao`. Na primeira vez abre uma tela de boas-vindas e testa a conexão com a plataforma (com diagnóstico: servidor desligado, endereço errado, demora). Depois:

- **Botão flutuante** “Perguntar ao StoneFalcon”: aparece só quando há texto selecionado.
- **Botão direito** sobre um texto: “StoneFalcon → Responder com: *agente*”, com os agentes que o seu perfil pode usar.
- **Painel lateral** em tema escuro: sugere o agente pelo trecho, preenche os campos que detectou (lojista citado, “eu mesmo” para colaborador), mostra os passos, pede a confirmação de ações sensíveis ali mesmo e guarda o histórico da sessão.
- A extensão não tem lógica nem chave: roda tudo na plataforma, com as permissões de quem está logado. Para ensaiar sem a extensão, abra `http://localhost:8765/demo/helpdesk`: um helpdesk fictício que abre o mesmo painel dentro da própria página.

## Como contribuir

- **Um ticket = um branch = um PR.** Branch `v7/NN-nome-curto` saindo de `main`; PR para `main` com o número do ticket no título e os critérios de aceite como checklist (o plano está em [PLANO-V7.md](PLANO-V7.md)).
- **A esteira de CI** (`.github/workflows/ci.yml`) roda em todo PR e em `main` e precisa estar verde para juntar:
  1. **Back:** `pytest` em Python 3.11 e 3.14, em modo simulado (sem chave da API).
  2. **Front:** checagem de tipos e compilação de produção (`npm run build`).
  3. **Extensão:** manifesto válido e arquivos citados existem (`scripts/verifica_extensao.py`).
  4. **Versão:** extensão, API e front contam o mesmo número (`scripts/verifica_versao.py`; a fonte é `backend/app/core/versao.py`).
  5. **Scripts de início:** `iniciar.sh` no Ubuntu e `iniciar.bat` no Windows sobem a plataforma e respondem a versão em `/api/v1/saude` (`scripts/fumaca_iniciar.py`).
- Para rodar o mesmo na sua máquina: `cd backend && uv run pytest -q`, `cd frontend && npm run build` e `python scripts/verifica_extensao.py` e `python scripts/verifica_versao.py`.
- Configuração do repositório (feita no GitHub, fora do código): em *Settings → Branches*, proteger `main` exigindo os jobs da esteira verdes antes de juntar.

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

## Novidades da v7

- **Atalho “Criar Agente de IA” na extensão** (painel lateral e menu do botão direito): abre o Estúdio numa aba nova, já no mesmo perfil, por um **passe de uso único** (60 s, vale uma vez; nem o perfil nem o texto vão no endereço). Quem não tem a aba Estúdio (Helena, Lucas) vê “Seu perfil não cria agentes”. Com uma planilha aberta, o painel oferece **“Criar Agente de IA a partir desta planilha”**.
- **Vários provedores de IA + balanceador.** Registro único (`backend/app/llm/registro.py`) com Claude, Gemini, GPT, DeepSeek e Grok, preços das tabelas públicas de 17/11/2026 (fonte e data em cada modelo). **Só o Claude roda de verdade; os outros são simulados** (selo “simulado” em toda tela). O balanceador dá a cada passo um nível de esforço (leve a crítico), escolhe o modelo mais barato que atende, delega a outro provedor se um cai e mostra “como o agente decidiu” na execução. Em Saúde, a Helena vê a política, simula a queda de um provedor e roda uma carga de teste. Finanças mostra o gasto por provedor e por modelo e o “e se tudo rodasse em X”.
- **Mapa de IA** (aba só da Helena): quem criou → agentes → modelos por provedor → plugins/ferramentas → plataformas, atualizado sozinho a cada poucos segundos, com pulso por execução, filtros por área e provedor e linha do tempo.
- **Tarefa de rotina:** o criador agenda um agente publicado (“toda segunda às 9h”) com entrada fixa; roda em nome de quem agendou, com as mesmas permissões, guardrails e orçamento; ação sensível espera a confirmação humana. Na demo, o relógio acelerado e “Rodar agora” mostram isso sem esperar.
- **Plugin Google Sheets** (só leitura) e a **planilha fictícia local** (`/demo/planilha`, para ensaiar sem internet). O Google Sheets desenha a grade sem texto selecionável, então a extensão lê só o **endereço** da aba e a plataforma importa a versão **publicada na web**.
- **Roteiro do pitch v7** (aba Roteiros, da Helena) e três Perguntas da Ferramenta novas. Detalhes em [ENSAIO-GERAL.md](ENSAIO-GERAL.md).

## Acesso por perfil e plugins (v6)

**A interface obedece ao perfil.** O back diz, junto com os dados da pessoa logada (`/eu`), quais abas ela vê (`abas`, calculado a partir dos papéis em `app/core/identidade.py`: uma fonte de verdade só). O menu e as rotas do front só leem essa lista; endereço digitado sem permissão volta ao Início; a API responde 403.

| Aba | Helena Castro (CoE de IA) | Demais perfis |
|---|---|---|
| Início, Agentes, Execuções, Saúde, Finanças, Ferramentas, **Plugins** | sim | sim |
| **Mapa de IA** (v7) | sim | **não** |
| Estúdio / Revisões / Auditoria | pelos papéis (criador / revisor de segurança / CoE ou Segurança), como na v5 | idem |
| **Roteiros** (todos), **Painel executivo**, **Perguntas da Ferramenta** (Alt + B) | sim | **não** |

Cada pessoa vê só o próprio roteiro (card “Seu roteiro guiado”, no Início). Os passos de quatro olhos continuam trocando de perfil (Rafael → Lucas → Helena; Carla → Lucas; Lucas → Marina): quem participa de um passo consegue carregar o roteiro para a barra funcionar, mas a página AS IS × TO BE de outra persona volta ao Início. “Perguntas da banca” virou **Perguntas da Ferramenta** e é só da Helena; os roteiros dos outros perfis terminam no cartão AS IS × TO BE.

**Fotos das personas** em `backend/app/static/avatares/<id>.png` (servidas em `/avatares/`); se a foto não carrega, aparecem as iniciais na cor da persona.

**Marketplace de plugins (simulado).** A aba **Plugins** mostra 9 plugins homologados (Zendesk, Salesforce, Slack, Jira, Google Drive, Google Sheets, ServiceNow, SAP SuccessFactors, Datadog): nomes reais, ícone genérico por categoria e selo “simulado”, sem logo oficial. O plugin nunca é executado: só as ferramentas que ele traz, com o mesmo contrato do Catálogo.

- **Integrar** (criador da área do plugin ou Engenharia): plugin público/interno entra na hora; as ferramentas aparecem no Catálogo com a origem “plugin X” e viram passo no Estúdio. Plugin **confidencial ou restrito** (Salesforce, SAP) vira pedido na fila de Revisões do Lucas, com parecer; ninguém aprova o próprio pedido (o pedido feito pela Segurança é decidido pela Helena, na página do plugin); quem pediu recebe o resultado nos alertas. Escrita em dado confidencial (registrar interação no Salesforce) exige confirmação humana a cada execução. Quem não cria nem governa só registra o pedido.
- **Página do plugin integrado:** agentes que usam, chamadas no mês, custo, latência e saúde (das execuções reais da demo) e, para Zendesk, Slack e Jira, uma janela simulada do sistema externo. Sem nível para a classificação do plugin, só os números agregados.
- Remover a integração tira as ferramentas do Catálogo; os agentes que as usam ficam sinalizados e escalam com o motivo. Integração, pedido, aprovação e remoção ficam na auditoria; reiniciar a demo desfaz tudo.
- O roteiro do Thiago inclui integrar o Slack e ver o aviso do agente no canal #logistica.
- Observação: aprovar um plugin não libera dado para todos. O SAP é confidencial e homologado só para Pessoas (RH): depois de aprovado, roda para a Carla, mas não para quem é de outra área ou não tem o nível.

## Roteiros guiados (v5)

A demonstração deixou de depender de quem apresenta saber onde clicar. Cada persona tem um **roteiro**: a mesma jornada, do mesmo jeito sempre, com entradas pré-determinadas e sem chave da API.

Na tela inicial (“Quem é você hoje?”) escolha **Iniciar roteiro**. A barra na base mostra “Passo 3 de 8 · Testar no sandbox”, a ação esperada e a fala sugerida; **Avançar** troca de perfil sozinho e abre a tela do passo. **Reiniciar** devolve a plataforma ao estado exato do início do roteiro.

| Persona | Processo (AS IS → TO BE) | O que o roteiro prova |
|---|---|---|
| **Marina Duarte** (Atendimento) | Resposta a dúvidas de lojistas: 8 min (hipótese) → agente | Criação sem código, publicação sem fila, uso na plataforma e na extensão |
| **Rafael Lima** (Prevenção a Fraudes) | Triagem de chargebacks: 25 min (hipótese) → agente | Passos paralelos, roteador explicando o Sonnet, **pausa para confirmação humana**, revisão de segurança e auditoria |
| **Carla Nogueira** (Pessoas) | Férias e benefícios: 10 min (hipótese) → agente | CPF e e-mail da ficha viram marcadores antes do modelo; nada no log |
| **Thiago Moreira** (Logística) | Troca de maquininha: 12 min (hipótese) → agente | Cadastro, regra e estoque em paralelo; nova ferramenta de estoque; chamado e aviso |
| **Lucas Prado** (Engenharia) | Governança sem headcount | Revisão só do risco alto, sistema fora do ar → alerta → pausa de emergência → normalização |
| **Helena Castro** (CoE de IA) | Gestão do retorno e do custo | AS IS × TO BE consolidado, 5 critérios da banca, economia do roteador, calculadora partindo dos processos |

Cada roteiro termina num cartão **AS IS × TO BE** nos 5 critérios (tempo, custo, produtividade, erros, ROI). **Cada número diz de onde vem**: *medido* (tempo do agente e custo em tokens da execução do roteiro), *estimado* (sem execução, pelo desenho do agente), *premissa* (R$ 45/h, aproveitamento, conferência humana) ou *hipótese* (o AS IS, até validarmos com a área).

**Perguntas da Ferramenta** (só da Helena): tela própria (menu, ou **Alt + B** de qualquer lugar) com 3 a 5 perguntas por persona e por tema (segurança, custo, escala, por que não um low-code genérico), cada uma com a resposta curta e o botão **Mostrar na tela**.

**Roteiro do pitch de 8 a 10 minutos e checklist:** [ENSAIO-GERAL.md](ENSAIO-GERAL.md). **Perfis (login simulado):** as seis personas acima; nos campos do agente ninguém digita código: lojista se escolhe pelo nome, colaborador vem como “Eu mesmo” (e o RH busca outros por nome).

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
 Claude Haiku 5.5 / Sonnet 5.5 (ou simulador); Gemini, GPT, DeepSeek e Grok só simulados
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
| `backend/app/plugins` | marketplace simulado: definições dos 9 plugins, sistemas externos fictícios, integração, pedidos e página consolidada |
| `backend/app/seed` | agentes de exemplo, demo inicial, histórico sintético |
| `backend/app/roteiros` | roteiros por persona, valor medido (AS IS × TO BE), Perguntas da Ferramenta, reinício por roteiro |
| `backend/app/runtime/respostas.py` | respostas pré-determinadas dos agentes (modo simulado e reserva do modo real) |
| `backend/app/static/helpdesk.html` | helpdesk fictício para ensaiar a extensão |
| `frontend/src/pages` | uma tela por arquivo |

## Números e de onde vêm

- **Preços** (US$/milhão de tokens, tabela oficial da Anthropic, conferida em 15/11/2026): Haiku 5.5 a 0,10 / 0,50 (prompts até 100 mil tokens; acima, 0,50 / 2,50); Sonnet 5.5 a 2 / 10, leitura de cache 0,10. A leitura de cache do Haiku (0,01) é **estimativa** (10% da entrada). Confira na véspera.
- **Dólar:** R$ 5,52 (`docs/custos-estimados.txt`). Ajuste em `COTACAO_DOLAR`.
- **Investimento e operação:** `docs/custos-estimados.txt` — R$ 690 mil (com 15% de contingência), módulos de integração R$ 300 mil, R$ 6,9 mil/mês de hospedagem + R$ 16 mil/mês de sustentação.
- **Premissas nossas, a validar num piloto:** R$ 45/h, 50% do tempo liberado vira ganho real, 2 min de conferência humana por tarefa, 25% de adoção em 12 meses, 1 execução por usuário ativo por dia útil, 8% de retrabalho manual.
- O **histórico de demonstração** é gerado pelo próprio app (marcado `demo`), não é medição.

## O que foi testado e o que não foi

- **558 testes automáticos** (`uv run pytest -q`): semelhança de texto e guardrails portados do v3, catálogo e permissões, runtime (paralelismo real, aprovação, retomada com o dado real, limites, escalada), Estúdio, ciclo de vida e revisão, alertas, finanças e as rotas da API. O **ensaio geral** (`tests/test_roteiros.py`) percorre os seis roteiros do início ao fim pela API (e `tests/test_pitch.py`, o roteiro do pitch v7); `tests/test_matriz_v7.py` confere a matriz de acesso da v7 para os seis perfis; `tests/test_acesso.py` confere a matriz de acesso (abas × perfis, roteiros × perfis, cada passo dos roteiros com o perfil do passo) e `tests/test_plugins.py` o marketplace.
- **Testado no navegador:** as telas da v4 e, na v5, os roteiros da Marina (até o helpdesk com o painel do copiloto), do Rafael (criação, revisão do Lucas, execução com confirmação e cartão AS IS × TO BE) e do Lucas (até o catálogo), o consolidado da Helena e as perguntas; na v6, o menu por perfil (Marina e Helena), a redireção de endereço sem permissão, a vitrine de plugins, a integração do Zendesk (Marina) e a do Slack no roteiro do Thiago até a criação do agente, além das capturas de tela refeitas.
- **Não testado:** chamadas à API real da Anthropic (não havia chave neste ambiente; o formato segue o SDK oficial `anthropic` 2.8), a **extensão carregada no Chrome** (os arquivos foram checados e o painel foi testado dentro do helpdesk fictício, mas o botão flutuante, o menu do botão direito e o painel lateral nativo não foram exercitados), os roteiros de Carla, Thiago e o restante do Lucas e da Helena na interface (cobertos só pelo ensaio via API), `iniciar.bat` numa máquina limpa e o Edge. Os tempos AS IS dos roteiros são hipóteses.

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
