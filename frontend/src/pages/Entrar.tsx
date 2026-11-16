import { useQuery } from "@tanstack/react-query";
import { api, type Persona } from "../api/cliente";
import Marca from "../components/Marca";

const PAPEL: Record<string, string> = {
  criador: "cria agentes", curador: "aprova conhecimento", revisor_seguranca: "revisa segurança",
  engenharia: "mantém o catálogo", gestor_ia: "vê custos e auditoria",
};

export default function Entrar({ aoEntrar }: { aoEntrar: (id: string) => void }) {
  const perfis = useQuery({ queryKey: ["perfis"], queryFn: () => api<Persona[]>("/perfis") });
  return (
    <div className="flex min-h-full items-center justify-center px-6 py-16">
      <div className="w-full max-w-3xl">
        <Marca />
        <h1 className="mt-8 text-4xl">A fábrica de agentes da Stone.</h1>
        <p className="mt-3 max-w-xl text-tinta-2">
          Descreva um processo e receba um agente pronto, ligado só às ferramentas que o seu papel permite,
          com guardrails, monitoramento e custo sob controle.
        </p>
        <h2 className="mt-10 text-sm font-semibold uppercase tracking-wide text-tinta-3">Entrar como (login simulado)</h2>
        {perfis.isError && <p className="mt-3 text-erro">Não consegui falar com o servidor. Ele está ligado?</p>}
        <div className="mt-3 grid gap-3 sm:grid-cols-2">
          {perfis.data?.map((p) => (
            <button key={p.id} onClick={() => aoEntrar(p.id)}
              className="caixa group p-4 text-left transition hover:border-pedra">
              <div className="font-titulo text-lg font-semibold group-hover:text-pedra-forte">{p.nome}</div>
              <div className="text-sm text-tinta-2">{p.cargo} · {p.area_nome}</div>
              <div className="mt-2 flex flex-wrap gap-1.5">
                {p.papeis.filter((x) => PAPEL[x]).map((x) => (
                  <span key={x} className="selo bg-papel text-tinta-2">{PAPEL[x]}</span>
                ))}
                <span className="selo bg-info-fundo text-info">acesso {p.nivel}</span>
              </div>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
