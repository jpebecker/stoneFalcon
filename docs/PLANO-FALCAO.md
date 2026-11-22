# Plano: o falcão da plataforma (ícone, corpo animado e ícones da interface)

Base: `main` da v8 (versão 8.1.0). Um ticket = um commit (ou um PR por ticket). Fecha como **8.2.0**.
Demonstração e decisões: artefato "Falcão StoneFalcon" (versão 2), com tudo rodando numa réplica da área logada.

## Contexto

- **O animal:** o falcão do nome Stone**Falcon** (grupo PinkFalcon). O **rosto** vira o ícone do sistema e fica sempre
  visível; o **corpo** é animado (pairando e voo lateral nos dois sentidos) e aparece só nos momentos de retorno.
- **Corpo: folha 1** (traço caligráfico, corpo inteiro de perfil). É a única com idle e voo nos dois sentidos no mesmo
  desenho e lê bem sobre fundo claro e escuro. Da folha 4 veio a "lágrima" sob o olho.
- **Rosto: folha 5** (pincel largo: arco verde da cabeça, bico em gancho claro, penas rosa do pescoço). É o único
  legível em 16 px; os da folha 4 somem (traços finos quase brancos) e o da folha 2 é um contorno fino. O pincel com
  ponta afinada é o mesmo traço do corpo, então rosto e corpo parecem o mesmo animal. Substitui a marca atual (três
  trapézios) no menu, na entrada, no favicon e na extensão.
- **Cores:** as do sistema. Corpo: traço `pedra`, penas `falcao`, rastro `tinta-3`; o `.ext-tema` acompanha sem arquivo
  extra. Rosto: sobre o quadrado escuro usa os valores da `Marca` (`#1FB37A`, `#E0428F`, bico `#E8F3EE`); sem fundo,
  `pedra`, `falcao` e `tinta`.
- **Sprites vetoriais gerados por código** (`docs/falcao/gerador.mjs`), não recortados dos bitmaps (quadros
  desalinhados, borrões, fundo). Quadro do corpo: 128 × 112. **Parado:** 6 quadros, 1,1 s. **Voo:** 8 quadros, 0,56 s,
  com rastro. **Voo para a esquerda:** espelhado. Abaixo de 72 px o traço engrossa (×1,3; ×1,7 até 48 px). Rosto: 64 × 64.
- **Animação:** a tira desliza numa janela de um quadro com CSS `steps()`; a travessia usa `requestAnimationFrame` só
  para a posição.
- **Ícones da interface** (`docs/falcao/icones.mjs`): linha no traço do sino que já existe (grade 24, traço 1,8,
  pontas redondas, `currentColor`). Sempre ao lado de texto, nunca no lugar dele. Entram em: as 15 abas do menu, o
  botão de ação principal (`botao-pedra`), os selos de resultado (concluído, falhou, simulado) e o menu da pessoa.
  Não entram em títulos, tabelas, links de texto, cartões nem botões claros. Sem biblioteca nova.
- **Regra de movimento (DESIGN.md §7.5):** só para dar retorno ou orientar. Por isso o corpo aparece **com propósito**,
  em todo momento de carga e de conclusão, e nunca voa sozinho. Não fica escondido: o rosto está sempre na tela e o
  corpo aparece em toda execução e publicação, o caminho principal de cada roteiro.
- **Movimento reduzido (§7.6):** sem batida de asa nem travessia; o falcão aparece parado no destino e some.

### Momentos do corpo

