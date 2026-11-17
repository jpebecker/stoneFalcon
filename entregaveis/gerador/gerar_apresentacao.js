// F9: gera entregaveis/apresentacao.pptx a partir de resumo.json (aba "Resumo para slides" do Excel).
// Uso:  node gerar_apresentacao.js   (antes: recalcular.py e exportar_resumo.py)
// Todo número do deck passa por N(), que registra a célula de origem em entregaveis/checagem-numeros.md.
const fs = require("fs");
const path = require("path");
const pptxgen = require("pptxgenjs");

const AQUI = __dirname;
const SAIDA = path.join(AQUI, "..", "apresentacao.pptx");
const TELAS = path.join(AQUI, "..", "telas");
const R = JSON.parse(fs.readFileSync(path.join(AQUI, "resumo.json"), "utf8"));
const SKILL_THEME = process.env.APPLY_THEME_JS;

// ---------- identidade (StoneFalcon: verde-pedra + rosa PinkFalcon; sem marca da Stone) ----------
const HEX = { tinta: "10201A", pedra: "128C5E", pedraForte: "0B6342", pedraFundo: "E2F3EB", falcao: "D63384",
  falcaoFundo: "FBE7F2", cinza: "46564F", cinzaClaro: "76847D", linha: "E4E4DC", branco: "FFFFFF", erro: "B3261E", azul: "2A78D6" };
const THEME = { name: "StoneFalcon", headFontFace: "Calibri", bodyFontFace: "Calibri",
  colors: { dk1: HEX.tinta, lt1: HEX.branco, dk2: HEX.pedraForte, lt2: HEX.pedraFundo, accent1: HEX.pedra, accent2: HEX.falcao,
    accent3: HEX.cinza, accent4: HEX.azul, accent5: HEX.erro, accent6: "9A5B00", hlink: HEX.pedra, folHlink: HEX.pedraForte } };

// ---------- números: formatação pt-BR e rastreio ----------
const usos = [];
let slideAtual = 0;
const br = (v, d = 0) => v.toLocaleString("pt-BR", { minimumFractionDigits: d, maximumFractionDigits: d });
const F = {
  mi: (v) => (v < 0 ? "−" : "") + "R$ " + br(Math.abs(v) / 1e6, 2) + " mi",
  mil: (v) => "R$ " + br(v / 1e3, v < 1e5 ? 1 : 0) + " mil",
  brl4: (v) => "R$ " + br(v, 3),
  brl2: (v) => "R$ " + br(v, 2),
  pct: (v) => br(v * 100, 0) + "%",
  pct1: (v) => br(v * 100, 1) + "%",
  mes: (v) => (typeof v === "number" ? "mês " + v : "não se paga em 36 meses"),
  num: (v) => br(v, 0),
  num1: (v) => br(v, 1),
  x: (v) => br(v, 1) + "×",
};
function N(chave, fmt) {
  if (!(chave in R.numeros)) throw new Error("Número sem origem no Excel: " + chave);
  const v = R.numeros[chave];
  const txt = F[fmt](v);
  usos.push({ slide: slideAtual, chave, txt, ...R.origem[chave] });
  return txt;
}
function D(rotulo, txt, chaves) {   // número derivado de dois ou mais números do Resumo
  usos.push({ slide: slideAtual, chave: chaves.join(" + "), txt, rotulo, celula: "derivado de " + chaves.map((c) => R.origem[c].celula).join(", "), origem: "conta simples no slide" });
  return txt;
}

// ---------- apresentação ----------
const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE";   // 13,333 × 7,5 pol.
pres.theme = { headFontFace: THEME.headFontFace, bodyFontFace: THEME.bodyFontFace };
pres.title = "StoneFalcon: proposta ao board";
pres.author = "Equipe StoneFalcon (UFSC)";
pres.subject = "Desafio StoneLab: plataforma institucional de agentes de IA";
// Cores em hex (mesmas do tema): o deck sai certo mesmo sem aplicar o tema depois.
const C = { text1: HEX.tinta, text2: HEX.pedraForte, background1: HEX.branco, background2: HEX.pedraFundo, accent1: HEX.pedra,
  accent2: HEX.falcao, accent3: HEX.cinza, accent4: HEX.azul, accent5: HEX.erro };
const W = 13.333;

const RODAPE = "StoneFalcon · protótipo acadêmico (UFSC / StoneLab) · não é um produto da Stone";
pres.defineSlideMaster({
  title: "CONTEUDO",
  background: { color: HEX.branco },
  objects: [
    { text: { text: RODAPE, options: { x: 0.6, y: 7.0, w: 9, h: 0.3, fontSize: 10, color: C.accent3, margin: 0 } } },
    { placeholder: { options: { name: "titulo", type: "title", x: 0.6, y: 0.35, w: 12.1, h: 1.0, fontSize: 30, bold: true,
      color: C.text1, valign: "top", align: "left", margin: 0 }, text: "" } },
  ],
  slideNumber: { x: 12.2, y: 7.0, w: 0.5, h: 0.3, fontSize: 10, color: C.accent3, align: "right" },
});
pres.defineSlideMaster({
  title: "ESCURO",
  background: { color: HEX.tinta },
  objects: [
    { placeholder: { options: { name: "titulo", type: "title", x: 0.8, y: 0.6, w: 11.7, h: 1.6, fontSize: 34, bold: true,
      color: C.background1, valign: "top", align: "left", margin: 0 }, text: "" } },
  ],
  slideNumber: { x: 12.2, y: 7.0, w: 0.5, h: 0.3, fontSize: 10, color: C.background2, align: "right" },
});

