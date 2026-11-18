import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link } from "react-router-dom";
import { api, type Persona, type ResumoFinancas } from "../api/cliente";
import { BarrasEmpilhadas } from "../components/Graficos";
import { num, pct, reais, reaisCurto } from "../components/formato";

function Tile({ rotulo, valor, nota }: { rotulo: string; valor: string; nota?: string }) {
  return (
    <div className="caixa p-4">
      <div className="text-xs font-semibold uppercase tracking-wide text-tinta-3">{rotulo}</div>
      <div className="mt-1 font-titulo text-2xl font-semibold">{valor}</div>
      {nota && <div className="mt-0.5 text-xs text-tinta-3">{nota}</div>}
    </div>
  );
}

function Orcamento({ uso, gasto, limite, editavel, aoMudar }: {
  uso: number | null; gasto: number; limite: number; editavel: boolean; aoMudar: (v: number) => void;
}) {
  const f = Math.min(uso ?? 0, 1);
  const cor = (uso ?? 0) >= 1 ? "bg-erro" : (uso ?? 0) >= 0.8 ? "bg-alerta" : "bg-pedra";
  return (
    <div className="min-w-[160px]">
      <div className="h-1.5 overflow-hidden rounded-full bg-linha"><div className={"h-full rounded-full " + cor} style={{ width: `${f * 100}%` }} /></div>
      <div className="mt-1 flex items-center justify-between gap-2 text-xs text-tinta-3">
        <span>{reais(gasto)} de</span>
        {editavel ? (
          <input type="number" min={0} step={10} defaultValue={limite} aria-label="Orçamento mensal (R$)"
            className="w-20 rounded border border-linha px-1 py-0.5 text-right"
            onBlur={(e) => Number(e.target.value) !== limite && aoMudar(Number(e.target.value))} />
        ) : <span>{reais(limite)}</span>}
      </div>
    </div>
  );
}

