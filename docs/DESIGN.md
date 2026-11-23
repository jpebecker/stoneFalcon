# StoneFalcon — Design

A linguagem visual do StoneFalcon (v8.2): cores, tipografia, componentes, padrões de tela, a roda seletora, o falcão e os ícones de linha. A fonte do código é `frontend/src/styles/global.css` e `frontend/tailwind.config.js`; se este documento e o código divergirem, o código vale e este arquivo deve ser corrigido. Contexto: [ARCHITECTURE.md](ARCHITECTURE.md), [REQUIREMENTS.md](REQUIREMENTS.md), [AGENTS.md](AGENTS.md).

> Protótipo acadêmico (UFSC) para o desafio StoneLab. Não é um produto da Stone: nenhum logotipo ou marca oficial.

## 1. Princípios (Apple HIG)

| Princípio | Diretriz | Como aparece |
|---|---|---|
| Simplicidade | `design-principles.md › Simplicity`: “Include just what's necessary.” | Em repouso, a roda mostra só as fotos; o nome não se repete na fatia, porque o miolo já o mostra. |
| Revelação progressiva | `layout.md › Visual hierarchy`: “Use progressive disclosure to make layouts cleaner and easier to interact with.” | Detalhes da persona só com mouse ou foco, e em menor quantidade. |
| Movimento com propósito | `motion.md`: “Add motion purposefully… Aim for brevity and precision in feedback animations.” | A fatia ativa se amplia; o escurecimento só existe nas vizinhas de uma fatia ativa; movimento reduzido é respeitado. |
| Acessibilidade | `accessibility.md`: “Let people use the keyboard alone to navigate and interact with your app.” / “Convey information with more than color alone.” | Teclado sempre funciona; nome no rótulo acessível; iniciais quando a foto falha; selos com texto, não só cor. |

## 2. Cores

Os valores são variáveis CSS em RGB (`:root` em `global.css`) e entram no Tailwind como `rgb(var(--x) / <alpha>)`. Use sempre a classe do Tailwind (`bg-pedra`, `text-tinta-2`), nunca o hexadecimal.

