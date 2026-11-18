import { useQuery } from "@tanstack/react-query";
import { api, type Ferramenta, type Passo, type RegistroModelos } from "../api/cliente";
import { NOME_TIPO } from "./formato";

export default function EditorPasso({ passo, ferramentas, aoMudar, aoRemover }: {
  passo: Passo; ferramentas: Ferramenta[]; aoMudar: (p: Passo) => void; aoRemover: () => void;
}) {
  const registro = useQuery({ queryKey: ["modelos"], queryFn: () => api<RegistroModelos>("/modelos"), staleTime: 60_000 });
  const opcoesModelo = [{ chave: "auto", nome: "Automático" }, ...(registro.data?.modelos ?? [])];
  const disponiveis = ferramentas.filter((f) => f.disponivel_para_mim);
  const nome = (id: string) => ferramentas.find((f) => f.id === id)?.nome ?? id;
  return (
    <div className="caixa space-y-4 p-4">
      <div className="flex items-center justify-between">
        <span className="text-xs font-semibold uppercase tracking-wide text-tinta-3">{NOME_TIPO[passo.tipo]}</span>
        <button className="text-xs font-semibold text-erro hover:underline" onClick={aoRemover}>Remover passo</button>
      </div>
      <label className="block">
        <span className="rotulo">Título</span>
        <input className="campo" value={passo.titulo} onChange={(e) => aoMudar({ ...passo, titulo: e.target.value })} />
      </label>

      {passo.tipo === "agente" && (
        <>
          <label className="block">
            <span className="rotulo">O que o agente deve fazer neste passo</span>
            <textarea className="campo min-h-[96px]" value={passo.instrucao}
              onChange={(e) => aoMudar({ ...passo, instrucao: e.target.value })} />
          </label>
          <div>
            <span className="rotulo">Modelo</span>
            <div className="flex gap-1.5">
              {opcoesModelo.map((m) => (
                <button key={m.chave} onClick={() => aoMudar({ ...passo, modelo: m.chave })}
                  className={"rounded-lg border px-3 py-1.5 text-xs font-semibold " +
                    (passo.modelo === m.chave || ("apelidos" in m && m.apelidos.includes(passo.modelo)) ? "border-pedra bg-pedra-fundo text-pedra-forte" : "border-linha text-tinta-2")}>
                  {m.nome}
                </button>
              ))}
            </div>
            <p className="mt-1 text-xs text-tinta-3">No automático, a plataforma usa o modelo mais barato que dá conta do passo.</p>
          </div>
          <div>
            <span className="rotulo">Ferramentas que pode acionar</span>
            <div className="space-y-1">
              {disponiveis.map((f) => (
                <label key={f.id} className="flex items-start gap-2 text-sm">
                  <input type="checkbox" className="mt-1 accent-[rgb(var(--pedra))]" checked={passo.ferramentas.includes(f.id)}
                    onChange={(e) => aoMudar({ ...passo, ferramentas: e.target.checked
                      ? [...passo.ferramentas, f.id] : passo.ferramentas.filter((x) => x !== f.id) })} />
                  <span>{f.nome}{f.exige_aprovacao && <span className="ml-1 text-xs text-alerta">(pede confirmação)</span>}</span>
                </label>
              ))}
            </div>
          </div>
        </>
      )}

      {passo.tipo === "ferramenta" && passo.ferramenta && (
        <div className="space-y-2 text-sm">
          <p><span className="rotulo inline">Consulta</span> {nome(passo.ferramenta)}</p>
          <pre className="rounded-lg bg-papel p-2 text-xs text-tinta-2">{JSON.stringify(passo.entrada, null, 2)}</pre>
          <p className="text-xs text-tinta-3">Valores entre chaves vêm da entrada do agente ou de passos anteriores.</p>
        </div>
      )}

      {passo.depende_de.length > 0 && (
        <p className="text-xs text-tinta-3">Espera: {passo.depende_de.join(", ")}. Para mudar, arraste no canvas ou selecione a seta e apague.</p>
      )}
    </div>
  );
}
