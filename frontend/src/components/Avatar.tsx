import type { Persona } from "../api/cliente";

export default function Avatar({ pessoa, tamanho = 36 }: { pessoa: Pick<Persona, "iniciais" | "cor" | "nome">; tamanho?: number }) {
  return (
    <span aria-hidden="true" title={pessoa.nome}
      className="inline-flex shrink-0 items-center justify-center rounded-full font-titulo font-semibold text-white"
      style={{ width: tamanho, height: tamanho, background: pessoa.cor, fontSize: tamanho * 0.38 }}>
      {pessoa.iniciais}
    </span>
  );
}
