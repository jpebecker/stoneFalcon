import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import {
  api, type Agente, type AgenteDetalhe, type Blueprint, type Execucao, type Ferramenta, type Passo, type Persona, type Saude, type Sugestao, type Validacao,
} from "../api/cliente";
import Canvas from "../components/Canvas";
import CampoEntrada from "../components/CampoEntrada";
import { registrarCtx, usePreenche } from "../roteiro/estado";
import EditorPasso from "../components/EditorPasso";
import LinhaDoTempo from "../components/LinhaDoTempo";
import { COR_RISCO, reais } from "../components/formato";
import { CHAVE_RASCUNHO } from "./ViaExtensao";

type Padrao = { id: string; titulo: string; area: string; exemplo: string };

const NOME_RISCO = { baixo: "Risco baixo", medio: "Risco médio", alto: "Risco alto" };

function novoId(bp: Blueprint) {
  let n = bp.passos.length + 1;
  while (bp.passos.some((p) => p.id === "passo_" + n)) n++;
  return "passo_" + n;
}

export default function Estudio({ pessoa }: { pessoa: Persona }) {
  const [descricao, setDescricao] = useState("");
  const [sug, setSug] = useState<Sugestao | null>(null);
  const [bp, setBp] = useState<Blueprint | null>(null);
  const [val, setVal] = useState<Validacao | null>(null);
  const [sel, setSel] = useState<string | null>(null);
  const [entrada, setEntrada] = useState<Record<string, string>>({});
  const [exe, setExe] = useState<Execucao | null>(null);
  const [params] = useSearchParams();
  const agenteId = params.get("agente");
  const navegar = useNavigate();
  const qc = useQueryClient();
  const [nota, setNota] = useState("");

  // roteiro guiado: o passo atual já deixa a descrição e a entrada do teste preenchidas
  const pre = usePreenche();
  useEffect(() => {
    if (pre?.passoId === "criar" && pre.descricao && !bp) setDescricao(pre.descricao);
    if (pre?.passoId === "testar" && pre.entrada) setEntrada(pre.entrada);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pre?.passoId]);

  // chegada pela extensão: o trecho selecionado vira o rascunho da descrição, com a sugestão já calculada
  useEffect(() => {
    if (agenteId) return;
    let texto = "";
    try {
      const guardado = sessionStorage.getItem(CHAVE_RASCUNHO);
      sessionStorage.removeItem(CHAVE_RASCUNHO);
      texto = guardado ? (JSON.parse(guardado).texto ?? "") : "";
    } catch { /* sem armazenamento */ }
    if (texto.trim()) { setDescricao(texto); sugerir.mutate(texto); }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // editando um agente existente: carrega a última versão
  const existente = useQuery({ queryKey: ["agente", agenteId], queryFn: () => api<AgenteDetalhe>("/agentes/" + agenteId), enabled: !!agenteId });
  useEffect(() => {
    if (existente.data && !bp) setBp(existente.data.versoes[0].blueprint);
  }, [existente.data, bp]);

  const salvar = useMutation({
    mutationFn: async (publicarDepois: boolean) => {
      const id = agenteId
        ? (await api(`/agentes/${agenteId}`, { blueprint: bp, nota }, "PUT"), agenteId)
        : (await api<Agente>("/agentes", { blueprint: bp, nota })).id;
      if (publicarDepois) await api(`/agentes/${id}/publicar`, {});
      return id;
    },
    onSuccess: (id) => { registrarCtx({ agenteId: id }); qc.invalidateQueries({ queryKey: ["agentes"] }); qc.invalidateQueries({ queryKey: ["agente", id] }); navegar("/agentes/" + id); },
  });

  const padroes = useQuery({ queryKey: ["padroes"], queryFn: () => api<Padrao[]>("/estudio/padroes") });
  const cat = useQuery({ queryKey: ["ferramentas"], queryFn: () => api<{ ferramentas: Ferramenta[] }>("/ferramentas") });
  const saude = useQuery({ queryKey: ["saude"], queryFn: () => api<Saude>("/saude") });

  const sugerir = useMutation({
    mutationFn: (d: string) => api<Sugestao>("/estudio/sugerir", { descricao: d }),
    onSuccess: (s) => { setSug(s); setBp(s.blueprint); setSel(null); setExe(null); setEntrada({}); },
  });
  const testar = useMutation({
    mutationFn: () => api<Execucao>("/estudio/testar", { blueprint: bp, entrada }),
    onSuccess: setExe,
  });

  // validação ao vivo enquanto a pessoa edita
  useEffect(() => {
    if (!bp) return;
    const t = setTimeout(() => { api<Validacao>("/estudio/validar", { blueprint: bp }).then(setVal).catch(() => {}); }, 250);
    return () => clearTimeout(t);
  }, [bp]);

  const valido = val?.valido ? val : null;
  const semPermissao = useMemo(() => new Set(Object.keys(valido?.sem_permissao ?? {})), [valido]);
  const modelos = useMemo(() => Object.fromEntries(Object.entries(valido?.estimativa.por_passo ?? {}).map(([k, v]) => [k, v.modelo && v.simulado ? v.modelo + " · simulado" : v.modelo])), [valido]);
  const passoSel = bp?.passos.find((p) => p.id === sel) ?? null;

  const mudarPasso = (novo: Passo) => bp && setBp({ ...bp, passos: bp.passos.map((p) => (p.id === novo.id ? novo : p)) });
  const removerPasso = (id: string) => {
    if (!bp) return;
    setBp({ ...bp, passos: bp.passos.filter((p) => p.id !== id).map((p) => ({ ...p, depende_de: p.depende_de.filter((d) => d !== id) })) });
    setSel(null);
  };
  const adicionar = (tipo: "agente" | "aprovacao") => {
    if (!bp) return;
    const id = novoId(bp);
    const ultimo = bp.passos[bp.passos.length - 1]?.id;
    const passo: Passo = {
      id, tipo, titulo: tipo === "agente" ? "Novo passo com IA" : "Confirmação humana",
      instrucao: tipo === "agente" ? "Descreva o que fazer neste passo." : "", ferramentas: [], modelo: "auto",
      max_iteracoes: 6, ferramenta: null, entrada: {}, depende_de: ultimo ? [ultimo] : [],
    };
    setBp({ ...bp, passos: [...bp.passos, passo] });
    setSel(id);
  };

  // ---------- etapa 1: descrever ----------
  if (agenteId && !bp) return <p className="text-tinta-3">Carregando o agente…</p>;
  if (!bp) {
    return (
      <div className="mx-auto max-w-3xl space-y-6">
        <div>
          <h1 className="text-3xl">Estúdio</h1>
          <p className="mt-1 text-tinta-2">Conte o processo como contaria a um colega novo: o que dispara, o que você consulta, o que decide e como termina. Se quiser, diga quanto tempo leva hoje.</p>
        </div>
        <div className="caixa p-5">
          <textarea className="campo min-h-[150px] text-base" value={descricao} onChange={(e) => setDescricao(e.target.value)}
            placeholder="Ex.: Quando o lojista diz que a maquininha quebrou, eu confiro o cadastro dele e abro um chamado de troca na logística. Levo uns 15 minutos." />
          <div className="mt-3 flex items-center justify-between gap-3">
            <p className="text-xs text-tinta-3">Dados pessoais escritos aqui são removidos antes de qualquer envio.</p>
            <button className="botao-pedra" disabled={descricao.trim().length < 15 || sugerir.isPending}
              onClick={() => sugerir.mutate(descricao)}>
              {sugerir.isPending ? "Montando o agente…" : "Montar meu agente"}
            </button>
          </div>
          {sugerir.isError && <p className="mt-2 text-sm text-erro">{(sugerir.error as Error).message}</p>}
        </div>
        <div>
          <h2 className="mb-2 text-sm font-semibold uppercase tracking-wide text-tinta-3">Ou comece por um exemplo</h2>
          <div className="grid gap-2 sm:grid-cols-2">
            {padroes.data?.map((p) => (
              <button key={p.id} className="caixa p-3 text-left text-sm transition hover:border-pedra" onClick={() => setDescricao(p.exemplo)}>
                <div className="font-semibold">{p.titulo}</div>
                <div className="mt-0.5 line-clamp-2 text-tinta-2">{p.exemplo}</div>
              </button>
            ))}
          </div>
        </div>
      </div>
    );
  }

  // ---------- etapas 2 e 3: ajustar e testar ----------
  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="min-w-0 flex-1">
          <input className="w-full bg-transparent font-titulo text-3xl font-semibold tracking-tight outline-none focus:border-b focus:border-pedra"
            value={bp.nome} onChange={(e) => setBp({ ...bp, nome: e.target.value })} aria-label="Nome do agente" />
          <textarea className="mt-1 w-full resize-none bg-transparent text-tinta-2 outline-none" rows={2}
            value={bp.objetivo} onChange={(e) => setBp({ ...bp, objetivo: e.target.value })} aria-label="Objetivo" />
        </div>
        <div className="flex gap-2">
          {!agenteId && <button className="botao-claro" onClick={() => { setBp(null); setSug(null); setVal(null); setExe(null); }}>Recomeçar</button>}
          <button className="botao-claro" disabled={!valido || salvar.isPending} onClick={() => salvar.mutate(false)}>Salvar rascunho</button>
          <button className="botao-pedra" disabled={!valido || salvar.isPending || semPermissao.size > 0} onClick={() => salvar.mutate(true)}
            title={valido?.risco.exige_revisao_seguranca ? "Vai para a revisão da Segurança antes de ir ao ar" : "Vai ao ar agora"}>
            {valido?.risco.exige_revisao_seguranca ? "Enviar para revisão" : "Publicar"}
          </button>
        </div>
      </div>

      {agenteId && (
        <label className="block max-w-xl">
          <span className="rotulo">O que mudou nesta versão</span>
          <input className="campo" value={nota} onChange={(e) => setNota(e.target.value)} placeholder="Ex.: incluí a confirmação do endereço" />
        </label>
      )}
      {salvar.isError && <p className="text-sm text-erro">{(salvar.error as Error).message}</p>}
      {sug && sug.alertas.length > 0 && (
        <ul className="space-y-1 rounded-caixa border border-alerta/40 bg-alerta-fundo/50 p-3 text-sm">
          {sug.alertas.map((a, i) => <li key={i}>• {a}</li>)}
          {Object.entries(sug.ferramentas_removidas).map(([f, m]) => <li key={f} className="text-tinta-2">– {m}</li>)}
        </ul>
      )}

      <div className="grid gap-6 xl:grid-cols-[1fr_360px]">
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <p className="text-sm text-tinta-3">Passos na mesma coluna rodam ao mesmo tempo. Clique num passo para ajustar.</p>
            <div className="flex gap-2">
              <button className="botao-claro py-1.5" onClick={() => adicionar("agente")}>+ Passo com IA</button>
              <button className="botao-claro py-1.5" onClick={() => adicionar("aprovacao")}>+ Aprovação humana</button>
            </div>
          </div>
          <Canvas bp={bp} niveis={valido?.niveis ?? sug?.niveis ?? []} modelos={modelos} semPermissao={semPermissao}
            selecionado={sel} aoSelecionar={setSel} aoMudar={setBp} />
          {val && !val.valido && (
            <div className="rounded-caixa border border-erro/30 bg-erro-fundo p-3 text-sm text-erro">
              {val.erros.map((e, i) => <p key={i}>{e}</p>)}
            </div>
          )}
        </div>

        <aside className="space-y-4">
          {passoSel ? (
            <EditorPasso passo={passoSel} ferramentas={cat.data?.ferramentas ?? []} aoMudar={mudarPasso} aoRemover={() => removerPasso(passoSel.id)} />
          ) : valido && (
            <div className="caixa space-y-4 p-4">
              <div className="flex items-center justify-between">
                <span className={"selo text-sm " + COR_RISCO[valido.risco.nivel]}>{NOME_RISCO[valido.risco.nivel]}</span>
                <span className="text-sm text-tinta-2">≈ {reais(valido.estimativa.custo_por_execucao_brl)} por execução</span>
              </div>
              <ul className="space-y-0.5 text-xs text-tinta-2">{valido.risco.motivos.map((m) => <li key={m}>• {m}</li>)}</ul>
              <p className="text-xs text-tinta-3">
                {valido.risco.exige_revisao_seguranca
                  ? "Por tocar dados ou ações sensíveis, a publicação passa pela revisão da Segurança."
                  : "Publicação direta: os guardrails da plataforma já cobrem este agente."}
              </p>
              <div className="border-t border-linha pt-3">
                <h3 className="mb-2 text-sm font-semibold">Como o agente vai trabalhar</h3>
                <ol className="space-y-2 text-sm">
                  {valido.explicacao.map((x, i) => (
                    <li key={x.passo}><b>{i + 1}. {x.titulo}.</b> <span className="text-tinta-2">{x.explicacao}</span></li>
                  ))}
                </ol>
              </div>
              <label className="block border-t border-linha pt-3">
                <span className="rotulo">Tempo da tarefa feita à mão (min)</span>
                <input type="number" min={0} className="campo w-28" value={bp.minutos_manual}
                  onChange={(e) => setBp({ ...bp, minutos_manual: Number(e.target.value) || 0 })} />
                <span className="mt-1 block text-xs text-tinta-3">Base para medir o retorno do agente.</span>
              </label>
            </div>
          )}
        </aside>
      </div>

      <section className="caixa p-5">
        <h2 className="text-lg">Testar no sandbox</h2>
        <p className="mt-1 text-sm text-tinta-3">Roda com as suas permissões, sobre sistemas de teste. Nada é publicado.</p>
        <div className="mt-4 flex flex-wrap items-end gap-3">
          {bp.campos.map((c) => (
            <CampoEntrada key={c.id} campo={c} pessoa={pessoa} valor={entrada[c.id] ?? ""}
              aoMudar={(v) => setEntrada((e) => ({ ...e, [c.id]: v }))} />
          ))}
          <button className="botao-pedra" disabled={!valido || testar.isPending || bp.campos.some((c) => !entrada[c.id])}
            onClick={() => testar.mutate()}>
            {testar.isPending ? "Executando…" : "Executar teste"}
          </button>
        </div>
        {testar.isError && <p className="mt-2 text-sm text-erro">{(testar.error as Error).message}</p>}
        {exe && (
          <div className="mt-5 border-t border-linha pt-5">
            <LinhaDoTempo exe={exe} pessoa={pessoa} cotacao={saude.data?.cotacao_dolar ?? 5.52} aoMudar={setExe} />
          </div>
        )}
      </section>
    </div>
  );
}
