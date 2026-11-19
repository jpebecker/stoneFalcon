// Arquivos e Planilhas (o plugin real): enviar CSV/XLSX, escolher classificação e áreas, ver a prévia e baixar a versão atual.
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRef, useState } from "react";
import { api, ErroApi, perfilAtual, type ArquivoPlugin, type LimitesArquivos, type Persona } from "../api/cliente";
import { classeSelo } from "./Plugin";
import { quando } from "./formato";

const AREAS: [string, string][] = [
  ["atendimento", "Atendimento"], ["risco", "Prevenção a Fraudes"], ["pessoas", "Pessoas (RH)"], ["logistica", "Logística"],
  ["engenharia", "Engenharia de Plataforma"], ["gestao", "CoE de IA"],
];

function paraBase64(buf: ArrayBuffer): string {
  let s = "";
  const bytes = new Uint8Array(buf);
  for (let i = 0; i < bytes.length; i += 0x8000) s += String.fromCharCode(...bytes.subarray(i, i + 0x8000));
  return btoa(s);
}

async function baixar(a: ArquivoPlugin) {
  const resp = await fetch(`/api/v1/plugins/arquivos/arquivos/${a.id}/download`, { headers: { "X-Usuario": perfilAtual() ?? "" } });
  if (!resp.ok) throw new ErroApi(resp.status, ((await resp.json().catch(() => ({}))) as { detail?: string }).detail ?? "Não consegui baixar o arquivo.");
  const url = URL.createObjectURL(await resp.blob());
  const link = document.createElement("a");
  link.href = url; link.download = a.nome; link.click();
  setTimeout(() => URL.revokeObjectURL(url), 2000);
}

function Previa({ a }: { a: ArquivoPlugin }) {
  const q = useQuery({ queryKey: ["arquivo", a.id, a.versao], queryFn: () => api<ArquivoPlugin>("/plugins/arquivos/arquivos/" + a.id) });
  const d = q.data;
  if (q.isError) return <p className="text-sm text-erro">{(q.error as Error).message}</p>;
  if (!d) return <p className="text-sm text-tinta-3">Carregando a prévia…</p>;
  return (
    <div className="overflow-x-auto rounded-lg border border-linha" data-testid="previa-arquivo">
      <table className="w-full min-w-[480px] text-sm">
        <thead className="bg-papel text-left text-xs uppercase tracking-wide text-tinta-3">
          <tr><th className="px-3 py-2">#</th>{d.colunas.map((c) => <th key={c} className="px-3 py-2">{c}</th>)}</tr>
        </thead>
        <tbody className="divide-y divide-linha">
          {(d.previa ?? []).map((l, i) => (
            <tr key={i}><td className="px-3 py-1.5 text-tinta-3">{i + 1}</td>{d.colunas.map((c) => <td key={c} className="px-3 py-1.5">{String(l[c] ?? "")}</td>)}</tr>
          ))}
        </tbody>
      </table>
      {d.total_linhas > (d.previa?.length ?? 0) && (
        <p className="border-t border-linha bg-papel px-3 py-1.5 text-xs text-tinta-3">Mostrando as primeiras {d.previa?.length} de {d.total_linhas} linhas. Baixe o arquivo para ver tudo.</p>
      )}
    </div>
  );
}

