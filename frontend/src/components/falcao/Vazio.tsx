import { useEffect, useRef, type ReactNode } from "react";
import Falcao from "./Falcao";
import { useFalcao } from "./Voo";

/**
 * Estado vazio: o falcão parado, sem animação, ao lado da frase. Só para listas vazias (nunca para erro ou bloqueio).
 * Com `dica`, o falcão sugere o próximo passo no balão (rotina ambiente: respeita o teto de frequência e as demais regras).
 */
export default function Vazio({ children, caixa = true, className = "", dica }: { children: ReactNode; caixa?: boolean; className?: string; dica?: string }) {
  const { pedirAmbiente, falar } = useFalcao();
  const aqui = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!dica) return;
    pedirAmbiente({ id: "vazio:" + dica, prio: 1, validadeMs: 20_000, executar: () => { if (aqui.current?.isConnected) falar(dica, { alvo: aqui.current }); } });
  }, [dica, pedirAmbiente, falar]);
  return (
    <div ref={aqui} className={(caixa ? "caixa " : "") + "flex items-center gap-3 p-5 text-tinta-3 " + className}>
      <Falcao estado="estatico" tamanho={56} />
      <p>{children}</p>
    </div>
  );
}
