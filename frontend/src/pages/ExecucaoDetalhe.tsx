import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";
import { api, type Execucao, type Persona, type Saude } from "../api/cliente";
import LinhaDoTempo from "../components/LinhaDoTempo";
import { quando } from "../components/formato";

export default function ExecucaoDetalhe({ pessoa }: { pessoa: Persona }) {
  const { id } = useParams();
  const qc = useQueryClient();
  const q = useQuery({ queryKey: ["execucao", id], queryFn: () => api<Execucao>("/execucoes/" + id) });
  const saude = useQuery({ queryKey: ["saude"], queryFn: () => api<Saude>("/saude") });
  if (q.isError) return <p className="text-erro">{(q.error as Error).message}</p>;
  if (!q.data) return <p className="text-tinta-3">Carregando…</p>;
  const e = q.data;
  return (
    <div className="max-w-4xl space-y-6">
      <Link to="/execucoes" className="text-sm text-tinta-3 hover:text-tinta">← Execuções</Link>
      <div>
        <h1 className="flex items-center gap-3 text-3xl">{e.agente_nome}
          {e.rotina && <span className="selo bg-info-fundo text-info" title={e.rotina.origem === "manual" ? "Rotina: Rodar agora" : "Rotina: disparou sozinha"}>rotina</span>}</h1>
        <p className="mt-1 text-sm text-tinta-3">{e.rotina ? "Rotina, em nome de" : "Disparada por"} {e.persona} em {quando(e.inicio)} · entrada {JSON.stringify(e.entrada)}</p>
      </div>
      <LinhaDoTempo exe={e} pessoa={pessoa} cotacao={saude.data?.cotacao_dolar ?? 5.52}
        aoMudar={(nova) => { qc.setQueryData<Execucao>(["execucao", id], nova); }} />
    </div>
  );
}