export default function Financas({ pessoa }: { pessoa: Persona }) {
  const qc = useQueryClient();
  const [dias, setDias] = useState(30);
  const q = useQuery({ queryKey: ["financas", dias], queryFn: () => api<ResumoFinancas>("/financas/resumo?dias=" + dias) });
  const gestor = pessoa.papeis.includes("gestor_ia");
  const orcamento = useMutation({
    mutationFn: ({ id, valor }: { id: string; valor: number }) => api(`/agentes/${id}/orcamento`, { valor_brl: valor }, "PUT"),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["financas"] }),
  });
  const gerar = useMutation({
    mutationFn: () => api("/demo/historico", {}),
    onSuccess: () => qc.invalidateQueries(),
  });
  const r = q.data;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-3xl">Finanças</h1>
          <p className="mt-1 text-tinta-2">Quanto os agentes custam e quanto devolvem, calculado das execuções registradas.</p>
        </div>
        <div className="flex items-center gap-2">
          <div className="flex rounded-lg border border-linha bg-folha p-0.5 text-sm">
            {[7, 30, 90].map((d) => (
              <button key={d} onClick={() => setDias(d)} className={"rounded-md px-3 py-1 " + (dias === d ? "bg-tinta text-white" : "text-tinta-2")}>{d} dias</button>
            ))}
          </div>
          <Link to="/financas/calculadora" className="botao-claro">Calculadora de investimento</Link>
        </div>
      </div>

      {r?.tem_demo && (
        <p className="rounded-caixa border border-alerta/40 bg-alerta-fundo/60 px-4 py-2 text-sm">
          Inclui <b>histórico de demonstração</b> (cenário gerado, não é medição). {gestor && (
            <button className="font-semibold underline" onClick={() => gerar.mutate()}>Gerar de novo</button>)}
        </p>
      )}
      {r && !r.tem_demo && r.execucoes === 0 && gestor && (
        <button className="botao-claro" onClick={() => gerar.mutate()}>Gerar histórico de demonstração</button>
      )}

      {r && (
        <>
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            <Tile rotulo="Execuções" valor={num(r.execucoes)} nota={`últimos ${r.dias} dias`} />
            <Tile rotulo="Custo em modelos" valor={reais(r.custo_brl)} nota={`sem o roteador seriam ${reais(r.custo_sem_roteador_brl)}`} />
            <Tile rotulo="Economia do roteador" valor={pct(r.economia_roteador_pct)} nota="vs. mandar tudo ao modelo forte" />
            <Tile rotulo="Valor do tempo liberado" valor={reaisCurto(r.ganho_brl)} nota="só execuções concluídas · premissas a validar" />
          </div>

          <section className="caixa p-5">
            <BarrasEmpilhadas titulo="Custo por dia, por modelo" dados={r.por_dia}
              rotulo={(d) => d.dia.slice(8, 10) + "/" + d.dia.slice(5, 7)} formatar={(v) => reais(v)}
              formatarEixo={(v) => "R$ " + v.toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
              series={r.por_modelo.map((m, i) => ({ chave: m.chave + "_brl", nome: m.modelo, cor: `var(--serie-${(i % 6) + 1})` }))} />
            <p className="mt-3 text-xs text-tinta-3">
              {r.por_modelo.map((m) => `${m.modelo}: ${num(m.chamadas)} chamadas, ${reais(m.custo_brl)}`).join(" · ")}
            </p>
          </section>

          <section className="caixa overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-papel text-left text-xs uppercase tracking-wide text-tinta-3">
                <tr>
                  <th className="px-4 py-2.5">Agente</th><th className="px-4 py-2.5 text-right">Execuções</th>
                  <th className="px-4 py-2.5 text-right">Custo</th><th className="px-4 py-2.5 text-right">Custo/execução</th>
                  <th className="px-4 py-2.5 text-right">Horas liberadas</th><th className="px-4 py-2.5 text-right">Valor gerado</th>
                  <th className="px-4 py-2.5 text-right">Retorno</th><th className="px-4 py-2.5">Orçamento do mês</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-linha">
                {r.por_agente.map((a) => (
                  <tr key={a.id}>
                    <td className="px-4 py-2.5"><Link to={"/agentes/" + a.id} className="font-medium hover:text-pedra-forte">{a.nome}</Link>
                      <div className="text-xs text-tinta-3">{a.area} · {a.minutos_manual} min à mão</div></td>
                    <td className="px-4 py-2.5 text-right">{num(a.execucoes)}<div className="text-xs text-tinta-3">{num(a.concluidas)} concluídas</div></td>
                    <td className="px-4 py-2.5 text-right">{reais(a.custo_brl)}</td>
                    <td className="px-4 py-2.5 text-right">{reais(a.custo_medio_brl)}</td>
                    <td className="px-4 py-2.5 text-right">{num(a.horas_liberadas)} h</td>
                    <td className="px-4 py-2.5 text-right">{reaisCurto(a.ganho_brl)}</td>
                    <td className="px-4 py-2.5 text-right font-semibold">{a.roi == null ? "—" : num(a.roi) + "×"}</td>
                    <td className="px-4 py-2.5">
                      <Orcamento uso={a.uso_orcamento} gasto={a.gasto_mes_brl} limite={a.orcamento_mensal_brl}
                        editavel={gestor} aoMudar={(v) => orcamento.mutate({ id: a.id, valor: v })} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {r.por_agente.length === 0 && <p className="p-5 text-sm text-tinta-3">Nenhum agente visível.</p>}
          </section>
          <p className="text-xs text-tinta-3">
            Valor gerado = execuções concluídas × (minutos à mão − {String(r.premissas?.minutos_revisao_humana ?? 2)} min de conferência) × R$ {String(r.premissas?.custo_hora ?? 45)}/h × {pct(Number(r.premissas?.aproveitamento ?? 0.5))} de aproveitamento.
            Escaladas não contam. Ao atingir o orçamento do mês, o agente para de executar (alerta aos 80%).
          </p>
        </>
      )}
    </div>
  );
}
