import { useEffect, useLayoutEffect, useRef, useState } from "react";
import type { Alvo } from "./Voo";

/** Uma fala do falcão: o texto, onde ele está (o poleiro, se não disser) e quanto tempo fica na tela. */
export interface Fala { id: number; texto: string; alvo?: Alvo; ms: number }

type Lado = "direita" | "abaixo" | "acima" | "esquerda";
const FOLGA = 12;
const MARGEM = 8;

/** Tempo na tela: o bastante para ler uma frase curta, sem prender a atenção. */
export const tempoDaFala = (texto: string) => Math.min(10_000, Math.max(5_000, 3_500 + texto.length * 60));

const cruza = (a: DOMRect, b: DOMRect, folga = 6) =>
  a.left < b.right + folga && a.right > b.left - folga && a.top < b.bottom + folga && a.bottom > b.top - folga;

/** O retângulo do que a fala aponta: um elemento, um ponto ou, sem nada, o poleiro. Sem poleiro na tela, o canto de cima. */
function ancora(alvo: Alvo): DOMRect {
  const el = alvo instanceof Element ? alvo : !alvo ? document.querySelector('[data-alvo="poleiro"]') : null;
  if (el && el.isConnected) { const r = el.getBoundingClientRect(); if (r.width + r.height > 0) return r; }
  if (alvo && !(alvo instanceof Element)) return new DOMRect(alvo.x, alvo.y, 0, 0);
  return new DOMRect(MARGEM, MARGEM, 0, 0);
}

/** O primeiro lado onde a fala cabe na janela e não cobre o botão da ação da tela (`data-alvo="acao-..."`) nem o próprio alvo. */
function posicionar(a: DOMRect, larg: number, alt: number): { x: number; y: number; lado: Lado } {
  const acoes = [...document.querySelectorAll('[data-alvo^="acao-"]')].map((e) => e.getBoundingClientRect()).filter((r) => r.width + r.height > 0);
  const candidatos: { x: number; y: number; lado: Lado }[] = [
    { lado: "direita", x: a.right + FOLGA, y: a.top + a.height / 2 - alt / 2 },
    { lado: "abaixo", x: a.left + a.width / 2 - larg / 2, y: a.bottom + FOLGA },
    { lado: "acima", x: a.left + a.width / 2 - larg / 2, y: a.top - alt - FOLGA },
    { lado: "esquerda", x: a.left - larg - FOLGA, y: a.top + a.height / 2 - alt / 2 },
  ];
  const cabe = (c: { x: number; y: number }) => c.x >= MARGEM && c.y >= MARGEM && c.x + larg <= innerWidth - MARGEM && c.y + alt <= innerHeight - MARGEM;
  const livre = (c: { x: number; y: number }) => {
    const r = new DOMRect(c.x, c.y, larg, alt);
    return !acoes.some((x) => cruza(r, x)) && !(a.width + a.height > 0 && cruza(r, a, 2));
  };
  const escolhido = candidatos.find((c) => cabe(c) && livre(c)) ?? candidatos.find(cabe) ?? candidatos[0];
  return { ...escolhido, x: Math.min(Math.max(escolhido.x, MARGEM), Math.max(MARGEM, innerWidth - larg - MARGEM)), y: Math.min(Math.max(escolhido.y, MARGEM), Math.max(MARGEM, innerHeight - alt - MARGEM)) };
}

/**
 * O balão de fala do falcão: texto curto junto de onde ele está. Fica na região `role="status"` (anunciada com educação pelo
 * leitor de tela, sem tirar o foco de ninguém), some sozinho, pode ser dispensado (botão ou Esc) e nunca cobre o botão
 * da ação da tela: se o lugar de costume cobriria, escolhe outro lado. Com o ponteiro ou o foco em cima, não some.
 */
export default function Balao({ fala, aoFechar }: { fala: Fala | null; aoFechar: () => void }) {
  const caixa = useRef<HTMLDivElement>(null);
  const [pos, setPos] = useState<{ x: number; y: number; lado: Lado } | null>(null);
  const [parado, setParado] = useState(false);

  useLayoutEffect(() => {
    if (!fala || !caixa.current) { setPos(null); return; }
    const refazer = () => { if (caixa.current) setPos(posicionar(ancora(fala.alvo), caixa.current.offsetWidth, caixa.current.offsetHeight)); };
    refazer();
    addEventListener("resize", refazer);
    return () => removeEventListener("resize", refazer);
  }, [fala]);

  useEffect(() => {
    if (!fala || parado) return;
    const t = window.setTimeout(aoFechar, fala.ms);
    return () => clearTimeout(t);
  }, [fala, parado, aoFechar]);

  useEffect(() => {
    if (!fala) return;
    const esc = (e: KeyboardEvent) => { if (e.key === "Escape") aoFechar(); };
    addEventListener("keydown", esc);
    return () => removeEventListener("keydown", esc);
  }, [fala, aoFechar]);

  return (
    <div className="falcao-balao-camada">
      <div role="status" aria-live="polite" aria-atomic="true">
        {fala && (
          <div ref={caixa} className="falcao-balao" data-lado={pos?.lado} data-testid="balao-falcao"
            style={{ transform: `translate(${pos?.x ?? -9999}px, ${pos?.y ?? -9999}px)`, visibility: pos ? "visible" : "hidden" }}
            onMouseEnter={() => setParado(true)} onMouseLeave={() => setParado(false)} onFocus={() => setParado(true)} onBlur={() => setParado(false)}>
            <p>{fala.texto}</p>
            <button type="button" className="falcao-balao-fechar" onClick={aoFechar} aria-label="Dispensar o recado do falcão">×</button>
          </div>
        )}
      </div>
    </div>
  );
}
