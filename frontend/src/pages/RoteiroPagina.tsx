// Cartões AS IS × TO BE de uma persona e, no fim do roteiro, o valor medido.
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Link, Navigate, useParams, useSearchParams } from "react-router-dom";
import { api, type Consolidado, type LinhaResultado, type Persona, type ResultadoRoteiro, type Roteiro } from "../api/cliente";
import Avatar from "../components/Avatar";
import { num, reais } from "../components/formato";
import { useControle } from "../roteiro/Controle";
import { useEstadoRoteiro } from "../roteiro/estado";

function Origem({ texto }: { texto: string }) {
  const cor = texto.startsWith("medido") ? "bg-pedra-fundo text-pedra-forte"
    : texto.startsWith("estimado") ? "bg-info-fundo text-info"
    : texto.startsWith("hipótese") ? "bg-alerta-fundo text-alerta" : "bg-papel text-tinta-2";
  return <span className={"selo whitespace-normal text-left font-medium " + cor}>{texto}</span>;
}

function valor(l: LinhaResultado, v: number | null) {
  if (v == null) return "—";
  if (l.unidade === "R$") return reais(v);
  if (l.unidade.startsWith("R$ por")) return "R$ " + num(v);
  return num(v) + " " + l.unidade;
}

function Resultado({ roteiro, gestor }: { roteiro: Roteiro; gestor: boolean }) {
  const est = useEstadoRoteiro();
  const agenteId = est?.id === roteiro.id ? est.ctx.agenteId : undefined;
  const q = useQuery({
    queryKey: ["resultado", roteiro.id, agenteId],
    queryFn: () => api<ResultadoRoteiro>(`/roteiros/${roteiro.id}/resultado` + (agenteId ? "?agente_id=" + agenteId : "")),
  });
  const r = q.data;
  if (!r) return <p className="text-tinta-3">Calculando…</p>;
  return (
    <section className="caixa space-y-4 p-6">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h2 className="text-xl">AS IS × TO BE medido</h2>
        {r.agente && <Link to={"/agentes/" + r.agente.id} className="text-sm font-semibold text-pedra-forte">Agente: {r.agente.nome} →</Link>}
      </div>
      {!r.execucao && (
        <p className="rounded-lg bg-alerta-fundo p-3 text-sm text-alerta">
          Ainda não há execução deste agente no roteiro: o TO BE abaixo é <b>estimado</b> pelo desenho do agente. Execute o agente para medir.
        </p>
      )}
      {r.indicadores.length > 0 && (
        <div className="grid gap-3 sm:grid-cols-2">
          {r.indicadores.map((i) => (
            <div key={i.nome} className="rounded-caixa border border-linha bg-papel p-4">
              <div className="text-xs font-semibold uppercase tracking-wide text-tinta-3">{i.nome}</div>
              <div className="mt-1 font-titulo text-3xl font-semibold text-pedra-forte">
                {i.valor == null ? "—" : i.unidade === "R$" ? reais(i.valor) : num(i.valor)}
                {i.unidade !== "R$" && <span className="ml-1 text-base text-tinta-2">{i.unidade}</span>}
              </div>
              <div className="mt-1"><Origem texto={i.origem} /></div>
              {i.detalhe && <p className="mt-1 text-xs text-tinta-3">{i.detalhe}</p>}
            </div>
          ))}
        </div>
      )}
      {r.linhas.length === 0 ? (r.indicadores.length === 0 && <p className="text-tinta-2">Este roteiro não tem um processo de tarefa para comparar.</p>) : (
        <div className="overflow-x-auto">
          <table className="w-full min-w-[720px] text-sm">
            <thead><tr className="border-b border-linha text-left text-xs uppercase tracking-wide text-tinta-3">
              <th className="py-2 pr-3">Critério</th><th className="pr-3">AS IS (hoje)</th><th className="pr-3">TO BE (com o agente)</th><th>Variação</th>
            </tr></thead>
            <tbody>
              {r.linhas.map((l) => (
                <tr key={l.criterio} className="border-b border-linha align-top">
                  <td className="py-3 pr-3 font-medium">{l.criterio}</td>
                  <td className="pr-3"><div className="font-semibold">{valor(l, l.as_is)}</div><Origem texto={l.origem_as_is} /></td>
                  <td className="pr-3"><div className="font-semibold text-pedra-forte">{valor(l, l.to_be)}</div><Origem texto={l.origem_to_be} /></td>
                  <td className="py-3 font-semibold">{l.delta_pct == null ? "—" : (l.delta_pct > 0 ? "+" : "") + Math.round(l.delta_pct * 100) + "%"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <p className="text-sm text-tinta-2">
        Ganho por tarefa (premissa de aproveitamento): <b>{reais(r.ganho_por_tarefa_brl)}</b>.
        {r.execucao && <> Execução medida: {num(r.execucao.duracao_min * 60)} s de agente, {reais(r.execucao.custo_brl)} em tokens.</>}
      </p>
      {r.rotina && (
        <div className="rounded-caixa border border-info/30 bg-info-fundo/50 p-4 text-sm" data-testid="ganho-rotina">
          <div className="text-xs font-semibold uppercase tracking-wide text-info">Rotina semanal</div>
          <p className="mt-1">
            {r.rotina.agendas.join(" · ")}: <b>{num(r.rotina.execucoes_feitas)}</b> execução(ões) já rodaram, e a rotina faz cerca de{" "}
            <b>{num(r.rotina.execucoes_por_mes)}</b> por mês sem ninguém iniciar. Ganho projetado: <b>{reais(r.rotina.ganho_mensal_brl)}</b> por mês.
          </p>
          <div className="mt-1"><Origem texto={r.rotina.origem} /></div>
        </div>
      )}
      {r.aviso && <p className="text-xs text-tinta-3">{r.aviso}</p>}
      {gestor && (
        <div className="flex gap-2 border-t border-linha pt-4">
          <Link className="botao-claro" to={"/perguntas?persona=" + roteiro.persona}>Perguntas</Link>
          <Link className="botao-claro" to="/painel">Painel executivo</Link>
        </div>
      )}
    </section>
  );
}

function ConsolidadoHelena() {
  const q = useQuery({ queryKey: ["consolidado"], queryFn: () => api<Consolidado>("/roteiros/consolidado") });
  if (!q.data) return <p className="text-tinta-3">Calculando…</p>;
  const { processos, totais, premissas } = q.data;
  return (
    <section className="caixa space-y-4 p-6">
      <h2 className="text-xl">AS IS × TO BE de todos os processos</h2>
      <div className="overflow-x-auto">
        <table className="w-full min-w-[760px] text-sm">
          <thead><tr className="border-b border-linha text-left text-xs uppercase tracking-wide text-tinta-3">
            <th className="py-2 pr-3">Processo</th><th className="pr-3">AS IS</th><th className="pr-3">TO BE</th><th className="pr-3">Redução</th>
            <th className="pr-3">Tokens/tarefa</th><th>Ganho/tarefa</th>
          </tr></thead>
          <tbody>
            {processos.map((p) => (
              <tr key={p.roteiro} className="border-b border-linha align-top">
                <td className="py-3 pr-3"><Link to={"/roteiro/" + p.roteiro} className="font-medium hover:text-pedra-forte">{p.processo}</Link></td>
                <td className="pr-3"><b>{num(p.as_is_min)} min</b><div><Origem texto="hipótese" /></div></td>
                <td className="pr-3"><b className="text-pedra-forte">{num(p.to_be_min)} min</b><div><Origem texto={p.origem_to_be === "medido" ? "medido + conferência (hipótese)" : "estimado + conferência (hipótese)"} /></div></td>
                <td className="pr-3 font-semibold">{p.reducao_pct == null ? "—" : Math.round(p.reducao_pct * 100) + "%"}</td>
                <td className="pr-3">{reais(p.custo_tokens_brl)}</td>
                <td>{reais(p.ganho_por_tarefa_brl)}</td>
              </tr>
            ))}
            <tr className="font-semibold"><td className="py-3 pr-3">Uma tarefa de cada processo</td><td className="pr-3">{num(totais.as_is_min)} min</td>
              <td className="pr-3 text-pedra-forte">{num(totais.to_be_min)} min</td><td className="pr-3">{totais.reducao_pct == null ? "—" : Math.round(totais.reducao_pct * 100) + "%"}</td><td /><td>{reais(totais.ganho_por_rodada_brl)}</td></tr>
          </tbody>
        </table>
      </div>
      <p className="text-xs text-tinta-3">
        Premissas a validar num piloto: R$ {premissas.custo_hora}/h, {Math.round(premissas.aproveitamento * 100)}% do tempo liberado vira ganho,
        {" "}{Math.round(premissas.taxa_erro_manual * 100)}% de retrabalho manual. Onde houve execução no roteiro o TO BE é medido; senão, estimado.
      </p>
      <div className="flex flex-wrap gap-2 border-t border-linha pt-4">
        <Link className="botao-pedra" to="/financas/calculadora">Abrir a calculadora de ROI</Link>
        <Link className="botao-claro" to="/painel">Painel executivo</Link>
        <Link className="botao-claro" to="/financas">Finanças</Link>
        <Link className="botao-claro" to="/perguntas?persona=helena">Perguntas da Ferramenta</Link>
      </div>
    </section>
  );
}

export default function RoteiroPagina({ pessoa }: { pessoa: Persona }) {
  const { id = "" } = useParams();
  const [params] = useSearchParams();
  const gestor = pessoa.abas.includes("roteiros");
  // a página de AS IS × TO BE é do dono do roteiro e da Helena; quem só participa de um passo (quatro olhos) volta ao Início
  const podeVer = id === pessoa.roteiro_id || gestor;
  const q = useQuery({ queryKey: ["roteiro", id], staleTime: Infinity, queryFn: () => api<Roteiro>("/roteiros/" + id), enabled: podeVer });
  const ativo = useEstadoRoteiro();
  const { iniciar } = useControle();
  const [iniciando, setIniciando] = useState(false);
  const r = q.data;
  if (!podeVer) return <Navigate to="/" replace />;
  if (q.isError) return <p className="text-erro">{(q.error as Error).message}</p>;
  if (!r) return <p className="text-tinta-3">Carregando…</p>;
  const resultado = params.get("etapa") === "resultado";

  return (
    <div className="space-y-6 pb-24">
      <div className="flex flex-wrap items-center gap-4">
        <Avatar pessoa={r.persona_dados} tamanho={56} />
        <div className="min-w-0 flex-1">
          <div className="text-sm text-tinta-3">{r.persona_dados.cargo} · {r.persona_dados.area_nome}</div>
          <h1 className="text-3xl">{r.persona_dados.nome}</h1>
          <p className="mt-1 text-tinta-2">{r.titulo}</p>
        </div>
        {ativo?.id !== r.id && (
          <button className="botao-pedra" disabled={iniciando} onClick={async () => { setIniciando(true); try { await iniciar(r.id, r.persona); } finally { setIniciando(false); } }}>
            {iniciando ? "Preparando…" : "Iniciar este roteiro"}
          </button>
        )}
      </div>

      {resultado ? (r.id === "helena" ? <ConsolidadoHelena /> : <Resultado roteiro={r} gestor={gestor} />) : (
        <>
          <section className="caixa p-6">
            <h2 className="text-lg">A dor</h2>
            <p className="mt-1 text-tinta-2">{r.as_is.dor}</p>
          </section>
          <div className="grid gap-6 lg:grid-cols-2">
            <section className="caixa border-alerta/40 p-6">
              <div className="flex items-center justify-between">
                <h2 className="text-lg">AS IS · como é hoje</h2>
                {r.as_is.minutos > 0 && <span className="selo bg-alerta-fundo text-alerta">≈ {r.as_is.minutos} min · hipótese</span>}
              </div>
              <ol className="mt-3 list-decimal space-y-1.5 pl-5 text-sm">{r.as_is.passos.map((p) => <li key={p}>{p}</li>)}</ol>
              <h3 className="mt-4 text-sm font-semibold">Erros típicos</h3>
              <ul className="mt-1 list-disc space-y-1 pl-5 text-sm text-tinta-2">{r.as_is.erros.map((e) => <li key={e}>{e}</li>)}</ul>
            </section>
            <section className="caixa border-pedra/40 p-6">
              <div className="flex items-center justify-between">
                <h2 className="text-lg">TO BE · com o agente</h2>
                <span className="selo bg-pedra-fundo text-pedra-forte">{r.agente_nome ?? "governança"}</span>
              </div>
              <ol className="mt-3 list-decimal space-y-1.5 pl-5 text-sm">{r.to_be.passos.map((p) => <li key={p}>{p}</li>)}</ol>
              <p className="mt-4 text-xs text-tinta-3">{r.to_be.nota}</p>
            </section>
          </div>
          <section className="caixa p-6">
            <h2 className="text-lg">O que vamos medir</h2>
            <ul className="mt-2 flex flex-wrap gap-2">{r.valor.map((v) => <li key={v} className="selo bg-papel text-tinta-2">{v}</li>)}</ul>
            <p className="mt-3 text-xs text-tinta-3">
              Os tempos do AS IS são <b>hipóteses</b> a validar com a área. O que é medido na execução (tempo do agente e custo em tokens) é
              marcado como medido; a conferência humana e o custo da hora são premissas.
            </p>
          </section>
          <section className="caixa p-6">
            <h2 className="text-lg">Jornada deste roteiro</h2>
            <ol className="mt-3 grid gap-2 sm:grid-cols-2">
              {r.passos.map((p, i) => (
                <li key={p.id} className="flex gap-3 rounded-lg bg-papel p-3 text-sm">
                  <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-tinta text-xs font-bold text-white">{i + 1}</span>
                  <span><b>{p.titulo}</b><span className="block text-xs text-tinta-3">{p.perfil === r.persona ? "" : "com " + p.perfil + " · "}{p.acao}</span></span>
                </li>
              ))}
            </ol>
          </section>
        </>
      )}
    </div>
  );
}
