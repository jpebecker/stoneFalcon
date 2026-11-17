import { useQuery } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, type Consolidado, type Premissas, type Projecao } from "../api/cliente";
import { LinhaAcumulada } from "../components/Graficos";
import { num, pct, reais, reaisCurto } from "../components/formato";

type Campo = { chave: string; rotulo: string; min: number; max: number; passo: number; tipo?: "pct" | "brl" };

const GRUPOS: { titulo: string; campos: Campo[] }[] = [
  { titulo: "Investimento e operação (documento de custos)", campos: [
    { chave: "investimento_inicial", rotulo: "Desenvolvimento + implantação", min: 0, max: 2_000_000, passo: 10_000, tipo: "brl" },
    { chave: "modulos_integracao", rotulo: "Módulos de integração", min: 0, max: 1_000_000, passo: 10_000, tipo: "brl" },
    { chave: "hospedagem_mensal", rotulo: "Hospedagem/mês", min: 0, max: 50_000, passo: 100, tipo: "brl" },
    { chave: "sustentacao_mensal", rotulo: "Sustentação/mês", min: 0, max: 100_000, passo: 500, tipo: "brl" },
  ]},
  { titulo: "Adoção (a validar no piloto)", campos: [
    { chave: "usuarios", rotulo: "Colaboradores com acesso", min: 0, max: 20_000, passo: 100 },
    { chave: "adocao_alvo", rotulo: "Adoção ao fim da rampa", min: 0, max: 1, passo: 0.01, tipo: "pct" },
    { chave: "meses_rampa", rotulo: "Meses de rampa", min: 1, max: 36, passo: 1 },
    { chave: "tarefas_por_usuario_dia", rotulo: "Execuções por usuário/dia", min: 0, max: 10, passo: 0.1 },
  ]},
  { titulo: "Valor por tarefa (a validar no piloto)", campos: [
    { chave: "minutos_por_tarefa", rotulo: "Minutos da tarefa à mão", min: 0, max: 120, passo: 1 },
    { chave: "minutos_revisao_humana", rotulo: "Minutos de conferência", min: 0, max: 60, passo: 0.5 },
    { chave: "custo_hora", rotulo: "Custo da hora (R$)", min: 0, max: 300, passo: 1 },
    { chave: "aproveitamento", rotulo: "Aproveitamento do tempo", min: 0, max: 1, passo: 0.05, tipo: "pct" },
    { chave: "custo_por_execucao", rotulo: "Tokens por execução (R$)", min: 0, max: 2, passo: 0.005 },
  ]},
];

function rotuloValor(c: Campo, v: number) {
  if (c.tipo === "pct") return pct(v);
  if (c.tipo === "brl") return reaisCurto(v);
  return num(v);
}

