// Vitrine do marketplace de plugins homologados (simulado). A integração em si é feita aqui ou na página do plugin.
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Link } from "react-router-dom";
import { api, type PedidoPluginInterno, type Persona, type Plugin } from "../api/cliente";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { reais } from "../components/formato";
import { quando } from "../components/formato";
import { AcoesPlugin, classeSelo, COR_ESTADO_PLUGIN, IconeCategoria, NOME_ESTADO_PLUGIN, SeloDoPlugin } from "../components/Plugin";

const NOME_ESTADO_INTERNO: Record<PedidoPluginInterno["estado"], string> = {
  aguardando_analista: "aguardando a analista de IA", aguardando_seguranca: "aguardando a Segurança", aprovado: "aprovado",
  publicado: "publicado no marketplace", recusado: "recusado", removido: "removido",
};

function DecidirPedido({ x }: { x: PedidoPluginInterno }) {
  const qc = useQueryClient();
  const [parecer, setParecer] = useState("");
  const decidir = useMutation({
    mutationFn: (aprovar: boolean) => api<PedidoPluginInterno>(`/plugins-internos/${x.id}/${x.etapa}`, { aprovar, parecer }),
    onSuccess: () => { setParecer(""); qc.invalidateQueries({ queryKey: ["plugins-internos"] }); qc.invalidateQueries({ queryKey: ["plugins"] }); },
  });
  const n = x.estimativa;
  return (
    <div className="mt-3 w-full space-y-3 rounded-lg border border-linha bg-papel p-4" data-testid="decidir-plugin">
      <p className="text-xs font-semibold uppercase tracking-wide text-tinta-3">
        {x.etapa === "seguranca" ? "Aval de segurança (dado " + x.classificacao + ")" : "Decisão da analista de IA"}
        {x.exige_seguranca && x.etapa === "analista" && " · depois segue para a Segurança"}
      </p>
      <div className="grid gap-4 md:grid-cols-2">
        <div>
          <h4 className="text-sm font-semibold">O que foi pedido</h4>
          <p className="text-xs text-tinta-3">Ferramenta de mercado: {x.ferramenta_mercado}</p>
          <p className="mt-1 text-sm text-tinta-2">{x.finalidade}</p>
          <p className="mt-1 max-h-32 overflow-y-auto rounded bg-folha p-2 text-xs text-tinta-3">{x.descricao_publica}</p>
        </div>
        <div>
          <h4 className="text-sm font-semibold">Especificação interna proposta</h4>
          <p className="text-xs text-tinta-3">{x.spec.nome} · {x.areas.join(", ")} · dado {x.classificacao}</p>
          <ul className="mt-1 space-y-0.5 text-sm text-tinta-2">{x.spec.ferramentas.map((f) => <li key={f.id}>• {f.nome} <span className="text-xs text-tinta-3">({f.acao})</span></li>)}</ul>
          {n && <p className="mt-2 text-xs text-tinta-2">Comprar {reais(n.custo_3_anos_comprar_brl)} × construir {reais(n.custo_3_anos_construir_brl)} em 3 anos → tende a compensar <b>{n.recomendacao}</b></p>}
        </div>
      </div>
      <label className="block">
        <span className="rotulo">Parecer (obrigatório)</span>
        <textarea className="campo" rows={2} value={parecer} onChange={(e) => setParecer(e.target.value)} />
      </label>
      <div className="flex gap-2">
        <button className="botao-pedra" disabled={decidir.isPending || parecer.trim().length < 5} onClick={() => decidir.mutate(true)}>Aprovar</button>
        <button className="botao-claro" disabled={decidir.isPending || parecer.trim().length < 5} onClick={() => decidir.mutate(false)}>Recusar</button>
      </div>
      {decidir.isError && <p className="text-sm text-erro" role="alert">{(decidir.error as Error).message}</p>}
    </div>
  );
}