function novo(master, secao, titulo) {
  slideAtual += 1;
  const s = pres.addSlide({ masterName: master, sectionTitle: secao });
  if (typeof titulo === "function") titulo = titulo();   // títulos com números: registra no slide certo
  if (titulo) s.addText(titulo, { placeholder: "titulo" });
  return s;
}
function txt(s, texto, o) { s.addText(texto, { isTextBox: true, margin: 0, fontSize: 15, color: C.text1, valign: "top", ...o }); }
function cartao(s, x, y, w, h, cor = C.background2, nome) {
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h, fill: { color: cor }, line: { color: cor }, rectRadius: 0.12, objectName: nome });
}
function circulo(s, x, y, d, rotulo, cor = C.accent1) {
  s.addShape(pres.shapes.OVAL, { x, y, w: d, h: d, fill: { color: cor }, line: { color: cor } });
  s.addText(rotulo, { isTextBox: true, x, y, w: d, h: d, align: "center", valign: "middle", fontSize: 16, bold: true, color: C.background1, margin: 0 });
}
function marca(s, x, y, t) {   // ícone do StoneFalcon (funil: as três camadas do roteador), desenhado em formas
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w: t, h: t, fill: { color: HEX.tinta }, line: { color: "2E4A3E", width: 1 }, rectRadius: t * 0.25 });
  const camada = (cx, cy, cw, ch, cor) => s.addShape(pres.shapes.TRAPEZOID, { x: x + cx * t, y: y + cy * t, w: cw * t, h: ch * t,
    fill: { color: cor }, line: { color: cor }, flipV: true });
  camada(0.175, 0.25, 0.65, 0.185, "1FB37A");
  camada(0.30, 0.51, 0.40, 0.157, "E8F3EE");
  camada(0.41, 0.74, 0.18, 0.135, "E0428F");
}
function imagem(s, arq, x, y, w, alt) {
  const h = w * 1119 / 2367;
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: x - 0.04, y: y - 0.04, w: w + 0.08, h: h + 0.08, fill: { color: HEX.linha }, line: { color: HEX.linha }, rectRadius: 0.06 });
  s.addImage({ path: path.join(TELAS, arq), x, y, w, h, altText: alt });
  return h;
}
const eixo = { catAxisLabelColor: HEX.cinza, valAxisLabelColor: HEX.cinza, catAxisLabelFontFace: "+mn-lt", valAxisLabelFontFace: "+mn-lt",
  catAxisLabelFontSize: 11, valAxisLabelFontSize: 11, valGridLine: { color: HEX.linha, size: 0.75 }, catGridLine: { style: "none" },
  legendFontFace: "+mn-lt", legendFontSize: 11, legendColor: HEX.cinza, titleFontFace: "+mn-lt", titleColor: HEX.tinta, titleFontSize: 13 };

// =========================================================================================
// 1. Capa
// =========================================================================================
pres.addSection({ title: "Abertura" });
{
  slideAtual += 1;
  const s = pres.addSlide({ masterName: "ESCURO", sectionTitle: "Abertura" });
  marca(s, 0.8, 0.8, 1.1);
  txt(s, "StoneFalcon", { x: 0.8, y: 2.35, w: 11, h: 1.1, fontSize: 60, bold: true, color: C.background1 });
  txt(s, "A fábrica governada de agentes de IA", { x: 0.8, y: 3.45, w: 11, h: 0.7, fontSize: 28, color: "1FB37A" });
  txt(s, "Proposta ao board · Desafio StoneLab · UFSC · novembro de 2026", { x: 0.8, y: 4.4, w: 11, h: 0.5, fontSize: 18, color: C.background2 });
  txt(s, [{ text: "Stone", options: { bold: true } }, { text: " (empresa patrocinadora) + " }, { text: "Falcon", options: { bold: true, color: "E0428F" } },
    { text: " (grupo PinkFalcon de empreendedorismo). Protótipo acadêmico: pessoas, áreas e dados são fictícios; não é um produto da Stone." }],
    { x: 0.8, y: 6.2, w: 11.5, h: 0.6, fontSize: 12, color: "A9B8B0" });
  s.addNotes("[0:30] Boa tarde. Somos o StoneFalcon: uma plataforma para qualquer colaborador da Stone criar agentes de IA, com governança, segurança e custo sob controle. O nome junta Stone, a patrocinadora, e Falcon, do nosso grupo PinkFalcon. Em 12 minutos: o problema, a solução funcionando, quanto custa, quando se paga e o que pedimos.");
}

// 2. Contexto
{
  const s = novo("CONTEUDO", "Abertura", "IA virou “jeito de ser” da Stone; o time de GenAI precisa servir a empresa inteira");
  const marcos = [["2023", "Nasce a área de Generative AI, com casos de uso em operações core, junto das áreas de negócio"],
    ["2025", "O sucesso dos casos internos leva a Stone a adotar “IA como jeito de ser” como pilar de crescimento"],
    ["Agora", "Reestruturar o time de GenAI para uma adoção descentralizada, com ownership nas áreas e uso consistente e seguro"]];
  s.addShape(pres.shapes.LINE, { x: 1.2, y: 2.35, w: 10.8, h: 0, line: { color: HEX.linha, width: 2 } });
  marcos.forEach(([ano, t], i) => {
    const x = 0.9 + i * 4.1;
    circulo(s, x, 1.95, 0.8, ano === "Agora" ? "→" : "✓", i === 2 ? C.accent2 : C.accent1);
    txt(s, ano, { x, y: 2.95, w: 3.6, h: 0.5, fontSize: 22, bold: true, color: i === 2 ? C.accent2 : C.text2 });
    txt(s, t, { x, y: 3.45, w: 3.6, h: 1.4, fontSize: 15, color: C.accent3 });
  });
  cartao(s, 0.6, 5.2, 12.1, 1.25, C.background2, "meta");
  txt(s, [{ text: "A meta da Stone: ", options: { bold: true, color: C.text2 } },
    { text: "qualquer colaborador, sem saber programar, cria agentes autônomos para a própria rotina (atendimento, operações, logística, RH), sem acionar um AI Engineer para cada nova demanda." }],
    { x: 0.95, y: 5.42, w: 11.4, h: 0.9, fontSize: 17, valign: "middle" });
  s.addNotes("[0:45] Em 2023 a Stone criou a área de GenAI. Em 2025, IA virou pilar: 'IA como jeito de ser'. Isso muda a escala: o time de GenAI não consegue fazer cada agente sob medida. A meta é que qualquer pessoa crie os próprios agentes, sem esperar um AI Engineer. Fonte: contexto do desafio, seção 1 e 2.1.");
}

// 3. A dor
pres.addSection({ title: "Problema" });
{
  const s = novo("CONTEUDO", "Problema", "Três forças puxam em direções opostas, e sem plataforma o resultado é shadow IT");
  const forcas = [
    ["1", "Operações e Negócio", "Querem automatizar processos com IA, com agilidade, sem fila de engenharia.", C.accent1],
    ["2", "Engenharia e Segurança", "Não podem liberar acessos sem governança e não têm headcount para um agente sob medida por time.", C.text2],
    ["3", "Sustentabilidade da escala", "A IA precisa escalar de forma sustentável no custo, na segurança e na robustez.", C.accent2]];
  forcas.forEach(([n, t, d, cor], i) => {
    const x = 0.6 + i * 4.1;
    cartao(s, x, 1.75, 3.8, 3.3, C.background2, "forca" + n);
    circulo(s, x + 0.35, 2.05, 0.7, n, cor);
    txt(s, t, { x: x + 0.35, y: 2.95, w: 3.2, h: 0.5, fontSize: 20, bold: true });
    txt(s, d, { x: x + 0.35, y: 3.5, w: 3.15, h: 1.4, fontSize: 15, color: C.accent3 });
  });
  txt(s, [{ text: "O risco de não decidir: ", options: { bold: true, color: C.accent2 } },
    { text: "cada time liga uma ferramenta low-code por conta própria, sem controle de acesso, sem auditoria e com dados sensíveis saindo da empresa." }],
    { x: 0.6, y: 5.45, w: 12.1, h: 0.9, fontSize: 17 });
  s.addNotes("[0:45] A dor tem três lados. Operações quer agilidade. Engenharia e Segurança não podem liberar acesso sem governança e não têm gente para fazer um agente por time. E a escala precisa fechar a conta, no custo e na segurança. Se ninguém resolver, o mercado resolve do pior jeito: shadow IT. Fonte: desafio, seção 2.1.");
}

