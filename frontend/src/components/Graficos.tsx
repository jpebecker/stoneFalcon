// Gráficos em SVG puro, seguindo as regras de dataviz do projeto:
// marcas finas, 2px de respiro entre segmentos, eixos discretos, legenda sempre presente
// com 2+ séries, tooltip ao passar o mouse e tabela como alternativa acessível.
import { useState } from "react";

type Serie = { chave: string; nome: string; cor: string };

function Legenda({ series }: { series: Serie[] }) {
  return (
    <ul className="flex flex-wrap gap-4 text-xs text-tinta-2">
      {series.map((s) => (
        <li key={s.chave} className="flex items-center gap-1.5">
          <span className="h-2.5 w-2.5 rounded-sm" style={{ background: s.cor }} />{s.nome}
        </li>
      ))}
    </ul>
  );
}

function Dica({ fracao, children }: { fracao: number; children: React.ReactNode }) {
  // fracao: posição horizontal (0 a 1) do ponto em foco; a dica abre para o lado com mais espaço
  const direita = fracao > 0.65;
  return (
    <div className="pointer-events-none absolute top-2 z-10 min-w-[150px] rounded-lg border border-linha bg-folha px-3 py-2 text-xs shadow-caixa"
      style={direita ? { right: `calc(${(1 - fracao) * 100}% + 12px)` } : { left: `calc(${fracao * 100}% + 12px)` }}>
      {children}
    </div>
  );
}

export function BarrasEmpilhadas<T extends Record<string, number | string>>({ dados, rotulo, series, formatar, formatarEixo, titulo }: {
  dados: T[]; rotulo: (d: T) => string; series: Serie[]; formatar: (v: number) => string; formatarEixo?: (v: number) => string; titulo: string;
}) {
  const [foco, setFoco] = useState<number | null>(null);
  const [tabela, setTabela] = useState(false);
  const L = 760, A = 220, me = 64, mb = 26, mt = 8;
  const eixo = formatarEixo ?? formatar;
  const total = (d: T) => series.reduce((s, x) => s + Number(d[x.chave] || 0), 0);
  const max = Math.max(...dados.map(total), 0) || 1;
  const largura = (L - me) / Math.max(dados.length, 1);
  const barra = Math.max(3, Math.min(22, largura - 4));
  const y = (v: number) => mt + (A - mt - mb) * (1 - v / max);
  const ticks = [0, 0.5, 1].map((f) => max * f);

  return (
    <figure className="space-y-3">
      <div className="flex items-center justify-between gap-3">
        <figcaption className="text-sm font-semibold">{titulo}</figcaption>
        <div className="flex items-center gap-4">
          <Legenda series={series} />
          <button className="text-xs font-semibold text-tinta-3 hover:text-tinta" onClick={() => setTabela(!tabela)}>
            {tabela ? "Ver gráfico" : "Ver tabela"}
          </button>
        </div>
      </div>
      {tabela ? (
        <div className="max-h-64 overflow-auto rounded-lg border border-linha">
          <table className="w-full text-xs">
            <thead className="bg-papel text-left text-tinta-3"><tr><th className="px-3 py-1.5">Dia</th>{series.map((s) => <th key={s.chave} className="px-3 py-1.5 text-right">{s.nome}</th>)}<th className="px-3 py-1.5 text-right">Total</th></tr></thead>
            <tbody>{dados.map((d, i) => (
              <tr key={i} className="border-t border-linha"><td className="px-3 py-1">{rotulo(d)}</td>{series.map((s) => <td key={s.chave} className="px-3 py-1 text-right">{formatar(Number(d[s.chave] || 0))}</td>)}<td className="px-3 py-1 text-right font-semibold">{formatar(total(d))}</td></tr>
            ))}</tbody>
          </table>
        </div>
      ) : (
        <div className="relative">
          <svg viewBox={`0 0 ${L} ${A}`} className="w-full" role="img" aria-label={titulo} onMouseLeave={() => setFoco(null)}>
            {ticks.map((t) => (
              <g key={t}>
                <line x1={me} x2={L} y1={y(t)} y2={y(t)} stroke="rgb(var(--linha))" />
                <text x={me - 8} y={y(t) + 4} textAnchor="end" fontSize="11" fill="rgb(var(--tinta-3))">{eixo(t)}</text>
              </g>
            ))}
            {dados.map((d, i) => {
              const cx = me + i * largura + largura / 2;
              let base = 0;
              const partes = series.map((s, k) => {
                const v = Number(d[s.chave] || 0);
                const y0 = y(base), y1 = y(base + v);
                base += v;
                const topo = k === series.length - 1 || series.slice(k + 1).every((x) => !Number(d[x.chave]));
                const h = Math.max(0, y0 - y1 - (k > 0 ? 2 : 0));   // 2px de respiro entre segmentos
                if (v <= 0 || h <= 0) return null;
                return <rect key={s.chave} x={cx - barra / 2} y={y1} width={barra} height={h} rx={topo ? 3 : 0} fill={s.cor}
                  opacity={foco === null || foco === i ? 1 : 0.45} />;
              });
              return (
                <g key={i}>
                  {partes}
                  <rect x={cx - largura / 2} y={mt} width={largura} height={A - mt - mb} fill="transparent" onMouseEnter={() => setFoco(i)} />
                  {(i === 0 || i === dados.length - 1 || i % Math.ceil(dados.length / 6) === 0) && (
                    <text x={cx} y={A - 8} textAnchor="middle" fontSize="11" fill="rgb(var(--tinta-3))">{rotulo(d)}</text>
                  )}
                </g>
              );
            })}
          </svg>
          {foco !== null && dados[foco] && (
            <Dica fracao={(me + foco * largura + largura / 2) / L}>
              <div className="mb-1 font-semibold">{rotulo(dados[foco])}</div>
              {series.map((s) => (
                <div key={s.chave} className="flex items-center justify-between gap-4">
                  <span className="flex items-center gap-1.5 text-tinta-2"><span className="h-2 w-2 rounded-sm" style={{ background: s.cor }} />{s.nome}</span>
                  <span>{formatar(Number(dados[foco][s.chave] || 0))}</span>
                </div>
              ))}
              <div className="mt-1 flex justify-between border-t border-linha pt-1 font-semibold"><span>Total</span><span>{formatar(total(dados[foco]))}</span></div>
            </Dica>
          )}
        </div>
      )}
    </figure>
  );
}

