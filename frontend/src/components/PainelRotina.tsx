import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link } from "react-router-dom";
import { api, type Campo, type Persona, type RelogioRotinas, type Rotina } from "../api/cliente";
import CampoEntrada from "./CampoEntrada";
import { usePreenche } from "../roteiro/estado";
import { quando } from "./formato";

const DIAS = ["segunda", "terça", "quarta", "quinta", "sexta", "sábado", "domingo"];

/** Agenda de rotina do agente: "toda segunda às 9h" com uma entrada fixa. Roda em nome de quem agendou. */
export default function PainelRotina({ agenteId, campos, pessoa, editor }: { agenteId: string; campos: Campo[]; pessoa: Persona; editor: boolean }) {
  const qc = useQueryClient();
  const rotinas = useQuery({ queryKey: ["rotinas", agenteId], queryFn: () => api<Rotina[]>(`/agentes/${agenteId}/rotinas`), refetchInterval: 5000 });
  const relogio = useQuery({ queryKey: ["relogio-rotinas"], queryFn: () => api<RelogioRotinas>("/rotinas/relogio"), refetchInterval: 3000 });
  const pre = usePreenche("rotina");   // roteiro guiado: a agenda do passo já vem preenchida
  const [freq, setFreq] = useState<"semanal" | "diaria">(pre?.frequencia ?? "semanal");
  const [dia, setDia] = useState(typeof pre?.dia_semana === "number" ? pre.dia_semana : 0);
  const [hora, setHora] = useState(pre?.hora ?? "09:00");
  const [entrada, setEntrada] = useState<Record<string, string>>(pre?.entrada ?? {});
  const [aviso, setAviso] = useState<string | null>(null);

  const recarregar = () => {
    qc.invalidateQueries({ queryKey: ["rotinas", agenteId] });
    qc.invalidateQueries({ queryKey: ["execucoes"] });
    qc.invalidateQueries({ queryKey: ["agente", agenteId] });
    qc.invalidateQueries({ queryKey: ["mapa"] });
  };
  const criar = useMutation({
    mutationFn: () => {
      const [h, m] = hora.split(":").map(Number);
      return api<Rotina>(`/agentes/${agenteId}/rotinas`, { frequencia: freq, dia_semana: freq === "semanal" ? dia : null, hora: h, minuto: m, entrada });
    },
    onSuccess: () => { setAviso(null); recarregar(); },
    onError: (e: Error) => setAviso(e.message),
  });
  const agir = useMutation({
    mutationFn: ({ id, rota, metodo }: { id: string; rota: string; metodo?: string }) => api<unknown>(`/rotinas/${id}${rota}`, metodo === "DELETE" ? undefined : {}, metodo),
    onSuccess: (r) => {
      const d = r as { status?: string; motivo?: string | null };
      setAviso(d?.status === "pulada" ? `Rotina pulada: ${d.motivo}` : d?.status === "aguardando_aprovacao" ? "A rotina parou esperando a confirmação de uma pessoa." : null);
      recarregar();
    },
    onError: (e: Error) => setAviso(e.message),
  });
  const relogioMut = useMutation({
    mutationFn: (corpo: { avancar_horas?: number; zerar?: boolean }) => api<RelogioRotinas>("/rotinas/relogio", corpo),
    onSuccess: (r) => { qc.setQueryData(["relogio-rotinas"], r); recarregar(); },
    onError: (e: Error) => setAviso(e.message),
  });

  const lista = rotinas.data ?? [];
  return (
    <section className="caixa p-5" aria-label="Rotina do agente">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-lg">Rotina</h2>
        {relogio.data?.demo && (
          <div className="flex flex-wrap items-center gap-2 text-xs text-tinta-3" aria-label="Relógio da demonstração">
            <span>Relógio da demo: <b className="text-tinta-2">{quando(relogio.data.agora)}</b></span>
            <button className="botao-claro px-2 py-1 text-xs" disabled={relogioMut.isPending} onClick={() => relogioMut.mutate({ avancar_horas: 24 })}>+1 dia</button>
            <button className="botao-claro px-2 py-1 text-xs" disabled={relogioMut.isPending} onClick={() => relogioMut.mutate({ avancar_horas: 24 * 7 })}>+1 semana</button>
            <button className="text-xs font-semibold text-tinta-3 hover:text-tinta" onClick={() => relogioMut.mutate({ zerar: true })}>voltar ao normal</button>
          </div>
        )}
      </div>
      <p className="mt-1 text-sm text-tinta-2">
        A plataforma roda o agente sozinha, com a entrada fixa abaixo, em nome de quem agendou: mesmas permissões, guardrails e orçamento. Ação sensível espera a confirmação de uma pessoa.
      </p>

      {lista.length === 0 && <p className="mt-3 text-sm text-tinta-3">Nenhuma rotina agendada.</p>}
      <ul className="mt-3 space-y-2">
        {lista.map((r) => (
          <li key={r.id} className="rounded-lg border border-linha p-3 text-sm">
            <div className="flex flex-wrap items-center gap-2">
              <b>{r.descricao}</b>
              <span className={"selo " + (r.ativa ? "bg-pedra-fundo text-pedra-forte" : "bg-alerta-fundo text-alerta")}>{r.ativa ? "ativa" : "pausada"}</span>
              <span className="text-xs text-tinta-3">por {r.dono}</span>
              <span className="ml-auto text-xs text-tinta-3">{r.ativa && r.proxima_em ? "próxima: " + quando(r.proxima_em) : ""}</span>
            </div>
            <p className="mt-1 text-xs text-tinta-3">
              Entrada fixa: {Object.entries(r.entrada).map(([k, v]) => `${k}: ${v}`).join(" · ")}
              {r.ultima_em && <> · última: {quando(r.ultima_em)} ({r.ultimo_resultado}){r.ultima_execucao_id && <> · <Link className="text-pedra-forte hover:underline" to={"/execucoes/" + r.ultima_execucao_id}>ver execução</Link></>}</>}
            </p>
            {r.pode_gerir && (
              <div className="mt-2 flex flex-wrap gap-2">
                <button className="botao-pedra px-3 py-1 text-xs" disabled={agir.isPending} onClick={() => agir.mutate({ id: r.id, rota: "/rodar" })}>
                  {agir.isPending ? "Rodando…" : "Rodar agora"}
                </button>
                {r.ativa
                  ? <button className="botao-claro px-3 py-1 text-xs" onClick={() => agir.mutate({ id: r.id, rota: "/pausar" })}>Pausar</button>
                  : <button className="botao-claro px-3 py-1 text-xs" onClick={() => agir.mutate({ id: r.id, rota: "/retomar" })}>Retomar</button>}
                <button className="botao-claro px-3 py-1 text-xs text-erro" onClick={() => agir.mutate({ id: r.id, rota: "", metodo: "DELETE" })}>Remover</button>
              </div>
            )}
          </li>
        ))}
      </ul>

      {editor && (
        <form className="mt-4 space-y-3 border-t border-linha pt-4" onSubmit={(ev) => { ev.preventDefault(); criar.mutate(); }}>
          <h3 className="text-base">Agendar uma rotina</h3>
          <div className="flex flex-wrap items-end gap-3">
            <label className="text-sm">Repete
              <select className="campo mt-1 w-auto" value={freq} onChange={(e) => setFreq(e.target.value as "semanal" | "diaria")}>
                <option value="semanal">toda semana</option><option value="diaria">todo dia</option>
              </select>
            </label>
            {freq === "semanal" && (
              <label className="text-sm">Dia
                <select className="campo mt-1 w-auto" value={dia} onChange={(e) => setDia(Number(e.target.value))}>
                  {DIAS.map((d, i) => <option key={d} value={i}>{d}</option>)}
                </select>
              </label>
            )}
            <label className="text-sm">Hora
              <input type="time" className="campo mt-1 w-auto" value={hora} onChange={(e) => setHora(e.target.value)} required />
            </label>
          </div>
          <div className="flex flex-wrap items-end gap-3">
            {campos.map((c) => (
              <CampoEntrada key={c.id} campo={c} pessoa={pessoa} valor={entrada[c.id] ?? ""} aoMudar={(v) => setEntrada((e) => ({ ...e, [c.id]: v }))} />
            ))}
          </div>
          <button className="botao-pedra" disabled={criar.isPending || campos.some((c) => !entrada[c.id])}>
            {criar.isPending ? "Agendando…" : "Agendar rotina"}
          </button>
        </form>
      )}
      {aviso && <p role="alert" className="mt-3 text-sm text-alerta">{aviso}</p>}
    </section>
  );
}
