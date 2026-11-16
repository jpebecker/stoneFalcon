// Canvas do fluxo do agente. Colunas = camadas do grafo (passos da mesma coluna rodam
// em paralelo). Arrastar de um passo a outro cria dependência; selecionar e apagar remove.
import {
  Background, Controls, Handle, MarkerType, Position, ReactFlow,
  type Connection, type Edge, type Node, type NodeProps,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { useMemo } from "react";
import type { Blueprint, Passo } from "../api/cliente";
import { NOME_TIPO } from "./formato";

type DadosNo = { passo: Passo; modelo: string | null; selecionado: boolean; semPermissao: boolean };

const COR_TIPO: Record<string, string> = {
  ferramenta: "border-l-info", agente: "border-l-pedra", aprovacao: "border-l-alerta",
};

function NoPasso({ data }: NodeProps<Node<DadosNo>>) {
  const { passo, modelo, selecionado, semPermissao } = data;
  return (
    <div className={"w-60 rounded-xl border border-l-4 bg-folha px-3.5 py-3 shadow-caixa transition " + COR_TIPO[passo.tipo] +
      (selecionado ? " ring-2 ring-pedra" : "") + (semPermissao ? " border-erro" : " border-linha")}>
      <Handle type="target" position={Position.Left} className="!h-2.5 !w-2.5 !bg-tinta-3" />
      <div className="text-[11px] font-semibold uppercase tracking-wide text-tinta-3">{NOME_TIPO[passo.tipo]}</div>
      <div className="mt-0.5 text-sm font-semibold leading-snug text-tinta">{passo.titulo}</div>
      <div className="mt-1.5 truncate text-xs text-tinta-2">
        {passo.tipo === "ferramenta" && passo.ferramenta}
        {passo.tipo === "agente" && (modelo ?? "modelo automático") + (passo.ferramentas.length ? " · " + passo.ferramentas.length + " ferramenta(s)" : "")}
        {passo.tipo === "aprovacao" && "espera confirmação"}
      </div>
      {semPermissao && <div className="mt-1 text-xs text-erro">sem permissão para você</div>}
      <Handle type="source" position={Position.Right} className="!h-2.5 !w-2.5 !bg-pedra" />
    </div>
  );
}

const tiposNo = { passo: NoPasso };

export default function Canvas({ bp, niveis, modelos, semPermissao, selecionado, aoSelecionar, aoMudar }: {
  bp: Blueprint; niveis: string[][]; modelos: Record<string, string | null>; semPermissao: Set<string>;
  selecionado: string | null; aoSelecionar: (id: string | null) => void; aoMudar: (bp: Blueprint) => void;
}) {
  const { nos, arestas } = useMemo(() => {
    const coluna: Record<string, [number, number]> = {};
    (niveis.length ? niveis : [bp.passos.map((p) => p.id)]).forEach((camada, x) =>
      camada.forEach((id, y) => { coluna[id] = [x, y]; }));
    const nos: Node<DadosNo>[] = bp.passos.map((p, i) => {
      const [x, y] = coluna[p.id] ?? [0, i];
      const usa = [p.ferramenta, ...p.ferramentas].filter(Boolean) as string[];
      return {
        id: p.id, type: "passo", position: { x: x * 310, y: y * 130 },
        data: { passo: p, modelo: modelos[p.id] ?? null, selecionado: selecionado === p.id,
                semPermissao: usa.some((f) => semPermissao.has(f)) },
      };
    });
    const arestas: Edge[] = bp.passos.flatMap((p) => p.depende_de.map((d) => ({
      id: `${d}->${p.id}`, source: d, target: p.id, markerEnd: { type: MarkerType.ArrowClosed },
    })));
    return { nos, arestas };
  }, [bp, niveis, modelos, semPermissao, selecionado]);

  const conectar = (c: Connection) => {
    if (!c.source || !c.target || c.source === c.target) return;
    aoMudar({ ...bp, passos: bp.passos.map((p) => p.id === c.target && !p.depende_de.includes(c.source!)
      ? { ...p, depende_de: [...p.depende_de, c.source!] } : p) });
  };

  const apagarArestas = (es: Edge[]) => {
    const fora = new Set(es.map((e) => e.id));
    aoMudar({ ...bp, passos: bp.passos.map((p) => ({ ...p, depende_de: p.depende_de.filter((d) => !fora.has(`${d}->${p.id}`)) })) });
  };

  return (
    <div className="h-[460px] overflow-hidden rounded-caixa border border-linha bg-papel">
      <ReactFlow nodes={nos} edges={arestas} nodeTypes={tiposNo} fitView fitViewOptions={{ padding: 0.25 }}
        onNodeClick={(_, n) => aoSelecionar(n.id)} onPaneClick={() => aoSelecionar(null)}
        onConnect={conectar} onEdgesDelete={apagarArestas} nodesDraggable={false} deleteKeyCode={["Backspace", "Delete"]}
        proOptions={{ hideAttribution: true }}>
        <Background gap={20} size={1} color="rgb(var(--linha))" />
        <Controls showInteractive={false} />
      </ReactFlow>
    </div>
  );
}