export default function ArquivosPlugin({ pessoa }: { pessoa: Persona }) {
  const qc = useQueryClient();
  const entrada = useRef<HTMLInputElement>(null);
  const lista = useQuery({ queryKey: ["arquivos"], queryFn: () => api<ArquivoPlugin[]>("/plugins/arquivos/arquivos"), refetchInterval: 5000 });
  const limites = useQuery({ queryKey: ["arquivos-limites"], queryFn: () => api<LimitesArquivos>("/plugins/arquivos/arquivos/limites") });
  const [aberto, setAberto] = useState<string | null>(null);
  const [classificacao, setClassificacao] = useState("interna");
  const [areas, setAreas] = useState<string[]>([]);
  const [todas, setTodas] = useState(false);
  const [aviso, setAviso] = useState<string | null>(null);

  const enviar = useMutation({
    mutationFn: async (arq: File) => api<ArquivoPlugin>("/plugins/arquivos/arquivos", {
      nome: arq.name, conteudo_base64: paraBase64(await arq.arrayBuffer()), classificacao, areas: todas ? ["*"] : areas,
    }),
    onSuccess: (a) => { setAviso(null); setAberto(a.id); qc.invalidateQueries({ queryKey: ["arquivos"] }); if (entrada.current) entrada.current.value = ""; },
    onError: (e: Error) => setAviso(e.message),
  });
  const remover = useMutation({
    mutationFn: (id: string) => api(`/plugins/arquivos/arquivos/${id}`, undefined, "DELETE"),
    onSuccess: () => { setAberto(null); qc.invalidateQueries({ queryKey: ["arquivos"] }); },
    onError: (e: Error) => setAviso(e.message),
  });
  const lim = limites.data;
  const permitidas = lim?.classificacoes ?? ["publica", "interna"];

  return (
    <section className="caixa space-y-4 p-6" aria-label="Arquivos do plugin">
      <div className="flex flex-wrap items-center gap-2">
        <h2 className="text-lg">Arquivos</h2>
        <span className="selo bg-pedra-fundo text-pedra-forte" title="Este plugin funciona de verdade, sem internet">real</span>
      </div>
      <p className="text-sm text-tinta-3">
        Envie uma planilha (CSV ou Excel) e escolha quem pode usá-la. Agentes e processos leem e escrevem nela pelas ferramentas abaixo,
        com dado pessoal protegido antes de qualquer modelo e tudo na auditoria.
      </p>

      <div className="grid gap-3 rounded-lg bg-papel p-4 md:grid-cols-[1fr_auto]">
        <div className="space-y-3">
          <label className="block">
            <span className="rotulo">Arquivo (.csv ou .xlsx)</span>
            <input ref={entrada} type="file" accept=".csv,.xlsx" className="campo" aria-label="Arquivo para enviar" />
            {lim && <span className="mt-1 block text-xs text-tinta-3">Até {lim.bytes / 1_000_000} MB, {lim.linhas.toLocaleString("pt-BR")} linhas e {lim.colunas} colunas. A primeira linha tem o nome das colunas.</span>}
          </label>
          <div className="flex flex-wrap gap-4">
            <label className="block">
              <span className="rotulo">Classificação</span>
              <select className="campo" value={classificacao} onChange={(e) => setClassificacao(e.target.value)} aria-label="Classificação do arquivo">
                {["publica", "interna", "confidencial", "restrita"].map((c) => (
                  <option key={c} value={c} disabled={!permitidas.includes(c)}>{c}{permitidas.includes(c) ? "" : " (acima do seu nível)"}</option>
                ))}
              </select>
              {(classificacao === "confidencial" || classificacao === "restrita") && (
                <span className="mt-1 block text-xs text-alerta">Escrever neste arquivo pede a confirmação de uma pessoa.</span>
              )}
            </label>
            <fieldset>
              <legend className="rotulo">Quem pode usar</legend>
              <div className="flex flex-wrap gap-x-3 gap-y-1 text-sm">
                <label className="flex items-center gap-1"><input type="checkbox" checked={todas} onChange={(e) => setTodas(e.target.checked)} /> todas as áreas</label>
                {AREAS.map(([id, nome]) => (
                  <label key={id} className="flex items-center gap-1">
                    <input type="checkbox" disabled={todas || id === pessoa.area} checked={todas || id === pessoa.area || areas.includes(id)}
                      onChange={(e) => setAreas((a) => (e.target.checked ? [...a, id] : a.filter((x) => x !== id)))} /> {nome}
                  </label>
                ))}
              </div>
              <span className="text-xs text-tinta-3">A sua área sempre pode usar.</span>
            </fieldset>
          </div>
        </div>
        <button className="botao-pedra self-end" disabled={enviar.isPending}
          onClick={() => { const f = entrada.current?.files?.[0]; if (!f) { setAviso("Escolha um arquivo CSV ou XLSX."); return; } enviar.mutate(f); }}>
          {enviar.isPending ? "Enviando…" : "Enviar arquivo"}
        </button>
      </div>
      {aviso && <p className="rounded-lg bg-erro-fundo p-3 text-sm text-erro" role="alert">{aviso}</p>}

      {lista.data?.length === 0 && <p className="text-sm text-tinta-3">Nenhum arquivo que a sua área e o seu nível de acesso possam usar ainda.</p>}
      <ul className="divide-y divide-linha">
        {lista.data?.map((a) => (
          <li key={a.id} className="space-y-3 py-3">
            <div className="flex flex-wrap items-center gap-2 text-sm">
              <button className="font-semibold hover:text-pedra-forte" onClick={() => setAberto(aberto === a.id ? null : a.id)} aria-expanded={aberto === a.id}>{a.nome}</button>
              <span className={"selo " + classeSelo(a.classificacao)}>{a.classificacao}</span>
              <span className="text-tinta-3">{a.total_linhas} linhas · {a.colunas.length} colunas · v{a.versao}</span>
              <span className="text-tinta-3">áreas: {a.areas_nomes.join(", ")}</span>
              <span className="ml-auto text-xs text-tinta-3">mudou em {quando(a.atualizado_em)}</span>
              <button className="botao-claro py-1" onClick={() => baixar(a).catch((e: Error) => setAviso(e.message))}>Baixar</button>
              {a.pode_remover && <button className="botao-claro py-1" disabled={remover.isPending} onClick={() => remover.mutate(a.id)}>Remover</button>}
            </div>
            {aberto === a.id && <Previa a={a} />}
          </li>
        ))}
      </ul>
    </section>
  );
}