export function LinhaAcumulada({ pontos, marco, titulo, formatar }: {
  pontos: { x: number; y: number }[]; marco?: number | null; titulo: string; formatar: (v: number) => string;
}) {
  const [foco, setFoco] = useState<number | null>(null);
  const L = 760, A = 240, me = 64, mb = 26, mt = 10;
  const ys = pontos.map((p) => p.y);
  const min = Math.min(0, ...ys), max = Math.max(0, ...ys);
  const amp = max - min || 1;
  const px = (i: number) => me + (L - me - 10) * (i / Math.max(pontos.length - 1, 1));
  const py = (v: number) => mt + (A - mt - mb) * (1 - (v - min) / amp);
  const caminho = pontos.map((p, i) => `${i ? "L" : "M"}${px(i)},${py(p.y)}`).join(" ");
  const iMarco = marco ? pontos.findIndex((p) => p.x === marco) : -1;

  return (
    <figure className="space-y-2">
      <figcaption className="text-sm font-semibold">{titulo}</figcaption>
      <div className="relative">
        <svg viewBox={`0 0 ${L} ${A}`} className="w-full" role="img" aria-label={titulo}
          onMouseMove={(e) => {
            const r = (e.currentTarget as SVGSVGElement).getBoundingClientRect();
            const x = ((e.clientX - r.left) / r.width) * L;
            setFoco(Math.max(0, Math.min(pontos.length - 1, Math.round(((x - me) / (L - me - 10)) * (pontos.length - 1)))));
          }} onMouseLeave={() => setFoco(null)}>
          {[min, (min + max) / 2, max].map((t, k) => (
            <g key={k}>
              <line x1={me} x2={L} y1={py(t)} y2={py(t)} stroke="rgb(var(--linha))" />
              <text x={me - 8} y={py(t) + 4} textAnchor="end" fontSize="11" fill="rgb(var(--tinta-3))">{formatar(t)}</text>
            </g>
          ))}
          <line x1={me} x2={L} y1={py(0)} y2={py(0)} stroke="rgb(var(--tinta-3))" strokeDasharray="4 4" />
          <path d={caminho} fill="none" stroke="var(--serie-1)" strokeWidth="2" strokeLinejoin="round" />
          {iMarco >= 0 && (
            <g>
              <line x1={px(iMarco)} x2={px(iMarco)} y1={mt} y2={A - mb} stroke="rgb(var(--pedra))" strokeDasharray="3 3" />
              <circle cx={px(iMarco)} cy={py(pontos[iMarco].y)} r="5" fill="rgb(var(--pedra))" stroke="white" strokeWidth="2" />
              <text x={px(iMarco) + 8} y={mt + 12} fontSize="11" fontWeight="600" fill="rgb(var(--pedra-forte))">payback no mês {marco}</text>
            </g>
          )}
          {pontos.map((p, i) => (i % 6 === 0 || i === pontos.length - 1) && (
            <text key={i} x={px(i)} y={A - 8} textAnchor={i === pontos.length - 1 ? "end" : i === 0 ? "start" : "middle"} fontSize="11" fill="rgb(var(--tinta-3))">mês {p.x}</text>
          ))}
          {foco !== null && (
            <g>
              <line x1={px(foco)} x2={px(foco)} y1={mt} y2={A - mb} stroke="rgb(var(--tinta-3))" />
              <circle cx={px(foco)} cy={py(pontos[foco].y)} r="4" fill="var(--serie-1)" stroke="white" strokeWidth="2" />
            </g>
          )}
        </svg>
        {foco !== null && (
          <Dica fracao={px(foco) / L}>
            <div className="font-semibold">Mês {pontos[foco].x}</div>
            <div className="text-tinta-2">Resultado acumulado: <b className="text-tinta">{formatar(pontos[foco].y)}</b></div>
          </Dica>
        )}
      </div>
    </figure>
  );
}