| Momento | Onde | O que faz |
|---|---|---|
| Executar agente, processo ou teste | Agente, Processo, Editor de processo, Estúdio, Alertas (ação de tratamento) | Paira ao lado do status; ao terminar bem, voa até o sino (resultado virou alerta) ou até a aba Execuções. |
| Montar o agente a partir da descrição | Estúdio | Paira com "Montando o seu agente…" (a espera mais longa). |
| Publicar agente ou processo | Estúdio, Agente, Editor de processo | Voa até a aba Agentes ou Processos, que ganha destaque curto. |
| Enviar para revisão / pedir plugin | Estúdio, Plugins, Criar plugin | Paira enquanto gera; voa até Revisões ou até o sino. |
| Analisar o trecho e executar | Painel da extensão | Paira no lugar dos blocos pulsantes. |
| Entrar pela roda | Entrada → Início | Voo de boas-vindas até a marca do menu, onde vira o rosto. |
| Etapa do roteiro concluída | Barra do roteiro | Voo curto da etapa feita até a próxima. |
| Lista vazia | Alertas, Revisões, Execuções, Plugins | Parado, sem animação, ao lado da frase do estado vazio. |

**Nunca:** erro, falha, bloqueio de guardrail, listas cheias, voo sem uma ação da pessoa antes. No máximo um voo por ação.

## Resumo

| # | Ticket | Bloqueado por | Status |
|---|---|---|---|
| 01 | Gerador do corpo e do rosto | — | feito |
| 02 | Rosto como ícone do sistema | 01 | parcial |
| 03 | Ícones da interface | — | feito |
| 04 | Componente `<Falcao>` | 01 | feito |
| 05 | Camada de voo | 04 | todo |
| 06 | Falcão na carga | 04 | todo |
| 07 | Voos de retorno e estados vazios | 05 | todo |
| 08 | Docs, roteiro e versão 8.2.0 | 02, 03, 06, 07 | todo |

Fronteira inicial: **01** e **03** (independentes).

---

# 01: Gerador do corpo e do rosto

**O que construir:** o gerador sai de `docs/falcao/` e vira `scripts/gera_falcao.mjs` (Node puro). Ele grava
`frontend/src/components/falcao/quadros.ts` (caminhos por animação e por peso de traço 1; 1,3; 1,7, e o rosto),
`frontend/public/icone.svg`, as tiras de referência em `docs/falcao/` e `extensao/icones/rosto.json` com os polígonos
do rosto, que o `extensao/icones/gerar.py` passa a rasterizar no lugar dos três trapézios. Os arquivos gerados entram no
Git; o build não roda o gerador.

**Bloqueado por:** nenhum.

**Status:** feito

- [x] `node scripts/gera_falcao.mjs` regrava tudo; rodar duas vezes não muda nada.
- [x] O script falha se algum ponto sair do quadro (128 × 112 no corpo, 64 × 64 no rosto).
- [x] Arquivos gerados com cabeçalho "gerado por scripts/gera_falcao.mjs, não edite à mão".
- [x] `npm run build` verde.

# 02: Rosto como ícone do sistema

**O que construir:** `Marca.tsx` passa a desenhar o rosto (quadrado escuro arredondado no tema claro; fundo
translúcido com a prop `claro` no menu). Favicon novo (`icone.svg`). Extensão: PNG 16/32/48/128 regerados, o rosto no
topo do painel e no botão flutuante "Perguntar ao StoneFalcon".

**Bloqueado por:** 01.

**Status:** parcial (falta conferir o favicon na aba e o ícone em `chrome://extensions`, no navegador)

- [x] Marca no menu lateral, na tela de entrada e no painel da extensão.
- [ ] Favicon conferido na aba do navegador (16 px).
- [ ] `python scripts/verifica_extensao.py` verde; ícone novo conferido em `chrome://extensions`.

# 03: Ícones da interface

**O que construir:** `frontend/src/components/Icone.tsx` com `<Icone nome="agentes" />` (SVG inline, `aria-hidden`,
`currentColor`, 18 px no menu e 16 px em botões e selos), com os desenhos de `docs/falcao/icones.mjs`. `NAV` em
`App.tsx` ganha o campo `icone`; o sino passa a usar o componente.

**Bloqueado por:** nenhum.

**Status:** feito

- [x] As 15 abas do menu com ícone à esquerda do rótulo; aba ativa e foco continuam como hoje.
- [x] Ícone no `botao-pedra` de Executar, Publicar e Enviar para revisão.
- [x] Selos de resultado com ícone (concluído, falhou, simulado/atenção) além da cor.
- [x] Menu da pessoa: Trocar de pessoa e Sair.
- [x] Nenhum controle vira só ícone: todo ícone tem texto visível ao lado.

