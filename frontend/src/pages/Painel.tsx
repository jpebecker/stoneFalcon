import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { api, type Indicadores } from "../api/cliente";
import { num, pct, reais, reaisCurto } from "../components/formato";

function Criterio({ n, titulo, pergunta, destaque, comparacao, detalhes }: {
  n: number; titulo: string; pergunta: string; destaque: string; comparacao: string; detalhes: string[];
}) {
  return (
    <article className="caixa flex flex-col p-5">
      <div className="flex items-baseline gap-2">
        <span className="font-titulo text-sm font-semibold text-pedra-forte">{n}</span>
        <h2 className="text-lg">{titulo}</h2>
      </div>
      <p className="text-xs text-tinta-3">{pergunta}</p>
      <div className="mt-4 font-titulo text-4xl font-semibold tracking-tight">{destaque}</div>
      <p className="mt-1 text-sm text-tinta-2">{comparacao}</p>
      <ul className="mt-4 space-y-1 border-t border-linha pt-3 text-xs text-tinta-2">
        {detalhes.map((d) => <li key={d}>{d}</li>)}
      </ul>
    </article>
  );
}

export default function Painel() {
  const q = useQuery({ queryKey: ["indicadores"], queryFn: () => api<Indicadores>("/financas/indicadores?dias=30") });
  const i = q.data;
  if (!i) return <p className="text-tinta-3">Carregando…</p>;
  const reducao = i.tempo_execucao.reducao_pct;
  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-3xl">Painel executivo</h1>
          <p className="mt-1 text-tinta-2">Os cinco indicadores do desafio, medidos nas execuções dos últimos {i.dias} dias ({num(i.execucoes)} execuções).</p>
        </div>
        <Link to="/financas/calculadora" className="botao-claro">Projeção de 36 meses</Link>
      </div>
      {i.tem_demo && (
        <p className="rounded-caixa border border-alerta/40 bg-alerta-fundo/60 px-4 py-2 text-sm">
          Inclui histórico de demonstração (cenário gerado). Os números mostram como a plataforma mede; os valores reais saem do piloto.
        </p>
      )}
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        <Criterio n={1} titulo="Tempo de execução" pergunta="Redução do tempo por tarefa"
          destaque={reducao == null ? "—" : "−" + pct(reducao)}
          comparacao={`${num(i.tempo_execucao.manual_min)} min à mão → ${num(i.tempo_execucao.agente_min)} min com o agente`}
          detalhes={[`Inclui ${num(i.tempo_execucao.revisao_humana_min)} min de conferência humana (premissa)`, "Tempo do agente: mediana das execuções concluídas"]} />
        <Criterio n={2} titulo="Custo operacional" pergunta="Economia gerada por operação"
          destaque={reais(i.custo_operacional.economia_por_operacao_brl)}
          comparacao={`${reais(i.custo_operacional.manual_brl)} de trabalho à mão vs. ${reais(i.custo_operacional.agente_brl)} em modelos`}
          detalhes={[`Roteador economiza ${pct(i.custo_operacional.economia_roteador_pct)} vs. usar só o modelo forte`, `Custo-hora de R$ ${i.premissas_usadas.custo_hora} (premissa)`]} />
        <Criterio n={3} titulo="Produtividade" pergunta="Aumento de tarefas realizadas"
          destaque={num(i.produtividade.horas_liberadas) + " h"}
          comparacao={`${num(i.produtividade.tarefas_concluidas)} tarefas concluídas sem intervenção`}
          detalhes={[`${i.produtividade.agentes_ativos} agentes publicados`, "Horas liberadas já descontam a conferência"]} />
        <Criterio n={4} titulo="Taxa de erros" pergunta="Redução de falhas e retrabalho"
          destaque={pct(i.taxa_erros.agente)}
          comparacao={`das execuções escalaram para humano, contra ${pct(i.taxa_erros.manual_premissa)} de retrabalho manual (premissa)`}
          detalhes={[`${num(i.taxa_erros.escaladas_ou_falhas)} escaladas, sempre com motivo registrado`,
                     `${num(i.taxa_erros.acessos_bloqueados)} acessos indevidos bloqueados · ${num(i.taxa_erros.dados_mascarados)} dados pessoais mascarados`]} />
        <Criterio n={5} titulo="ROI" pergunta="Retorno financeiro sobre o investimento"
          destaque={i.roi.projecao_payback_mes ? `payback no mês ${i.roi.projecao_payback_mes}` : "—"}
          comparacao={`VPL de ${reaisCurto(i.roi.projecao_vpl)} em 36 meses${i.roi.projecao_tir_anual != null ? `, TIR de ${pct(i.roi.projecao_tir_anual)} ao ano` : ""}`}
          detalhes={[`No período: ${reaisCurto(i.roi.periodo_ganho_brl)} de valor gerado para ${reais(i.roi.periodo_custo_brl)} em modelos`,
                     "Projeção usa o tempo e o custo medidos aqui + premissas de adoção"]} />
        <article className="caixa flex flex-col justify-between bg-tinta p-5 text-white">
          <div>
            <h2 className="text-lg">Por que institucional</h2>
            <p className="mt-2 text-sm text-white/75">Cada número acima vem da própria plataforma: execução, custo, escalada e bloqueio ficam na trilha de auditoria encadeada. Ferramentas low-code genéricas não medem isso por agente, nem por área, nem com guardrails nativos.</p>
          </div>
          <Link to="/saude" className="mt-4 text-sm font-semibold text-white underline">Ver a saúde dos agentes</Link>
        </article>
      </div>
    </div>
  );
}
