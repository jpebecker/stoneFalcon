// Estado do roteiro em andamento: qual roteiro, em que passo e o que já foi criado.
// Fica no navegador (localStorage), então sobrevive a recarregar a página e a trocar de perfil.
import { useQuery } from "@tanstack/react-query";
import { useSyncExternalStore } from "react";
import { api, type PassoRoteiro, type Roteiro } from "../api/cliente";

const CHAVE = "stonefalcon.roteiro";

export type EstadoRoteiro = { id: string; passo: number; ctx: Record<string, string> };

let atual: EstadoRoteiro | null = null;
const ouvintes = new Set<() => void>();

function ler(): EstadoRoteiro | null {
  try {
    const bruto = localStorage.getItem(CHAVE);
    return bruto ? (JSON.parse(bruto) as EstadoRoteiro) : null;
  } catch {
    return null;
  }
}
atual = ler();

function gravar(e: EstadoRoteiro | null) {
  atual = e;
  try {
    if (e) localStorage.setItem(CHAVE, JSON.stringify(e));
    else localStorage.removeItem(CHAVE);
  } catch {
    /* navegação privada: segue só na memória */
  }
  ouvintes.forEach((f) => f());
}

export const definirRoteiro = (e: EstadoRoteiro | null) => gravar(e);
export const registrarCtx = (parcial: Record<string, string>) => {
  if (atual) gravar({ ...atual, ctx: { ...atual.ctx, ...parcial } });
};
export const estadoAtual = () => atual;

function assinar(f: () => void) {
  ouvintes.add(f);
  return () => ouvintes.delete(f);
}

export function useEstadoRoteiro(): EstadoRoteiro | null {
  return useSyncExternalStore(assinar, () => atual, () => null);
}

/** O roteiro ativo com os dados do passo atual. `passo` é null quando não há roteiro em andamento. */
export function useRoteiro(): { estado: EstadoRoteiro | null; roteiro: Roteiro | undefined; passo: PassoRoteiro | null } {
  const estado = useEstadoRoteiro();
  const q = useQuery({
    queryKey: ["roteiro", estado?.id], enabled: !!estado, staleTime: Infinity,
    queryFn: () => api<Roteiro>("/roteiros/" + estado!.id),
  });
  const passo = estado && q.data ? q.data.passos[Math.min(estado.passo, q.data.passos.length - 1)] : null;
  return { estado, roteiro: q.data, passo };
}

/** Valores que o passo atual já deixa preenchidos (só quando o roteiro está nesse passo). */
export function usePreenche(idPasso?: string | string[]) {
  const { passo } = useRoteiro();
  if (!passo) return null;
  const ids = idPasso === undefined ? null : Array.isArray(idPasso) ? idPasso : [idPasso];
  if (ids && !ids.includes(passo.id)) return null;
  return { passoId: passo.id, ...passo.preenche };
}

/** `{agente:Nome}` ou `{processo:Nome}` na rota vira o endereço do agente ou do processo com esse nome (o mais recente). */
export async function resolverRota(rota: string): Promise<string> {
  const m = rota.match(/\{(agente|processo):([^}]+)\}/);
  if (!m) return rota;
  const base = m[1] === "agente" ? "/agentes" : "/processos";
  try {
    const itens = await api<{ id: string; nome: string }[]>(base);
    const achado = itens.find((a) => a.nome === m[2]);
    return achado ? rota.replace(m[0], achado.id) : base;
  } catch {
    return base;
  }
}
