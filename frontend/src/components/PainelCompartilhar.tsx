import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { api, type Processo } from "../api/cliente";

export type Area = { id: string; nome: string };

/** As áreas da empresa (as mesmas que o menu do perfil conhece), em ordem alfabética. */
export const useAreas = () => useQuery({ queryKey: ["areas"], queryFn: () => api<Area[]>("/areas"), staleTime: 5 * 60_000 });

/**
 * Compartilhar um processo com outras áreas (e parar de compartilhar). Quem recebe passa a ver e executar o processo, mas só a
 * área dona o edita; a mudança vai para a trilha e os alertas abertos passam a chegar a quem recebe. Só aparece para quem edita.
 */
export default function PainelCompartilhar({ p, aoFechar }: { p: Processo; aoFechar: () => void }) {
  const qc = useQueryClient();
  const areas = useAreas();
  const [marcadas, setMarcadas] = useState<string[]>(p.compartilhado_com ?? []);
  const salvar = useMutation({
    mutationFn: () => api<Processo>(`/processos/${p.id}/compartilhar`, { areas: marcadas }),
    onSuccess: () => {
      for (const k of ["processo", "processos", "execucoes", "alertas", "notificacoes", "mapa"]) qc.invalidateQueries({ queryKey: [k] });
      aoFechar();
    },
  });
  const outras = (areas.data ?? []).filter((a) => a.id !== p.area);
  const alterou = [...marcadas].sort().join() !== [...(p.compartilhado_com ?? [])].sort().join();
  const alternar = (id: string) => setMarcadas((m) => (m.includes(id) ? m.filter((x) => x !== id) : [...m, id]));

  return (
    <section className="caixa space-y-3 p-5" aria-labelledby="titulo-compartilhar" data-testid="painel-compartilhar">
      <div>
        <h2 id="titulo-compartilhar" className="text-lg">Compartilhar com outras áreas</h2>
        <p className="mt-1 text-sm text-tinta-2">
          Quem recebe vê o processo, o histórico e os alertas dele e pode executá-lo. Só a sua área o edita. Tirar a marca devolve o processo só à sua área, na hora.
        </p>
      </div>
      <fieldset className="flex flex-wrap gap-x-6 gap-y-2" disabled={salvar.isPending}>
        <legend className="sr-only">Áreas com acesso</legend>
        {areas.isPending && <p className="text-sm text-tinta-3">Carregando as áreas…</p>}
        {outras.map((a) => (
          <label key={a.id} className="flex items-center gap-2 text-sm">
            <input type="checkbox" className="h-4 w-4 accent-[rgb(var(--pedra))]" checked={marcadas.includes(a.id)} onChange={() => alternar(a.id)} />
            {a.nome}
          </label>
        ))}
      </fieldset>
      {salvar.isError && <p className="text-sm text-erro" role="alert">{(salvar.error as Error).message}</p>}
      <div className="flex gap-2">
        <button className="botao-pedra" disabled={!alterou || salvar.isPending} onClick={() => salvar.mutate()}>
          {salvar.isPending ? "Salvando…" : alterou && marcadas.length === 0 ? "Parar de compartilhar" : "Salvar"}
        </button>
        <button className="botao-claro" onClick={aoFechar} disabled={salvar.isPending}>Cancelar</button>
      </div>
    </section>
  );
}
