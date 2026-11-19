// Vitrine do marketplace de plugins homologados (simulado). A integração em si é feita aqui ou na página do plugin.
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Link } from "react-router-dom";
import { api, type Plugin } from "../api/cliente";
import { AcoesPlugin, classeSelo, COR_ESTADO_PLUGIN, IconeCategoria, NOME_ESTADO_PLUGIN, SeloDoPlugin } from "../components/Plugin";

export default function Plugins() {
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
          <h1 className="text-3xl">Plugins</h1><span className="selo bg-papel text-tinta-2" title="A maioria dos plugins é simulada; o Arquivos e Planilhas é de verdade">simulados · 1 real</span>
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
              <SeloDoPlugin real={p.real} />
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
