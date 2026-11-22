import Falcao from "./Falcao";

/**
 * Estado de carga: o falcão paira ao lado do texto de status. A região fica sempre montada (para o leitor de
 * tela anunciar a mudança) e só ocupa espaço enquanto `ativo`. O botão da ação continua desabilitado, com o mesmo texto.
 */
export default function Carregando({ ativo, texto, tamanho = 48, className = "" }: { ativo: boolean; texto: string; tamanho?: number; className?: string }) {
  return (
    <div role="status" aria-live="polite" aria-busy={ativo} className={ativo ? "flex shrink-0 items-center gap-2 whitespace-nowrap text-sm text-tinta-2 " + className : "sr-only"}>
      {ativo && <Falcao estado="parado" tamanho={tamanho} />}
      {ativo ? texto : ""}
    </div>
  );
}