// 4. Objetivo
{
  slideAtual += 1;
  const s = pres.addSlide({ masterName: "ESCURO", sectionTitle: "Problema" });
  s.addText("Objetivo: uma plataforma institucional no-code para criar, gerir e sustentar agentes de IA com segurança", { placeholder: "titulo" });
  const caps = [["Decidir", "com o contexto fornecido"], ["Usar ferramentas", "APIs e sistemas internos"], ["Executar", "em sequência ou em paralelo"],
    ["Raciocinar", "loop que escolhe o próximo passo"], ["Gerir", "custo, retorno e manutenção"]];
  caps.forEach(([t, d], i) => {
    const x = 0.8 + i * 2.38;
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y: 3.0, w: 2.18, h: 2.0, fill: { color: "1B3A2E" }, line: { color: "2E4A3E" }, rectRadius: 0.12 });
    txt(s, t, { x: x + 0.2, y: 3.2, w: 1.85, h: 0.8, fontSize: 19, bold: true, color: "1FB37A" });
    txt(s, d, { x: x + 0.2, y: 4.05, w: 1.85, h: 0.85, fontSize: 15, color: C.background2 });
  });
  txt(s, "Sem gerar débito técnico e sem sobrecarregar os times de IA: Engenharia e Segurança governam o catálogo, não cada agente.",
    { x: 0.8, y: 5.6, w: 11.7, h: 0.8, fontSize: 18, color: C.background1, italic: true });
  s.addNotes("[0:30] O objetivo, nas palavras do desafio: uma plataforma agêntica institucional, no-code, em que não técnicos criam agentes que decidem, usam ferramentas, executam fluxos em sequência e em paralelo, raciocinam e são geridos em custo e retorno. Nossa tese: a governança fica no catálogo, não em cada agente.");
}

// 5. Por que institucional
pres.addSection({ title: "Solução" });
{
  const s = novo("CONTEUDO", "Solução", "Por que construir uma plataforma institucional, e não liberar low-code genérico");
  const cab = (t, fill, cor) => ({ text: t, options: { bold: true, color: cor, fill: { color: fill }, fontSize: 15 } });
  const linhas = [
    ["Quem constrói", "Colaboradores isolados (shadow IT)", "Qualquer colaborador, na infraestrutura oficial; o Estúdio monta o agente a partir de uma descrição em português"],
    ["Governança", "Limitada ou inexistente", "Catálogo governado, ciclo de vida com versões, revisão em quatro olhos para risco alto e pausa de emergência"],
    ["Escala e integração", "Casos isolados, sem integração", "Conectores aos sistemas internos, rodando com as permissões de quem disparou o agente"],
    ["Segurança e compliance", "Risco de vazamento de dados", "Guardrails silenciosos: dados pessoais viram marcadores antes do modelo; trilha de auditoria encadeada"]];
  const rows = [[cab("Dimensão", HEX.tinta, HEX.branco), cab("Low-code genérico", HEX.cinza, HEX.branco), cab("StoneFalcon (o que o protótipo já faz)", HEX.pedra, HEX.branco)]];
  linhas.forEach(([d, g, f]) => rows.push([{ text: d, options: { bold: true } }, { text: g, options: { color: HEX.cinza } }, { text: f }]));
  s.addTable(rows, { x: 0.6, y: 1.65, w: 12.1, colW: [2.6, 3.2, 6.3], fontSize: 15, color: HEX.tinta, fontFace: "Calibri",
    border: { type: "solid", color: HEX.linha, pt: 1 }, rowH: [0.5, 0.95, 0.95, 0.95, 0.95], valign: "middle", margin: 0.1 });
  txt(s, "Tabela do desafio (seção 2.3), preenchida com o que a plataforma entrega. Custo comparado no slide 11.",
    { x: 0.6, y: 6.45, w: 12.1, h: 0.35, fontSize: 12, color: C.accent3 });
  s.addNotes("[0:50] Esta é a pergunta central do desafio: por que não liberar uma ferramenta de mercado? Em cada dimensão da tabela, o genérico deixa um buraco e o StoneFalcon já tem a resposta funcionando no protótipo: quem constrói é qualquer pessoa, mas dentro da infraestrutura oficial; a governança é central; a integração respeita a permissão de quem disparou; e os guardrails funcionam sem o criador configurar nada.");
}

// 6. A solução em um quadro
{
  const s = novo("CONTEUDO", "Solução", "A solução em um quadro: do pedido em português ao custo por agente, tudo na trilha");
  const etapas = [["Estúdio", "Descrição em português vira agente: passos, ferramentas, modelo, risco e custo; canvas editável e sandbox"],
    ["Catálogo governado", "Cada ferramenta tem classificação e áreas; ações sensíveis pedem confirmação humana"],
    ["Runtime com roteador", "Passos em sequência e em paralelo; loop pensar → agir → observar; cada passo vai ao modelo mais barato que resolve"],
    ["Saúde", "Nota por agente e por sistema, 5 regras de alerta ao dono, que fecham sozinhas"],
    ["Finanças", "Custo por execução, agente, área e modelo; orçamento com corte; ROI e calculadora"]];
  etapas.forEach(([t, d], i) => {
    const x = 0.6 + i * 2.47;
    cartao(s, x, 1.75, 2.22, 3.1, i === 2 ? C.text2 : C.background2, "etapa" + i);
    txt(s, t, { x: x + 0.18, y: 1.95, w: 1.9, h: 0.75, fontSize: 18, bold: true, color: i === 2 ? C.background1 : C.text2 });
    txt(s, d, { x: x + 0.18, y: 2.75, w: 1.9, h: 2.0, fontSize: 14, color: i === 2 ? C.background2 : C.accent3 });
    if (i < 4) s.addShape(pres.shapes.RIGHT_ARROW, { x: x + 2.24, y: 3.38, w: 0.2, h: 0.3, fill: { color: HEX.cinzaClaro }, line: { color: HEX.cinzaClaro } });
  });
  cartao(s, 0.6, 5.2, 12.1, 0.95, C.text1, "trilha");
  txt(s, [{ text: "Trilha de auditoria encadeada por hash  ", options: { bold: true, color: "1FB37A" } },
    { text: "criação → modificações → execuções → escaladas → deprecação, com dados pessoais só como marcadores", options: { color: C.background1 } }],
    { x: 0.9, y: 5.27, w: 11.6, h: 0.8, fontSize: 16, valign: "middle" });
  s.addNotes("[0:50] Em um quadro: a pessoa descreve o processo no Estúdio e recebe o agente montado. O agente só enxerga ferramentas do catálogo governado. O runtime executa os passos, em paralelo quando dá, e o roteador manda cada passo ao modelo mais barato que resolve: Haiku para o simples, Sonnet para análise. Saúde avisa o dono quando algo degrada, e Finanças mostra custo e retorno por agente. Tudo fica numa trilha de auditoria encadeada por hash. Modelos: Claude Haiku 5.5 e Sonnet 5.5; sem chave, roda em modo simulado.");
}

