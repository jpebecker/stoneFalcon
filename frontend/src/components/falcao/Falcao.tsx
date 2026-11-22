import { QUADRO, QUADROS, type Animacao, type Peso } from "./quadros";

export type EstadoFalcao = "parado" | "voo" | "estatico";

/** Peso do traço pelo tamanho (largura em px): até 48 px engrossa 1,7; até 72 px, 1,3; acima disso, 1. */
export function pesoDoTamanho(tamanho: number): Peso {
  return tamanho <= 48 ? "1.7" : tamanho <= 72 ? "1.3" : "1";
}

/**
 * O corpo do falcão, de perfil. Os quadros ficam lado a lado numa tira que desliza dentro de uma janela de um
 * quadro (CSS `steps()`), então o desenho é todo vetorial e muda de cor pelas variáveis do `.falcao`.
 *
 * - `parado`: paira no lugar (6 quadros, 1,1 s). `voo`: batida completa com rastro (8 quadros, 0,56 s).
 * - `estatico`: primeiro quadro do pairar, sem animação (estados vazios).
 * - `direcao="esquerda"` espelha o desenho. `claro`: cores para o menu escuro.
 * - `aria-hidden`: o falcão nunca é a única informação. Com movimento reduzido, mostra o primeiro quadro, parado.
 *
 * `tamanho` é a largura em px; a altura segue a proporção do quadro (128 × 112).
 */
export default function Falcao({ estado = "parado", direcao = "direita", tamanho = 48, claro = false, className = "" }: {
  estado?: EstadoFalcao;
  direcao?: "direita" | "esquerda";
  tamanho?: number;
  claro?: boolean;
  className?: string;
}) {
  const animacao: Animacao = estado === "voo" ? "voo" : "parado";
  const quadros = QUADROS[animacao][pesoDoTamanho(tamanho)];
  const alturaPx = (tamanho * QUADRO.altura) / QUADRO.largura;
  const mostrar = estado === "estatico" ? quadros.slice(0, 1) : quadros;
  return (
    <svg
      viewBox={`0 0 ${QUADRO.largura} ${QUADRO.altura}`} width={tamanho} height={alturaPx} aria-hidden="true" focusable="false"
      className={["falcao", claro ? "falcao-claro" : "", direcao === "esquerda" ? "falcao-esquerda" : "", className].filter(Boolean).join(" ")}
      data-estado={estado}
    >
      <g className={estado === "estatico" ? "" : "falcao-tira falcao-tira-" + animacao}>
        {mostrar.map((q, i) => (
          <g key={i} transform={i ? `translate(${i * QUADRO.largura} 0)` : undefined}>
            {q.rastro && <path className="falcao-rastro" d={q.rastro} />}
            <path className="falcao-pena" d={q.rosas} />
            <path className="falcao-traco" d={q.verdes} />
          </g>
        ))}
      </g>
    </svg>
  );
}
