// Mapa de IA (só da Helena): quem criou -> agentes -> modelos (por provedor) -> plugins/ferramentas -> plataformas.
// A tela consulta o back a cada poucos segundos. O que entrou desde a última consulta aparece com uma animação de entrada
// e cada execução nova acende um pulso que percorre agente -> modelo -> ferramenta -> plataforma, na cor do resultado.
import {
  BaseEdge, Background, Controls, getSmoothStepPath, Handle, MarkerType, Position, ReactFlow, ReactFlowProvider, useReactFlow,
  type Edge, type EdgeProps, type Node, type NodeProps,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useMemo, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api, type ExecucaoRecenteMapa, type MapaIA, type NoMapa, type RelogioRotinas } from "../api/cliente";
import { COR_STATUS, NOME_STATUS, num, reais } from "../components/formato";

const INTERVALO_MS = 2500;      // consulta curta (padrão de Saúde e da página do plugin); sem infraestrutura nova
const LARGURA_COLUNA = 330;
const ALTURA_LINHA = 112;
const DESTAQUE_MS = 6000;       // quanto tempo um nó recém-chegado fica em destaque
const ETAPA_MS = 540;           // intervalo entre as etapas do pulso (agente -> modelo -> ferramenta -> plataforma)

type Dados = NoMapa & { novo: boolean };
type Pulso = { chave: string; cor: string; atraso: number };

const BORDA: Record<string, string> = {
  criador: "border-l-falcao", agente: "border-l-pedra", modelo: "border-l-info", ferramenta: "border-l-info", plugin: "border-l-info", sistema: "border-l-tinta-3",
};
const ROTULO_TIPO: Record<string, string> = {
  criador: "Criador", agente: "Agente", modelo: "Modelo", ferramenta: "Ferramenta", plugin: "Plugin", sistema: "Plataforma",
};
const COR_PROVEDOR: Record<string, string> = {
  anthropic: "var(--serie-1)", google: "var(--serie-2)", openai: "var(--serie-3)", deepseek: "var(--serie-4)", xai: "var(--serie-5)",
};
// cor do pulso = resultado da execução
const COR_PULSO: Record<string, string> = {
  concluida: "rgb(var(--pedra))", escalada: "rgb(var(--alerta))", falhou: "rgb(var(--erro))", negada: "rgb(var(--erro))",
  aguardando_aprovacao: "rgb(var(--info))", em_andamento: "rgb(var(--info))",
};

const reduzirMovimento = () => typeof window !== "undefined" && !!window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;

