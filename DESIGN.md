# StoneFalcon — Design

A linguagem visual do StoneFalcon (v8): cores, tipografia, componentes, padrões de tela e a roda seletora. A fonte do código é `frontend/src/styles/global.css` e `frontend/tailwind.config.js`; se este documento e o código divergirem, o código vale e este arquivo deve ser corrigido. Contexto: [ARCHITECTURE.md](ARCHITECTURE.md), [REQUIREMENTS.md](REQUIREMENTS.md), [AGENTS.md](AGENTS.md).

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
| Marca | `Marca` | Identidade no topo da entrada e no menu lateral. |

Foco visível global: `:focus-visible` desenha um contorno de 2 px na cor `pedra`. Não remova; ao criar um componente com foco próprio, mantenha pelo menos esse contraste.

## 5. Padrões de tela

- **Entrada** (`pages/Entrar.tsx`): marca, aviso opcional, a roda (a partir de `md`) ou os cartões (abaixo de `md`), e a nota “Login simulado de demonstração… Pessoas e dados são fictícios.”
- **Área logada** (`App.tsx`): menu lateral escuro (`tinta`) à esquerda com as abas permitidas e o aviso de protótipo; cabeçalho fixo com selo de modo (simulado ou real), sino de alertas e o menu da pessoa; conteúdo em coluna de até 1400 px.
- **Páginas de lista e detalhe:** título, ação principal (`botao-pedra`) à direita, conteúdo em `.caixa`.
- **Canvas** (React Flow): arestas em `tinta-3`; nó novo e aresta recém-ligada destacados em `pedra`.
- **Barra do roteiro:** fixa na base enquanto há roteiro ativo; o conteúdo ganha folga inferior.
- **Estados vazios, de erro e de carga:** frase curta em português dizendo o que houve e o que fazer; erro em `text-erro` ou `role="alert"`; carga com `aria-busy`.
- **Tela estreita:** o que é desenho radial ou canvas ganha alternativa em cartões ou lista.

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
- Navegação por teclado: Tab entra na roda (uma fatia só na ordem do Tab), setas movem entre fatias, Home e End vão às pontas, Enter ou Espaço entram. A instrução não é anunciada no texto porque só vale depois de focar uma fatia.
- Clicar numa fatia entra como a persona e abre o Início; o botão do miolo inicia o roteiro guiado.
- O miolo tem `aria-live="polite"`, então leitores de tela ouvem a persona ativa.
- Geometria em unidades de um `viewBox` de 720: raio externo 320, interno 190, folga de 1,2° entre fatias.

## 7. Acessibilidade e movimento

Regras que todo ticket de tela deve seguir:

1. **Teclado.** Tudo que se faz com o mouse se faz só com o teclado; ordem de Tab previsível; foco sempre visível (nunca `outline: none` sem substituto).
2. **Nome acessível.** Todo controle sem texto visível (ícone, foto, fatia) tem `aria-label` ou `alt`.
3. **Cor não basta.** Estado e categoria também em texto ou ícone; contraste de texto adequado sobre `papel` e `folha`.
4. **Avisos.** Erro de formulário e de servidor com `role="alert"`; carga com `aria-busy`; região que muda sozinha com `aria-live`.
5. **Movimento com propósito.** Animação só para dar retorno ou orientar (ampliar a fatia, entrada de nó novo); curta (≈ 0,2 s para retorno) e sem efeito decorativo.
6. **Reduzir movimento.** Toda animação ou transição nova tem tratamento em `@media (prefers-reduced-motion: reduce)` (sem animação, estado final direto). Já cobertos: roda, Mapa de IA e `animate-pulse`.
7. **Imagens que falham.** Foto de persona nunca deixa buraco: iniciais na cor da persona.
8. **Idioma.** `lang="pt-BR"`; texto em português do Brasil, linguagem simples, sem jargão.
9. **Tela estreita.** Sem rolagem horizontal; alternativa para desenhos radiais e canvas.
10. **Verificação.** O front não tem testes automatizados: cumpra estas regras com `npm run build` verde e conferência no navegador (repouso, ativo e foco para telas com estados), com captura de tela no PR.
