import { createContext, useCallback, useContext, useEffect, useLayoutEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { useLocation } from "react-router-dom";
import Falcao from "./Falcao";

/** Um alvo do voo: um elemento da tela ou um ponto (px da janela). Ausente = sem alvo. */
export type Alvo = HTMLElement | { x: number; y: number } | null | undefined;

export interface PedidoVoo {
  /** De onde sai (ex.: o botão que a pessoa clicou). Sem `de`, o falcão entra pela lateral. */
  de?: Alvo;
  /** Para onde vai (ex.: a aba Execuções, o sino). */
  para: Alvo;
  /** Se `para` estiver ausente ou fora da tela (menu recolhido), voa até este (ex.: o botão do menu). */
  alternativo?: Alvo;
  /** Chamado quando o falcão chega (aqui o alvo pode ganhar o destaque curto). Não é chamado se o voo for cancelado. */
  aoChegar?: () => void;
}

interface Voo {
  id: number;
  caminho: string;
  de: { x: number; y: number };
  para: { x: number; y: number };
  direcao: "direita" | "esquerda";
  duracaoMs: number;
  arco: number;
  aoChegar?: () => void;
}

const TAMANHO = 56; // largura do falcão em voo, em px
const ALTURA = (TAMANHO * 112) / 128;
const PAIRAR_MS = 900;
const SUMIR_MS = 250;
const REDUZIDO_MS = 1200;
const MIN_MS = 600;

const nada = { voar: (p: PedidoVoo) => p.aoChegar?.(), cancelar: () => {} };
const Contexto = createContext<{ voar: (p: PedidoVoo) => void; cancelar: () => void }>(nada);

/** `useFalcao().voar({ de, para, aoChegar })` e `cancelar()`. Fora do provedor, não faz nada (só chama `aoChegar`). */
export const useFalcao = () => useContext(Contexto);

/** Elemento marcado com `data-alvo="nome"` (abas do menu, sino, marca), para usar em `de`/`para`. */
export function alvoDe(nome: string): HTMLElement | null {
  return document.querySelector<HTMLElement>(`[data-alvo="${nome}"]`);
}

const visivel = (r: DOMRect) => r.width + r.height > 0 && r.bottom > 0 && r.top < window.innerHeight && r.right > 0 && r.left < window.innerWidth;
const preso = (n: number, a: number, b: number) => Math.min(Math.max(n, a), b);

function centroDe(a: Alvo): { x: number; y: number } | null {
  if (!a) return null;
  if (!(a instanceof HTMLElement)) return a;
  if (!a.isConnected) return null;
  const r = a.getBoundingClientRect();
  return visivel(r) ? { x: r.left + r.width / 2, y: r.top + r.height / 2 } : null;
}

/** Ponto de pouso ao lado do alvo, do lado de onde o falcão vem; um ponto solto é usado como está. */
function destinoDe(a: Alvo, deX: number): { x: number; y: number } | null {
  if (!a) return null;
  if (!(a instanceof HTMLElement)) return a;
  if (!a.isConnected) return null;
  const r = a.getBoundingClientRect();
  if (!visivel(r)) return null;
  const vemDaEsquerda = deX <= r.left + r.width / 2;
  const x = vemDaEsquerda ? r.left - TAMANHO / 2 - 4 : r.right + TAMANHO / 2 + 4;
  return { x: preso(x, TAMANHO / 2, window.innerWidth - TAMANHO / 2), y: preso(r.top + r.height / 2, ALTURA / 2, window.innerHeight - ALTURA / 2) };
}

function resolver(p: PedidoVoo, caminho: string, id: number): Voo | null {
  const dePonto = centroDe(p.de);
  const refX = dePonto?.x ?? 0;
  const para = destinoDe(p.para, refX) ?? destinoDe(p.alternativo, refX);
  if (!para) return null; // sem alvo na tela: não voa
  const de = dePonto ?? { x: para.x - 240, y: para.y - 40 };
  const direcao = para.x >= de.x ? "direita" : "esquerda";
  const dist = Math.hypot(para.x - de.x, para.y - de.y);
  return { id, caminho, de, para, direcao, duracaoMs: Math.round(Math.min(1600, Math.max(MIN_MS, dist / 0.8))), arco: Math.min(70, dist * 0.12), aoChegar: p.aoChegar };
}

function Camada({ voo, aoFim }: { voo: Voo; aoFim: (id: number) => void }) {
  const caixa = useRef<HTMLDivElement>(null);
  const reduzido = typeof matchMedia === "function" && matchMedia("(prefers-reduced-motion: reduce)").matches;
  const [fase, setFase] = useState<"voo" | "parado" | "saindo">(reduzido ? "parado" : "voo");
  const posicionar = (x: number, y: number) => {
    if (caixa.current) caixa.current.style.transform = `translate(${x - TAMANHO / 2}px, ${y - ALTURA / 2}px)`;
  };

  useLayoutEffect(() => posicionar(reduzido ? voo.para.x : voo.de.x, reduzido ? voo.para.y : voo.de.y), [voo, reduzido]);

  useEffect(() => {
    let vivo = true;
    let quadro = 0;
    const tempos: number[] = [];
    const chegou = () => {
      if (!vivo) return;
      posicionar(voo.para.x, voo.para.y);
      setFase("parado");
      try { voo.aoChegar?.(); } catch { /* o destaque é opcional: não derruba a tela */ }
      const pairar = reduzido ? REDUZIDO_MS - SUMIR_MS : PAIRAR_MS;
      tempos.push(window.setTimeout(() => vivo && setFase("saindo"), pairar));
      tempos.push(window.setTimeout(() => vivo && aoFim(voo.id), pairar + SUMIR_MS));
    };
    if (reduzido) {
      chegou(); // sem travessia: aparece parado no destino
    } else {
      const inicio = performance.now();
      // a travessia usa requestAnimationFrame só para a posição; a batida de asa é CSS
      const passo = (agora: number) => {
        if (!vivo) return;
        const t = Math.min(1, (agora - inicio) / voo.duracaoMs);
        const suave = t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2;
        posicionar(voo.de.x + (voo.para.x - voo.de.x) * suave, voo.de.y + (voo.para.y - voo.de.y) * suave - Math.sin(Math.PI * t) * voo.arco);
        if (t < 1) quadro = requestAnimationFrame(passo); else chegou();
      };
      quadro = requestAnimationFrame(passo);
    }
    return () => { vivo = false; cancelAnimationFrame(quadro); tempos.forEach(clearTimeout); };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [voo, reduzido]);

  return (
    <div ref={caixa} className={"falcao-voante" + (fase === "saindo" ? " falcao-saindo" : "")}>
      <Falcao estado={fase === "voo" ? "voo" : "parado"} direcao={voo.direcao} tamanho={TAMANHO} />
    </div>
  );
}

/**
 * Camada de voo: o falcão atravessa a tela uma vez por ação (um voo por vez, cancelado ao trocar de página).
 * Fica acima do conteúdo e abaixo da barra do roteiro, sem capturar cliques. Deve ficar dentro do roteador.
 */
export function ProvedorFalcao({ children }: { children: ReactNode }) {
  const { pathname } = useLocation();
  const [voo, setVoo] = useState<Voo | null>(null);
  const contador = useRef(0);

  const voar = useCallback((p: PedidoVoo) => {
    const novo = resolver(p, window.location.pathname, ++contador.current);
    if (!novo) { setVoo(null); p.aoChegar?.(); return; }
    setVoo(novo); // substitui o voo em curso, se houver
  }, []);
  const cancelar = useCallback(() => setVoo(null), []);
  const aoFim = useCallback((id: number) => setVoo((v) => (v?.id === id ? null : v)), []);

  // trocar de página cancela o voo que veio da página anterior (um voo iniciado já na nova página segue)
  useEffect(() => { setVoo((v) => (v && v.caminho !== pathname ? null : v)); }, [pathname]);

  const valor = useMemo(() => ({ voar, cancelar }), [voar, cancelar]);
  // o painel da extensão é escuro: a camada herda os tokens do `.ext-tema`
  const extensao = pathname.startsWith("/extensao");
  return (
    <Contexto.Provider value={valor}>
      {children}
      <div className={"falcao-camada" + (extensao ? " ext-tema" : "")} aria-hidden="true">
        {voo && <Camada key={voo.id} voo={voo} aoFim={aoFim} />}
      </div>
    </Contexto.Provider>
  );
}
