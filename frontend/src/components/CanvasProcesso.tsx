// Canvas do processo: cada bloco é um cartão colorido. Colunas = camadas (blocos da mesma coluna rodam ao mesmo tempo).
// Arrastar de um bloco a outro cria a dependência; a condição tem duas saídas, "sim" e "não". Selecionar e apagar remove.
import {
  Background, Controls, Handle, MarkerType, Position, ReactFlow,
  type Connection, type Edge, type Node, type NodeProps,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { useMemo } from "react";
import type { Bloco, ProcessoBlueprint } from "../api/cliente";
import { BLOCOS } from "./formato";

type DadosNo = { bloco: Bloco; subtitulo: string; selecionado: boolean; problemas: string[] };

const ENTRADA = "__entrada";

/** Camadas por ordem topológica; se houver ciclo (rascunho inválido) os blocos presos vão para a última coluna. */
export function camadas(blocos: Bloco[]): string[][] {
  const pend = new Map(blocos.map((b) => [b.id, new Set(b.depende_de.filter((d) => blocos.some((x) => x.id === d)))]));
  const feitos = new Set<string>();
  const saida: string[][] = [];
  while (pend.size) {
    const prontos = [...pend.keys()].filter((id) => [...pend.get(id)!].every((d) => feitos.has(d)));
    const camada = prontos.length ? prontos : [...pend.keys()];
    saida.push(blocos.map((b) => b.id).filter((id) => camada.includes(id)));
    camada.forEach((id) => { feitos.add(id); pend.delete(id); });
  }
  return saida;
}

function NoBloco({ data }: NodeProps<Node<DadosNo>>) {
  const { bloco, subtitulo, selecionado, problemas } = data;
  const info = BLOCOS[bloco.tipo];
  return (
    <div className={"w-64 rounded-xl border border-l-4 bg-folha px-3.5 py-3 shadow-caixa transition " + info.cor +
      (selecionado ? " ring-2 ring-pedra" : "") + (problemas.length ? " border-erro" : " border-linha")} data-testid={"bloco-" + bloco.id}>
      <Handle type="target" position={Position.Left} className="!h-2.5 !w-2.5 !bg-tinta-3" />
      <div className="flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wide text-tinta-3">
        <span aria-hidden="true">{info.icone}</span>{info.nome}
        {bloco.ramo && <span className={"selo ml-auto !py-0 " + (bloco.ramo.valor === "sim" ? "bg-pedra-fundo text-pedra-forte" : "bg-falcao-fundo text-falcao")}>
          se {bloco.ramo.valor === "sim" ? "sim" : "não"}</span>}
      </div>
      <div className="mt-0.5 text-sm font-semibold leading-snug text-tinta">{bloco.titulo}</div>
      {subtitulo && <div className="mt-1 truncate text-xs text-tinta-2">{subtitulo}</div>}
      {problemas.slice(0, 2).map((p) => <div key={p} className="mt-1 text-xs text-erro">{p}</div>)}
      {bloco.tipo === "condicao" ? (
        <>
          <Handle id="sim" type="source" position={Position.Right} style={{ top: "30%" }} className="!h-2.5 !w-2.5 !bg-pedra" />
          <Handle id="nao" type="source" position={Position.Right} style={{ top: "70%" }} className="!h-2.5 !w-2.5 !bg-falcao" />
          <span className="absolute -right-6 top-[18%] text-[10px] font-semibold text-pedra-forte">sim</span>
          <span className="absolute -right-6 top-[58%] text-[10px] font-semibold text-falcao">não</span>
        </>
      ) : <Handle type="source" position={Position.Right} className="!h-2.5 !w-2.5 !bg-pedra" />}
    </div>
  );
}

function NoEntrada({ data }: NodeProps<Node<{ campos: string[]; selecionado: boolean }>>) {
  return (
    <div className={"w-56 rounded-xl border border-l-4 bg-folha px-3.5 py-3 shadow-caixa " + BLOCOS.entrada.cor + (data.selecionado ? " ring-2 ring-pedra" : " border-linha")}
      data-testid="bloco-entrada">
      <div className="flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wide text-tinta-3"><span aria-hidden="true">{BLOCOS.entrada.icone}</span>Entradas</div>
      <div className="mt-0.5 text-sm font-semibold text-tinta">Quem roda preenche</div>
      <div className="mt-1 truncate text-xs text-tinta-2">{data.campos.length ? data.campos.join(" · ") : "nenhum campo"}</div>
      <Handle type="source" position={Position.Right} className="!h-2.5 !w-2.5 !bg-pedra" />
    </div>
  );
}

const tiposNo = { bloco: NoBloco, entrada: NoEntrada };

export default function CanvasProcesso({ bp, subtitulos, problemas, selecionado, aoSelecionar, aoMudar }: {
  bp: ProcessoBlueprint; subtitulos: Record<string, string>; problemas: Record<string, string[]>;
  selecionado: string | null; aoSelecionar: (id: string | null) => void; aoMudar: (bp: ProcessoBlueprint) => void;
}) {
  const { nos, arestas } = useMemo(() => {
    const cols = camadas(bp.blocos);
    const pos: Record<string, [number, number]> = {};
    cols.forEach((c, x) => c.forEach((id, y) => { pos[id] = [x + 1, y]; }));
    const nos: Node<DadosNo | { campos: string[]; selecionado: boolean }>[] = [
      { id: ENTRADA, type: "entrada", position: { x: 0, y: 0 }, data: { campos: bp.campos.map((c) => c.rotulo), selecionado: selecionado === ENTRADA } },
      ...bp.blocos.map((b) => ({
        id: b.id, type: "bloco", position: { x: pos[b.id][0] * 320, y: pos[b.id][1] * 140 },
        data: { bloco: b, subtitulo: subtitulos[b.id] ?? "", selecionado: selecionado === b.id, problemas: problemas[b.id] ?? [] },
      })),
    ];
    const arestas: Edge[] = bp.blocos.flatMap((b) => {
      const vindas: Edge[] = b.depende_de.map((d) => ({
        id: `${d}->${b.id}`, source: d, target: b.id, markerEnd: { type: MarkerType.ArrowClosed },
        sourceHandle: b.ramo && b.ramo.condicao === d ? b.ramo.valor : undefined,
        label: b.ramo && b.ramo.condicao === d ? (b.ramo.valor === "sim" ? "sim" : "não") : undefined,
      }));
      if (!b.depende_de.length) vindas.push({ id: `${ENTRADA}->${b.id}`, source: ENTRADA, target: b.id, markerEnd: { type: MarkerType.ArrowClosed }, deletable: false, style: { strokeDasharray: "4 4" } });
      return vindas;
    });
    return { nos, arestas };
  }, [bp, subtitulos, problemas, selecionado]);

  const conectar = (c: Connection) => {
    if (!c.source || !c.target || c.source === c.target || c.source === ENTRADA || c.target === ENTRADA) return;
    const origem = bp.blocos.find((b) => b.id === c.source);
    aoMudar({ ...bp, blocos: bp.blocos.map((b) => {
      if (b.id !== c.target) return b;
      const ramo: Bloco["ramo"] = origem?.tipo === "condicao" && (c.sourceHandle === "sim" || c.sourceHandle === "nao") ? { condicao: c.source!, valor: c.sourceHandle } : b.ramo;
      return { ...b, depende_de: b.depende_de.includes(c.source!) ? b.depende_de : [...b.depende_de, c.source!], ramo };
    }) });
  };

  const apagarArestas = (es: Edge[]) => {
    const fora = new Set(es.map((e) => e.id));
    aoMudar({ ...bp, blocos: bp.blocos.map((b) => {
      const depende_de = b.depende_de.filter((d) => !fora.has(`${d}->${b.id}`));
      return { ...b, depende_de, ramo: b.ramo && depende_de.includes(b.ramo.condicao) ? b.ramo : null };
    }) });
  };

  const apagarNos = (ns: Node[]) => {
    const ids = new Set(ns.map((n) => n.id).filter((id) => id !== ENTRADA));
    if (!ids.size) return;
    aoMudar({ ...bp, blocos: bp.blocos.filter((b) => !ids.has(b.id)).map((b) => {
      const depende_de = b.depende_de.filter((d) => !ids.has(d));
      return { ...b, depende_de, ramo: b.ramo && depende_de.includes(b.ramo.condicao) ? b.ramo : null };
    }) });
    aoSelecionar(null);
  };

  return (
    <div className="h-[480px] overflow-hidden rounded-caixa border border-linha bg-papel" data-testid="canvas-processo">
      <ReactFlow nodes={nos} edges={arestas} nodeTypes={tiposNo} fitView fitViewOptions={{ padding: 0.2 }}
        onNodeClick={(_, n) => aoSelecionar(n.id)} onPaneClick={() => aoSelecionar(null)}
        onConnect={conectar} onEdgesDelete={apagarArestas} onNodesDelete={apagarNos}
        nodesDraggable={false} deleteKeyCode={["Backspace", "Delete"]} proOptions={{ hideAttribution: true }}>
        <Background gap={20} size={1} color="rgb(var(--linha))" />
        <Controls showInteractive={false} />
      </ReactFlow>
    </div>
  );
}

export { ENTRADA };
