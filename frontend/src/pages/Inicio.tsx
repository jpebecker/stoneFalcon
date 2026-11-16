import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { api, type Execucao, type ItemRevisao, type Persona } from "../api/cliente";
import { COR_STATUS, NOME_STATUS, quando, reais } from "../components/formato";

export default function Inicio({ pessoa }: { pessoa: Persona }) {
  const execs = useQuery({ queryKey: ["execucoes"], queryFn: () => api<Execucao[]>("/execucoes?limite=8") });
  const pendentes = (execs.data ?? []).filter((e) => e.status === "aguardando_aprovacao");
  const criador = pessoa.papeis.includes("criador");
  const gestor = pessoa.papeis.includes("gestor_ia");
  const revisor = pessoa.papeis.includes("revisor_seguranca");
  const qc = useQueryClient();
  const revisoes = useQuery({ queryKey: ["revisoes"], queryFn: () => api<ItemRevisao[]>("/revisoes"), enabled: revisor });
  const reiniciar = useMutation({ mutationFn: () => api("/demo/reiniciar", {}), onSuccess: () => qc.invalidateQueries() });

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl">Olá, {pessoa.nome.split(" ")[0]}.</h1>
        <p className="mt-1 text-tinta-2">
          {criador ? "Que processo da sua rotina você quer automatizar hoje?"
            : gestor ? "Visão da empresa: retorno, custos e saúde de todos os agentes."
            : revisor ? "Governança: revisões de segurança e o catálogo de ferramentas."
            : "Acompanhe os agentes da sua área."}
        </p>
      </div>

      {criador && (
        <Link to="/estudio" className="caixa flex items-center justify-between gap-6 border-pedra/30 bg-pedra-fundo/40 p-6 transition hover:border-pedra">
          <div>
            <h2 className="text-xl">Criar um agente</h2>
            <p className="mt-1 text-sm text-tinta-2">Conte o que você faz, passo a passo, como contaria a um colega novo. O Estúdio monta o resto.</p>
          </div>
          <span className="botao-pedra">Abrir o Estúdio</span>
        </Link>
      )}

      {gestor && (
        <div className="grid gap-3 md:grid-cols-3">
          <Link to="/painel" className="caixa p-5 transition hover:border-pedra"><h2 className="text-lg">Painel executivo</h2><p className="mt-1 text-sm text-tinta-2">Os 5 indicadores da banca, medidos.</p></Link>
          <Link to="/financas" className="caixa p-5 transition hover:border-pedra"><h2 className="text-lg">Finanças</h2><p className="mt-1 text-sm text-tinta-2">Custo, retorno e orçamento por agente.</p></Link>
          <div className="caixa p-5">
            <h2 className="text-lg">Demonstração</h2>
            <p className="mt-1 text-sm text-tinta-2">Volta tudo ao estado inicial: 3 agentes publicados e 30 dias de histórico gerado.</p>
            <button className="botao-claro mt-3" disabled={reiniciar.isPending}
              onClick={() => confirm("Apagar tudo o que foi feito e voltar ao estado inicial da demonstração?") && reiniciar.mutate()}>
              {reiniciar.isPending ? "Reiniciando…" : reiniciar.isSuccess ? "Pronto" : "Reiniciar a demo"}
            </button>
          </div>
        </div>
      )}

      {revisor && (
        <div className="grid gap-3 md:grid-cols-2">
          <Link to="/revisoes" className="caixa p-5 transition hover:border-pedra">
            <h2 className="text-lg">Revisões de segurança</h2>
            <p className="mt-1 text-sm text-tinta-2">{revisoes.data?.length ? `${revisoes.data.length} versão(ões) esperando o seu parecer.` : "Nada esperando revisão."}</p>
          </Link>
          <Link to="/ferramentas" className="caixa p-5 transition hover:border-pedra">
            <h2 className="text-lg">Catálogo de ferramentas</h2>
            <p className="mt-1 text-sm text-tinta-2">Quem usa o quê, com que classificação. Simule falhas para testar os alertas.</p>
          </Link>
        </div>
      )}

      {pendentes.length > 0 && (
        <section className="caixa border-alerta/40 p-5">
          <h2 className="text-lg">Esperando a sua decisão</h2>
          <ul className="mt-3 divide-y divide-linha">
            {pendentes.map((e) => (
              <li key={e.id} className="flex items-center justify-between py-2.5 text-sm">
                <span><b>{e.agente_nome}</b> quer: {e.pendencia?.conector_nome ?? e.pendencia?.titulo}</span>
                <Link to={"/execucoes/" + e.id} className="botao-claro py-1">Revisar</Link>
              </li>
            ))}
          </ul>
        </section>
      )}

      <section>
        <div className="mb-3 flex items-baseline justify-between">
          <h2 className="text-lg">Execuções recentes</h2>
          <Link to="/execucoes" className="text-sm font-semibold text-pedra-forte">Ver todas</Link>
        </div>
        <div className="caixa divide-y divide-linha">
          {(execs.data ?? []).length === 0 && <p className="p-5 text-sm text-tinta-3">Nenhuma execução ainda.</p>}
          {execs.data?.map((e) => (
            <Link key={e.id} to={"/execucoes/" + e.id} className="flex items-center gap-4 px-5 py-3 text-sm hover:bg-papel">
              <span className={"selo " + COR_STATUS[e.status]}>{NOME_STATUS[e.status] ?? e.status}</span>
              <span className="flex-1 font-medium">{e.agente_nome}{e.agente_id === "sandbox" && <span className="ml-2 text-xs text-tinta-3">teste</span>}</span>
              <span className="text-tinta-3">{reais(e.custo_brl)}</span>
              <span className="w-32 text-right text-tinta-3">{quando(e.inicio)}</span>
            </Link>
          ))}
        </div>
      </section>
    </div>
  );
}
