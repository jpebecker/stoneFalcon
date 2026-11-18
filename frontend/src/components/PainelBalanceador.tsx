import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, type CargaBalanceador, type PoliticaBalanceador } from "../api/cliente";
import SeloSimulado from "./SeloSimulado";
import { reais } from "./formato";

const pct = (v: number | null) => (v === null ? "—" : (v * 100).toLocaleString("pt-BR", { maximumFractionDigits: 0 }) + "%");

function Carga({ c }: { c: CargaBalanceador }) {
  const total = c.passos || 1;
  return (
    <div className="mt-3 space-y-3 rounded-caixa border border-linha p-4" aria-live="polite">
      <p className="text-sm">
        <b>{c.passos}</b> passos sintéticos custaram <b>{reais(c.custo_brl)}</b>; no modelo forte seriam <b>{reais(c.custo_tudo_forte_brl)}</b>
        {c.economia_pct !== null && <> (economia de <b>{pct(c.economia_pct)}</b>)</>}.
        {c.fora.length > 0 && <span className="text-alerta"> Com provedor fora do ar: {c.fora.join(", ")}.</span>}
      </p>
      <div className="grid gap-4 md:grid-cols-2">
        <div>
          <h4 className="rotulo">Por nível de esforço</h4>
          <ul className="space-y-1 text-sm">
            {c.por_nivel.map((n) => (
              <li key={n.nivel} className="flex items-center gap-2">
                <span className="w-20">{n.rotulo}</span>
                <span className="h-2 flex-1 overflow-hidden rounded-full bg-linha"><span className="block h-full bg-pedra" style={{ width: `${(n.passos / total) * 100}%` }} /></span>
                <span className="w-24 text-right text-xs text-tinta-3">{n.passos} · {reais(n.custo_brl)}</span>
              </li>
            ))}
          </ul>
        </div>
        <div>
          <h4 className="rotulo">Por provedor</h4>
          <ul className="space-y-1 text-sm">
            {c.por_provedor.map((p) => (
              <li key={p.provedor} className="flex items-center gap-2">
                <span className="w-32 truncate">{p.nome}</span>
                <span className="h-2 flex-1 overflow-hidden rounded-full bg-linha"><span className="block h-full bg-info" style={{ width: `${(p.passos / total) * 100}%` }} /></span>
                <span className="w-24 text-right text-xs text-tinta-3">{p.passos} · {reais(p.custo_brl)}</span>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
}

/** Política do balanceador: a Helena vê, simula a queda de um provedor e roda a carga de teste; a Engenharia só vê. */
export default function PainelBalanceador() {
  const qc = useQueryClient();
  const q = useQuery({ queryKey: ["balanceador"], queryFn: () => api<PoliticaBalanceador>("/balanceador/politica"), retry: false, refetchInterval: 15000 });
  const falha = useMutation({
    mutationFn: ({ id, fora }: { id: string; fora: boolean }) => api<PoliticaBalanceador>(`/balanceador/provedores/${id}/falha`, { fora }),
    onSuccess: (d) => { qc.setQueryData(["balanceador"], d); qc.invalidateQueries({ queryKey: ["alertas"] }); qc.invalidateQueries({ queryKey: ["notificacoes"] }); },
  });
  const carga = useMutation({
    mutationFn: () => api<CargaBalanceador>("/balanceador/simular-carga", { passos: 300 }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["balanceador"] }),
  });
  const p = q.data;
  if (!p) return null;
  const c = carga.data ?? p.ultima_carga;
  return (
    <section aria-label="Balanceador de modelos">
      <h2 className="mb-1 text-lg">Balanceador de modelos</h2>
      <p className="mb-3 max-w-3xl text-sm text-tinta-2">
        Cada passo automático recebe um nível de esforço e vai ao modelo mais barato que atende. {p.demonstracao}
      </p>
      <div className="caixa overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-papel text-left text-xs uppercase tracking-wide text-tinta-3">
            <tr><th className="px-4 py-2.5">Nível</th><th className="px-4 py-2.5">O que exige</th><th className="px-4 py-2.5">Vai para (agora)</th><th className="px-4 py-2.5">Por quê</th></tr>
          </thead>
          <tbody className="divide-y divide-linha">
            {p.niveis.map((n) => (
              <tr key={n.id}>
                <td className="px-4 py-2 font-semibold">{n.rotulo}</td>
                <td className="px-4 py-2 text-tinta-2">{n.descricao} <span className="text-xs text-tinta-3">(raciocínio {n.raciocinio_min}+)</span></td>
                <td className="px-4 py-2">{n.escolha.modelo}{n.escolha.simulado && <SeloSimulado className="ml-2" />}</td>
                <td className="px-4 py-2 text-xs text-tinta-3">{n.escolha.motivo}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <p className="border-t border-linha px-4 py-2 text-xs text-tinta-3">
          Regras: o provedor homologado ({p.regras.provedor_homologado}) vale até {p.regras.tolerancia_homologado}× o preço do mais barato capaz;
          com {pct(p.regras.orcamento_apertado)} do orçamento do mês gasto, o agente vai sempre ao mais barato; provedor fora do ar é descartado.
        </p>
      </div>

      <h3 className="mb-2 mt-5 text-base">Provedores</h3>
      <ul className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
        {p.provedores.map((pr) => (
          <li key={pr.id} className={"caixa flex items-center gap-3 p-3 " + (pr.fora ? "border-erro/50 bg-erro-fundo" : "")}>
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-2 text-sm font-semibold">{pr.nome}{!pr.real && <SeloSimulado />}</div>
              <div className="truncate text-xs text-tinta-3">{pr.modelos.join(" · ")}</div>
              <div className={"text-xs " + (pr.fora ? "font-semibold text-erro" : "text-pedra-forte")}>{pr.fora ? "● fora do ar (simulado)" : "● no ar"}</div>
            </div>
            {p.pode_simular && (
              <button className={pr.fora ? "botao-claro px-3 py-1.5 text-xs" : "botao-claro px-3 py-1.5 text-xs text-erro"} disabled={falha.isPending}
                onClick={() => falha.mutate({ id: pr.id, fora: !pr.fora })}>
                {pr.fora ? "Normalizar" : "Simular queda"}
              </button>
            )}
          </li>
        ))}
      </ul>

      {p.pode_simular && (
        <div className="mt-5">
          <button className="botao-pedra" disabled={carga.isPending} onClick={() => carga.mutate()}>
            {carga.isPending ? "Rodando…" : "Simular carga (300 passos)"}
          </button>
          <span className="ml-3 text-xs text-tinta-3">Lote sintético, sem chamar nenhum modelo. Reiniciar a demo desfaz.</span>
        </div>
      )}
      {c && <Carga c={c} />}
    </section>
  );
}
