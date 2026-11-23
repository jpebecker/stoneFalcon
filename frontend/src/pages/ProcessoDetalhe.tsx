import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api, type Agente, type Execucao, type Mudanca, type Persona, type ProcessoDetalhe as Detalhe, type Saude } from "../api/cliente";
import CampoEntrada from "../components/CampoEntrada";
import LinhaDoTempo from "../components/LinhaDoTempo";
import ListaMudancas from "../components/ListaMudancas";
import PainelCompartilhar, { useAreas } from "../components/PainelCompartilhar";
import PainelRotina from "../components/PainelRotina";
import { BLOCOS, COR_ESTADO, COR_RISCO, NOME_ESTADO, NOME_EVENTO, NOME_RISCO, quando, reais } from "../components/formato";
import Icone from "../components/Icone";
import SeloCompartilhado from "../components/SeloCompartilhado";
import Carregando from "../components/falcao/Carregando";
import { alvoDe, useFalcao } from "../components/falcao/Voo";

export default function ProcessoDetalhe({ pessoa }: { pessoa: Persona }) {
  const { id } = useParams();
  const qc = useQueryClient();
  const q = useQuery({ queryKey: ["processo", id], queryFn: () => api<Detalhe>("/processos/" + id) });
  const saude = useQuery({ queryKey: ["saude"], queryFn: () => api<Saude>("/saude") });
  const agentes = useQuery({ queryKey: ["agentes"], queryFn: () => api<Agente[]>("/agentes") });
  const [entrada, setEntrada] = useState<Record<string, string>>({});
  const [exe, setExe] = useState<Execucao | null>(null);
  const [diff, setDiff] = useState<{ numero: number; mudancas: Mudanca[] } | null>(null);
  const [compartilhando, setCompartilhando] = useState(false);
  const areas = useAreas();
  const nomeDaArea = (a: unknown) => areas.data?.find((x) => x.id === a)?.nome ?? String(a);
  useEffect(() => { setExe(null); setEntrada({}); setCompartilhando(false); }, [id]);

  const recarregar = () => { qc.invalidateQueries({ queryKey: ["processo", id] }); qc.invalidateQueries({ queryKey: ["processos"] }); };
  const { retornar } = useFalcao();
  const acao = useMutation({
    mutationFn: ({ rota, corpo }: { rota: string; corpo?: unknown }) => api(`/processos/${id}/${rota}`, corpo ?? {}),
    onSuccess: (_r, v) => {
      recarregar();
      if (v.rota === "publicar") retornar({ de: alvoDe("acao-publicar"), para: "aba-processos", alternativo: "sino" });
    },
  });
  const executar = useMutation({
    mutationFn: () => api<Execucao>(`/processos/${id}/executar`, { entrada }),
    onSuccess: (e) => {
      setExe(e); recarregar();
      if (e.status === "concluida") retornar({ de: alvoDe("acao-executar"), para: "aba-execucoes", alternativo: "sino" });
    },
  });
  const verDiff = async (numero: number) => {
    const mudancas = await api<Mudanca[]>(`/processos/${id}/diff?de=${numero - 1}&para=${numero}`);
    setDiff({ numero, mudancas });
  };

  if (q.isError) return <p className="text-erro">{(q.error as Error).message}</p>;
  if (!q.data) return <p className="text-tinta-3">Carregando…</p>;
  const p = q.data;
  const publicada = p.versoes.find((v) => v.numero === p.versao_publicada);
  const ultima = p.versoes[0];
  const bp = publicada?.blueprint ?? ultima?.blueprint;
  const operador = p.pode_editar || pessoa.papeis.includes("gestor_ia") || pessoa.papeis.includes("revisor_seguranca");
  const podeDepreciar = pessoa.id === p.dono || pessoa.papeis.includes("gestor_ia");
  const campos = publicada?.blueprint.campos ?? [];

  return (
    <div className="space-y-6">
      <Link to="/processos" className="text-sm text-tinta-3 hover:text-tinta">← Processos</Link>
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="flex flex-wrap items-center gap-3">
            <h1 className="text-3xl">{p.nome}</h1>
            <span className={"selo " + COR_ESTADO[p.estado]}>{NOME_ESTADO[p.estado]}</span>
            <span className={"selo " + COR_RISCO[p.risco]}>{NOME_RISCO[p.risco]}</span>
            <SeloCompartilhado p={p} pessoa={pessoa} />
          </div>
          <p className="mt-1 text-tinta-2">{bp?.objetivo}</p>
          <p className="mt-1 text-sm text-tinta-3">Área {p.area} · dono {p.dono} · {p.execucoes} execuções · {reais(p.custo_brl)} gastos</p>
          {p.as_is && <p className="mt-1 text-sm text-tinta-2">Realiza o processo AS IS → TO BE: <Link className="font-semibold text-pedra-forte hover:underline" to={"/roteiro/" + p.as_is.persona}>{p.as_is.processo}</Link></p>}
          {p.motivo_estado && <p className="mt-2 text-sm text-alerta">Motivo: {p.motivo_estado}</p>}
        </div>
        <div className="flex flex-wrap gap-2">
          {p.pode_editar && p.estado !== "depreciado" && <Link to={`/processos/${p.id}/editar`} className="botao-claro">Editar processo</Link>}
          {p.pode_editar && p.estado !== "depreciado" && (
            <button className="botao-claro" data-alvo="acao-compartilhar" aria-expanded={compartilhando} aria-controls="painel-compartilhar"
              onClick={() => setCompartilhando((v) => !v)}>Compartilhar</button>
          )}
          {p.pode_editar && ultima?.estado === "rascunho" && p.estado !== "depreciado" && (
            <button className="botao-pedra" data-alvo="acao-publicar" onClick={() => acao.mutate({ rota: "publicar" })}><Icone nome="publicar" />Publicar v{ultima.numero}</button>
          )}
          {operador && p.estado === "publicado" && (
            <button className="botao-claro" data-alvo="acao-pausar" onClick={() => { const m = prompt("Motivo da pausa (opcional):") ?? ""; acao.mutate({ rota: "pausar", corpo: { motivo: m } }); }}>Pausar</button>
          )}
          {operador && p.estado === "pausado" && <button className="botao-claro" onClick={() => acao.mutate({ rota: "retomar" })}>Retomar</button>}
          {podeDepreciar && p.estado !== "depreciado" && (
            <button className="botao-claro text-erro" onClick={() => { const m = prompt("Por que depreciar este processo? Ele deixa de executar e não volta."); if (m) acao.mutate({ rota: "depreciar", corpo: { motivo: m } }); }}>Depreciar</button>
          )}
        </div>
      </div>
      {acao.isError && <p className="text-sm text-erro">{(acao.error as Error).message}</p>}
      {compartilhando && p.pode_editar && <div id="painel-compartilhar"><PainelCompartilhar p={p} aoFechar={() => setCompartilhando(false)} /></div>}
      {p.alertas_agentes && p.alertas_agentes.length > 0 && (
        <ul className="space-y-1 rounded-lg bg-alerta-fundo p-3 text-sm text-alerta" role="alert" data-testid="alertas-agentes">
          {p.alertas_agentes.map((a) => (
            <li key={a.id}>O agente <Link to={"/agentes/" + a.id} className="font-semibold underline">{a.nome}</Link> está {a.estado}{a.motivo ? ` (${a.motivo})` : ""}: o bloco dele escala para um humano.</li>
          ))}
        </ul>
      )}

      <div className="grid gap-6 xl:grid-cols-[1fr_380px]">
        <div className="space-y-6">
          {p.pode_executar && p.estado === "publicado" && publicada && (
            <section className="caixa p-5">
              <h2 className="text-lg">Executar v{publicada.numero}</h2>
              <div className="mt-3 flex flex-wrap items-end gap-3">
                {campos.map((c) => (
                  <CampoEntrada key={c.id} campo={c} pessoa={pessoa} valor={entrada[c.id] ?? ""} aoMudar={(v) => setEntrada((e) => ({ ...e, [c.id]: v }))} />
                ))}
                <button className="botao-pedra" data-alvo="acao-executar" disabled={executar.isPending || campos.some((c) => !entrada[c.id])} onClick={() => executar.mutate()}>
                  <Icone nome="executar" />{executar.isPending ? "Executando…" : "Executar"}
                </button>
                <Carregando ativo={executar.isPending} texto="Executando o processo…" />
              </div>
              {executar.isError && <p className="mt-2 text-sm text-erro">{(executar.error as Error).message}</p>}
              {exe && <div className="mt-5 border-t border-linha pt-5"><LinhaDoTempo exe={exe} pessoa={pessoa} cotacao={saude.data?.cotacao_dolar ?? 5.52} aoMudar={setExe} /></div>}
            </section>
          )}

          {p.estado === "publicado" && publicada && (
            <PainelRotina agenteId={p.id} base="processos" campos={campos} pessoa={pessoa} editor={p.pode_executar} />
          )}

          <section className="caixa p-5">
            <h2 className="text-lg">Blocos</h2>
            <ol className="mt-3 space-y-1.5 text-sm">
              {bp?.blocos.map((b) => (
                <li key={b.id} className="flex items-center gap-2">
                  <span aria-hidden="true" className="w-5 text-center">{BLOCOS[b.tipo].icone}</span>
                  <b>{b.titulo}</b><span className="text-tinta-3">· {BLOCOS[b.tipo].nome}</span>
                  {b.tipo === "agente" && b.agente_id && <Link className="text-pedra-forte hover:underline" to={"/agentes/" + b.agente_id}>{p.agentes_info?.find((a) => a.id === b.agente_id)?.nome ?? agentes.data?.find((a) => a.id === b.agente_id)?.nome ?? b.agente_id}</Link>}
                </li>
              ))}
            </ol>
          </section>

          <section className="caixa p-5">
            <h2 className="text-lg">Versões</h2>
            <ul className="mt-3 divide-y divide-linha">
              {p.versoes.map((v) => (
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
            {p.historico.map((e) => (
              <li key={e.id} className="relative text-sm">
                <span className="absolute -left-[21px] top-1.5 h-2.5 w-2.5 rounded-full bg-pedra" />
                <div className="font-medium">{NOME_EVENTO[e.tipo] ?? e.tipo}{e.dados.versao ? ` · v${e.dados.versao}` : ""}</div>
                <div className="text-xs text-tinta-3">{e.ator} · {quando(e.quando)}</div>
                {Array.isArray(e.dados.areas) && (
                  <div className="text-xs text-tinta-2">{e.dados.areas.length ? "com " + e.dados.areas.map(nomeDaArea).join(", ") : "sem compartilhamento"}</div>
                )}
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
