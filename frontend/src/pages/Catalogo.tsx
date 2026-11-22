import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { api, type Ferramenta, type Persona } from "../api/cliente";

const COR_CLASSE: Record<string, string> = {
  publica: "bg-papel text-tinta-2", interna: "bg-info-fundo text-info",
  confidencial: "bg-alerta-fundo text-alerta", restrita: "bg-falcao-fundo text-falcao",
};

export default function Catalogo({ pessoa }: { pessoa: Persona }) {
  const qc = useQueryClient();
  const q = useQuery({ queryKey: ["ferramentas"], queryFn: () => api<{ modulos: Record<string, string>; ferramentas: Ferramenta[] }>("/ferramentas") });
  const engenharia = pessoa.papeis.includes("engenharia");
  const falha = useMutation({
    mutationFn: ({ id, valor }: { id: string; valor: string | null }) => api(`/ferramentas/${id}/falha`, { falha: valor }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["ferramentas"] }),
  });

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl">Ferramentas</h1>
        <p className="mt-1 max-w-2xl text-tinta-2">
          Conectores aprovados pela Engenharia de Plataforma e ferramentas de plugins integrados. Um agente só usa o que está aqui,
          e cada chamada roda com as permissões de quem disparou o agente. Para trazer uma ferramenta nova, veja a aba{" "}
          <Link to="/plugins" className="font-semibold text-pedra-forte">Plugins</Link>.
        </p>
      </div>
      {q.data && Object.entries(q.data.modulos).map(([mod, nome]) => (
        <section key={mod}>
          <h2 className="mb-2 text-sm font-semibold uppercase tracking-wide text-tinta-3">{nome}</h2>
          <div className="grid gap-3 md:grid-cols-2">
            {q.data.ferramentas.filter((f) => f.modulo === mod).map((f) => (
              <article key={f.id} className={"caixa p-4 " + (f.disponivel_para_mim ? "" : "opacity-70")}>
                <div className="flex items-start justify-between gap-3">
                  <h3 className="text-base">{f.nome}</h3>
                  <div className="flex shrink-0 gap-1.5">
                    {f.plugin && <Link to={"/plugins/" + f.plugin} className="selo bg-info-fundo text-info hover:underline">{f.origem}</Link>}
                    <span className={"selo " + COR_CLASSE[f.classificacao]}>{f.classificacao}</span>
                    <span className="selo bg-papel text-tinta-2">{f.acao}</span>
                  </div>
                </div>
                <p className="mt-1 text-sm text-tinta-2">{f.descricao}</p>
                <div className="mt-3 flex flex-wrap items-center gap-2 text-xs">
                  <span className={f.disponivel_para_mim ? "text-pedra-forte" : "text-erro"}>
                    {f.disponivel_para_mim ? "✓ Disponível para você" : "✕ " + f.motivo}
                  </span>
                  {f.exige_aprovacao && <span className="selo bg-alerta-fundo text-alerta">pede confirmação humana</span>}
                  {f.falha && <span className="selo bg-erro-fundo text-erro">falha simulada: {f.falha}</span>}
                </div>
                {engenharia && (
                  <label className="mt-3 flex items-center gap-2 text-xs text-tinta-3">
                    Simular falha
                    <select className="campo w-auto py-1 text-xs" data-alvo={f.id === "consultar_lojista" ? "acao-simular-falha" : undefined} value={f.falha ?? ""}
                      onChange={(e) => falha.mutate({ id: f.id, valor: e.target.value || null })}>
                      <option value="">nenhuma</option>
                      <option value="erro">erro</option>
                      <option value="lento">lentidão</option>
                      <option value="fora_do_ar">fora do ar</option>
                    </select>
                  </label>
                )}
              </article>
            ))}
          </div>
        </section>
      ))}
    </div>
  );
}
