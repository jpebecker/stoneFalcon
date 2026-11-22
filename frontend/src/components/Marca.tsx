import { ROSTO } from "./falcao/quadros";

/** Marca do sistema: o rosto do falcão (sempre visível), sobre quadrado escuro; com `claro`, sobre fundo translúcido (menu escuro). */
export default function Marca({ claro = false }: { claro?: boolean }) {
  return (
    <div className="flex items-center gap-2.5 px-1">
      <svg viewBox="0 0 64 64" className="h-8 w-8" aria-hidden="true" data-alvo="marca">
        <rect width="64" height="64" rx="16" fill={claro ? "#ffffff14" : "#10201A"} />
        <path fill="#E0428F" d={ROSTO.rosas} />
        <path fill="#1FB37A" d={ROSTO.verdes} />
        <path fill="#E8F3EE" d={ROSTO.claros} />
      </svg>
      <span className={"font-titulo text-xl font-semibold tracking-tight " + (claro ? "text-white" : "text-tinta")}>
        StoneFalcon
      </span>
    </div>
  );
}
