import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { api, type Agente, type Persona } from "../api/cliente";
import { COR_ESTADO, COR_RISCO, NOME_ESTADO, NOME_RISCO, reais } from "../components/formato";

export default function Agentes({ pessoa }: { pessoa: Persona }) {
  const q = useQuery({ queryKey: ["agentes"], queryFn: () => api<Agente[]>("/agentes") });
  return (
    <div className="space-y-6">
      <div className="flex items-end justify-between gap-4">
        <div>
          <h1 className="text-3xl">Agentes</h1>
          <p className="mt-1 text-tinta-2">Agentes que você pode ver: os da sua área e os compartilhados com ela.</p>
        </div>
        {pessoa.papeis.includes("criador") && <Link to="/estudio" className="botao-pedra">Criar agente</Link>}
      </div>
      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
        {q.data?.map((a) => (
          <Link key={a.id} to={"/agentes/" + a.id} className="caixa block p-4 transition hover:border-pedra">
            <div className="flex items-start justify-between gap-2">
              <h2 className="text-lg leading-snug">{a.nome}</h2>
              <span className={"selo shrink-0 " + COR_ESTADO[a.estado]}>{NOME_ESTADO[a.estado]}</span>
            </div>
            <p className="mt-1 text-sm text-tinta-3">Área {a.area} · dono {a.dono} · v{a.versao_publicada ?? "–"} no ar{a.ultima_versao !== a.versao_publicada ? ` · v${a.ultima_versao} em edição` : ""}</p>
            <div className="mt-3 flex items-center gap-3 text-sm">
              <span className={"selo " + COR_RISCO[a.risco]}>{NOME_RISCO[a.risco]}</span>
              <span className="text-tinta-2">{a.execucoes} execuções</span>
              {a.escaladas > 0 && <span className="text-falcao">{a.escaladas} escaladas</span>}
              {a.plugins_indisponiveis.length > 0 && <span className="selo bg-alerta-fundo text-alerta" title="Depende de plugin que não está integrado">plugin removido</span>}
              <span className="ml-auto text-tinta-3">{reais(a.custo_brl)}</span>
            </div>
          </Link>
        ))}
      </div>
      {q.data?.length === 0 && <p className="text-tinta-3">Nenhum agente visível para você ainda.</p>}
    </div>
  );
}