export default function Plugins({ pessoa }: { pessoa: Persona }) {
  const podePedir = pessoa.papeis.includes("criador") || pessoa.papeis.includes("engenharia");
  const pedidos = useQuery({ queryKey: ["plugins-internos"], queryFn: () => api<PedidoPluginInterno[]>("/plugins-internos"), refetchInterval: 8000 });
  const q = useQuery({ queryKey: ["plugins"], queryFn: () => api<Plugin[]>("/plugins") });
  const [categoria, setCategoria] = useState("");
  const [busca, setBusca] = useState("");
  const todos = q.data ?? [];
  const categorias = [...new Map(todos.map((p) => [p.categoria, p.categoria_nome])).entries()];
  const norm = (t: string) => t.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
  const lista = todos.filter((p) => (!categoria || p.categoria === categoria) && (!busca.trim() || norm(p.nome).includes(norm(busca.trim()))));

  return (
    <div className="space-y-6">
      <div>
        <div className="flex flex-wrap items-center gap-3">
          <h1 className="text-3xl">Plugins</h1>
<span className="selo bg-papel text-tinta-2" title="A maioria dos plugins é simulada; o Arquivos e Planilhas é de verdade">simulados · 1 real</span>
          {podePedir && <Link to="/plugins/criar" className="botao-pedra ml-auto">Crie o seu plugin</Link>}
        </div>
        <p className="mt-1 max-w-3xl text-tinta-2">
          Marketplace de integrações homologadas. Os plugins simulados nunca são executados: só as ferramentas que eles trazem; o Arquivos e Planilhas funciona de verdade. Integrar as coloca no
          Catálogo (governança) e como passo no Estúdio. Plugin com dado confidencial ou restrito passa pela aprovação da Segurança.
        </p>
      </div>

      <div className="flex flex-wrap items-center gap-3">
        <input className="campo max-w-xs" type="search" placeholder="Buscar plugin por nome" aria-label="Buscar plugin por nome"
          value={busca} onChange={(e) => setBusca(e.target.value)} />
        <div className="flex flex-wrap gap-2" role="group" aria-label="Filtrar por categoria">
          <button className={"selo px-3 py-1.5 text-sm " + (!categoria ? "bg-tinta text-white" : "bg-papel text-tinta-2")} onClick={() => setCategoria("")}>Todas as categorias</button>
          {categorias.map(([id, nome]) => (
            <button key={id} className={"selo px-3 py-1.5 text-sm " + (categoria === id ? "bg-tinta text-white" : "bg-papel text-tinta-2")} onClick={() => setCategoria(id)}>{nome}</button>
          ))}
        </div>
      </div>

      {pedidos.data && pedidos.data.length > 0 && (
        <section className="caixa p-5" aria-label="Pedidos de plugin">
          <h2 className="text-lg">Pedidos “Crie o seu plugin”</h2>
          <ul className="mt-2 divide-y divide-linha">
            {pedidos.data.map((x) => (
              <li key={x.id} className="flex flex-wrap items-center gap-2 py-2 text-sm">
                <b>{x.spec.nome}</b>
                <span className="selo bg-papel text-tinta-2">{NOME_ESTADO_INTERNO[x.estado]}</span>
                <span className="text-tinta-3">{x.meu ? "seu pedido" : "de " + x.solicitante_nome} · {quando(x.criado_em)}</span>
                {x.plugin_id && <Link className="ml-auto font-semibold text-pedra-forte" to={"/plugins/" + x.plugin_id}>Abrir plugin</Link>}
                {x.decisao_analista && !x.decisao_analista.aprovar && <span className="w-full text-xs text-erro">Recusado por {x.decisao_analista.por_nome}: {x.decisao_analista.parecer}</span>}
                {x.decisao_seguranca && !x.decisao_seguranca.aprovar && <span className="w-full text-xs text-erro">Recusado pela Segurança: {x.decisao_seguranca.parecer}</span>}
                {x.pode_decidir && <DecidirPedido x={x} />}
              </li>
            ))}
          </ul>
        </section>
      )}

      {q.isError && <p className="text-erro">{(q.error as Error).message}</p>}
      {q.data && lista.length === 0 && <p className="caixa p-5 text-tinta-3">Nenhum plugin com esses filtros.</p>}
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {lista.map((p) => (
          <article key={p.id} className="caixa flex flex-col p-5" aria-label={p.nome}>
            <div className="flex items-start gap-3">
              <IconeCategoria categoria={p.categoria} />
              <div className="min-w-0 flex-1">
                <h2 className="truncate text-lg leading-tight"><Link to={"/plugins/" + p.id} className="hover:text-pedra-forte">{p.nome}</Link></h2>
                <div className="mt-0.5 text-xs text-tinta-3">{p.categoria_nome}</div>
              </div>
              <SeloDoPlugin real={p.real} interno={p.interno} />
            </div>
            <p className="mt-3 text-sm text-tinta-2">{p.descricao}</p>
            <ul className="mt-3 space-y-1 text-sm">
              {p.ferramentas.map((f) => (
                <li key={f.id} className="flex items-center gap-2">
                  <span className={"selo " + (f.acao === "escrita" ? "bg-alerta-fundo text-alerta" : "bg-papel text-tinta-2")}>{f.acao}</span>
                  <span className="truncate">{f.nome}</span>
                </li>
              ))}
            </ul>
            <div className="mt-3 flex flex-wrap items-center gap-1.5">
              <span className={"selo " + classeSelo(p.classificacao)}>{p.classificacao}</span>
              <span className={"selo " + COR_ESTADO_PLUGIN[p.estado]}>{NOME_ESTADO_PLUGIN[p.estado]}</span>
              {p.sensivel && <span className="selo bg-alerta-fundo text-alerta">integrar pede aprovação</span>}
            </div>
            <p className="mt-2 text-xs text-tinta-3">Áreas: {p.areas_nomes.join(", ")}</p>
            <p className={"mt-1 text-sm font-medium " + (p.vale_para_minha_area ? "text-pedra-forte" : "text-tinta-3")}>
              {p.vale_para_minha_area ? "✓ Vale para a sua área" : "✕ Não é homologado para a sua área"}
            </p>
            <div className="mt-auto pt-4">
              <div className="flex flex-wrap items-center gap-2">
                <Link to={"/plugins/" + p.id} className="botao-claro">Detalhes</Link>
              </div>
              <div className="mt-2"><AcoesPlugin p={p} /></div>
            </div>
          </article>
        ))}
      </div>
    </div>
  );
}
