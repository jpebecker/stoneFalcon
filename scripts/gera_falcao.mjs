// Gerador do falcão StoneFalcon (corpo animado e rosto). Node puro, sem dependências.
//
//   node scripts/gera_falcao.mjs
//
// Grava, a partir de desenho feito em código (nada é recortado de bitmap):
//   frontend/src/components/falcao/quadros.ts   caminhos do corpo por animação e peso de traço, mais o rosto
//   frontend/public/icone.svg                   o rosto sobre o quadrado escuro (favicon)
//   extensao/icones/rosto.json                  polígonos do rosto, lidos por extensao/icones/gerar.py
//   docs/falcao/falcao-{parado,voo,rosto}.svg   tiras de referência para olhar o desenho
//
// Os arquivos gerados entram no Git; o build não roda este script. Rodar duas vezes não muda nada.
// Falha (código 1) se algum ponto sair do quadro (128 x 112 no corpo, 64 x 64 no rosto).
//
// Estilo do corpo: traço caligráfico, corpo inteiro de perfil, voltado para a direita. Cada traço é uma forma
// preenchida que engrossa e afina ao longo de uma curva, como pincel. O rosto usa o mesmo pincel, mais largo.
// Cores por variável CSS, com valor de reserva: --falcao-traco, --falcao-pena e --falcao-rastro.

import { mkdirSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const RAIZ = join(dirname(fileURLToPath(import.meta.url)), "..");
const AVISO = "gerado por scripts/gera_falcao.mjs, não edite à mão";

export const QUADRO = { largura: 128, altura: 112 };
export const LADO_ROSTO = 64;
// Deslocamento do rosto dentro do quadrado 64 x 64 (centraliza o desenho).
const DESLOCA_ROSTO = [1.5, -1];

export const ANIMACOES = {
  // pairando no lugar: asa quase parada, respiração leve
  parado: { quadros: 6, meio: 40, amp: 9, bob: 1.4, rastro: false, duracaoMs: 1100 },
  // voo lateral: batida completa e rastro de velocidade atrás da cauda
  voo: { quadros: 8, meio: 34, amp: 28, bob: 2.6, rastro: true, duracaoMs: 560 },
};

// Peso do traço por tamanho de exibição (o componente escolhe: até 48 px 1,7; até 72 px 1,3; acima disso 1).
export const PESOS = [1, 1.3, 1.7];

// Cores do rosto sobre o quadrado escuro (iguais às da Marca).
const CORES_ROSTO = { fundo: "#10201A", verde: "#1FB37A", rosa: "#E0428F", claro: "#E8F3EE" };

const r1 = (n) => Math.round(n * 10) / 10;
const rad = (g) => (g * Math.PI) / 180;
const soma = (a, b, k = 1) => [a[0] + b[0] * k, a[1] + b[1] * k];

function bezier([p0, p1, p2, p3], t) {
  const u = 1 - t;
  const a = u * u * u, b = 3 * u * u * t, c = 3 * u * t * t, d = t * t * t;
  return [a * p0[0] + b * p1[0] + c * p2[0] + d * p3[0], a * p0[1] + b * p1[1] + c * p2[1] + d * p3[1]];
}
function tangente([p0, p1, p2, p3], t) {
  const u = 1 - t;
  return [
    3 * u * u * (p1[0] - p0[0]) + 6 * u * t * (p2[0] - p1[0]) + 3 * t * t * (p3[0] - p2[0]),
    3 * u * u * (p1[1] - p0[1]) + 6 * u * t * (p2[1] - p1[1]) + 3 * t * t * (p3[1] - p2[1]),
  ];
}

// Largura relativa ao longo do traço: parte de `ini`, chega a 1 no `pico` e afina até `fim`.
function perfil(t, { pico, ini, fim }) {
  if (t < pico) return ini + (1 - ini) * Math.sin((t / pico) * (Math.PI / 2));
  return fim + (1 - fim) * Math.sin(((1 - t) / (1 - pico)) * (Math.PI / 2));
}

// Traço afinado sobre uma ou mais cúbicas encadeadas. Devolve o contorno como lista de pontos [x, y].
function contorno(segmentos, largura, forma = {}) {
  const f = { pico: 0.35, ini: 0.3, fim: 0.03, amostras: 12, ...forma };
  const n = segmentos.length, total = f.amostras * n;
  const ida = [], volta = [];
  for (let i = 0; i <= total; i++) {
    const tg = i / total;
    const s = Math.min(n - 1, Math.floor(tg * n));
    const t = tg * n - s;
    const p = bezier(segmentos[s], t);
    const d = tangente(segmentos[s], t);
    const len = Math.hypot(d[0], d[1]) || 1;
    const meia = (largura * perfil(tg, f)) / 2;
    const nx = (-d[1] / len) * meia, ny = (d[0] / len) * meia;
    ida.push([r1(p[0] + nx), r1(p[1] + ny)]);
    volta.push([r1(p[0] - nx), r1(p[1] - ny)]);
  }
  return [...ida, ...volta.reverse()];
}

// Contorno como "d" de caminho fechado, só com M, L e Z.
const dePontos = (pontos) => `M${pontos.map(([x, y]) => `${x} ${y}`).join("L")}Z`;
const traco = (segmentos, largura, forma) => dePontos(contorno(segmentos, largura, forma));

// Quadrática amostrada em pontos (usada para o olho do rosto, que vira polígono).
function quadratica(p0, p1, p2, amostras = 8) {
  const pts = [];
  for (let i = 0; i <= amostras; i++) {
    const t = i / amostras, u = 1 - t;
    pts.push([r1(u * u * p0[0] + 2 * u * t * p1[0] + t * t * p2[0]), r1(u * u * p0[1] + 2 * u * t * p1[1] + t * t * p2[1])]);
  }
  return pts;
}

const desloca = (segs, dy) => segs.map((seg) => seg.map(([x, y]) => [x, y + dy]));

// ---------- Corpo ----------

// Um quadro: `fase` de 0 a 1 percorre uma batida de asa (0 = asa no alto).
function quadro(fase, cfg, peso = 1) {
  const ang = 2 * Math.PI * fase;
  const recolhe = Math.max(0, -Math.sin(ang)); // asa dobra um pouco na subida
  const balancoCorpo = -cfg.bob * Math.sin(ang - 0.6); // corpo sobe na descida da asa
  const dy = 6 + balancoCorpo; // 6: folga para a ponta da asa no alto
  const verdes = [], rosas = [], rastro = [];

  // Cauda: três penas longas para baixo e para trás, balançando de leve.
  const balanco = 1.6 * Math.sin(ang + 1.2);
  const cauda = [
    [[[56, 80], [44, 84], [30, 90 + balanco], [14, 96 + balanco]], 2.8],
    [[[61, 81], [52, 87], [42, 94 + balanco], [32, 100 + balanco]], 2.4],
    [[[50, 79], [38, 80], [24, 82 + balanco * 0.6], [8, 85 + balanco * 0.6]], 2.2],
  ];
  for (const [seg, w] of cauda) rosas.push(traco(desloca([seg], dy), w * peso, { pico: 0.25, ini: 0.45 }));

  // Asa: borda de ataque verde saindo da nuca; penas rosa penduradas na borda.
  const a = rad(cfg.meio + cfg.amp * Math.cos(ang));
  const S = [77, 59 + dy];
  const L = 60 * (1 - 0.22 * recolhe);
  const d = [-Math.cos(a), -Math.sin(a)];
  const nF = [Math.sin(a), -Math.cos(a)]; // lado da frente da asa
  const borda = [S, soma(soma(S, d, 0.3 * L), nF, 10), soma(soma(S, d, 0.72 * L), nF, 7), soma(soma(S, d, L), nF, -1)];
  const penas = [
    [0.28, 48, 20, 2.4], [0.42, 38, 25, 2.5], [0.56, 29, 28, 2.6], [0.7, 21, 28, 2.5], [0.84, 13, 24, 2.2],
  ];
  for (const [u, beta0, len0, w] of penas) {
    const beta = rad(beta0 + 14 * recolhe);
    const len = len0 * (1 - 0.15 * recolhe);
    const Q = soma(bezier(borda, u), nF, -2.2);
    const f = [d[0] * Math.cos(beta) - nF[0] * Math.sin(beta), d[1] * Math.cos(beta) - nF[1] * Math.sin(beta)];
    const seg = [Q, soma(Q, f, 0.35 * len), soma(soma(Q, f, 0.7 * len), nF, -0.08 * len), soma(Q, f, len)];
    rosas.push(traco([seg], w * peso, { pico: 0.25, ini: 0.5 }));
  }
  verdes.push(traco([borda], 3.4 * peso, { pico: 0.3, ini: 0.55 }));

  // Nuca e alto da cabeça (continua a borda da asa), bico em gancho, peito e barriga.
  verdes.push(traco(desloca([[[77, 59], [80, 50], [90, 44.5], [101, 46]]], dy), 3 * peso, { pico: 0.45, ini: 0.7, fim: 0.45 }));
  verdes.push(traco(desloca([[[100, 45.6], [107, 45.4], [111.5, 49.5], [107.5, 57]]], dy), 3 * peso, { pico: 0.35, ini: 0.7, fim: 0.04 }));
  verdes.push(traco(desloca([
    [[105, 53.5], [98, 56], [93, 64], [81, 71]],
    [[81, 71], [68, 78], [52, 79], [38, 76]],
  ], dy), 3.4 * peso, { pico: 0.3, ini: 0.25 }));
  // Olho de falcão e a "lágrima" (faixa malar) logo abaixo dele.
  const ey = 50 + dy;
  verdes.push(`M91.8 ${r1(ey + 0.2)}Q95.6 ${r1(ey - 2.6)} 99.2 ${r1(ey - 1.2)}Q96 ${r1(ey + 1.9)} 91.8 ${r1(ey + 0.2)}Z`);
  verdes.push(traco(desloca([[[95.4, 52.6], [95.2, 55], [94.6, 57], [93.4, 59.5]]], dy), 2.2 * peso, { pico: 0.2, ini: 0.7, fim: 0.05 }));

  // Rastro de velocidade (só no voo lateral).
  if (cfg.rastro) {
    [[62, 20], [71, 28], [82, 14]].forEach(([y, base], i) => {
      const x0 = 1 + 7 * ((fase * 2 + i * 0.37) % 1);
      const comp = base * (0.75 + 0.25 * Math.sin(ang + i));
      rastro.push(`M${r1(x0)} ${r1(y + 6 + balancoCorpo * 0.5)}H${r1(x0 + comp)}`);
    });
  }
  return { verdes, rosas, rastro };
}

function quadrosDe(nome, peso) {
  const cfg = ANIMACOES[nome];
  return Array.from({ length: cfg.quadros }, (_, i) => quadro(i / cfg.quadros, cfg, peso));
}

// ---------- Rosto (pincel largo: arco verde da cabeça, bico em gancho claro, penas rosa do pescoço) ----------

function rosto() {
  const verdes = [], rosas = [], claros = [];
  // arco do alto da cabeça, da nuca até a base do bico
  verdes.push(contorno([[[9, 37], [14, 17], [34, 9], [50, 17]]], 8.6, { pico: 0.55, ini: 0.15, fim: 0.55, amostras: 16 }));
  // bico em gancho
  claros.push(contorno([[[46, 16.5], [56, 13.5], [62.5, 21], [57, 32]]], 8.6, { pico: 0.3, ini: 0.9, fim: 0.04, amostras: 14 }));
  // olho (duas quadráticas viram polígono)
  claros.push([...quadratica([37.5, 25.6], [42.5, 20.6], [48.4, 22.6]), ...quadratica([48.4, 22.6], [44, 27.8], [37.5, 25.6]).slice(1)]);
  // penas do pescoço (rosa) e a garganta (verde), descendo para trás
  rosas.push(contorno([[[27, 24], [19, 30], [12, 40], [6, 54]]], 7.6, { pico: 0.35, ini: 0.35, amostras: 14 }));
  rosas.push(contorno([[[35, 31], [27, 37], [21, 46], [17, 58]]], 7, { pico: 0.35, ini: 0.35, amostras: 14 }));
  verdes.push(contorno([[[47, 32], [42, 40], [35, 49], [30, 60]]], 7, { pico: 0.3, ini: 0.45, amostras: 14 }));
  // já no espaço final de 64 x 64
  const move = (poligonos) => poligonos.map((p) => p.map(([x, y]) => [r1(x + DESLOCA_ROSTO[0]), r1(y + DESLOCA_ROSTO[1])]));
  return { rosas: move(rosas), verdes: move(verdes), claros: move(claros) };
}

// ---------- Saídas ----------

const juntaPontos = (poligonos) => poligonos.map(dePontos).join("");

function svgRosto({ fundo = CORES_ROSTO.fundo, verde = CORES_ROSTO.verde, rosa = CORES_ROSTO.rosa, claro = CORES_ROSTO.claro } = {}) {
  const c = rosto();
  const base = fundo ? `<rect width="64" height="64" rx="16" fill="${fundo}"/>` : "";
  const g = (cor, ps) => `<path fill="${cor}" d="${juntaPontos(ps)}"/>`;
  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">${base}${g(rosa, c.rosas)}${g(verde, c.verdes)}${g(claro, c.claros)}</svg>`;
}

function grupoQuadro(q, x = 0) {
  const t = x ? ` transform="translate(${x} 0)"` : "";
  const rastro = q.rastro.length
    ? `<g style="fill:none;stroke:var(--falcao-rastro,#76847D);stroke-width:1.6;stroke-linecap:round;opacity:.55"><path d="${q.rastro.join("")}"/></g>`
    : "";
  return `<g${t}>${rastro}<g style="fill:var(--falcao-pena,#D63384)"><path d="${q.rosas.join("")}"/></g><g style="fill:var(--falcao-traco,#128C5E)"><path d="${q.verdes.join("")}"/></g></g>`;
}

function svgTira(nome) {
  const qs = quadrosDe(nome, 1);
  const W = QUADRO.largura * qs.length;
  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${W} ${QUADRO.altura}" width="${W}" height="${QUADRO.altura}">${qs.map((q, i) => grupoQuadro(q, i * QUADRO.largura)).join("")}</svg>`;
}

function quadrosTs() {
  const linhas = [
    `// ${AVISO}.`,
    `// Caminhos vetoriais do corpo do falcão (quadro de ${QUADRO.largura} x ${QUADRO.altura}) e do rosto (${LADO_ROSTO} x ${LADO_ROSTO}).`,
    "",
    'export type Animacao = "parado" | "voo";',
    'export type Peso = "1" | "1.3" | "1.7";',
    "",
    "/** Um quadro do corpo: cada campo é o `d` de um <path> (o rastro só existe no voo). */",
    "export interface Quadro { rastro: string; rosas: string; verdes: string }",
    "",
    `export const QUADRO = { largura: ${QUADRO.largura}, altura: ${QUADRO.altura} } as const;`,
    "",
    "export const ANIMACOES = {",
    ...Object.entries(ANIMACOES).map(([n, c]) => `  ${n}: { quadros: ${c.quadros}, duracaoMs: ${c.duracaoMs} },`),
    "} as const;",
    "",
    "export const QUADROS: Record<Animacao, Record<Peso, Quadro[]>> = {",
  ];
  for (const nome of Object.keys(ANIMACOES)) {
    linhas.push(`  ${nome}: {`);
    for (const peso of PESOS) {
      linhas.push(`    "${peso}": [`);
      for (const q of quadrosDe(nome, peso)) {
        linhas.push(`      { rastro: ${JSON.stringify(q.rastro.join(""))}, rosas: ${JSON.stringify(q.rosas.join(""))}, verdes: ${JSON.stringify(q.verdes.join(""))} },`);
      }
      linhas.push("    ],");
    }
    linhas.push("  },");
  }
  linhas.push("};", "");
  const r = rosto();
  linhas.push(
    "/** Rosto, já no espaço de 64 x 64: três cores (pena rosa, traço verde, bico e olho claros). */",
    "export const ROSTO = {",
    `  lado: ${LADO_ROSTO},`,
    `  rosas: ${JSON.stringify(juntaPontos(r.rosas))},`,
    `  verdes: ${JSON.stringify(juntaPontos(r.verdes))},`,
    `  claros: ${JSON.stringify(juntaPontos(r.claros))},`,
    "} as const;",
    "",
  );
  return linhas.join("\n");
}

function rostoJson() {
  const r = rosto();
  const dados = {
    _gerado: AVISO,
    lado: LADO_ROSTO,
    raio: 16,
    cores: { fundo: CORES_ROSTO.fundo, verde: CORES_ROSTO.verde, rosa: CORES_ROSTO.rosa, claro: CORES_ROSTO.claro },
    // ordem de pintura: rosa, verde, claro
    formas: [
      { cor: "rosa", poligonos: r.rosas },
      { cor: "verde", poligonos: r.verdes },
      { cor: "claro", poligonos: r.claros },
    ],
  };
  return JSON.stringify(dados) + "\n";
}

// ---------- Conferência dos limites ----------

// Percorre um "d" com M, L, Q, H e Z e devolve [minX, minY, maxX, maxY] dos pontos.
function limites(d) {
  const caixa = [Infinity, Infinity, -Infinity, -Infinity];
  const toma = (x, y) => {
    caixa[0] = Math.min(caixa[0], x); caixa[1] = Math.min(caixa[1], y);
    caixa[2] = Math.max(caixa[2], x); caixa[3] = Math.max(caixa[3], y);
  };
  let y = 0;
  for (const [, cmd, nums] of d.matchAll(/([MLQHZ])([^MLQHZ]*)/g)) {
    const n = (nums.match(/-?\d+(?:\.\d+)?/g) || []).map(Number);
    if (cmd === "H") { toma(n[0], y); continue; }
    for (let i = 0; i + 1 < n.length; i += 2) { toma(n[i], n[i + 1]); y = n[i + 1]; }
  }
  return caixa;
}

function confere() {
  const erros = [];
  const dentro = (rotulo, ds, largura, altura) => {
    for (const d of ds) {
      const [x0, y0, x1, y1] = limites(d);
      if (x0 < 0 || y0 < 0 || x1 > largura || y1 > altura) erros.push(`${rotulo}: ponto fora do quadro (x ${x0}..${x1}, y ${y0}..${y1})`);
    }
  };
  for (const nome of Object.keys(ANIMACOES)) {
    for (const peso of PESOS) {
      quadrosDe(nome, peso).forEach((q, i) =>
        dentro(`${nome} peso ${peso} quadro ${i}`, [q.rastro.join(""), q.rosas.join(""), q.verdes.join("")].filter(Boolean), QUADRO.largura, QUADRO.altura));
    }
  }
  const r = rosto();
  dentro("rosto", [...r.rosas, ...r.verdes, ...r.claros].map(dePontos), LADO_ROSTO, LADO_ROSTO);
  return erros;
}

// ---------- Execução ----------

function grava(caminho, texto) {
  const completo = join(RAIZ, caminho);
  mkdirSync(dirname(completo), { recursive: true });
  writeFileSync(completo, texto);
  console.log(caminho);
}

const erros = confere();
if (erros.length) {
  console.error(erros.slice(0, 10).join("\n"));
  console.error(`gera_falcao: ${erros.length} problema(s); nada foi gravado.`);
  process.exit(1);
}

const comentario = `<!-- ${AVISO} -->\n`;
grava("frontend/src/components/falcao/quadros.ts", quadrosTs());
grava("frontend/public/icone.svg", comentario + svgRosto() + "\n");
grava("extensao/icones/rosto.json", rostoJson());
for (const nome of Object.keys(ANIMACOES)) grava(`docs/falcao/falcao-${nome}.svg`, comentario + svgTira(nome) + "\n");
grava("docs/falcao/falcao-rosto.svg", comentario + svgRosto({ fundo: null, verde: "#128C5E", rosa: "#D63384", claro: "#76847D" }) + "\n");