// 7. Demo
pres.addSection({ title: "Demonstração" });
{
  const s = novo("CONTEUDO", "Demonstração", "Demonstração: criar, confirmar a ação sensível e receber o alerta");
  imagem(s, "01-estudio-canvas.png", 0.6, 1.65, 7.6, "Estúdio do StoneFalcon com o canvas do agente de troca de maquininha");
  const passos = [["1", "Marina cria um agente", "Descreve a troca de maquininha; o Estúdio monta o fluxo, mostra risco médio e custo por execução; ela testa e publica"],
    ["2", "Rafael confirma a ação sensível", "A triagem de chargebacks roda dois passos juntos, sobe ao Sonnet na análise e para pedindo confirmação para reter repasses"],
    ["3", "O alerta chega ao dono", "Um sistema cai; a execução escala para humano com o motivo; o sino acende e a nota de saúde cai"]];
  passos.forEach(([n, t, d], i) => {
    const y = 1.65 + i * 1.32;
    circulo(s, 8.6, y, 0.55, n, i === 1 ? C.accent2 : C.accent1);
    txt(s, t, { x: 9.3, y: y - 0.02, w: 3.45, h: 0.4, fontSize: 17, bold: true });
    txt(s, d, { x: 9.3, y: y + 0.38, w: 3.45, h: 0.95, fontSize: 13, color: C.accent3 });
  });
  txt(s, "Ao vivo no protótipo (sem chave e sem internet), com vídeo de ~2 min como reserva. Roteiro completo no LEIA-ME.",
    { x: 0.6, y: 5.5, w: 7.6, h: 0.6, fontSize: 13, color: C.accent3 });
  s.addNotes("[2:00 – DEMO] Antes: Helena → Início → Reiniciar a demo. 1) Marina: Estúdio → exemplo 'Pedido de troca de maquininha' → Montar meu agente; mostrar canvas (dois passos na mesma coluna rodam juntos), risco e custo; testar com L1001; publicar. 2) Rafael: Agentes → Triagem de chargebacks → executar com L1003; abrir o passo da análise ('por que este modelo'); Confirmar ação. 3) Lucas: Ferramentas → Consultar cadastro do lojista → fora do ar; Marina executa Resposta a dúvidas → escala; sino acende; Saúde mostra a nota caindo; Lucas normaliza. Se algo falhar, trocar para o vídeo.");
}

// 8. Governança e segurança
{
  const s = novo("CONTEUDO", "Demonstração", "Governança e segurança vêm de fábrica: o criador não configura nada");
  const h = imagem(s, "02-execucao-acao-sensivel.png", 0.6, 1.65, 6.6, "Execução da triagem de chargebacks aguardando confirmação para reter repasses");
  txt(s, "A ação restrita (reter repasses) espera a confirmação de quem disparou; os dados consultados já chegam mascarados.",
    { x: 0.6, y: 1.65 + h + 0.2, w: 6.6, h: 0.7, fontSize: 13, color: C.accent3 });
  const itens = [["Guardrails silenciosos", "CPF, CNPJ, cartão, e-mail e segredos viram marcadores antes do modelo"],
    ["Permissão de quem disparou", "O agente nunca tem mais acesso que a pessoa que o executa"],
    ["Fluxo por classificação", "Dado confidencial não vaza para uma ferramenta de nível menor"],
    ["Revisão em quatro olhos", "Agente de risco alto só publica com a revisão da Segurança"],
    ["Pausa de emergência", "Para o agente e barra até as ações já pendentes"],
    ["Auditoria encadeada", "Cada evento guarda o hash do anterior: alterar quebra a cadeia"]];
  itens.forEach(([t, d], i) => {
    const x = 7.55 + (i % 2) * 2.62, y = 1.65 + Math.floor(i / 2) * 1.62;
    cartao(s, x, y, 2.47, 1.47, C.background2, "gov" + i);
    txt(s, t, { x: x + 0.15, y: y + 0.1, w: 2.2, h: 0.55, fontSize: 14, bold: true, color: C.text2, valign: "middle" });
    txt(s, d, { x: x + 0.15, y: y + 0.72, w: 2.2, h: 0.7, fontSize: 12, color: C.accent3 });
  });
  s.addNotes("[0:50] Segurança não é um passo que o criador precisa lembrar. Os dados pessoais viram marcadores antes de chegar ao modelo; o agente roda com a permissão de quem disparou; o dado confidencial só volta a um sistema que tenha a mesma classificação; risco alto passa pela Segurança; existe pausa de emergência; e a auditoria é encadeada por hash, então qualquer adulteração aparece. No print: a ação de reter repasses parou esperando o Rafael.");
}

