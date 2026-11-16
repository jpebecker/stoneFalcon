import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { api, type Execucao, type Persona, type RegistroPasso } from "../api/cliente";
import { COR_STATUS, NOME_STATUS, NOME_TIPO, ms, reais } from "./formato";

function Saida({ valor }: { valor: unknown }) {
  if (valor == null) return null;
  if (typeof valor === "string") return <p className="whitespace-pre-wrap text-sm text-tinta">{valor}</p>;
  return <pre className="max-h-56 overflow-auto rounded-lg bg-papel p-3 text-xs text-tinta-2">{JSON.stringify(valor, null, 2)}</pre>;
}

function CartaoPasso({ r, cotacao }: { r: RegistroPasso; cotacao: number }) {
  const [aberto, setAberto] = useState(false);
  return (
    <li className="caixa p-4">
      <button className="flex w-full items-center gap-3 text-left" onClick={() => setAberto(!aberto)} aria-expanded={aberto}>
        <span className={"selo " + COR_STATUS[r.status]}>{NOME_STATUS[r.status] ?? r.status}</span>
        <span className="flex-1 font-medium">{r.titulo}</span>
        <span className="text-xs text-tinta-3">{NOME_TIPO[r.tipo]}{r.modelo ? " · " + r.modelo : ""}</span>
        <span className="w-20 text-right text-xs text-tinta-3">{ms(r.duracao_estimada_ms)}</span>
      </button>
      {r.motivo && <p className="mt-2 text-sm text-falcao">{r.motivo}</p>}
      {r.ferramentas.length > 0 && (
        <ul className="mt-2 flex flex-wrap gap-1.5">
          {r.ferramentas.map((f, i) => (
            <li key={i} className={"selo " + (f.ok ? "bg-papel text-tinta-2" : f.tipo_erro === "aprovacao" ? "bg-alerta-fundo text-alerta" : "bg-erro-fundo text-erro")}
              title={f.erro ?? undefined}>
              {f.ok ? "✓" : f.tipo_erro === "aprovacao" ? "⏸" : "✕"} {f.conector}{f.tipo_erro === "aprovacao" && " · pediu confirmação"}
              {f.mascarados.length > 0 && <span className="text-pedra-forte"> · {f.mascarados.reduce((a, m) => a + m.quantidade, 0)} dado(s) mascarado(s)</span>}
              {f.suspeitas.length > 0 && <span className="text-falcao"> · conteúdo suspeito isolado</span>}
            </li>
          ))}
        </ul>
      )}
      {aberto && (
        <div className="mt-3 space-y-2 border-t border-linha pt-3">
          {r.motivos_modelo.length > 0 && (
            <p className="text-xs text-tinta-3">Por que este modelo: {r.motivos_modelo.join(", ")}.</p>
          )}
          <p className="text-xs text-tinta-3">{r.iteracoes} volta(s) de raciocínio · custo {reais(r.custo_usd * cotacao)}</p>
          <Saida valor={r.saida} />
        </div>
      )}
    </li>
  );
}

export default function LinhaDoTempo({ exe, pessoa, cotacao, aoMudar }: {
  exe: Execucao; pessoa: Persona; cotacao: number; aoMudar?: (e: Execucao) => void;
}) {
  const qc = useQueryClient();
  const passos = exe.passos_tela ?? exe.passos;
  const ordem = exe.blueprint.passos.map((p) => p.id).filter((id) => passos[id]);
  const decidir = useMutation({
    mutationFn: (aprovar: boolean) => api<Execucao>(`/execucoes/${exe.id}/decisao`, { aprovar }),
    onSuccess: (e) => { aoMudar?.(e); qc.invalidateQueries({ queryKey: ["execucoes"] }); },
  });
  const podeDecidir = exe.status === "aguardando_aprovacao" && pessoa.area === exe.area
    && (pessoa.id === exe.persona || pessoa.papeis.includes("curador"));

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-3">
        <span className={"selo text-sm " + COR_STATUS[exe.status]}>{NOME_STATUS[exe.status] ?? exe.status}</span>
        <span className="text-sm text-tinta-2">{reais(exe.custo_brl)} · {exe.chamadas_modelo} chamada(s) de modelo · {ms(exe.duracao_estimada_ms)}</span>
        {exe.simulado && <span className="selo bg-alerta-fundo text-alerta">simulado</span>}
      </div>

      {exe.status === "aguardando_aprovacao" && exe.pendencia && (
        <div className="rounded-caixa border border-alerta/40 bg-alerta-fundo/60 p-4">
          <h3 className="text-base">O agente quer: {exe.pendencia.conector_nome ?? exe.pendencia.titulo}</h3>
          {exe.pendencia.justificativa && <p className="mt-1 text-sm text-tinta-2">{exe.pendencia.justificativa}</p>}
          {exe.pendencia.entrada && <pre className="mt-2 rounded-lg bg-folha p-2 text-xs">{JSON.stringify(exe.pendencia.entrada, null, 2)}</pre>}
          {podeDecidir ? (
            <div className="mt-3 flex gap-2">
              <button className="botao-pedra" disabled={decidir.isPending} onClick={() => decidir.mutate(true)}>Confirmar ação</button>
              <button className="botao-claro" disabled={decidir.isPending} onClick={() => decidir.mutate(false)}>Recusar</button>
            </div>
          ) : <p className="mt-2 text-sm text-tinta-3">Só quem disparou o agente ou um curador da área pode decidir.</p>}
          {decidir.isError && <p className="mt-2 text-sm text-erro">{(decidir.error as Error).message}</p>}
        </div>
      )}
      {exe.status === "escalada" && exe.motivo && (
        <div className="rounded-caixa border border-falcao/30 bg-falcao-fundo/60 p-4 text-sm">
          <b>O agente parou com segurança e passou o caso para um humano.</b> {exe.motivo}
        </div>
      )}

      <ol className="space-y-2">
        {ordem.map((id) => <CartaoPasso key={id} r={passos[id]} cotacao={cotacao} />)}
      </ol>

      {(exe.resultado_tela ?? exe.resultado) && (
        <div className="caixa p-4">
          <h3 className="mb-1 text-sm font-semibold uppercase tracking-wide text-tinta-3">Resultado</h3>
          <p className="whitespace-pre-wrap text-sm">{exe.resultado_tela ?? exe.resultado}</p>
        </div>
      )}
    </div>
  );
}