function No({ data }: NodeProps<Node<Dados>>) {
  const n = data;
  const removido = n.tipo === "plugin" && n.integrado === false;
  return (
    <div data-testid={"no-" + n.id} role="group" aria-label={`${ROTULO_TIPO[n.tipo]}: ${n.rotulo}`}
      style={n.tipo === "modelo" && n.provedor ? { borderLeftColor: COR_PROVEDOR[n.provedor] } : undefined}
      className={"mapa-no w-[250px] rounded-xl border border-l-4 bg-folha px-3.5 py-2.5 shadow-caixa " + BORDA[n.tipo] +
        (n.novo ? " mapa-no-novo ring-2 ring-pedra " : " ") + (removido ? " border-dashed border-erro " : " border-linha ") +
        (n.estado === "pausado" ? " opacity-60 " : "") + (n.rota ? " cursor-pointer hover:border-pedra" : "")}>
      <Handle type="target" position={Position.Left} className="!h-2 !w-2 !bg-tinta-3" />
      <div className="flex items-center gap-2 text-[11px] font-semibold uppercase tracking-wide text-tinta-3">
        <span>{ROTULO_TIPO[n.tipo]}{n.tipo === "sistema" && (n.externo ? " externa" : " da Stone")}{n.tipo === "modelo" && n.provedor_nome ? " · " + n.provedor_nome : ""}</span>
        {n.novo && <span className="selo bg-pedra-fundo text-pedra-forte">novo</span>}
        {removido && <span className="selo bg-erro-fundo text-erro">removido</span>}
        {n.estado === "pausado" && <span className="selo bg-alerta-fundo text-alerta">pausado</span>}
        {n.tipo === "modelo" && n.simulado && <span className="selo bg-alerta-fundo text-alerta">simulado</span>}
      </div>
      <div className="mt-0.5 truncate text-sm font-semibold leading-snug text-tinta" title={n.rotulo}>{n.rotulo}</div>
      <div className="mt-0.5 truncate text-xs text-tinta-2">
        {n.tipo === "agente" && `${num(n.execucoes)} execuções · ${reais(n.custo_brl ?? 0)}${n.risco ? " · risco " + n.risco : ""}`}
        {n.tipo === "criador" && `${n.detalhe ?? ""} · ${num(n.execucoes)} exec. · ${reais(n.custo_brl ?? 0)}`}
        {n.tipo === "modelo" && `${num(n.chamadas ?? 0)} chamadas · ${reais(n.custo_brl ?? 0)}`}
        {(n.tipo === "ferramenta" || n.tipo === "plugin") && `${n.detalhe ?? ""} · usada por ${n.usada_por ?? 0} · ${num(n.execucoes)} exec.`}
        {n.tipo === "sistema" && `${num(n.execucoes)} chamadas no período`}
      </div>
      <Handle type="source" position={Position.Right} className="!h-2 !w-2 !bg-pedra" />
    </div>
  );
}

/** Aresta que carrega os pulsos das execuções (um ponto que percorre o caminho; com "reduzir movimento", só um realce). */
function ArestaFluxo(p: EdgeProps<Edge<{ pulsos: Pulso[]; reduzir: boolean }>>) {
  const [caminho] = getSmoothStepPath({
    sourceX: p.sourceX, sourceY: p.sourceY, targetX: p.targetX, targetY: p.targetY,
    sourcePosition: p.sourcePosition, targetPosition: p.targetPosition,
  });
  const pulsos = p.data?.pulsos ?? [];
  const realce = pulsos[0];
  return (
    <>
      <BaseEdge id={p.id} path={caminho} markerEnd={p.markerEnd}
        style={p.data?.reduzir && realce ? { ...p.style, stroke: realce.cor, strokeWidth: 4 } : p.style} />
      {!p.data?.reduzir && pulsos.map((x) => (
        <circle key={x.chave} r={6} fill={x.cor} className="mapa-pulso-ponto" data-testid="pulso"
          style={{ offsetPath: `path("${caminho}")`, animationDelay: `${x.atraso}ms` }} />
      ))}
    </>
  );
}

const tiposNo = { no: No };
const tiposAresta = { fluxo: ArestaFluxo };

/** Posição de cada nó: uma coluna por camada, centradas na mesma altura; modelos agrupados por provedor. */
function disposicao(mapa: MapaIA): Record<string, { x: number; y: number }> {
  const ordem = mapa.colunas.map((c) => c.id);
  const grupos: Record<string, NoMapa[]> = Object.fromEntries(ordem.map((c) => [c, []]));
  mapa.nos.forEach((n) => grupos[n.coluna]?.push(n));
  const maior = Math.max(1, ...Object.values(grupos).map((g) => g.length));
  const pos: Record<string, { x: number; y: number }> = {};
  ordem.forEach((c, x) => {
    const g = grupos[c].sort((a, b) => (a.provedor ?? "").localeCompare(b.provedor ?? "") || a.rotulo.localeCompare(b.rotulo, "pt-BR"));
    const topo = ((maior - g.length) * ALTURA_LINHA) / 2;
    g.forEach((n, i) => { pos[n.id] = { x: x * LARGURA_COLUNA, y: topo + i * ALTURA_LINHA }; });
  });
  return pos;
}

type PulsoAtivo = { id: string; cor: string; arestas: [string, string, number][] };