// 9. Recorte financeiro 1: quanto custa
pres.addSection({ title: "Finanças" });
{
  const s = novo("CONTEUDO", "Finanças", () => "Quanto custa: o investimento é a equipe; os tokens são só " + N("tokens_min", "pct") + " a " + N("tokens_max", "pct") + " do custo");
  const stats = [
    [N("investimento_total", "mi"), "investimento: " + N("investimento_inicial", "mil") + " de plataforma + " + N("modulos", "mil") + " de conectores", C.text2],
    [N("custo_fixo", "mil"), "por mês de operação (hospedagem + time de sustentação)", C.text2],
    [N("tokens_min", "pct") + "–" + N("tokens_max", "pct"), "do custo total em 36 meses vai para tokens", C.accent1],
    ["−" + N("economia_roteador", "pct"), "de custo de tokens com o roteador, contra mandar tudo ao Sonnet", C.accent2]];
  stats.forEach(([v, d, cor], i) => {
    const x = 0.6 + i * 3.08;
    cartao(s, x, 1.6, 2.86, 1.85, C.background2, "stat" + i);
    txt(s, v, { x: x + 0.2, y: 1.72, w: 2.5, h: 0.75, fontSize: 30, bold: true, color: cor });
    txt(s, d, { x: x + 0.2, y: 2.5, w: 2.5, h: 0.9, fontSize: 13, color: C.accent3 });
  });
  const g2 = R.g2;
  const nomes = g2[0].slice(1);
  s.addChart(pres.charts.BAR, g2.slice(1).map((l) => ({ name: l[0], labels: nomes, values: l.slice(1).map((v) => v / 1e6) })), {
    x: 0.6, y: 3.7, w: 7.4, h: 3.15, barDir: "col", barGrouping: "stacked", chartColors: [HEX.pedraForte, HEX.cinzaClaro, HEX.falcao],
    showTitle: true, title: "Custo total em 36 meses por cenário (R$ mi)", showLegend: true, legendPos: "r",
    valAxisLabelFormatCode: "0.0", valAxisMinVal: 0, ...eixo });
  txt(s, [{ text: "Custo por execução: ", options: { bold: true } }, { text: N("cpe_modelado", "brl4") + " modelado nos agentes da demo; a análise usa " + N("cpe_premissa", "brl4") + " (conservador).\n\n" },
    { text: "Leitura: ", options: { bold: true, color: C.accent2 } }, { text: "o preço do modelo quase não mexe no resultado. Quem decide é a adoção e o valor de cada tarefa." }],
    { x: 8.4, y: 3.95, w: 4.3, h: 2.8, fontSize: 15 });
  s.addNotes("[0:50] Quanto custa. O grosso é o investimento: " + N("investimento_inicial", "mil") + " de desenvolvimento e implantação, com 15% de contingência, mais " + N("modulos", "mil") + " em quatro conectores. A operação custa " + N("custo_fixo", "mil") + " por mês. Os tokens são só " + N("tokens_min", "pct") + " a " + N("tokens_max", "pct") + " do custo total, e o roteador corta " + N("economia_roteador", "pct") + " do custo de tokens. Fonte: abas Investimento, Operação e Tokens da planilha. Se perguntarem do documento de custos: os R$ 8,5 mil/mês de tokens reaparecem convertendo pelo euro; com o dólar dá R$ 7,7 mil (aba Tokens).");
}

// 10. Recorte financeiro 2: quando se paga
{
  const s = novo("CONTEUDO", "Finanças", () => "Quando se paga: no cenário base, no " + N("payback_base", "mes") + ", com VPL de " + N("vpl_base", "mi"));
  const g1 = R.g1;
  const meses = g1.slice(1).map((l) => String(l[0]));
  const series = g1[0].slice(1).map((nome, j) => ({ name: nome, labels: meses, values: g1.slice(1).map((l) => l[j + 1] / 1e6) }));
  s.addChart(pres.charts.LINE, series, { x: 0.6, y: 1.6, w: 8.0, h: 5.2, chartColors: [HEX.pedra, HEX.erro, HEX.falcao, HEX.azul],
    lineSize: 2.5, lineDataSymbol: "none", showTitle: true, title: "Resultado acumulado por cenário (R$ mi), meses 0 a 36",
    showLegend: true, legendPos: "b", valAxisLabelFormatCode: "0.0", catAxisLabelFrequency: 6, catAxisTitle: "mês", showCatAxisTitle: false, ...eixo });
  const cx = 8.95;
  const linhas = [
    ["Base", N("payback_base", "mes") + " · VPL " + N("vpl_base", "mi") + " · TIR " + N("tir_base", "pct") + " a.a.", C.accent1],
    ["Base medido (o que o piloto confirma)", N("payback_medido", "mes") + " · VPL " + N("vpl_medido", "mi"), C.accent4],
    ["Otimista", N("payback_otimista", "mes") + " · VPL " + N("vpl_otimista", "mi"), C.accent2],
    ["Conservador", "não se paga em 36 meses · VPL " + N("vpl_conservador", "mi"), C.accent5]];
  linhas.forEach(([t, d, cor], i) => {
    const y = 1.65 + i * 0.95;
    s.addShape(pres.shapes.OVAL, { x: cx, y: y + 0.08, w: 0.2, h: 0.2, fill: { color: cor }, line: { color: cor } });
    txt(s, t, { x: cx + 0.35, y, w: 3.45, h: 0.35, fontSize: 14, bold: true });
    txt(s, d, { x: cx + 0.35, y: y + 0.36, w: 3.45, h: 0.5, fontSize: 13, color: C.accent3 });
  });
  cartao(s, cx, 5.55, 3.8, 1.25, C.text1, "equilibrio");
  txt(s, [{ text: "Ponto de equilíbrio: ", options: { bold: true, color: "1FB37A" } },
    { text: "o projeto se paga em 36 meses com adoção a partir de " + N("adocao_minima", "pct") + " (hoje supomos 25%).", options: { color: C.background1 } }],
    { x: cx + 0.2, y: 5.65, w: 3.45, h: 1.05, fontSize: 14, valign: "middle" });
  s.addNotes("[0:50] Quando se paga. No cenário base, com as premissas da equipe, o acumulado vira positivo no " + N("payback_base", "mes") + ", VPL de " + N("vpl_base", "mi") + " a 12% ao ano e TIR de " + N("tir_base", "pct") + ". Com o tempo e o custo por execução estimados no protótipo, o payback cai para o " + N("payback_medido", "mes") + ": é isso que o piloto vai confirmar. Sendo honestos: o conservador, com 15% de adoção e menos aproveitamento, não se paga em 36 meses. Por isso a adoção mínima, " + N("adocao_minima", "pct") + ", vira meta de saída do piloto. Limite do modelo: como a calculadora, ele põe o investimento no mês 0 e o benefício desde o mês 1.");
}

