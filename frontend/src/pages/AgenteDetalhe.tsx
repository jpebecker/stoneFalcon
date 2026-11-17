import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api, type AgenteDetalhe as Detalhe, type Execucao, type Mudanca, type Persona, type Saude } from "../api/cliente";
import CampoEntrada from "../components/CampoEntrada";
import LinhaDoTempo from "../components/LinhaDoTempo";
import { usePreenche } from "../roteiro/estado";
import ListaMudancas from "../components/ListaMudancas";
import { COR_ESTADO, COR_RISCO, NOME_ESTADO, NOME_EVENTO, NOME_RISCO, quando, reais } from "../components/formato";

export default function AgenteDetalhe({ pessoa }: { pessoa: Persona }) {
  const { id } = useParams();
  const qc = useQueryClient();
  const q = useQuery({ queryKey: ["agente", id], queryFn: () => api<Detalhe>("/agentes/" + id) });
  const saude = useQuery({ queryKey: ["saude"], queryFn: () => api<Saude>("/saude") });
  const [entrada, setEntrada] = useState<Record<string, string>>({});
  const [exe, setExe] = useState<Execucao | null>(null);
  const [diff, setDiff] = useState<{ numero: number; mudancas: Mudanca[] } | null>(null);
  const pre = usePreenche("usar");
  useEffect(() => { setExe(null); setEntrada({}); }, [id]);   // outro agente: começa limpo
  useEffect(() => { if (pre?.entrada) { setEntrada(pre.entrada); setExe(null); } }, [pre?.passoId, id]); // eslint-disable-line react-hooks/exhaustive-deps

  const recarregar = () => { qc.invalidateQueries({ queryKey: ["agente", id] }); qc.invalidateQueries({ queryKey: ["agentes"] }); };
  const acao = useMutation({
    mutationFn: ({ rota, corpo }: { rota: string; corpo?: unknown }) => api(`/agentes/${id}/${rota}`, corpo ?? {}),
    onSuccess: recarregar,
  });
  const executar = useMutation({
    mutationFn: () => api<Execucao>(`/agentes/${id}/executar`, { entrada }),
    onSuccess: (e) => { setExe(e); recarregar(); },
  });
  const verDiff = async (numero: number) => {
    const mudancas = await api<Mudanca[]>(`/agentes/${id}/diff?de=${numero - 1}&para=${numero}`);
    setDiff({ numero, mudancas });
  };

  if (q.isError) return <p className="text-erro">{(q.error as Error).message}</p>;
  if (!q.data) return <p className="text-tinta-3">Carregando…</p>;
  const a = q.data;
  const publicada = a.versoes.find((v) => v.numero === a.versao_publicada);
  const ultima = a.versoes[0];
  const editor = pessoa.id === a.dono || (pessoa.papeis.includes("criador") && pessoa.area === a.area);
  const operador = editor || pessoa.papeis.includes("gestor_ia") || pessoa.papeis.includes("revisor_seguranca");
  const podeDepreciar = pessoa.id === a.dono || pessoa.papeis.includes("gestor_ia");
  const campos = publicada?.blueprint.campos ?? [];

  return (
    <div className="space-y-6">
      <Link to="/agentes" className="text-sm text-tinta-3 hover:text-tinta">← Agentes</Link>
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-3xl">{a.nome}</h1>
            <span className={"selo " + COR_ESTADO[a.estado]}>{NOME_ESTADO[a.estado]}</span>
            <span className={"selo " + COR_RISCO[a.risco]}>{NOME_RISCO[a.risco]}</span>
          </div>
          <p className="mt-1 text-tinta-2">{publicada?.blueprint.objetivo ?? ultima?.blueprint.objetivo}</p>
          <p className="mt-1 text-sm text-tinta-3">Área {a.area} · dono {a.dono} · {a.execucoes} execuções · {reais(a.custo_brl)} gastos</p>
          {a.motivo_estado && <p className="mt-2 text-sm text-alerta">Motivo: {a.motivo_estado}</p>}
        </div>
        <div className="flex flex-wrap gap-2">
          {editor && a.estado !== "depreciado" && <Link to={"/estudio?agente=" + a.id} className="botao-claro">Editar no Estúdio</Link>}
          {editor && ultima?.estado === "rascunho" && a.estado !== "depreciado" && (
            <button className="botao-pedra" onClick={() => acao.mutate({ rota: "publicar" })}>Publicar v{ultima.numero}</button>
          )}
          {operador && a.estado === "publicado" && (
            <button className="botao-claro" onClick={() => { const m = prompt("Motivo da pausa (opcional):") ?? ""; acao.mutate({ rota: "pausar", corpo: { motivo: m } }); }}>Pausar</button>
          )}
          {operador && a.estado === "pausado" && <button className="botao-claro" onClick={() => acao.mutate({ rota: "retomar" })}>Retomar</button>}
          {podeDepreciar && a.estado !== "depreciado" && (
            <button className="botao-claro text-erro" onClick={() => { const m = prompt("Por que depreciar este agente? Ele deixa de executar e não volta."); if (m) acao.mutate({ rota: "depreciar", corpo: { motivo: m } }); }}>Depreciar</button>
          )}
        </div>
      </div>
      {acao.isError && <p className="text-sm text-erro">{(acao.error as Error).message}</p>}

      <div className="grid gap-6 xl:grid-cols-[1fr_380px]">
        <div className="space-y-6">
          {a.pode_executar && a.estado === "publicado" && publicada && (
            <section className="caixa p-5">
              <h2 className="text-lg">Executar v{publicada.numero}</h2>
              <div className="mt-3 flex flex-wrap items-end gap-3">
                {campos.map((c) => (
                  <CampoEntrada key={c.id} campo={c} pessoa={pessoa} valor={entrada[c.id] ?? ""}
                    aoMudar={(v) => setEntrada((e) => ({ ...e, [c.id]: v }))} />
                ))}
                <button className="botao-pedra" disabled={executar.isPending || campos.some((c) => !entrada[c.id])} onClick={() => executar.mutate()}>
                  {executar.isPending ? "Executando…" : "Executar"}
                </button>
              </div>
              {executar.isError && <p className="mt-2 text-sm text-erro">{(executar.error as Error).message}</p>}
              {exe && <div className="mt-5 border-t border-linha pt-5"><LinhaDoTempo exe={exe} pessoa={pessoa} cotacao={saude.data?.cotacao_dolar ?? 5.52} aoMudar={setExe} /></div>}
            </section>
          )}

          <section className="caixa p-5">
            <h2 className="text-lg">Versões</h2>
            <ul className="mt-3 divide-y divide-linha">
              {a.versoes.map((v) => (
                <li key={v.id} className="py-3">
                  <div className="flex flex-wrap items-center gap-2 text-sm">
                    <b>v{v.numero}</b>
                    <span className={"selo " + COR_ESTADO[v.estado]}>{NOME_ESTADO[v.estado] ?? v.estado}</span>
                    <span className={"selo " + COR_RISCO[v.risco]}>{NOME_RISCO[v.risco]}</span>
                    <span className="text-tinta-3">por {v.autor} em {quando(v.criada_em)}</span>
                    <button className="ml-auto text-xs font-semibold text-pedra-forte" onClick={() => verDiff(v.numero)}>ver mudanças</button>
                  </div>
                  {v.nota && <p className="mt-1 text-sm text-tinta-2">{v.nota}</p>}
                  {v.parecer && <p className="mt-1 text-sm"><span className="text-tinta-3">Parecer de {v.revisor}:</span> {v.parecer}</p>}
                  {diff?.numero === v.numero && <div className="mt-2 rounded-lg bg-papel p-3"><ListaMudancas mudancas={diff.mudancas} /></div>}
                </li>
              ))}
            </ul>
          </section>
        </div>

        <aside className="caixa h-fit p-5">
          <h2 className="text-lg">Ciclo de vida</h2>
          <p className="text-xs text-tinta-3">Registrado na trilha de auditoria encadeada.</p>
          <ol className="mt-4 space-y-3 border-l border-linha pl-4">
            {a.historico.map((e) => (
              <li key={e.id} className="relative text-sm">
                <span className="absolute -left-[21px] top-1.5 h-2.5 w-2.5 rounded-full bg-pedra" />
                <div className="font-medium">{NOME_EVENTO[e.tipo] ?? e.tipo}{e.dados.versao ? ` · v${e.dados.versao}` : ""}</div>
                <div className="text-xs text-tinta-3">{e.ator} · {quando(e.quando)}</div>
                {typeof e.dados.motivo === "string" && e.dados.motivo && <div className="text-xs text-tinta-2">{e.dados.motivo}</div>}
                {typeof e.dados.parecer === "string" && <div className="text-xs text-tinta-2">{e.dados.parecer}</div>}
              </li>
            ))}
          </ol>
        </aside>
      </div>
    </div>
  );
}