# 04: Componente `<Falcao>`

**O que construir:** `frontend/src/components/falcao/Falcao.tsx` com
`<Falcao estado="parado" | "voo" | "estatico" direcao="direita" | "esquerda" tamanho={px} />`. Cores pelas variáveis
`--falcao-traco`, `--falcao-pena` e `--falcao-rastro`, definidas no próprio `.falcao` a partir dos tokens (funciona no
tema claro, no `.ext-tema` e sobre o menu com a prop `claro`). Estilos em `global.css`.

**Bloqueado por:** 01.

**Status:** feito

- [x] `aria-hidden="true"`: o falcão nunca é a única informação.
- [x] Peso do traço pelo tamanho (≤ 48 px: 1,7; ≤ 72 px: 1,3; acima: 1).
- [x] `prefers-reduced-motion`: primeiro quadro, sem animação.
- [x] Conferido sobre `papel`, `folha`, menu escuro e `.ext-tema`, com captura no PR.

# 05: Camada de voo

**O que construir:** `ProvedorFalcao` em volta da área logada e do painel da extensão, com
`useFalcao().voar({ de, para, aoChegar })` (`de` e `para` são elementos ou pontos). Camada fixa acima do conteúdo e
abaixo de diálogos e da barra do roteiro, com `pointer-events: none`. Um voo por vez; cancelado ao trocar de página.
Ao chegar, paira ~0,9 s ao lado do alvo e some em 0,25 s.

**Bloqueado por:** 04.

**Status:** todo

- [ ] Direção automática pela posição do alvo; arco leve; duração pela distância (mínimo 0,6 s).
- [ ] Movimento reduzido: aparece parado no destino por 1,2 s, sem travessia.
- [ ] Alvo fora da tela ou ausente (menu recolhido): voa até o botão do menu ou não voa, sem erro.

# 06: Falcão na carga

**O que construir:** o falcão pairando (40 a 56 px) ao lado do texto de status onde hoje há "Executando…" ou blocos
`animate-pulse`: `AgenteDetalhe`, `ProcessoDetalhe`, `ProcessoEditor`, `Estudio` (montar o agente e executar teste),
`Alertas` (ação de tratamento), `PluginCriar` e `Extensao`. O botão segue desabilitado com o mesmo texto.

**Bloqueado por:** 04.

**Status:** todo

- [ ] Região de status com `aria-busy="true"` durante a carga e `aria-live="polite"`.
- [ ] Painel da extensão em tema escuro conferido no navegador.

# 07: Voos de retorno e estados vazios

**O que construir:** os voos da tabela "Momentos do corpo": execução concluída (sino ou Execuções), publicação (aba
Agentes ou Processos), revisão e pedido de plugin (Revisões ou sino), entrada pela roda (até a marca do menu) e etapa do
roteiro concluída. Falcão estático nos estados vazios de Alertas, Revisões, Execuções e Plugins.

**Bloqueado por:** 05.

**Status:** todo

- [ ] Só em sucesso; em erro ou bloqueio, nenhum falcão.
- [ ] O alvo ganha destaque curto (`pedra-fundo` por ~1,6 s): o retorno não depende só do movimento.
- [ ] No máximo um voo por ação; nada voa sem uma ação antes.

# 08: Docs, roteiro e versão 8.2.0

**O que construir:** DESIGN.md com seções do falcão (momentos, quando não usar), da marca nova e dos ícones; linha no
ARCHITECTURE.md sobre o gerador; o falcão num roteiro de demonstração; versão 8.2.0 na extensão, na API e no front.

**Bloqueado por:** 02, 03, 06, 07.

**Status:** todo

- [ ] `python scripts/verifica_versao.py` e `python scripts/verifica_extensao.py` verdes.
- [ ] `pytest` e `npm run build` verdes.
- [ ] Capturas da marca nova, do menu com ícones e do falcão parado e em voo no PR.