// 11. Recorte financeiro 3: o que move o resultado
{
  const s = novo("CONTEUDO", "Finanças", "O que move o resultado: adoção e valor por tarefa; o preço dos tokens quase não pesa");
  const g3 = R.g3.slice(1, 9);
  const rot = g3.map((l) => l[0]);
  s.addChart(pres.charts.BAR, [{ name: "Premissa 20% menor", labels: rot, values: g3.map((l) => l[1] / 1e6) },
    { name: "Premissa 20% maior", labels: rot, values: g3.map((l) => l[2] / 1e6) }], {
    x: 0.6, y: 1.6, w: 7.6, h: 5.2, barDir: "bar", barGrouping: "stacked", chartColors: [HEX.erro, HEX.pedra], catAxisOrientation: "maxMin", catAxisLabelPos: "low",
    showTitle: true, title: "Variação do VPL do cenário base (R$ mi) com ±20% em cada premissa", showLegend: true, legendPos: "b",
    valAxisLabelFormatCode: "0.0", ...eixo });
  const ult = R.g3.find((l) => /tokens/i.test(l[0]));
  const impTok = "R$ " + br(Math.abs(ult[2]) / 1e3, 0) + " mil";
  usos.push({ slide: slideAtual, chave: "g3 (tornado)", txt: impTok, rotulo: "Δ VPL com custo de tokens +20%", celula: "Resumo para slides, tabela do gráfico 3 (Sensibilidade!L)", origem: "Sensibilidade" });
  txt(s, [{ text: "A adoção decide. ", options: { bold: true, color: C.text2 } },
    { text: "Minutos por tarefa, custo-hora, aproveitamento e adoção movem o VPL em centenas de milhares de reais. O custo de tokens, ±20%, mexe em " + impTok + "." }],
    { x: 8.6, y: 1.7, w: 4.1, h: 2.2, fontSize: 15 });
  cartao(s, 8.6, 4.05, 4.1, 2.75, C.background2, "cxc");
  const dif = R.numeros.custo_36m_stonefalcon - R.numeros.custo_36m_copilot;
  const mult = R.numeros.cpe_copilot / R.numeros.cpe_modelado;
  txt(s, [{ text: "Construir × comprar\n", options: { bold: true, color: C.text2, fontSize: 16 } },
    { text: "No volume do base, um SaaS como o Copilot Studio custa " + D("diferença 36m", F.mi(dif), ["custo_36m_stonefalcon", "custo_36m_copilot"]) + " a menos em 36 meses, mas cobra " + N("cpe_copilot", "brl2") + " por execução (" + D("múltiplo", br(mult, 0) + "×", ["cpe_copilot", "cpe_modelado"]) + " o nosso). Com " + N("empate_copilot_x", "x") + " o volume, construir fica mais barato, e só a plataforma própria mantém dados, permissões e auditoria na Stone." }],
    { x: 8.85, y: 4.2, w: 3.65, h: 2.5, fontSize: 13 });
  s.addNotes("[0:50] O tornado mostra o que move o VPL quando cada premissa varia 20%. No topo: minutos por tarefa, custo-hora, aproveitamento e adoção. Lá embaixo, o preço dos tokens. Ou seja, o risco do projeto é de adoção, não de preço de modelo. Construir ou comprar: no volume do cenário base, comprar sai um pouco mais barato em 36 meses porque evita o desenvolvimento, mas o custo por execução é muito maior; com cerca de " + N("empate_copilot_x", "x") + " o volume, construir vence. E comprar não resolve integração, permissões nem auditoria. Preços públicos consultados em 15/11/2026 (aba Construir × comprar).");
}

// 12. Os 5 indicadores
{
  const s = novo("CONTEUDO", "Finanças", "Os 5 indicadores da banca saem medidos da própria plataforma, por agente e por área");
  imagem(s, "06-painel-executivo.png", 0.6, 1.65, 7.5, "Painel executivo com os cinco indicadores");
  const ind = [["Tempo de execução", "redução do tempo por tarefa: minutos à mão × execução + conferência"],
    ["Custo operacional", "economia por operação: trabalho à mão × custo de modelos por execução"],
    ["Produtividade", "tarefas concluídas sem intervenção e horas liberadas"],
    ["Taxa de erros", "escaladas e falhas, com o motivo, contra o retrabalho manual"],
    ["ROI", "valor gerado ÷ custo no período e projeção de 36 meses"]];
  ind.forEach(([t, d], i) => {
    const y = 1.65 + i * 0.98;
    circulo(s, 8.45, y + 0.02, 0.48, String(i + 1), C.accent1);
    txt(s, t, { x: 9.1, y, w: 3.6, h: 0.35, fontSize: 16, bold: true });
    txt(s, d, { x: 9.1, y: y + 0.36, w: 3.6, h: 0.6, fontSize: 12, color: C.accent3 });
  });
  txt(s, "No print, os números vêm do histórico de demonstração (sintético); no piloto, viram medição real.",
    { x: 0.6, y: 5.45, w: 7.5, h: 0.5, fontSize: 12, color: C.accent3 });
  s.addNotes("[0:40] Os cinco critérios de avaliação, com os nomes exatos: tempo de execução, custo operacional, produtividade, taxa de erros e ROI. A plataforma mede cada um nas execuções, por agente e por área, porque tudo passa pela trilha. Atenção: o painel do print usa o histórico de demonstração, que é sintético; ele mostra 79% de economia do roteador, enquanto a planilha calcula " + N("economia_roteador", "pct") + " pela estrutura dos agentes. No piloto, esses números passam a ser medição.");
}

// 13. Go-to-market interno
pres.addSection({ title: "Plano" });
{
  const s = novo("CONTEUDO", "Plano", "Go-to-market interno: piloto com metas de saída, depois ondas por área");
  const fases = [["Piloto", "Atendimento e Risco · " + N("piloto_meses", "num") + " meses",
      ["Agentes reais nas 2 áreas, com 2 conectores", "Medir adoção, minutos por tarefa e custo por execução", "Metas de saída decidem a próxima tranche"], C.accent1],
    ["Ondas por área", "uma área por vez",
      ["Conectores restantes do catálogo", "Embaixadores formados no piloto treinam a próxima área", "Galeria de agentes que já funcionam"], C.text2],
    ["CoE de IA", "escala sustentável",
      ["Mantém catálogo, revisões e orçamento", "Comunidade de embaixadores por área", "Painel executivo para o board"], C.accent2]];
  fases.forEach(([t, sub, itens, cor], i) => {
    const x = 0.6 + i * 4.1;
    cartao(s, x, 1.65, 3.8, 3.35, C.background2, "fase" + i);
    circulo(s, x + 0.3, 1.9, 0.6, String(i + 1), cor);
    txt(s, t, { x: x + 1.05, y: 1.9, w: 2.6, h: 0.35, fontSize: 19, bold: true });
    txt(s, sub, { x: x + 1.05, y: 2.27, w: 2.6, h: 0.3, fontSize: 13, color: C.accent3 });
    txt(s, itens.map((it, k) => ({ text: it, options: { bullet: true, breakLine: k < itens.length - 1 } })),
      { x: x + 0.3, y: 2.85, w: 3.3, h: 2.0, fontSize: 14, paraSpaceAfter: 6 });
    if (i < 2) s.addShape(pres.shapes.RIGHT_ARROW, { x: x + 3.85, y: 3.18, w: 0.2, h: 0.3, fill: { color: HEX.cinzaClaro }, line: { color: HEX.cinzaClaro } });
  });
  txt(s, [{ text: "O piloto valida as premissas marcadas “a validar”: ", options: { bold: true, color: C.text2 } },
    { text: "adoção, minutos de cada tarefa à mão, quanto do tempo liberado vira ganho real, custo por execução com modelos reais e taxa de escalada." }],
    { x: 0.6, y: 5.35, w: 12.1, h: 0.9, fontSize: 16 });
  s.addNotes("[0:50] Como levar para dentro da Stone. Começamos com um piloto em Atendimento e Prevenção a Fraudes, as áreas dos agentes da demo, por " + N("piloto_meses", "num") + " meses e com dois conectores. O piloto existe para trocar premissa por medição: adoção, minutos por tarefa, aproveitamento e custo real por execução. Se as metas forem atingidas, expandimos por ondas, área a área, com embaixadores formados no piloto. No fim, um CoE de IA mantém catálogo, revisões e orçamento.");
}

