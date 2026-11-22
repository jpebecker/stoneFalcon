import { useEffect, useRef, useState, type KeyboardEvent } from "react";
import type { Persona } from "../api/cliente";

/** Seletor radial de persona: um anel dividido em fatias iguais, uma por pessoa, cada uma com a foto.
 *  Passar o mouse (ou focar com o teclado) expande a fatia e mostra os detalhes da pessoa no centro. */

export const PAPEL: Record<string, string> = {
  criador: "cria agentes", curador: "aprova conhecimento", revisor_seguranca: "revisa segurança",
  engenharia: "mantém o catálogo", gestor_ia: "vê custos e auditoria", ai_analyst: "analisa plugins de IA",
};

const T = 720;                 // lado do desenho (unidades do SVG)
const C = T / 2;               // centro
const R_EXT = 320;             // raio externo da fatia em repouso
const R_INT = 190;             // raio interno (o miolo com os detalhes fica por dentro)
const FOLGA = 1.2;             // graus entre fatias

const rad = (g: number) => (g * Math.PI) / 180;
const pt = (r: number, g: number) => `${(C + r * Math.cos(rad(g))).toFixed(2)} ${(C + r * Math.sin(rad(g))).toFixed(2)}`;

/** Caminho de um setor de anel entre os ângulos a0 e a1 (graus, sentido horário a partir do eixo x). */
export function caminhoFatia(a0: number, a1: number, rExt = R_EXT, rInt = R_INT): string {
  const grande = a1 - a0 > 180 ? 1 : 0;
  return `M ${pt(rExt, a0)} A ${rExt} ${rExt} 0 ${grande} 1 ${pt(rExt, a1)} L ${pt(rInt, a1)} A ${rInt} ${rInt} 0 ${grande} 0 ${pt(rInt, a0)} Z`;
}

type Props = {
  pessoas: Persona[];
  iniciando: string | null;
  aoEntrar: (id: string) => void;
  aoIniciarRoteiro: (p: Persona) => void;
};

