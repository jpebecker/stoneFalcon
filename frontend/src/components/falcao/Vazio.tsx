import type { ReactNode } from "react";
import Falcao from "./Falcao";

/** Estado vazio: o falcão parado, sem animação, ao lado da frase. Só para listas vazias (nunca para erro ou bloqueio). */
export default function Vazio({ children, caixa = true, className = "" }: { children: ReactNode; caixa?: boolean; className?: string }) {
  return (
    <div className={(caixa ? "caixa " : "") + "flex items-center gap-3 p-5 text-tinta-3 " + className}>
      <Falcao estado="estatico" tamanho={56} />
      <p>{children}</p>
    </div>
  );
}
