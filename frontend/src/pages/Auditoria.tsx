import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Link } from "react-router-dom";
import { api, type EventoAuditoria } from "../api/cliente";
import { NOME_EVENTO, quando } from "../components/formato";

type Resposta = { eventos: EventoAuditoria[]; cadeia: { integra: boolean; quebra_em: number | null; total: number | null } };

const GRUPOS: Record<string, string[]> = {
  "Ciclo de vida": ["agente_criado", "agente_modificado", "agente_enviado_revisao", "revisao_aprovada", "revisao_rejeitada", "agente_publicado", "agente_pausado", "agente_retomado", "agente_depreciado", "orcamento_definido"],
  Execuções: ["execucao_iniciada", "execucao_concluida", "execucao_escalada", "execucao_aguardando_aprovacao", "aprovacao_concedida", "aprovacao_recusada", "execucao_negada"],
  Ferramentas: ["ferramenta_executada", "ferramenta_negada", "ferramenta_erro", "ferramenta_aguardando_aprovacao"],
  Plugins: ["plugin_integrado", "plugin_removido", "plugin_pedido_criado", "plugin_pedido_registrado", "plugin_pedido_aprovado", "plugin_pedido_recusado"],
  Alertas: ["alerta_aberto", "alerta_resolvido", "conector_falha_injetada", "conector_normalizado"],
};

export default function Auditoria() {
  const [grupo, setGrupo] = useState<string>("Todos");
  const [aberto, setAberto] = useState<string | null>(null);
  const q = useQuery({ queryKey: ["auditoria"], queryFn: () => api<Resposta>("/auditoria?limite=400") });
  const eventos = (q.data?.eventos ?? []).filter((e) => grupo === "Todos" || GRUPOS[grupo]?.includes(e.tipo));
  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-3xl">Auditoria</h1>
          <p className="mt-1 max-w-2xl text-tinta-2">Cada evento guarda o hash do anterior: alterar ou apagar qualquer registro quebra a cadeia, e a plataforma mostra onde. Dados pessoais aparecem só como marcadores.</p>
        </div>
        {q.data && (
          <span className={"selo px-3 py-1 text-sm " + (q.data.cadeia.integra ? "bg-pedra-fundo text-pedra-forte" : "bg-erro-fundo text-erro")}>
            {q.data.cadeia.integra ? `✓ Cadeia íntegra · ${q.data.cadeia.total} eventos` : `✕ Cadeia quebrada no evento ${q.data.cadeia.quebra_em}`}
          </span>
        )}
      </div>
      {q.isError && <p className="text-erro">{(q.error as Error).message}</p>}
      <div className="flex flex-wrap gap-1.5">
        {["Todos", ...Object.keys(GRUPOS)].map((g) => (
          <button key={g} onClick={() => setGrupo(g)} className={"rounded-full px-3 py-1 text-sm " + (grupo === g ? "bg-tinta text-white" : "bg-folha text-tinta-2 border border-linha")}>{g}</button>
        ))}
      </div>
      <div className="caixa divide-y divide-linha">
        {eventos.map((e) => (
          <div key={e.id}>
            <button className="flex w-full items-center gap-4 px-4 py-2.5 text-left text-sm hover:bg-papel" onClick={() => setAberto(aberto === e.id ? null : e.id)} aria-expanded={aberto === e.id}>
              <span className="w-12 text-xs text-tinta-3">#{e.seq}</span>
              <span className="w-56 font-medium">{NOME_EVENTO[e.tipo] ?? e.tipo.replace(/_/g, " ")}</span>
              <span className="w-24 text-tinta-2">{e.ator}</span>
              <span className="flex-1 truncate text-tinta-3">{e.agente_id ? <Link className="hover:text-pedra-forte" to={"/agentes/" + e.agente_id} onClick={(ev) => ev.stopPropagation()}>{e.agente_id}</Link> : "—"}</span>
              <span className="text-xs text-tinta-3">{quando(e.quando)}</span>
            </button>
            {aberto === e.id && <pre className="mx-4 mb-3 max-h-64 overflow-auto rounded-lg bg-papel p-3 text-xs text-tinta-2">{JSON.stringify(e.dados, null, 2)}</pre>}
          </div>
        ))}
        {q.data && eventos.length === 0 && <p className="p-5 text-sm text-tinta-3">Nenhum evento neste filtro.</p>}
      </div>
    </div>
  );
}