export default function RodaPersonas({ pessoas, iniciando, aoEntrar, aoIniciarRoteiro }: Props) {
  const [ativo, setAtivo] = useState<number | null>(null);      // fatia mostrada no miolo (mouse ou foco)
  const [focado, setFocado] = useState<number | null>(null);    // fatia com o foco do teclado
  const [tab, setTab] = useState(0);                            // única fatia na ordem do Tab (roving tabindex)
  const [semFoto, setSemFoto] = useState<Record<string, boolean>>({});
  const fatias = useRef<(SVGGElement | null)[]>([]);
  const raiz = useRef<HTMLDivElement>(null);
  const timer = useRef<number | undefined>(undefined);
  const n = pessoas.length;

  useEffect(() => () => window.clearTimeout(timer.current), []);

  const mostrar = (i: number) => { window.clearTimeout(timer.current); setAtivo(i); };
  const agendarNeutro = () => {
    window.clearTimeout(timer.current);
    // pequena espera: ao atravessar a folga entre fatias (ou ir da fatia ao miolo) o centro não pisca
    timer.current = window.setTimeout(() => setAtivo(focado), 140);
  };

  const teclas = (e: KeyboardEvent, i: number) => {
    const ir = (j: number) => { e.preventDefault(); const k = (j + n) % n; setTab(k); fatias.current[k]?.focus(); };
    if (e.key === "ArrowRight" || e.key === "ArrowDown") ir(i + 1);
    else if (e.key === "ArrowLeft" || e.key === "ArrowUp") ir(i - 1);
    else if (e.key === "Home") ir(0);
    else if (e.key === "End") ir(n - 1);
    else if (e.key === "Enter" || e.key === " ") { e.preventDefault(); aoEntrar(pessoas[i].id); }
  };

  const p = ativo !== null ? pessoas[ativo] : null;
  const passo = 360 / Math.max(n, 1);

  return (
    <div ref={raiz} className="roda relative mx-auto aspect-square" data-testid="roda-personas"
      style={{ width: "min(100%, 46rem, calc(100vh - 13rem))", minWidth: "28rem" }}
      onBlur={(e) => { if (!raiz.current?.contains(e.relatedTarget as Node)) { setFocado(null); agendarNeutro(); } }}>
      <svg viewBox={`0 0 ${T} ${T}`} className="absolute inset-0 h-full w-full" role="group" aria-label="Escolha quem é você hoje">
        <defs>
          {pessoas.map((x, i) => {
            const c = -90 + i * passo;
            return <clipPath key={x.id} id={`roda-clip-${x.id}`}><path d={caminhoFatia(c - passo / 2 + FOLGA, c + passo / 2 - FOLGA)} /></clipPath>;
          })}
        </defs>
        {pessoas.map((x, i) => {
          const c = -90 + i * passo;
          const a0 = c - passo / 2 + FOLGA, a1 = c + passo / 2 - FOLGA;
          const meio = (R_EXT + R_INT) / 2;
          const [mx, my] = [C + meio * Math.cos(rad(c)), C + meio * Math.sin(rad(c))];
          const estado = ativo === i ? "ativa" : ativo !== null ? "vizinha" : "";
          const falhou = !x.foto || semFoto[x.id];
          return (
            <g key={x.id} ref={(el) => { fatias.current[i] = el; }} className={`roda-fatia ${estado}`}
              role="button" tabIndex={i === tab ? 0 : -1}
              aria-label={`${x.nome}, ${x.cargo}, ${x.area_nome}. Entrar como ${x.nome}`}
              data-testid={`fatia-${x.id}`}
              onMouseEnter={() => mostrar(i)} onMouseLeave={agendarNeutro}
              onFocus={() => { setFocado(i); setTab(i); mostrar(i); }}
              onKeyDown={(e) => teclas(e, i)} onClick={() => aoEntrar(x.id)}>
              <path className="roda-forma" d={caminhoFatia(a0, a1)} fill={x.cor} />
              {!falhou && (
                <image href={x.foto} x={mx - 150} y={my - 150} width={300} height={300} preserveAspectRatio="xMidYMid slice"
                  clipPath={`url(#roda-clip-${x.id})`} onError={() => setSemFoto((s) => ({ ...s, [x.id]: true }))} />
              )}
              {falhou && (
                <text x={mx} y={my} textAnchor="middle" dominantBaseline="central" className="roda-iniciais">{x.iniciais}</text>
              )}
              <path className="roda-sombra" d={caminhoFatia(a0, a1)} />
            </g>
          );
        })}
      </svg>

      <div className="absolute left-1/2 top-1/2 flex -translate-x-1/2 -translate-y-1/2 flex-col items-center justify-center rounded-full border border-linha bg-folha px-6 text-center shadow-caixa"
        style={{ width: `${(2 * (R_INT - 10) / T) * 100}%`, height: `${(2 * (R_INT - 10) / T) * 100}%` }}
        onMouseEnter={() => window.clearTimeout(timer.current)} onMouseLeave={agendarNeutro} aria-live="polite" data-testid="roda-miolo">
        {p ? (
          <>
            <div className="font-titulo text-xl font-semibold leading-tight">{p.nome}</div>
            <div className="mt-0.5 text-xs text-tinta-2">{p.cargo} · {p.area_nome}</div>
            <p className="mt-2 line-clamp-2 text-xs text-tinta-2">{p.descricao}</p>
            <div className="mt-2 flex justify-center">
              <span className="selo bg-info-fundo text-info">acesso {p.nivel}</span>
            </div>
            {p.roteiro_id && (
              <button className="botao-pedra mt-3 !px-3 !py-1.5 !text-xs" disabled={!!iniciando} onClick={() => aoIniciarRoteiro(p)}>
                {iniciando === p.id ? "Preparando…" : "Iniciar roteiro guiado"}
              </button>
            )}
          </>
        ) : (
          <>
            <div className="font-titulo text-2xl font-semibold leading-tight">Quem é você hoje?</div>
            <p className="mt-2 text-xs text-tinta-3">Passe o mouse sobre uma foto para ver quem é. Clique para entrar.</p>
          </>
        )}
      </div>
    </div>
  );
}
