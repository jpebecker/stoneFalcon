/** Selo "simulado": aparece em todo lugar onde um modelo que não roda de verdade (todos, exceto o Claude) é mostrado. */
export default function SeloSimulado({ className = "" }: { className?: string }) {
  return (
    <span className={"selo bg-alerta-fundo text-alerta " + className} title="Modelo simulado: sem chamada real, custo estimado pela tabela pública de preços">
      simulado
    </span>
  );
}
