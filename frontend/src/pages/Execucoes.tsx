import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { api, type Execucao } from "../api/cliente";
import { COR_STATUS, NOME_STATUS, ms, quando, reais } from "../components/formato";

export default function Execucoes() {
  const q = useQuery({ queryKey: ["execucoes", "todas"], queryFn: () => api<Execucao[]>("/execucoes?limite=100") });
  return (
    <div className="space-y-6">
      <h1 className="text-3xl">Execuções</h1>
      <div className="caixa overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-papel text-left text-xs uppercase tracking-wide text-tinta-3">
            <tr>
              <th className="px-4 py-2.5">Status</th><th className="px-4 py-2.5">Agente</th><th className="px-4 py-2.5">Quem disparou</th>
              <th className="px-4 py-2.5 text-right">Custo</th><th className="px-4 py-2.5 text-right">Duração</th><th className="px-4 py-2.5 text-right">Quando</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-linha">
            {q.data?.map((e) => (
              <tr key={e.id} className="hover:bg-papel">
                <td className="px-4 py-2.5"><span className={"selo " + COR_STATUS[e.status]}>{NOME_STATUS[e.status] ?? e.status}</span></td>
                <td className="px-4 py-2.5"><Link className="font-medium hover:text-pedra-forte" to={"/execucoes/" + e.id}>{e.agente_nome}</Link>
                  {e.agente_id === "sandbox" && <span className="ml-2 text-xs text-tinta-3">teste</span>}
                  {e.rotina && <span className="selo ml-2 bg-info-fundo text-info" title={e.rotina.origem === "manual" ? "Rotina: Rodar agora" : "Rotina: disparou sozinha"}>rotina</span>}</td>
                <td className="px-4 py-2.5 text-tinta-2">{e.persona}</td>
                <td className="px-4 py-2.5 text-right">{reais(e.custo_brl)}</td>
                <td className="px-4 py-2.5 text-right text-tinta-2">{ms(e.duracao_estimada_ms)}</td>
                <td className="px-4 py-2.5 text-right text-tinta-3">{quando(e.inicio)}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {q.data?.length === 0 && <p className="p-5 text-sm text-tinta-3">Nenhuma execução ainda.</p>}
      </div>
    </div>
  );
}