// 14. Riscos e próximos passos
{
  const s = novo("CONTEUDO", "Plano", "Riscos e como reduzimos cada um");
  const cab = (t) => ({ text: t, options: { bold: true, color: HEX.branco, fill: { color: HEX.tinta } } });
  const riscos = [["Adoção abaixo do esperado", "É o que mais move o VPL", "Piloto com metas de saída; embaixadores; galeria de agentes prontos; tranche 2 condicionada"],
    ["Qualidade do modelo", "Respostas erradas ou ações indevidas", "Escalada para humano com motivo; confirmação nas ações sensíveis; sandbox antes de publicar"],
    ["Integração real (n8n e APIs)", "Conectores do protótipo são simulados", "Mesmo contrato dos conectores; n8n só para integrações; saúde e alertas por sistema"],
    ["LGPD e dados sensíveis", "Dado pessoal fora do lugar", "Mascaramento antes do modelo; fluxo por classificação; auditoria; DLP e SSO em produção"]];
  const rows = [[cab("Risco"), cab("Por que importa"), cab("Mitigação")]];
  riscos.forEach(([r, p, m]) => rows.push([{ text: r, options: { bold: true } }, { text: p, options: { color: HEX.cinza } }, { text: m }]));
  s.addTable(rows, { x: 0.6, y: 1.55, w: 12.1, colW: [3.0, 3.3, 5.8], fontSize: 14, color: HEX.tinta, fontFace: "Calibri",
    border: { type: "solid", color: HEX.linha, pt: 1 }, rowH: [0.45, 0.78, 0.78, 0.78, 0.78], valign: "middle", margin: 0.08 });
  const marcos = [["Meses 1 a 5", "Construção: plataforma, SSO, Postgres e 2 conectores"], ["Meses 6 a 8", "Piloto em Atendimento e Risco"],
    ["Mês 9 em diante", "Ondas por área e conectores restantes"]];
  marcos.forEach(([t, d], i) => {
    const x = 0.6 + i * 4.1;
    cartao(s, x, 5.45, 3.8, 1.1, i === 1 ? C.text2 : C.background2, "marco" + i);
    txt(s, t, { x: x + 0.2, y: 5.55, w: 3.4, h: 0.35, fontSize: 15, bold: true, color: i === 1 ? C.background1 : C.text2 });
    txt(s, d, { x: x + 0.2, y: 5.92, w: 3.4, h: 0.55, fontSize: 13, color: i === 1 ? C.background2 : C.accent3 });
  });
  s.addNotes("[0:40] Os quatro riscos que mais nos preocupam. Adoção é o principal, e o piloto com metas de saída existe para isso. Qualidade do modelo: escalada com motivo e confirmação humana nas ações sensíveis. Integração: no protótipo os sistemas são simulados, mas o contrato do conector é o mesmo. LGPD: os dados pessoais nunca chegam ao modelo, e em produção somamos DLP e SSO. Cronograma: cinco meses de construção, três de piloto, depois ondas.");
}

// 15. O pedido ao board
{
  slideAtual += 1;
  const s = pres.addSlide({ masterName: "ESCURO", sectionTitle: "Plano" });
  s.addText("O pedido: " + N("piloto_tranche1", "mi") + " para construir e pilotar em 8 meses, com a escala condicionada a metas", { placeholder: "titulo" });
  const col = [["Investimento", ["Tranche 1: plataforma, 2 conectores e " + N("piloto_meses", "num") + " meses de operação no piloto", "Tranche 2 (conectores restantes) só depois das metas"]],
    ["Prazo", ["5 meses de construção", N("piloto_meses", "num") + " meses de piloto em Atendimento e Risco", "Decisão de escala no mês 9"]],
    ["Metas de saída do piloto", ["Adoção semanal ≥ 25% nas 2 áreas (equilíbrio da empresa: " + N("adocao_minima", "pct") + ")",
      "Tarefa média ≥ " + D("meta minutos", F.num(Math.ceil(R.numeros.minutos_minimos)) + " min", ["minutos_minimos"]) + " à mão, medida (equilíbrio: " + N("minutos_minimos", "num1") + " min)",
      "Escalada ≤ 8% e zero dado pessoal fora dos marcadores"]]];
  col.forEach(([t, itens], i) => {
    const x = 0.8 + i * 3.95;
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y: 2.75, w: 3.7, h: 3.4, fill: { color: "1B3A2E" }, line: { color: "2E4A3E" }, rectRadius: 0.12 });
    txt(s, t, { x: x + 0.25, y: 2.95, w: 3.2, h: 0.45, fontSize: 20, bold: true, color: "1FB37A" });
    txt(s, itens.map((it, k) => ({ text: it, options: { bullet: true, breakLine: k < itens.length - 1 } })),
      { x: x + 0.25, y: 3.55, w: 3.25, h: 2.5, fontSize: 15, color: C.background1, paraSpaceAfter: 8 });
  });
  txt(s, "Números da planilha analise-financeira.xlsx (aba Resumo para slides). Premissas marcadas “a validar” são o que o piloto mede.",
    { x: 0.8, y: 6.45, w: 11.5, h: 0.4, fontSize: 12, color: "A9B8B0" });
  s.addNotes("[0:40] O pedido. " + N("piloto_tranche1", "mi") + " na primeira tranche: construir a plataforma, entregar dois conectores e operar " + N("piloto_meses", "num") + " meses de piloto. A escala só vem se as metas forem atingidas: adoção semanal de pelo menos 25% nas duas áreas, tarefa média medida acima do ponto de equilíbrio, escalada até 8% e nenhum dado pessoal fora dos marcadores. Obrigado; abrimos para perguntas.");
}

