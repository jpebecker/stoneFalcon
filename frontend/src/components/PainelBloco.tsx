import { useQuery } from "@tanstack/react-query";
import { api, type AgenteDisponivel, type Bloco } from "../api/cliente";
import { BLOCOS } from "./formato";

/** Painel lateral: configura o bloco selecionado, em linguagem de quem monta o processo. */
export default function PainelBloco({ bloco, problemas, aoMudar, aoRemover }: {
  bloco: Bloco; problemas: string[]; aoMudar: (b: Bloco) => void; aoRemover: () => void;
}) {
  const info = BLOCOS[bloco.tipo];
  const agentes = useQuery({ queryKey: ["processos", "agentes-disponiveis"], queryFn: () => api<AgenteDisponivel[]>("/processos/agentes-disponiveis") });
  const escolhido = agentes.data?.find((a) => a.id === bloco.agente_id);
  return (
    <div className="caixa space-y-4 p-4" data-testid="painel-bloco">
      <div className="flex items-center justify-between">
        <span className="text-xs font-semibold uppercase tracking-wide text-tinta-3"><span aria-hidden="true">{info.icone}</span> {info.nome}</span>
        <button className="text-xs font-semibold text-erro hover:underline" onClick={aoRemover}>Remover bloco</button>
      </div>
      <p className="text-xs text-tinta-3">{info.descricao}</p>
      <label className="block">
        <span className="rotulo">Título</span>
        <input className="campo" value={bloco.titulo} onChange={(e) => aoMudar({ ...bloco, titulo: e.target.value })} />
      </label>

      {bloco.tipo === "agente" && (
        <div>
          <span className="rotulo">Agente que faz esta tarefa</span>
          <select className="campo" value={bloco.agente_id ?? ""} onChange={(e) => aoMudar({ ...bloco, agente_id: e.target.value || null })} aria-label="Agente do bloco">
            <option value="">Escolha um agente…</option>
            {agentes.data?.map((a) => (
              <option key={a.id} value={a.id} disabled={!a.trabalhador}>
                {a.nome}{!a.publicado ? " (rascunho)" : ""}{!a.trabalhador ? " — formato antigo" : ""}
              </option>
            ))}
          </select>
          {escolhido && (
            <div className="mt-2 space-y-1 rounded-lg bg-papel p-2 text-xs text-tinta-2">
              <p>{escolhido.objetivo}</p>
              <p>Ferramentas: {escolhido.ferramentas.length ? escolhido.ferramentas.join(", ") : "nenhuma"} · modelo {escolhido.modelo === "auto" ? "automático" : escolhido.modelo}</p>
              {!escolhido.publicado && <p className="text-alerta">Ainda é rascunho: dá para testar, mas só publica o processo depois de publicar o agente.</p>}
            </div>
          )}
          {agentes.data?.some((a) => !a.trabalhador) && <p className="mt-1 text-xs text-tinta-3">Agentes de vários passos (formato antigo) não aparecem como opção: converta-os em processo.</p>}
        </div>
      )}

      {bloco.depende_de.length > 0 && <p className="text-xs text-tinta-3">Espera por: {bloco.depende_de.join(", ")}. Para mudar, arraste no canvas ou selecione a seta e apague.</p>}
      {problemas.length > 0 && <ul className="space-y-0.5 text-xs text-erro">{problemas.map((p) => <li key={p}>• {p}</li>)}</ul>}
    </div>
  );
}
