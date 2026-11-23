import type { Alerta } from "../api/cliente";

type Severidade = Alerta["severidade"];

/** A cor e o rótulo de cada gravidade de alerta, num lugar só (a página de Alertas e o card do Início usam os mesmos). */
const SEVERIDADES: Record<Severidade, { rotulo: string; selo: string; borda: string }> = {
  critico: { rotulo: "Crítico", selo: "bg-erro-fundo text-erro", borda: "border-l-erro" },
  atencao: { rotulo: "Atenção", selo: "bg-alerta-fundo text-alerta", borda: "border-l-alerta" },
};

export function bordaDaSeveridade(s: Severidade): string {
  return SEVERIDADES[s].borda;
}

export default function SeloSeveridade({ severidade }: { severidade: Severidade }) {
  const s = SEVERIDADES[severidade];
  return <span className={"selo " + s.selo}>{s.rotulo}</span>;
}