// ---------- Anexos ----------
pres.addSection({ title: "Anexos" });
{
  const s = novo("CONTEUDO", "Anexos", "Anexo A · Premissas do cenário base e de onde vêm");
  const chaves = ["investimento_inicial", "modulos_integracao", "hospedagem_mensal", "sustentacao_mensal", "usuarios", "adocao_alvo", "meses_rampa",
    "tarefas_por_usuario_dia", "dias_uteis", "minutos_por_tarefa", "minutos_revisao_humana", "custo_hora", "aproveitamento", "custo_por_execucao",
    "taxa_desconto_anual", "cotacao_dolar"];
  const fmtP = (p) => {
    const v = p.valor;
    if (p.unidade === "%" || p.unidade === "% a.a.") return F.pct1(v);
    if (String(p.unidade).startsWith("R$/exec")) return F.brl4(v);
    if (String(p.unidade).startsWith("R$")) return v >= 1000 ? "R$ " + br(v, 0) : F.brl2(v);
    return br(v, v % 1 ? 2 : 0) + " " + (p.unidade || "");
  };
  const cab = (t) => ({ text: t, options: { bold: true, color: HEX.branco, fill: { color: HEX.tinta } } });
  const rows = [[cab("Premissa (nome no código)"), cab("Valor"), cab("Status")]];
  chaves.forEach((k) => {
    const p = R.premissas.find((x) => x.nome === k);
    usos.push({ slide: slideAtual, chave: k, txt: fmtP(p), rotulo: p.descricao, celula: "Premissas!D" + p.linha, origem: p.status });
    rows.push([{ text: p.descricao + " (" + k + ")" }, { text: fmtP(p) }, { text: p.status, options: { color: p.status === "Premissa a validar" ? HEX.falcao : HEX.cinza } }]);
  });
  s.addTable(rows, { x: 0.6, y: 1.45, w: 12.1, colW: [7.4, 2.0, 2.7], fontSize: 11, color: HEX.tinta, fontFace: "Calibri",
    border: { type: "solid", color: HEX.linha, pt: 0.75 }, rowH: 0.31, valign: "middle", margin: 0.05 });
  s.addNotes("Anexo para perguntas. Lista completa, com fonte de cada célula, na aba Premissas da planilha.");
}
{
  const s = novo("CONTEUDO", "Anexos", "Anexo B · Fontes e data de conferência");
  const fontes = [
    ["Desafio", "contexto-desafio.pdf (StoneLab) e critérios de avaliação (5 indicadores)"],
    ["Custos da equipe", "docs/custos-estimados.txt: equipe, contingência, módulos, hospedagem, sustentação, tokens (out. e nov. de 2026)"],
    ["Preços dos modelos", "Tabela oficial da Anthropic (platform.claude.com/docs/en/about-claude/pricing), conferida em 15/11/2026"],
    ["Câmbio", "R$ 5,52 (documento da equipe, igual ao protótipo); PTAX de 13/11/2026 = R$ 5,6518 (Banco Central), só referência"],
    ["Copilot Studio", "microsoft.com (pricing/copilot-studio) e learn.microsoft.com (tabela de créditos), consultados em 15/11/2026"],
    ["n8n e Zapier", "n8n.io/pricing e zapier.com/pricing, consultados em 15/11/2026; blocos extras do n8n por fonte de terceiros"],
    ["Protótipo", "backend/app/finance (calculadora), agents/governanca.py (tamanho dos passos), llm/roteador.py; histórico da demo é sintético"],
    ["Consistência", "testar_consistencia.py: Excel recalculado = calculadora.projetar() mês a mês, tolerância de R$ 1"]];
  fontes.forEach(([t, d], i) => {
    const y = 1.5 + i * 0.66;
    txt(s, t, { x: 0.6, y, w: 2.6, h: 0.55, fontSize: 15, bold: true, color: C.text2 });
    txt(s, d, { x: 3.3, y, w: 9.4, h: 0.6, fontSize: 14, color: C.accent3 });
  });
  s.addNotes("Anexo de fontes. Conferir preços e câmbio na véspera.");
}
{
  const s = novo("CONTEUDO", "Anexos", "Anexo C · Declaração de uso de IA");
  marca(s, 0.6, 1.6, 0.9);
  txt(s, [{ text: "O código do protótipo, a planilha financeira e esta apresentação foram produzidos com o Claude (Anthropic), a pedido da equipe.", options: { breakLine: true } },
    { text: "A equipe definiu o problema, as premissas de negócio e o documento de custos, revisou os resultados e responde por eles.", options: { breakLine: true } },
    { text: "Os geradores ficam em entregaveis/gerador/ e reproduzem os arquivos a partir das premissas." }],
    { x: 1.8, y: 1.6, w: 10.9, h: 3.0, fontSize: 18, paraSpaceAfter: 12 });
  s.addNotes("Registrar também na declaração de uso de IA do trabalho escrito.");
}

// ---------- gravar ----------
(async () => {
  await pres.writeFile({ fileName: SAIDA });
  if (SKILL_THEME) {
    const { applyTheme } = require(SKILL_THEME);
    await applyTheme(SAIDA, THEME);
  }
  const linhas = ["# Checagem dos números da apresentação", "",
    "Gerado por `entregaveis/gerador/gerar_apresentacao.js`. Cada número do deck aponta para uma célula da planilha `analise-financeira.xlsx`.", "",
    "| Slide | Texto no slide | Número | Célula de origem | Calculado em |", "|---|---|---|---|---|"];
  const vistos = new Set();
  usos.forEach((u) => {
    const k = u.slide + "|" + u.chave + "|" + u.txt;
    if (vistos.has(k)) return;
    vistos.add(k);
    linhas.push(`| ${u.slide} | ${u.txt} | ${u.rotulo} | ${u.celula} | ${u.origem} |`);
  });
  linhas.push("", "Os 5 indicadores aparecem no slide 12 com os nomes exatos dos critérios: Tempo de execução, Custo operacional, Produtividade, Taxa de erros e ROI.");
  fs.writeFileSync(path.join(AQUI, "..", "checagem-numeros.md"), linhas.join("\n") + "\n", "utf8");
  console.log("ok", SAIDA, "·", slideAtual, "slides ·", vistos.size, "números rastreados");
})();