| Token | Valor | Papel |
|---|---|---|
| `tinta` | `16 32 26` (#10201A) | Texto principal, menu lateral, botão padrão. |
| `tinta-2` | `70 86 79` | Texto secundário. |
| `tinta-3` | `118 132 125` | Texto de apoio, rótulos, notas. |
| `papel` | `246 245 241` | Fundo da página (off-white quente). |
| `folha` | `255 255 255` | Superfície de caixas, campos e miolo da roda. |
| `linha` | `228 228 220` | Bordas e divisores. |
| `pedra` / `pedra-forte` / `pedra-fundo` | `18 140 94` / `11 99 66` / `226 243 235` | Verde de pedra preciosa: ação principal, confiança, foco. |
| `falcao` / `falcao-fundo` | `214 51 132` / `251 231 242` | Rosa do PinkFalcon: só destaque pontual. |
| `alerta` / `alerta-fundo` | `154 91 0` / `253 241 216` | Atenção; selo “simulado” e “Modo simulado”. |
| `erro` / `erro-fundo` | `179 38 30` / `251 233 231` | Erro e bloqueio. |
| `info` / `info-fundo` | `39 94 196` / `229 237 252` | Informação neutra; selo de nível de acesso. |
| `--serie-1` a `--serie-6` | `#2a78d6`, `#eb6834`, `#1fb37a`, `#e0428f`, `#6b5bd0`, `#8a8f98` | Séries de gráfico (1 e 2 validadas para daltonismo; 3 a 6 distinguem provedores). |

**Claro e escuro.** A plataforma é só clara (`color-scheme: light`). O **painel da extensão** usa a classe `.ext-tema`, que redefine as mesmas variáveis num tema escuro; por isso `caixa`, `campo`, `selo` e botões acompanham sem código extra. Componente novo deve usar apenas tokens, para funcionar nos dois temas.

**Cor nunca sozinha.** Estado (erro, alerta, simulado, acesso) sempre vem com texto ou ícone além da cor.

## 3. Tipografia

| Família | Classe | Uso |
|---|---|---|
| Bricolage (variável, 200–800) | `font-titulo` | Títulos (`h1`–`h3` já aplicam), nome da persona, números de destaque. |
| Instrument (variável, 400–700) | `font-texto` | Texto corrido e interface (padrão do `body`). |

As fontes são servidas pela própria plataforma (`frontend/public/fontes`, com licenças) e caem em `Segoe UI`, `system-ui`. Texto base: 15 px, entrelinha 1,5. Rótulos de campo usam `.rotulo` (12 px, caixa alta, `tinta-3`).

## 4. Componentes recorrentes

| Componente | Classe | Quando usar |
|---|---|---|
| Caixa | `.caixa` | Superfície de conteúdo: fundo `folha`, borda `linha`, raio 14 px (`rounded-caixa`) e sombra suave. Cartões, painéis, menus. |
| Botão padrão | `.botao` | Ação comum (fundo `tinta`). |
| Botão de ação principal | `.botao-pedra` | A ação que avança a tarefa: Executar, Publicar, Iniciar roteiro. Um por região. |
| Botão claro | `.botao-claro` | Ação secundária ou neutra (Entrar nos cartões, Cancelar). |
| Campo | `.campo` | Entrada de texto; foco com borda `pedra`. |
| Rótulo | `.rotulo` | Título de campo ou de seção pequena. |
| Selo | `.selo` + `bg-*-fundo text-*` | Estado curto: nível de acesso (`info`), simulado (`alerta`), papel (`papel`), resultado. Sempre com texto. |
| Selo “simulado” | `SeloSimulado` | Em todo lugar onde aparece um modelo ou sistema que não roda de verdade. |
| Avatar | `Avatar` | Foto da persona; sem foto ou com erro, iniciais na cor da persona. |
| Marca | `Marca` | Identidade no topo da entrada, no menu lateral e no painel da extensão: o **rosto do falcão** (ver §8). Sobre quadrado escuro arredondado; com a prop `claro`, sobre fundo translúcido no menu escuro. |
| Ícone | `Icone` | Linha de 24 px com traço 1,8 e pontas redondas, sempre ao lado de texto (ver §9). |
| Falcão (corpo) | `Falcao`, `Carregando`, `Vazio` | Pairando na carga, voando no retorno, parado nos estados vazios (ver §8). |

Foco visível global: `:focus-visible` desenha um contorno de 2 px na cor `pedra`. Não remova; ao criar um componente com foco próprio, mantenha pelo menos esse contraste.

## 5. Padrões de tela

- **Entrada** (`pages/Entrar.tsx`): marca, aviso opcional, a roda (a partir de `md`) ou os cartões (abaixo de `md`), e a nota “Login simulado de demonstração… Pessoas e dados são fictícios.”
- **Área logada** (`App.tsx`): menu lateral escuro (`tinta`) à esquerda com o poleiro do falcão ao lado da marca, as abas permitidas e o aviso de protótipo; cabeçalho fixo com selo de modo (simulado ou real), sino de alertas e o menu da pessoa; conteúdo em coluna de até 1400 px.
- **Menu lateral em grupos** (`components/MenuLateral.tsx`): Início e quatro grupos sanfonados por finalidade (Construir: Estúdio, Agentes, Processos, Plugins, Ferramentas; Acompanhar: Execuções, Saúde, Revisões; Gestão e valor: Painel executivo, Finanças, Mapa de IA, Auditoria; Apresentação: Roteiros, Perguntas da Ferramenta). Só apresentação: quem vê cada aba vem do back. O cabeçalho do grupo é um botão com `aria-expanded` e `aria-controls` (Enter e Espaço alternam); um grupo aberto por vez; o grupo da página atual abre a cada navegação; grupo sem aba permitida não aparece e grupo com uma aba é um link simples. O grupo aberto é lembrado por navegador (conveniência, com `try/catch`). O menu rola por dentro se a janela for baixa (nenhuma aba fica inalcançável). Uma aba dentro de um grupo recolhido leva `data-alvo-recuo`, e o voo de retorno pousa no cabeçalho do grupo.
- **Páginas de lista e detalhe:** título, ação principal (`botao-pedra`) à direita, conteúdo em `.caixa`.
- **Canvas** (React Flow): arestas em `tinta-3`; nó novo e aresta recém-ligada destacados em `pedra`.
- **Barra do roteiro:** fixa na base enquanto há roteiro ativo; o conteúdo ganha folga inferior.
- **Estados vazios, de erro e de carga:** frase curta em português dizendo o que houve e o que fazer; erro em `text-erro` ou `role="alert"`; carga com `aria-busy` e o falcão pairando ao lado do texto (`Carregando`); lista vazia com o falcão parado (`Vazio`, que aceita uma `dica` para o balão sugerir o próximo passo); erro e bloqueio nunca levam o falcão.
- **Tela estreita:** o que é desenho radial ou canvas ganha alternativa em cartões ou lista.
- **Texto dinâmico nunca estoura o cartão (8.3.1).** JSON, motivos, entradas e nomes vindos de dados quebram a linha ou rolam **dentro da própria caixa**; um título ao lado de selos ou de metadados mantém uma largura mínima e os selos descem para baixo dele, em vez de espremê-lo. Nenhuma tela rola para o lado em 1024 px ou mais.

  | Faça | Não faça |
  |---|---|
  | `<pre className="max-h-64 overflow-auto whitespace-pre-wrap [overflow-wrap:anywhere]">` para JSON e texto preformatado | `<pre>` sem quebra nem rolagem: um valor longo alarga a página inteira |
  | Linha com título e selos: `flex flex-wrap`, título com `min-w-[…rem] flex-1`, selos num `flex flex-wrap` | Selos com `shrink-0` ao lado de um título sem largura mínima: o título vira uma palavra por linha |
  | `[overflow-wrap:anywhere]` em linha que imprime um valor sem espaços (ex.: a “entrada” de uma execução) | Contar com os espaços do texto para quebrar |

## 6. A roda seletora de personas

Componente: `frontend/src/components/RodaPersonas.tsx`; estilos `.roda-*` em `global.css`. Um anel dividido em fatias iguais, uma por pessoa, cada uma com a foto; o miolo (círculo branco no centro) conta quem é a pessoa ativa. Aparece só a partir de `md`; abaixo disso a entrada usa cartões.

| Estado | Como se chega | Fatias | Miolo |
|---|---|---|---|
| **Repouso** | Nada sob o mouse e nenhum foco na roda | Só as seis fotos, limpas: sem nome, sem texto sobreposto, sem camada escura. Se a foto falha, as iniciais na cor da persona. | “Quem é você hoje?” e “Passe o mouse sobre uma foto para ver quem é. Clique para entrar.” Sem menção a teclas. |
| **Ativa** | Mouse sobre a fatia ou foco do teclado nela | A fatia se amplia (escala 1,08, leve brilho); as vizinhas escurecem de leve (camada preta a 18%) e encolhem um pouco (0,97). | Nome, cargo · área, descrição em até 2 linhas, selo “acesso *nível*” e, se a persona tem roteiro, o botão “Iniciar roteiro guiado”. Sem selos de papel (eles ficam nos cartões da tela estreita). |
| **Foco do teclado** | Tab até a roda, depois setas, Home e End | Contorno `pedra` grosso na borda da fatia focada, além do estado ativo. | O mesmo da ativa. |
| **Saída** | Mouse sai da roda e não há foco | Volta ao repouso depois de uma espera curta (140 ms), para o miolo não piscar ao atravessar a folga entre fatias ou ir da fatia ao botão. | Volta ao texto de repouso. |

Regras:

- Cada fatia é um botão (`role="button"`) com rótulo acessível “Nome, cargo, área. Entrar como Nome”. O nome sai do desenho, mas **não** do rótulo.
- Navegação por teclado: Tab entra na roda (uma fatia só na ordem do Tab), setas movem entre fatias, Home e End vão às pontas, Enter ou Espaço entram. A instrução não aparece no texto visível porque só vale depois de focar uma fatia; quem usa leitor de tela a ouve no rótulo acessível do grupo da roda ao entrar nela.
- Clicar numa fatia entra como a persona e abre o Início; o botão do miolo inicia o roteiro guiado.
- O miolo tem `aria-live="polite"`, então leitores de tela ouvem a persona ativa.
- Geometria em unidades de um `viewBox` de 720: raio externo 320, interno 190, folga de 1,2° entre fatias.

## 7. Acessibilidade e movimento

Regras que todo ticket de tela deve seguir:

1. **Teclado.** Tudo que se faz com o mouse se faz só com o teclado; ordem de Tab previsível; foco sempre visível (nunca `outline: none` sem substituto).
2. **Nome acessível.** Todo controle sem texto visível (ícone, foto, fatia) tem `aria-label` ou `alt`.
3. **Cor não basta.** Estado e categoria também em texto ou ícone; contraste de texto adequado sobre `papel` e `folha`.
4. **Avisos.** Erro de formulário e de servidor com `role="alert"`; carga com `aria-busy`; região que muda sozinha com `aria-live`.
5. **Movimento com propósito.** Animação só para dar retorno ou orientar (ampliar a fatia, entrada de nó novo); curta (≈ 0,2 s para retorno) e sem efeito decorativo. A exceção é o falcão: desde a 8.3 ele também tem os papéis de presença, guia e ambiente, cada um com o seu limite (teto de frequência, nunca enquanto a pessoa digita, com um diálogo aberto ou durante um voo de ação), descritos na regra de movimento do §8.
6. **Reduzir movimento.** Toda animação ou transição nova tem tratamento em `@media (prefers-reduced-motion: reduce)` (sem animação, estado final direto). Já cobertos: roda, Mapa de IA, `animate-pulse` e o falcão (batida de asa, travessia, destaque, saída da camada de voo, entrada do balão e o poleiro, que fica parado). Com movimento reduzido o falcão companheiro não faz voo de chegada, não tem comportamento ambiente e o balão aparece sem animação (§8, regra de movimento).
7. **Imagens que falham.** Foto de persona nunca deixa buraco: iniciais na cor da persona.
8. **Idioma.** `lang="pt-BR"`; texto em português do Brasil, linguagem simples, sem jargão.
9. **Tela estreita.** Sem rolagem horizontal; alternativa para desenhos radiais e canvas.
10. **Verificação.** O front não tem testes automatizados: cumpra estas regras com `npm run build` verde e conferência no navegador (repouso, ativo e foco para telas com estados), com captura de tela no PR.

## 8. O falcão

O animal do nome Stone**Falcon** (grupo PinkFalcon) tem duas formas. O **rosto** é o ícone do sistema e fica sempre visível. O **corpo** é animado (pairando e voo lateral). Desde a 8.3 ele é um **companheiro**: fica no **poleiro** ao lado da marca, fala pelo **balão** e voa para dar retorno e para guiar (veja a regra de movimento). Os dois são desenhados por código em `scripts/gera_falcao.mjs`, em traço de pincel que engrossa e afina, e usam as cores do sistema: traço `pedra`, penas `falcao`, rastro `tinta-3`; sobre o menu escuro (`claro`), tons mais claros. Os arquivos gerados (`frontend/src/components/falcao/quadros.ts`, `frontend/public/icone.svg`, `extensao/icones/rosto.*` e os PNGs) entram no Git e **não se editam à mão**: mude o gerador e rode `node scripts/gera_falcao.mjs`.

**Rosto (marca).** Arco verde da cabeça, bico em gancho claro, penas rosa do pescoço; é legível em 16 px. Aparece no menu, na entrada, no favicon, no painel e no botão flutuante da extensão. Sobre o quadrado escuro usa `#1FB37A`, `#E0428F` e `#E8F3EE` (os valores da `Marca`).

**Corpo.** `<Falcao estado="parado" | "voo" | "estatico" direcao tamanho />`: quadro de 128 × 112, 6 quadros em 1,1 s parado e 8 quadros em 0,56 s no voo (com rastro). O traço engrossa em tamanhos pequenos (×1,7 até 48 px, ×1,3 até 72 px). É sempre `aria-hidden`: o falcão nunca é a única informação.

**Regra de movimento (amplia a regra 5 do §7 na 8.3).** O falcão é parte da interface, não só um efeito de retorno. Ele pode estar em quatro papéis, cada um com o seu limite:

1. **Poleiro (presença).** Parado ao lado da marca, no menu, em toda tela logada (quadro estático, sem animação). Enquanto um voo acontece o poleiro fica vazio e, quando o voo termina, o falcão volta a ele. Não é decoração que se mexe: não anima sozinho.
2. **Retorno (feedback de uma ação).** Como sempre: **só depois de uma ação da pessoa** e **no máximo um voo por ação**.
3. **Guia (roteiros guiados).** Em cada etapa de um roteiro ele voa até o elemento que a pessoa deve usar e fala a ação no balão (ticket 09). É a pessoa que está conduzindo a demonstração; a cada etapa, no máximo um voo.
4. **Ambiente (rotinas do falcão).** Comportamentos que acontecem sozinhos, cada um ligado a algo real do estado da pessoa (alerta novo, dica de página, primeira execução do dia, estado vazio; ticket 10). Limites que valem para todos juntos:
   - **Teto de frequência:** no máximo um comportamento ambiente a cada poucos minutos (um só agendador decide; dois nunca na mesma janela).
   - **Nunca** enquanto a pessoa digita, com um diálogo aberto, durante um voo de ação ou durante um roteiro guiado (o roteiro é do papel de guia).
   - **Nunca** move o foco, bloqueia um clique nem cobre o botão da ação da tela.
   - Desligado com movimento reduzido e com o falcão silenciado.

**Rotinas ambiente** (`Ambiente`, `agendador.ts`). Um **agendador único** decide por todas, com o teto de 3 minutos (`CONFIG_AMBIENTE.capMs`, ajustável) e as regras acima; uma rotina que não pode rodar agora espera a sua vez (a de maior prioridade vai primeiro) e desiste se envelhecer. São cinco, cada uma ligada a algo real:

| Rotina | Gatilho real | O que faz |
|---|---|---|
| Alerta novo | O número de **não lidos do sino sobe** (a primeira leitura não conta) | Sai do poleiro, voa até o sino e diz uma linha ("Chegou um alerta novo."). |
| Dica | Um minuto sem mexer na tela | Uma dica curta da página atual, uma vez por página (lista em `DICAS`, em português simples). |
| Espreguiçar | 40 s sem mexer, e só às vezes | O poleiro paira no lugar e olha para o outro lado por ~2,5 s. Sem voo e sem fala. |
| Primeira do dia | A primeira execução bem-sucedida **da pessoa, nesta sessão** (não é histórico, teste nem rotina agendada) | Uma comemoração curta no balão; uma vez por pessoa por dia. |
| Estado vazio | Uma lista vazia com `dica` (`Vazio`) | O balão sugere o próximo passo. |

Para rever cada rotina sem esperar o relógio, `window.__ambiente.capMs` ajusta o teto pelo console (em desenvolvimento). Quem mantém a página local de teste do falcão (`frontend/falcao-teste.html`, fora do Git) tem nela o poleiro, o balão e um botão por rotina: os de "forçar" ignoram o agendador e "Pedir as três" mostra o teto e a prioridade.

**Balão de fala** (`Balao`, `falar(texto)` em `useFalcao()`): uma frase curta, em português simples, junto de onde o falcão está (o poleiro, ou o elemento para onde ele voou). Fica numa região `role="status"` `aria-live="polite"` (anunciada sem tirar o foco), some sozinho (5 a 10 s, conforme o tamanho; parado enquanto o ponteiro ou o foco estiverem nele), pode ser dispensado (botão × ou Esc) e **nunca cobre o botão da ação da tela** (`data-alvo="acao-…"`): se o lugar de costume cobriria, usa outro lado. Trocar de página o recolhe. Só uma fala por vez.

**Saudação.** Ao entrar pela roda, o falcão voa até o poleiro e cumprimenta pelo primeiro nome com uma frase sobre o dia: quantos alertas a pessoa tem abertos e quantos ainda não leu. Trocar de perfil pelo menu não faz festa.

**Silenciar o falcão.** O interruptor está no menu da pessoa (canto de cima à direita). Ligado, não há balão nem comportamento ambiente; o poleiro e os voos que respondem a uma ação continuam. É por navegador e só uma conveniência: se o armazenamento do navegador falhar, o falcão segue falando e nada quebra.

**Movimento reduzido (§7.6).** O poleiro continua parado; não há voo de chegada nem comportamento ambiente; o balão aparece sem animação; os voos de retorno viram aparições paradas no destino por 1,2 s, como antes.

| Momento | Onde | O que faz |
|---|---|---|
| Executar agente, processo ou teste | Agente, Processo, Editor de processo, Estúdio, Alertas | Paira ao lado do status (`Carregando`); ao terminar bem, voa até o sino (alerta) ou até a aba Execuções, que ganha destaque. |
| Montar o agente a partir da descrição | Estúdio | Paira com “Montando o seu agente…”. |
| Publicar agente ou processo | Estúdio, Agente, Editor de processo | Voa até a aba Agentes ou Processos. |
| Enviar para revisão / pedir plugin | Estúdio, Editor de processo, Criar plugin | Paira enquanto gera; voa até Revisões ou, se a pessoa não tem a aba, até o sino. |
| Analisar o trecho e executar | Painel da extensão | Paira no lugar dos blocos pulsantes. |
| Entrar pela roda | Entrada → Início | Voo de boas-vindas até o poleiro, onde o falcão pousa e fala a saudação no balão (sem voo e sem animação com movimento reduzido). |
| Estar no menu | Toda tela logada | Parado no poleiro, ao lado da marca; vazio enquanto voa. |
| Etapa do roteiro concluída | Barra do roteiro | Voo curto da etapa feita até a próxima (única exceção em que o falcão voa por cima da barra). |
| Lista vazia | Alertas, Revisões, Execuções, Plugins | Parado, sem animação, ao lado da frase (`Vazio`). |

**Quando não usar:** erro, falha, bloqueio de guardrail, listas cheias, e qualquer voo fora dos quatro papéis acima. Não use o falcão como decoração nem para preencher espaço.

**Camada de voo** (`ProvedorFalcao`, `useFalcao()`): `voar({ de, para, alternativo, aoChegar })` e `retornar({ de, para: "aba-execucoes", alternativo: "sino" })`. Os alvos são elementos com `data-alvo` (`aba-<nome>`, `grupo-<nome>`, `sino`, `marca`, `poleiro`, `acao-<nome>`); `sobre: true` pousa em cima do alvo (o poleiro) em vez de ao lado. Uma aba dentro de um grupo recolhido do menu leva `data-alvo-recuo` e o falcão pousa no cabeçalho do grupo. A camada é fixa, fica acima do conteúdo e do menu e abaixo da barra do roteiro, sem capturar cliques; um voo por vez, cancelado ao trocar de página. O falcão paira ~0,9 s ao lado do alvo e some em 0,25 s; o alvo ganha o destaque `pedra-fundo` por ~1,6 s, porque o retorno não pode depender só do movimento. Alvo ausente ou fora da tela: voa até o alternativo ou não voa, sem erro.

## 9. Ícones da interface

`Icone` (`frontend/src/components/Icone.tsx`): linhas no mesmo traço do sino do cabeçalho (grade 24, traço 1,8, pontas redondas, `currentColor`), sem biblioteca. 18 px no menu, 16 px em botões e selos.

- **Entram em:** as 15 abas do menu, o botão de ação principal (`botao-pedra`: Executar, Publicar, Enviar para revisão), os selos de resultado (concluído, falhou, simulado/atenção) e o menu da pessoa (Trocar de perfil, Sair).
- **Não entram em:** títulos, tabelas, links de texto, cartões nem botões claros.
- **Sempre ao lado de texto visível, nunca no lugar dele.** O ícone é `aria-hidden`; nenhum controle vira só ícone.
