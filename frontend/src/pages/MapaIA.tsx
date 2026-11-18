// Mapa de IA (só da Helena): quem criou -> agentes -> plugins/ferramentas -> plataformas, atualizado sozinho.
// A tela consulta o back a cada poucos segundos; o que entrou desde a última consulta aparece com uma animação de entrada.
import {
  Background, Controls, Handle, MarkerType, Position, ReactFlow, ReactFlowProvider, useReactFlow,
  type Edge, type Node, type NodeProps,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { useQuery } from "@tanstack/react-query";
import { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, type MapaIA, type NoMapa } from "../api/cliente";
import { num, reais } from "../components/formato";

const INTERVALO_MS = 2500;      // consulta curta (padrão de Saúde e da página do plugin); sem infraestrutura nova
const LARGURA_COLUNA = 330;
const ALTURA_LINHA = 112;
const DESTAQUE_MS = 6000;       // quanto tempo um nó recém-chegado fica em destaque

type Dados = NoMapa & { novo: boolean };

const BORDA: Record<string, string> = {
  criador: "border-l-falcao", agente: "border-l-pedra", ferramenta: "border-l-info", plugin: "border-l-info", sistema: "border-l-tinta-3",
};
const ROTULO_TIPO: Record<string, string> = {
  criador: "Criador", agente: "Agente", ferramenta: "Ferramenta", plugin: "Plugin", sistema: "Plataforma",
};

function No({ data }: NodeProps<Node<Dados>>) {
  const n = data;
  const removido = n.tipo === "plugin" && n.integrado === false;
  return (
    <div data-testid={"no-" + n.id} role="group" aria-label={`${ROTULO_TIPO[n.tipo]}: ${n.rotulo}`}
      className={"mapa-no w-[250px] rounded-xl border border-l-4 bg-folha px-3.5 py-2.5 shadow-caixa " + BORDA[n.tipo] +
        (n.novo ? " mapa-no-novo ring-2 ring-pedra " : " ") + (removido ? " border-dashed border-erro " : " border-linha ") +
        (n.estado === "pausado" ? " opacity-60 " : "") + (n.rota ? " cursor-pointer hover:border-pedra" : "")}>
      <Handle type="target" position={Position.Left} className="!h-2 !w-2 !bg-tinta-3" />
      <div className="flex items-center gap-2 text-[11px] font-semibold uppercase tracking-wide text-tinta-3">
        <span>{ROTULO_TIPO[n.tipo]}{n.tipo === "sistema" && (n.externo ? " externa" : " da Stone")}</span>
        {n.novo && <span className="selo bg-pedra-fundo text-pedra-forte">novo</span>}
        {removido && <span className="selo bg-erro-fundo text-erro">removido</span>}
        {n.estado === "pausado" && <span className="selo bg-alerta-fundo text-alerta">pausado</span>}
      </div>
      <div className="mt-0.5 truncate text-sm font-semibold leading-snug text-tinta" title={n.rotulo}>{n.rotulo}</div>
      <div className="mt-0.5 truncate text-xs text-tinta-2">
        {n.tipo === "agente" && `${num(n.execucoes)} execuções · ${reais(n.custo_brl ?? 0)}${n.risco ? " · risco " + n.risco : ""}`}
        {n.tipo === "criador" && `${n.detalhe ?? ""} · ${num(n.execucoes)} execuções`}
        {(n.tipo === "ferramenta" || n.tipo === "plugin") && `${n.detalhe ?? ""} · usada por ${n.usada_por ?? 0}`}
        {n.tipo === "sistema" && `${num(n.execucoes)} chamadas no período`}
      </div>
      <Handle type="source" position={Position.Right} className="!h-2 !w-2 !bg-pedra" />
    </div>
  );
}

const tiposNo = { no: No };

/** Posição de cada nó: uma coluna por camada, centradas na mesma altura. */
function disposicao(mapa: MapaIA): Record<string, { x: number; y: number }> {
  const ordem = mapa.colunas.map((c) => c.id);
  const grupos: Record<string, NoMapa[]> = Object.fromEntries(ordem.map((c) => [c, []]));
  mapa.nos.forEach((n) => grupos[n.coluna]?.push(n));
  const maior = Math.max(1, ...Object.values(grupos).map((g) => g.length));
  const pos: Record<string, { x: number; y: number }> = {};
  ordem.forEach((c, x) => {
    const g = grupos[c].sort((a, b) => a.rotulo.localeCompare(b.rotulo, "pt-BR"));
    const topo = ((maior - g.length) * ALTURA_LINHA) / 2;
    g.forEach((n, i) => { pos[n.id] = { x: x * LARGURA_COLUNA, y: topo + i * ALTURA_LINHA }; });
  });
  return pos;
}

function Quadro({ mapa }: { mapa: MapaIA }) {
  const navegar = useNavigate();
  const { fitView } = useReactFlow();
  const vistos = useRef<Set<string> | null>(null);
  const [recentes, setRecentes] = useState<Set<string>>(new Set());

  // o que chegou desde a última consulta ganha destaque (a primeira carga não anima nada)
  useEffect(() => {
    const ids = new Set(mapa.nos.map((n) => n.id));
    const antes = vistos.current;
    vistos.current = ids;
    if (!antes) return;
    const novos = [...ids].filter((id) => !antes.has(id));
    if (novos.length === 0) return;
    setRecentes((r) => new Set([...r, ...novos]));
    const t = setTimeout(() => setRecentes((r) => new Set([...r].filter((id) => !novos.includes(id)))), DESTAQUE_MS);
    return () => clearTimeout(t);
  }, [mapa]);

  const assinatura = mapa.nos.map((n) => n.id).sort().join("|");
  useEffect(() => { const t = setTimeout(() => fitView({ padding: 0.12, duration: 300 }), 50); return () => clearTimeout(t); }, [assinatura, fitView]);

  const { nos, arestas } = useMemo(() => {
    const pos = disposicao(mapa);
    const nos: Node<Dados>[] = mapa.nos.map((n) => ({
      id: n.id, type: "no", position: pos[n.id] ?? { x: 0, y: 0 }, draggable: false,
      data: { ...n, novo: recentes.has(n.id) },
    }));
    const maximo = Math.max(1, ...mapa.ligacoes.map((l) => l.volume));
    const porId = new Map(mapa.nos.map((n) => [n.id, n]));
    const arestas: Edge[] = mapa.ligacoes.map((l) => {
      const removido = porId.get(l.para)?.integrado === false;
      return {
        id: `${l.de}->${l.para}`, source: l.de, target: l.para, type: "smoothstep",
        markerEnd: { type: MarkerType.ArrowClosed },
        className: recentes.has(l.de) || recentes.has(l.para) ? "mapa-aresta-nova" : "",
        style: { strokeWidth: 1 + (l.volume / maximo) * 3, stroke: removido ? "rgb(var(--erro))" : undefined, strokeDasharray: removido ? "6 4" : undefined },
      };
    });
    return { nos, arestas };
  }, [mapa, recentes]);

  return (
    <div className="h-[calc(100vh-290px)] min-h-[460px] overflow-hidden rounded-caixa border border-linha bg-papel" data-testid="mapa-quadro">
      <ReactFlow nodes={nos} edges={arestas} nodeTypes={tiposNo} fitView fitViewOptions={{ padding: 0.12 }}
        nodesDraggable={false} nodesConnectable={false} elementsSelectable={false} minZoom={0.3}
        onNodeClick={(_, n) => { const r = (n.data as Dados).rota; if (r) navegar(r); }}
        proOptions={{ hideAttribution: true }}>
        <Background gap={20} size={1} color="rgb(var(--linha))" />
        <Controls showInteractive={false} />
      </ReactFlow>
    </div>
  );
}

export default function MapaIAPagina() {
  const q = useQuery({ queryKey: ["mapa"], queryFn: () => api<MapaIA>("/mapa?dias=7"), refetchInterval: INTERVALO_MS, refetchIntervalInBackground: false });
  const m = q.data;
  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-3xl">Mapa de IA</h1>
          <p className="mt-1 max-w-3xl text-tinta-2">
            Tudo o que os colaboradores criaram, ao vivo: quem criou, os agentes publicados, os plugins e ferramentas que eles usam e as
            plataformas da Stone e externas que eles tocam. Um agente publicado em outra janela aparece aqui sozinho.
          </p>
        </div>
        <p className="flex items-center gap-2 text-xs text-tinta-3" role="status">
          <span className={"inline-block h-2 w-2 rounded-full " + (q.isError ? "bg-erro" : "bg-pedra mapa-vivo")} aria-hidden="true" />
          {q.isError ? "Sem conexão com a plataforma" : "Ao vivo · atualiza a cada poucos segundos"}
        </p>
      </div>
      {m?.tem_demo && (
        <p className="rounded-caixa border border-alerta/40 bg-alerta-fundo/60 px-4 py-2 text-sm">
          Os números do período incluem o histórico de demonstração (cenário gerado, não é medição).
        </p>
      )}
      {m && (
        <ul className="flex flex-wrap gap-2 text-xs" aria-label="Totais">
          <li className="selo bg-papel text-tinta-2">{m.colunas.map((c) => c.rotulo).join(" → ")}</li>
          <li className="selo bg-pedra-fundo text-pedra-forte">{m.totais.agentes} agentes · {m.totais.plugins} plugins · {m.totais.ferramentas} ferramentas · {m.totais.plataformas} plataformas · {num(m.totais.execucoes)} execuções em {m.dias} dias</li>
        </ul>
      )}
      {m ? (
        <ReactFlowProvider><Quadro mapa={m} /></ReactFlowProvider>
      ) : (
        <p className="text-tinta-3" aria-busy="true">{q.isError ? "Não consegui carregar o mapa." : "Carregando o mapa…"}</p>
      )}
    </div>
  );
}