function Quadro({ mapa, filtroChave }: { mapa: MapaIA; filtroChave: string }) {
  const navegar = useNavigate();
  const { fitView } = useReactFlow();
  const reduzir = useMemo(reduzirMovimento, []);
  const vistos = useRef<{ chave: string; nos: Set<string>; exec: Set<string> } | null>(null);
  const [recentes, setRecentes] = useState<Set<string>>(new Set());
  const [ativos, setAtivos] = useState<PulsoAtivo[]>([]);

  // o que chegou desde a última consulta ganha destaque; execuções novas viram pulsos (a primeira carga e a troca de filtro não animam)
  useEffect(() => {
    const nos = new Set(mapa.nos.map((n) => n.id));
    // execução ainda em andamento não pulsa: o pulso espera o resultado (para ter a cor e o caminho certos)
    const finalizadas = mapa.execucoes_recentes.filter((e) => e.status !== "em_andamento");
    const exec = new Set(finalizadas.map((e) => e.id));
    const antes = vistos.current;
    vistos.current = { chave: filtroChave, nos, exec };
    if (!antes || antes.chave !== filtroChave) return;
    const novosNos = [...nos].filter((id) => !antes.nos.has(id));
    const novasExec = finalizadas.filter((e) => !antes.exec.has(e.id));
    const timers: number[] = [];
    if (novosNos.length) {
      setRecentes((r) => new Set([...r, ...novosNos]));
      timers.push(window.setTimeout(() => setRecentes((r) => new Set([...r].filter((id) => !novosNos.includes(id)))), DESTAQUE_MS));
    }
    if (novasExec.length) {
      const novos: PulsoAtivo[] = novasExec.map((e: ExecucaoRecenteMapa) => ({ id: e.id, cor: COR_PULSO[e.status] ?? COR_PULSO.concluida, arestas: e.arestas }));
      setAtivos((a) => [...a, ...novos]);
      timers.push(window.setTimeout(() => setAtivos((a) => a.filter((p) => !novos.some((n) => n.id === p.id))), 3 * ETAPA_MS + (reduzir ? 2500 : 1200)));
    }
    return () => timers.forEach((t) => window.clearTimeout(t));
  }, [mapa, filtroChave, reduzir]);

  const assinatura = mapa.nos.map((n) => n.id).sort().join("|");
  useEffect(() => { const t = setTimeout(() => fitView({ padding: 0.12, duration: 300 }), 50); return () => clearTimeout(t); }, [assinatura, fitView]);

  const { nos, arestas } = useMemo(() => {
    const pos = disposicao(mapa);
    const nos: Node<Dados>[] = mapa.nos.map((n) => ({
      id: n.id, type: "no", position: pos[n.id] ?? { x: 0, y: 0 }, draggable: false,
      data: { ...n, novo: recentes.has(n.id) },
    }));
    const pulsosPorAresta = new Map<string, Pulso[]>();
    for (const p of ativos) {
      for (const [de, para, ordem] of p.arestas) {
        const k = `${de}->${para}`;
        pulsosPorAresta.set(k, [...(pulsosPorAresta.get(k) ?? []), { chave: `${p.id}-${ordem}`, cor: p.cor, atraso: ordem * ETAPA_MS }]);
      }
    }
    const maximo = Math.max(1, ...mapa.ligacoes.map((l) => l.volume));
    const porId = new Map(mapa.nos.map((n) => [n.id, n]));
    const arestas: Edge[] = mapa.ligacoes.map((l) => {
      const removido = porId.get(l.para)?.integrado === false;
      const id = `${l.de}->${l.para}`;
      return {
        id, source: l.de, target: l.para, type: "fluxo",
        markerEnd: { type: MarkerType.ArrowClosed },
        className: recentes.has(l.de) || recentes.has(l.para) ? "mapa-aresta-nova" : "",
        data: { pulsos: pulsosPorAresta.get(id) ?? [], reduzir },
        style: { strokeWidth: 1 + (l.volume / maximo) * 3, stroke: removido ? "rgb(var(--erro))" : undefined, strokeDasharray: removido ? "6 4" : undefined },
      };
    });
    return { nos, arestas };
  }, [mapa, recentes, ativos, reduzir]);

  return (
    <div className="h-[calc(100vh-300px)] min-h-[460px] min-w-0 flex-1 overflow-hidden rounded-caixa border border-linha bg-papel" data-testid="mapa-quadro">
      <ReactFlow nodes={nos} edges={arestas} nodeTypes={tiposNo} edgeTypes={tiposAresta} fitView fitViewOptions={{ padding: 0.12 }}
        nodesDraggable={false} nodesConnectable={false} elementsSelectable={false} minZoom={0.25}
        onNodeClick={(_, n) => { const r = (n.data as Dados).rota; if (r) navegar(r); }}
        proOptions={{ hideAttribution: true }}>
        <Background gap={20} size={1} color="rgb(var(--linha))" />
        <Controls showInteractive={false} />
      </ReactFlow>
    </div>
  );
}

