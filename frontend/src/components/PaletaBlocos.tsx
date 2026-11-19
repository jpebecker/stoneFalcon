import type { TipoBloco } from "../api/cliente";
import { BLOCOS } from "./formato";

const ORDEM: (TipoBloco | "entrada")[] = ["entrada", "dados", "agente", "plugin", "aprovacao", "condicao", "saida"];

/** A paleta: os 7 tipos de bloco, cada um com ícone, cor e uma frase. "Entradas" já existe em todo processo: clicar nele o seleciona. */
export default function PaletaBlocos({ aoAdicionar, aoSelecionarEntradas }: {
  aoAdicionar: (tipo: TipoBloco) => void; aoSelecionarEntradas: () => void;
}) {
  return (
    <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-4 xl:grid-cols-7" data-testid="paleta" role="group" aria-label="Paleta de blocos">
      {ORDEM.map((t) => {
        const b = BLOCOS[t];
        return (
          <button key={t} type="button" data-testid={"paleta-" + t} title={b.descricao}
            className={"caixa border-l-4 p-2.5 text-left transition hover:border-pedra " + b.cor}
            onClick={() => (t === "entrada" ? aoSelecionarEntradas() : aoAdicionar(t))}>
            <span className="flex items-center gap-1.5 text-sm font-semibold"><span aria-hidden="true">{b.icone}</span>{b.nome}</span>
            <span className="mt-0.5 block text-[11px] leading-snug text-tinta-3">{b.descricao}</span>
          </button>
        );
      })}
    </div>
  );
}
