import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link } from "react-router-dom";
import { api, type Alerta } from "../api/cliente";
import { quando } from "../components/formato";

export default function Alertas() {
  const qc = useQueryClient();
  const [abertos, setAbertos] = useState(true);
  const q = useQuery({ queryKey: ["alertas", abertos], queryFn: () => api<Alerta[]>("/alertas?abertos=" + abertos), refetchInterval: 15000 });
  const ler = useMutation({
    mutationFn: (id: string) => api(`/alertas/${id}/lido`, {}),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["alertas"] }); qc.invalidateQueries({ queryKey: ["notificacoes"] }); },
  });
  return (
    <div className="max-w-4xl space-y-6">
      <div className="flex items-end justify-between gap-4">
        <div>
          <h1 className="text-3xl">Alertas</h1>
          <p className="mt-1 text-tinta-2">Avisos automáticos sobre os agentes e processos pelos quais você responde.</p>
        </div>
        <div className="flex rounded-lg border border-linha bg-folha p-0.5 text-sm">
          {[true, false].map((v) => (
            <button key={String(v)} onClick={() => setAbertos(v)}
              className={"rounded-md px-3 py-1 " + (abertos === v ? "bg-tinta text-white" : "text-tinta-2")}>
              {v ? "Abertos" : "Todos"}
            </button>
          ))}
        </div>
      </div>
      {q.data?.length === 0 && <p className="caixa p-5 text-tinta-3">Tudo certo por aqui.</p>}
      <ul className="space-y-3">
        {q.data?.map((a) => (
          <li key={a.id} className={"caixa border-l-4 p-4 " + (a.resolvido_em ? "border-l-linha opacity-70" : a.severidade === "critico" ? "border-l-erro" : "border-l-alerta")}>
            <div className="flex flex-wrap items-center gap-2">
              <span className={"selo " + (a.severidade === "critico" ? "bg-erro-fundo text-erro" : "bg-alerta-fundo text-alerta")}>
                {a.severidade === "critico" ? "Crítico" : "Atenção"}
              </span>
              {a.resolvido_em && <span className="selo bg-pedra-fundo text-pedra-forte">Resolvido</span>}
              {!a.lido && !a.resolvido_em && <span className="h-2 w-2 rounded-full bg-falcao" aria-label="não lido" />}
              <h2 className="text-base">{a.titulo}</h2>
              <span className="ml-auto text-xs text-tinta-3">{quando(a.aberto_em)}{a.ocorrencias > 1 ? ` · ${a.ocorrencias} atualizações` : ""}</span>
            </div>
            <p className="mt-1.5 text-sm text-tinta-2">{a.detalhe}</p>
            <div className="mt-2 flex gap-3 text-sm">
              {a.agente_id && <Link to={"/agentes/" + a.agente_id} className="font-semibold text-pedra-forte">Abrir o agente</Link>}
              {a.processo_id && <Link to={"/processos/" + a.processo_id} className="font-semibold text-pedra-forte">Abrir o processo</Link>}
              {!a.lido && <button className="font-semibold text-tinta-2 hover:text-tinta" onClick={() => ler.mutate(a.id)}>Marcar como lido</button>}
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