export default function Calculadora() {
  const base = useQuery({ queryKey: ["premissas"], queryFn: () => api<{ valores: Premissas; medidas: Premissas; medidas_demo: boolean }>("/financas/premissas") });
  const cons = useQuery({ queryKey: ["consolidado"], queryFn: () => api<Consolidado>("/roteiros/consolidado") });
  const inicial = base.data ? { ...base.data.valores, ...base.data.medidas } : null;
  const [p, setP] = useState<Premissas | null>(null);
  const [proj, setProj] = useState<Projecao | null>(null);
  useEffect(() => { if (inicial && !p) setP(inicial); }, [inicial, p]);
  useEffect(() => {
    if (!p) return;
    const t = setTimeout(() => { api<Projecao>("/financas/calculadora", p).then(setProj).catch(() => {}); }, 150);
    return () => clearTimeout(t);
  }, [p]);
  if (!p) return <p className="text-tinta-3">Carregando…</p>;
  const mudar = (k: string, v: number | boolean) => setP({ ...p, [k]: v });

  return (
    <div className="space-y-6">
      <Link to="/financas" className="text-sm text-tinta-3 hover:text-tinta">← Finanças</Link>
      <div>
        <h1 className="text-3xl">Calculadora de investimento</h1>
        <p className="mt-1 max-w-3xl text-tinta-2">Fluxo de caixa de {String(p.meses)} meses. Investimento e operação vêm do documento de custos da equipe; adoção e valor são premissas nossas, a validar num piloto.</p>
        {base.data && Object.keys(base.data.medidas).length > 0 && (
          <p className="mt-2 text-sm text-tinta-3">
            Tempo da tarefa ({num(Number(base.data.medidas.minutos_por_tarefa))} min) e custo por execução ({reais(Number(base.data.medidas.custo_por_execucao))}) já vêm medidos pela plataforma{base.data.medidas_demo ? " (no histórico de demonstração)" : ""}.
          </p>
        )}
      </div>

      {cons.data && (
        <div className="caixa flex flex-wrap items-center gap-2 p-4 text-sm">
          <span className="font-semibold">Partir de um processo dos roteiros:</span>
          {cons.data.processos.map((pr) => (
            <button key={pr.roteiro} className="botao-claro py-1.5" onClick={() => setP({ ...p, ...pr.calculadora })}
              title={`${pr.as_is_min} min à mão, ${pr.to_be_min} min com o agente (${pr.origem_to_be})`}>{pr.processo}</button>
          ))}
          <span className="text-xs text-tinta-3">Carrega o tempo da tarefa, a conferência humana e o custo de tokens daquele processo.</span>
        </div>
      )}

      <div className="grid gap-6 xl:grid-cols-[380px_1fr]">
        <aside className="space-y-5">
          {GRUPOS.map((g) => (
            <section key={g.titulo} className="caixa space-y-3 p-4">
              <h2 className="text-sm font-semibold">{g.titulo}</h2>
              {g.campos.map((c) => (
                <label key={c.chave} className="block">
                  <div className="flex justify-between text-xs"><span className="text-tinta-2">{c.rotulo}</span><b>{rotuloValor(c, Number(p[c.chave]))}</b></div>
                  <input type="range" className="w-full accent-[rgb(var(--pedra))]" min={c.min} max={c.max} step={c.passo}
                    value={Number(p[c.chave])} onChange={(e) => mudar(c.chave, Number(e.target.value))} />
                </label>
              ))}
              {g.campos.some((c) => c.chave === "modulos_integracao") && (
                <label className="flex items-center gap-2 text-xs text-tinta-2">
                  <input type="checkbox" checked={Boolean(p.incluir_modulos)} onChange={(e) => mudar("incluir_modulos", e.target.checked)} />
                  Incluir os módulos de integração no investimento
                </label>
              )}
            </section>
          ))}
          <button className="botao-claro w-full" onClick={() => inicial && setP(inicial)}>Voltar aos valores iniciais</button>
        </aside>

        {proj && (
          <div className="space-y-5">
            <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
              {[
                ["Payback", proj.payback_mes ? `mês ${proj.payback_mes}` : "não se paga", "investimento recuperado"],
                ["VPL", reaisCurto(proj.vpl), `taxa de ${pct(Number(p.taxa_desconto_anual))} ao ano`],
                ["TIR", proj.tir_anual == null ? "—" : pct(proj.tir_anual), "ao ano"],
                ["Retorno", proj.roi == null ? "—" : num(proj.roi) + "×", `benefício líquido sobre o custo em ${String(p.meses)} meses`],
              ].map(([r, v, n]) => (
                <div key={r} className="caixa p-4">
                  <div className="text-xs font-semibold uppercase tracking-wide text-tinta-3">{r}</div>
                  <div className="mt-1 font-titulo text-2xl font-semibold">{v}</div>
                  <div className="mt-0.5 text-xs text-tinta-3">{n}</div>
                </div>
              ))}
            </div>
            <section className="caixa p-5">
              <LinhaAcumulada titulo="Resultado acumulado (benefício − custos − investimento)" marco={proj.payback_mes}
                pontos={[{ x: 0, y: -proj.investimento_total }, ...proj.meses.map((m) => ({ x: m.mes, y: m.acumulado }))]}
                formatar={reaisCurto} />
            </section>
            <section className="caixa grid gap-4 p-5 text-sm sm:grid-cols-2">
              <div>
                <h3 className="font-semibold">Para onde vai o custo</h3>
                <ul className="mt-2 space-y-1 text-tinta-2">
                  <li>Investimento: <b className="text-tinta">{reais(proj.investimento_total)}</b></li>
                  <li>Custo fixo: <b className="text-tinta">{reais(proj.custo_fixo_mensal)}</b>/mês</li>
                  <li>Tokens: <b className="text-tinta">{pct(proj.tokens_participacao)}</b> do custo total — o roteador mantém os modelos uma fração pequena</li>
                </ul>
              </div>
              <div>
                <h3 className="font-semibold">Unidade de valor</h3>
                <ul className="mt-2 space-y-1 text-tinta-2">
                  <li>Ganho por tarefa: <b className="text-tinta">{reais(proj.ganho_por_tarefa)}</b></li>
                  <li>Para pagar o custo fixo: <b className="text-tinta">{proj.ponto_de_equilibrio_execucoes_mes ? num(proj.ponto_de_equilibrio_execucoes_mes) : "—"}</b> execuções/mês</li>
                  <li>No mês {proj.meses.length}: <b className="text-tinta">{num(proj.meses[proj.meses.length - 1].execucoes)}</b> execuções e {num(proj.meses[proj.meses.length - 1].horas_liberadas)} h liberadas</li>
                </ul>
              </div>
            </section>
          </div>
        )}
      </div>
    </div>
  );
}
