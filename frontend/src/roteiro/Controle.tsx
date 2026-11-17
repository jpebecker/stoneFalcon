// Controle do roteiro guiado: iniciar, avançar, voltar, reiniciar e a barra fixa com o passo atual.
// Trocar de passo troca o perfil sozinho e leva para a tela do passo.
import { useQueryClient } from "@tanstack/react-query";
import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from "react";
import { useNavigate } from "react-router-dom";
import { api, perfilAtual, type Roteiro } from "../api/cliente";
import { definirRoteiro, estadoAtual, resolverRota, useRoteiro } from "./estado";

type Controle = {
  iniciar: (roteiroId: string, personaId: string) => Promise<void>;
  ir: (roteiro: Roteiro, passo: number) => Promise<void>;
  sair: () => void;
  reiniciar: () => Promise<void>;
  mostrarProva: (p: { perfil: string; rota: string; roteiro: string; passo: string | null }) => Promise<void>;
};

const Ctx = createContext<Controle | null>(null);
export const useControle = () => useContext(Ctx)!;

export function ProvedorRoteiro({ trocar, children }: { trocar: (id: string | null) => void; children: ReactNode }) {
  const navegar = useNavigate();
  const qc = useQueryClient();

  const ir = useCallback(async (roteiro: Roteiro, i: number) => {
    const n = Math.max(0, Math.min(i, roteiro.passos.length - 1));
    const passo = roteiro.passos[n];
    // abrir outra aba exige o gesto do clique: tem de acontecer antes de qualquer await (senão o Chrome bloqueia)
    if (passo.externa) window.open(passo.rota, "_blank", "noopener");
    const est = estadoAtual();
    definirRoteiro({ id: roteiro.id, passo: n, ctx: est?.id === roteiro.id ? est.ctx : {} });
    if (perfilAtual() !== passo.perfil) trocar(passo.perfil);
    if (passo.externa) return;
    navegar(await resolverRota(passo.rota));
  }, [navegar, trocar]);

  const iniciar = useCallback(async (roteiroId: string, personaId: string) => {
    trocar(personaId);                             // entra como a persona do roteiro (atualiza a tela e os cabeçalhos)
    await api(`/roteiros/${roteiroId}/reiniciar`, {});
    qc.clear();
    definirRoteiro({ id: roteiroId, passo: 0, ctx: {} });
    const r = await api<Roteiro>("/roteiros/" + roteiroId);
    qc.setQueryData(["roteiro", roteiroId], r);
    await ir(r, 0);
  }, [ir, qc, trocar]);

  const reiniciar = useCallback(async () => {
    const est = estadoAtual();
    if (!est) return;
    await api(`/roteiros/${est.id}/reiniciar`, {});
    qc.clear();
    const r = await api<Roteiro>("/roteiros/" + est.id);
    qc.setQueryData(["roteiro", est.id], r);
    definirRoteiro({ id: est.id, passo: 0, ctx: {} });
    await ir(r, 0);
  }, [ir, qc]);

  const sair = useCallback(() => definirRoteiro(null), []);

  // "Mostrar na tela" das perguntas da banca: abre a tela de prova com o perfil certo e,
  // se a prova é um passo de roteiro, posiciona o roteiro nesse passo.
  const mostrarProva = useCallback(async (p: { perfil: string; rota: string; roteiro: string; passo: string | null }) => {
    if (p.rota.startsWith("/demo/")) window.open(p.rota, "_blank", "noopener");   // antes de qualquer await
    if (p.passo) {
      try {
        const r = await api<Roteiro>("/roteiros/" + p.roteiro);
        const i = r.passos.findIndex((x) => x.id === p.passo);
        const est = estadoAtual();
        definirRoteiro({ id: p.roteiro, passo: Math.max(i, 0), ctx: est?.id === p.roteiro ? est.ctx : {} });
        qc.setQueryData(["roteiro", p.roteiro], r);
      } catch { /* sem roteiro: só abre a tela */ }
    }
    if (perfilAtual() !== p.perfil) trocar(p.perfil);
    if (p.rota.startsWith("/demo/")) return;
    navegar(await resolverRota(p.rota));
  }, [navegar, qc, trocar]);

  const valor = useMemo(() => ({ iniciar, ir, sair, reiniciar, mostrarProva }), [iniciar, ir, sair, reiniciar, mostrarProva]);
  return <Ctx.Provider value={valor}>{children}</Ctx.Provider>;
}

export function BarraRoteiro() {
  const { estado, roteiro, passo } = useRoteiro();
  const c = useControle();
  const [fala, setFala] = useState(false);
  const [ocupado, setOcupado] = useState(false);
  if (!estado || !roteiro || !passo) return null;
  const total = roteiro.passos.length;
  const i = Math.min(estado.passo, total - 1);
  const comOcupado = async (f: () => Promise<void>) => { setOcupado(true); try { await f(); } finally { setOcupado(false); } };

  return (
    <div role="region" aria-label="Roteiro guiado" className="fixed inset-x-0 bottom-0 z-40 border-t border-white/10 bg-tinta text-white shadow-[0_-8px_24px_rgb(0_0_0/0.25)]">
      {fala && (
        <div className="border-b border-white/10 bg-white/5 px-6 py-2.5 text-sm text-white/85">
          <b className="text-pedra">Fala sugerida:</b> {passo.fala}
        </div>
      )}
      <div className="flex flex-wrap items-center gap-x-5 gap-y-2 px-6 py-3">
        <div className="min-w-0">
          <div className="text-xs uppercase tracking-wide text-white/50">Roteiro · {roteiro.persona_dados.nome.split(" ")[0]} · {roteiro.processo}</div>
          <div className="truncate font-titulo text-base font-semibold">Passo {i + 1} de {total} · {passo.titulo}</div>
        </div>
        <p className="min-w-[220px] flex-1 text-sm text-white/80">{passo.acao}{passo.externa && " (abre em outra aba)"}</p>
        <div className="flex items-center gap-2">
          <span className="mr-1 hidden gap-1 sm:flex" aria-hidden="true">
            {roteiro.passos.map((p, k) => <span key={p.id} className={"h-1.5 w-5 rounded-full " + (k < i ? "bg-pedra" : k === i ? "bg-white" : "bg-white/20")} />)}
          </span>
          <button className="rounded-lg border border-white/20 px-3 py-1.5 text-sm hover:bg-white/10" onClick={() => setFala(!fala)} aria-pressed={fala}>Fala</button>
          <button className="rounded-lg border border-white/20 px-3 py-1.5 text-sm hover:bg-white/10 disabled:opacity-40" disabled={i === 0 || ocupado}
            onClick={() => comOcupado(() => c.ir(roteiro, i - 1))}>Voltar</button>
          <button className="rounded-lg bg-pedra px-4 py-1.5 text-sm font-semibold hover:bg-pedra-forte disabled:opacity-40" disabled={i >= total - 1 || ocupado}
            onClick={() => comOcupado(() => c.ir(roteiro, i + 1))}>Avançar</button>
          <button className="rounded-lg border border-white/20 px-3 py-1.5 text-sm hover:bg-white/10 disabled:opacity-40" disabled={ocupado}
            title="Volta a plataforma ao estado exato do início deste roteiro"
            onClick={() => confirm("Reiniciar este roteiro? Isso apaga o que foi criado nele e volta ao início.") && comOcupado(c.reiniciar)}>Reiniciar</button>
          <button className="rounded-lg px-2 py-1.5 text-sm text-white/60 hover:text-white" onClick={c.sair} aria-label="Sair do roteiro">Sair</button>
        </div>
      </div>
    </div>
  );
}
