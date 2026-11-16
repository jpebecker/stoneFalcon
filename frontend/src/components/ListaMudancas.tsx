import type { Mudanca } from "../api/cliente";

const curto = (v: unknown) => {
  if (v == null) return "—";
  const t = typeof v === "string" ? v : JSON.stringify(v);
  return t.length > 140 ? t.slice(0, 140) + "…" : t;
};

export default function ListaMudancas({ mudancas }: { mudancas: Mudanca[] }) {
  if (!mudancas.length) return <p className="text-sm text-tinta-3">Sem mudanças.</p>;
  return (
    <ul className="space-y-1.5 text-sm">
      {mudancas.map((m, i) => (
        <li key={i} className="flex gap-2">
          <span className={"selo h-fit shrink-0 " + (m.tipo === "adicionado" ? "bg-pedra-fundo text-pedra-forte"
            : m.tipo === "removido" ? "bg-erro-fundo text-erro" : "bg-info-fundo text-info")}>{m.tipo}</span>
          <span>
            <b>{m.alvo.replace("passo:", "passo ")}</b>{m.campo ? " · " + m.campo : ""}
            {m.tipo === "alterado" && <span className="text-tinta-2">: <s className="text-tinta-3">{curto(m.antes)}</s> → {curto(m.depois)}</span>}
            {m.tipo !== "alterado" && <span className="text-tinta-2"> {curto(m.depois ?? m.antes)}</span>}
          </span>
        </li>
      ))}
    </ul>
  );
}
