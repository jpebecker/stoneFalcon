import { useEffect, useState } from "react";
import type { Persona } from "../api/cliente";

/** Foto da persona (servida pela própria plataforma). Se não carregar, volta para as iniciais na cor dela. */
export default function Avatar({ pessoa, tamanho = 36 }: { pessoa: Pick<Persona, "iniciais" | "cor" | "nome" | "foto">; tamanho?: number }) {
  const [falhou, setFalhou] = useState(false);
  useEffect(() => setFalhou(false), [pessoa.foto]);
  const caixa = { width: tamanho, height: tamanho };
  if (pessoa.foto && !falhou) {
    return (
      <img src={pessoa.foto} alt={pessoa.nome} title={pessoa.nome} width={tamanho} height={tamanho} loading="lazy"
        onError={() => setFalhou(true)}
        className="inline-block shrink-0 rounded-full object-cover" style={{ ...caixa, background: pessoa.cor }} />
    );
  }
  return (
    <span role="img" aria-label={pessoa.nome} title={pessoa.nome}
      className="inline-flex shrink-0 items-center justify-center rounded-full font-titulo font-semibold text-white"
      style={{ ...caixa, background: pessoa.cor, fontSize: tamanho * 0.38 }}>
      {pessoa.iniciais}
    </span>
  );
}
