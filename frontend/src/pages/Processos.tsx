import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { api, type Persona, type Processo } from "../api/cliente";
import { COR_ESTADO, COR_RISCO, NOME_ESTADO, NOME_RISCO, reais } from "../components/formato";

export default function Processos({ pessoa }: { pessoa: Persona }) {
  const q = useQuery({ queryKey: ["processos"], queryFn: () => api<Processo[]>("/processos") });
  return (
    <div className="space-y-6">
      <div className="flex items-end justify-between gap-4">
        <div>
          <h1 className="text-3xl">Processos</h1>
          <p className="mt-1 max-w-3xl text-tinta-2">
            Um processo é o fluxo de uma área, montado em blocos: dados, agentes, ações em plugins e aprovações. Cada um está ligado ao processo AS IS → TO BE da pessoa que o criou.
          </p>
        </div>
        {pessoa.papeis.includes("criador") && <Link to="/processos/novo" className="botao-pedra">Novo processo</Link>}
      </div>
      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
        {q.data?.map((p) => (
          <Link key={p.id} to={"/processos/" + p.id} className="caixa block p-4 transition hover:border-pedra" data-testid={"processo-" + p.id}>
            <div className="flex items-start justify-between gap-2">
              <h2 className="text-lg leading-snug">{p.nome}</h2>
              <span className={"selo shrink-0 " + COR_ESTADO[p.estado]}>{NOME_ESTADO[p.estado]}</span>
            </div>
            <p className="mt-1 text-sm text-tinta-3">Área {p.area} · dono {p.dono} · v{p.versao_publicada ?? "–"} no ar{p.ultima_versao !== p.versao_publicada ? ` · v${p.ultima_versao} em edição` : ""}</p>
            {p.as_is && <p className="mt-1 text-sm text-tinta-2">AS IS → TO BE: <b>{p.as_is.processo}</b></p>}
            <div className="mt-3 flex items-center gap-3 text-sm">
              <span className={"selo " + COR_RISCO[p.risco]}>{NOME_RISCO[p.risco]}</span>
              <span className="text-tinta-2">{p.execucoes} execuções</span>
              {p.escaladas > 0 && <span className="text-falcao">{p.escaladas} escaladas</span>}
              <span className="ml-auto text-tinta-3">{reais(p.custo_brl)}</span>
            </div>
          </Link>
        ))}
      </div>
      {q.data?.length === 0 && <p className="text-tinta-3">Nenhum processo visível para você ainda.</p>}
    </div>
  );
}