function LinhaDoTempoMapa({ itens }: { itens: ExecucaoRecenteMapa[] }) {
  return (
    <aside className="caixa w-full shrink-0 p-3 lg:w-72" aria-label="Últimas execuções">
      <h2 className="rotulo">Últimas execuções</h2>
      {itens.length === 0 ? (
        <p className="text-sm text-tinta-3">Nenhuma execução no período. O mapa fica parado até alguém rodar um agente.</p>
      ) : (
        <ol className="max-h-[calc(100vh-380px)] space-y-1.5 overflow-auto">
          {itens.map((e) => (
            <li key={e.id}>
              <Link to={"/execucoes/" + e.id} className="block rounded-lg border border-linha px-2.5 py-1.5 text-xs hover:border-pedra">
                <div className="flex items-center gap-1.5">
                  <span className={"selo " + (COR_STATUS[e.status] ?? "")}>{NOME_STATUS[e.status] ?? e.status}</span>
                  {e.rotina && <span className="selo bg-info-fundo text-info">rotina</span>}
                  <span className="ml-auto text-tinta-3">{new Date(e.quando).toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" })}</span>
                </div>
                <div className="mt-0.5 truncate font-medium text-tinta">{e.agente}</div>
                <div className="truncate text-tinta-3">{e.modelos.join(" · ") || "sem modelo"} · {reais(e.custo_brl)}</div>
              </Link>
            </li>
          ))}
        </ol>
      )}
    </aside>
  );
}

/** Relógio da demonstração: avançar o tempo faz as rotinas vencidas dispararem sozinhas (e o pulso aparece no mapa). */
function RelogioDemo() {
  const qc = useQueryClient();
  const relogio = useQuery({ queryKey: ["relogio-rotinas"], queryFn: () => api<RelogioRotinas>("/rotinas/relogio"), refetchInterval: 4000 });
  const mover = useMutation({
    mutationFn: (corpo: { avancar_horas?: number; zerar?: boolean }) => api<RelogioRotinas>("/rotinas/relogio", corpo),
    onSuccess: (r) => { qc.setQueryData(["relogio-rotinas"], r); qc.invalidateQueries({ queryKey: ["mapa"] }); qc.invalidateQueries({ queryKey: ["execucoes"] }); },
  });
  if (!relogio.data?.demo || !relogio.data.pode_mexer) return null;
  return (
    <div className="flex flex-wrap items-center gap-2 text-xs text-tinta-3" aria-label="Relógio da demonstração">
      <span>Relógio da demo: <b className="text-tinta-2">{new Date(relogio.data.agora).toLocaleString("pt-BR", { dateStyle: "short", timeStyle: "short" })}</b></span>
      <button className="botao-claro px-2 py-1 text-xs" disabled={mover.isPending} onClick={() => mover.mutate({ avancar_horas: 24 })}>+1 dia</button>
      <button className="botao-claro px-2 py-1 text-xs" disabled={mover.isPending} onClick={() => mover.mutate({ avancar_horas: 24 * 7 })}>+1 semana</button>
      <button className="text-xs font-semibold text-tinta-3 hover:text-tinta" onClick={() => mover.mutate({ zerar: true })}>voltar ao normal</button>
    </div>
  );
}

export default function MapaIAPagina() {
  const [area, setArea] = useState("");
  const [provedor, setProvedor] = useState("");
  const consulta = `/mapa?dias=7${area ? "&area=" + encodeURIComponent(area) : ""}${provedor ? "&provedor=" + provedor : ""}`;
  const q = useQuery({ queryKey: ["mapa", area, provedor], queryFn: () => api<MapaIA>(consulta), refetchInterval: INTERVALO_MS,
    refetchIntervalInBackground: false, placeholderData: (anterior) => anterior });
  const m = q.data;
  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-3xl">Mapa de IA</h1>
          <p className="mt-1 max-w-3xl text-tinta-2">
            Tudo o que os colaboradores criaram, ao vivo: quem criou, os agentes publicados, os modelos de cada provedor, os plugins e ferramentas
            e as plataformas da Stone e externas que eles tocam. Cada execução acende um pulso pelo caminho dela.
          </p>
        </div>
        <p className="flex items-center gap-2 text-xs text-tinta-3" role="status">
          <span className={"inline-block h-2 w-2 rounded-full " + (q.isError ? "bg-erro" : "bg-pedra mapa-vivo")} aria-hidden="true" />
          {q.isError ? "Sem conexão com a plataforma" : "Ao vivo · atualiza a cada poucos segundos"}
        </p>
      </div>
      {m?.tem_demo && (
        <p className="rounded-caixa border border-alerta/40 bg-alerta-fundo/60 px-4 py-2 text-sm">
          Os números do período incluem o histórico de demonstração (cenário gerado, não é medição). Provedores que não são o Claude são simulados.
        </p>
      )}
      <div className="flex flex-wrap items-center gap-3 text-sm">
        <label className="flex items-center gap-2">Área
          <select className="campo w-auto" value={area} onChange={(e) => setArea(e.target.value)} aria-label="Filtrar por área">
            <option value="">Todas</option>
            {m?.filtros.areas.map((a) => <option key={a} value={a}>{a}</option>)}
          </select>
        </label>
        <label className="flex items-center gap-2">Provedor
          <select className="campo w-auto" value={provedor} onChange={(e) => setProvedor(e.target.value)} aria-label="Filtrar por provedor">
            <option value="">Todos</option>
            {m?.filtros.provedores.map((p) => <option key={p.id} value={p.id}>{p.nome}</option>)}
          </select>
        </label>
        <RelogioDemo />
        {(area || provedor) && <button className="text-xs font-semibold text-pedra-forte" onClick={() => { setArea(""); setProvedor(""); }}>limpar filtros</button>}
        {m && (
          <span className="selo ml-auto bg-pedra-fundo text-pedra-forte">
            {m.totais.agentes} agentes · {m.totais.modelos} modelos · {m.totais.plugins} plugins · {m.totais.ferramentas} ferramentas · {m.totais.plataformas} plataformas · {num(m.totais.execucoes)} execuções em {m.dias} dias
          </span>
        )}
      </div>
      {m ? (
        <div className="flex flex-col gap-4 lg:flex-row">
          <ReactFlowProvider><Quadro mapa={m} filtroChave={area + "|" + provedor} /></ReactFlowProvider>
          <LinhaDoTempoMapa itens={m.execucoes_recentes} />
        </div>
      ) : (
        <p className="text-tinta-3" aria-busy="true">{q.isError ? "Não consegui carregar o mapa." : "Carregando o mapa…"}</p>
      )}
    </div>
  );
}
