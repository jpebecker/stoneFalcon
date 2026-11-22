import Falcao from "./Falcao";
import { useFalcao } from "./Voo";

/**
 * O poleiro: o falcão parado ao lado da marca, no menu escuro. É de onde ele sai para os voos e para onde o recado do balão
 * aponta. Enquanto ele voa a camada de voo, o poleiro fica vazio; quando o voo acaba, ele volta. Sempre `aria-hidden`.
 */
export default function Poleiro({ className = "" }: { className?: string }) {
  const { emVoo } = useFalcao();
  return (
    <div data-alvo="poleiro" aria-hidden="true" data-testid="poleiro" data-em-voo={emVoo}
      className={"transition-opacity duration-200 motion-reduce:transition-none " + (emVoo ? "opacity-0 " : "opacity-100 ") + className}>
      <Falcao estado="estatico" direcao="esquerda" claro tamanho={38} />
    </div>
  );
}
