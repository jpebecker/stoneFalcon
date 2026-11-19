import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";
import { Link, useLocation, useNavigate, useParams } from "react-router-dom";
import {
  api, type AgenteDisponivel, type Bloco, type Execucao, type Ferramenta, type Persona, type Processo, type ProcessoBlueprint,
  type ProcessoDetalhe, type Saude, type TipoBloco, type ValidacaoProcesso,
} from "../api/cliente";
import CampoEntrada from "../components/CampoEntrada";
import CanvasProcesso, { ENTRADA } from "../components/CanvasProcesso";
import EditorCampos from "../components/EditorCampos";
import LinhaDoTempo from "../components/LinhaDoTempo";
import PainelBloco from "../components/PainelBloco";
import PaletaBlocos from "../components/PaletaBlocos";
import { BLOCOS, COR_RISCO, NOME_RISCO, ms, reais } from "../components/formato";
import { registrarCtx, usePreenche } from "../roteiro/estado";

const VAZIO: ProcessoBlueprint = {
  nome: "Novo processo", objetivo: "Descreva em uma frase o que este processo resolve.", area: "", campos: [], blocos: [],
  limites: { max_custo_brl: 2, max_chamadas_modelo: 20 }, minutos_manual: 10, roteiro_id: null,
};

function novoId(bp: ProcessoBlueprint, tipo: TipoBloco) {
  let n = bp.blocos.length + 1;
  while (bp.blocos.some((b) => b.id === `${tipo}_${n}`)) n++;
  return `${tipo}_${n}`;
}

export function blocoNovo(bp: ProcessoBlueprint, tipo: TipoBloco): Bloco {
  const ultimo = bp.blocos[bp.blocos.length - 1]?.id;
  return {
    id: novoId(bp, tipo), tipo, titulo: tipo === "agente" ? "Novo agente" : BLOCOS[tipo].nome, depende_de: ultimo ? [ultimo] : [], ramo: null,
    agente_id: null, ferramenta: null, entrada: {}, regra: null, texto: "",
  };
}

export default function ProcessoEditor({ pessoa }: { pessoa: Persona }) {
  const { id } = useParams();
  const navegar = useNavigate();
  const qc = useQueryClient();
  const inicial = (useLocation().state as { rascunho?: ProcessoBlueprint } | null)?.rascunho;
  const [bp, setBp] = useState<ProcessoBlueprint | null>(inicial ?? (id ? null : { ...VAZIO, area: pessoa.area }));
  const [sel, setSel] = useState<string | null>(null);
  const [val, setVal] = useState<ValidacaoProcesso | null>(null);
  const [nota, setNota] = useState("");
  const [entrada, setEntrada] = useState<Record<string, string>>({});
  const [exe, setExe] = useState<Execucao | null>(null);

  const existente = useQuery({ queryKey: ["processo", id], queryFn: () => api<ProcessoDetalhe>("/processos/" + id), enabled: !!id });
  useEffect(() => { if (existente.data && !bp) setBp(existente.data.versoes[0].blueprint); }, [existente.data, bp]);
  const saude = useQuery({ queryKey: ["saude"], queryFn: () => api<Saude>("/saude") });
  const agentes = useQuery({ queryKey: ["processos", "agentes-disponiveis"], queryFn: () => api<AgenteDisponivel[]>("/processos/agentes-disponiveis") });
  const cat = useQuery({ queryKey: ["ferramentas"], queryFn: () => api<{ ferramentas: Ferramenta[] }>("/ferramentas") });
  const asIs = useQuery({ queryKey: ["processos", "as-is"], queryFn: () => api<{ roteiro_id: string; processo: string }[]>("/processos/as-is") });

  // roteiro guiado: "montar" traz os blocos do processo (o agente vem pelo nome: troca pelo id do que a pessoa acabou de criar)
  const pre = usePreenche(["montar", "testar"]);
  useEffect(() => {
    if (id || pre?.passoId !== "montar" || !pre.processo || !agentes.data) return;
    const { blocos, ...resto } = pre.processo;
    setBp((atual) => {
      if (atual && atual.blocos.length > 0) return atual;
      return {
        ...(atual ?? VAZIO), ...resto, area: pessoa.area,
        blocos: blocos.map(({ agente_nome, ...b }) => ({
          ...b, ramo: b.ramo ?? null, agente_id: agente_nome ? [...agentes.data].reverse().find((a) => a.nome === agente_nome)?.id ?? null : b.agente_id ?? null,
          ferramenta: b.ferramenta ?? null, regra: b.regra ?? null, texto: b.texto ?? "",
        })),
      } as ProcessoBlueprint;
    });
  }, [pre?.passoId, agentes.data]); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => { if (pre?.passoId === "testar" && pre.entrada) setEntrada(pre.entrada); }, [pre?.passoId]); // eslint-disable-line react-hooks/exhaustive-deps

  // validação ao vivo enquanto a pessoa monta o fluxo
  useEffect(() => {
    if (!bp) return;
    const t = setTimeout(() => { api<ValidacaoProcesso>("/processos/validar", { blueprint: bp }).then(setVal).catch(() => {}); }, 250);
    return () => clearTimeout(t);
  }, [bp]);

  const salvar = useMutation({
    mutationFn: async (publicarDepois: boolean) => {
      const pid = id
        ? (await api(`/processos/${id}`, { blueprint: bp, nota }, "PUT"), id)
        : (await api<Processo>("/processos", { blueprint: bp, nota })).id;
      if (publicarDepois) await api(`/processos/${pid}/publicar`, {});
      return pid;
    },
    onSuccess: (pid) => { registrarCtx({ agenteId: pid }); qc.invalidateQueries({ queryKey: ["processos"] }); qc.invalidateQueries({ queryKey: ["processo", pid] }); navegar("/processos/" + pid); },
  });
  const testar = useMutation({
    mutationFn: () => api<Execucao>("/processos/testar", { blueprint: bp, entrada }),
    onSuccess: setExe,
  });

  const valido = val?.valido ? val : null;
  const subtitulos = useMemo(() => {
    const s: Record<string, string> = {};
    for (const b of bp?.blocos ?? []) {
      if (b.tipo === "agente") s[b.id] = agentes.data?.find((a) => a.id === b.agente_id)?.nome ?? "escolha um agente";
      else if (b.ferramenta) s[b.id] = cat.data?.ferramentas.find((f) => f.id === b.ferramenta)?.nome ?? b.ferramenta;
    }
    return s;
  }, [bp, agentes.data, cat.data]);
  const problemas = useMemo(() => {
    const p: Record<string, string[]> = {};
    for (const b of bp?.blocos ?? []) {
      const lista = [...(valido?.bloqueios?.[b.id] ? [valido.bloqueios[b.id]] : []), ...(val?.blocos?.[b.id] ?? [])];
      if (lista.length) p[b.id] = [...new Set(lista)];
    }
    return p;
  }, [bp, valido, val]);

  if (id && !bp) return <p className="text-tinta-3">Carregando o processo…</p>;
  if (!bp) return null;
  const blocoSel = bp.blocos.find((b) => b.id === sel) ?? null;
  const mudarBloco = (novo: Bloco) => setBp({ ...bp, blocos: bp.blocos.map((b) => (b.id === novo.id ? novo : b)) });
  const removerBloco = (bid: string) => {
    setBp({ ...bp, blocos: bp.blocos.filter((b) => b.id !== bid).map((b) => {
      const depende_de = b.depende_de.filter((d) => d !== bid);
      return { ...b, depende_de, ramo: b.ramo && depende_de.includes(b.ramo.condicao) ? b.ramo : null };
    }) });
    setSel(null);
  };
  const adicionar = (tipo: TipoBloco) => { const b = blocoNovo(bp, tipo); setBp({ ...bp, blocos: [...bp.blocos, b] }); setSel(b.id); };
  const semBlocosValidos = !valido || Object.keys(problemas).length > 0;
  const semPermissao = Object.keys(valido?.sem_permissao ?? {}).length > 0;

  return (
    <div className="space-y-6">
      <Link to={id ? "/processos/" + id : "/processos"} className="text-sm text-tinta-3 hover:text-tinta">← {id ? "Voltar ao processo" : "Processos"}</Link>
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="min-w-0 flex-1">
          <input className="w-full bg-transparent font-titulo text-3xl font-semibold tracking-tight outline-none focus:border-b focus:border-pedra"
            value={bp.nome} onChange={(e) => setBp({ ...bp, nome: e.target.value })} aria-label="Nome do processo" />
          <textarea className="mt-1 w-full resize-none bg-transparent text-tinta-2 outline-none" rows={2}
            value={bp.objetivo} onChange={(e) => setBp({ ...bp, objetivo: e.target.value })} aria-label="Objetivo do processo" />
        </div>
        <div className="flex gap-2">
          <button className="botao-claro" disabled={!valido || salvar.isPending} onClick={() => salvar.mutate(false)}>Salvar rascunho</button>
          <button className="botao-pedra" disabled={semBlocosValidos || salvar.isPending || semPermissao} onClick={() => salvar.mutate(true)}
            title={valido?.risco.exige_revisao_seguranca ? "Vai para a revisão da Segurança antes de ir ao ar" : "Vai ao ar agora"}>
            {valido?.risco.exige_revisao_seguranca ? "Enviar para revisão" : "Publicar"}
          </button>
        </div>
      </div>
      {id && (
        <label className="block max-w-xl">
          <span className="rotulo">O que mudou nesta versão</span>
          <input className="campo" value={nota} onChange={(e) => setNota(e.target.value)} placeholder="Ex.: incluí a conferência de um analista" />
        </label>
      )}
      {salvar.isError && <p className="text-sm text-erro">{(salvar.error as Error).message}</p>}

      <section className="caixa grid gap-4 p-4 md:grid-cols-2">
        <label className="block">
          <span className="rotulo">Processo AS IS → TO BE que ele realiza</span>
          <select className="campo" value={bp.roteiro_id ?? ""} onChange={(e) => setBp({ ...bp, roteiro_id: e.target.value || null })} aria-label="Processo AS IS ligado">
            <option value="">Nenhum</option>
            {asIs.data?.map((r) => <option key={r.roteiro_id} value={r.roteiro_id}>{r.processo}</option>)}
          </select>
          <span className="mt-1 block text-xs text-tinta-3">Liga o fluxo ao processo real da área, para medir o ganho do AS IS × TO BE.</span>
        </label>
        <label className="block">
          <span className="rotulo">Tempo do processo feito à mão (min)</span>
          <input type="number" min={0} className="campo w-28" value={bp.minutos_manual} onChange={(e) => setBp({ ...bp, minutos_manual: Number(e.target.value) || 0 })} />
          <span className="mt-1 block text-xs text-tinta-3">Base para medir o retorno do processo.</span>
        </label>
        <div className="md:col-span-2">
          <span className="rotulo">Entradas: o que quem roda o processo preenche</span>
          <EditorCampos campos={bp.campos} aoMudar={(campos) => setBp({ ...bp, campos })} />
        </div>
      </section>

      <div className="grid gap-6 xl:grid-cols-[1fr_360px]">
        <div className="space-y-3">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <p className="text-sm text-tinta-3">Blocos na mesma coluna rodam ao mesmo tempo. Clique num bloco para ajustar; arraste de um ao outro para ligar.</p>
          </div>
          <PaletaBlocos aoAdicionar={adicionar} aoSelecionarEntradas={() => setSel(ENTRADA)} />
          <CanvasProcesso bp={bp} subtitulos={subtitulos} problemas={problemas} selecionado={sel} aoSelecionar={setSel} aoMudar={setBp} />
          {val && !val.valido && (
            <div className="rounded-caixa border border-erro/30 bg-erro-fundo p-3 text-sm text-erro" role="alert">
              {val.erros.map((e, i) => <p key={i}>{e}</p>)}
            </div>
          )}
          {bp.blocos.length === 0 && <p className="text-sm text-tinta-3">Comece adicionando um bloco de agente.</p>}
        </div>

        <aside className="space-y-4">
          {blocoSel ? (
            <PainelBloco bp={bp} bloco={blocoSel} ferramentas={cat.data?.ferramentas ?? []} problemas={problemas[blocoSel.id] ?? []}
              aoMudar={mudarBloco} aoRemover={() => removerBloco(blocoSel.id)} />
          ) : sel === ENTRADA ? (
            <div className="caixa space-y-2 p-4 text-sm"><h3 className="text-base">{BLOCOS.entrada.nome}</h3><p className="text-tinta-2">{BLOCOS.entrada.descricao}</p>
              <p className="text-xs text-tinta-3">Edite os campos na seção acima do canvas.</p></div>
          ) : valido && (
            <div className="caixa space-y-4 p-4">
              <div className="flex items-center justify-between">
                <span className={"selo text-sm " + COR_RISCO[valido.risco.nivel]}>{NOME_RISCO[valido.risco.nivel]}</span>
                <span className="text-sm text-tinta-2">≈ {reais(valido.estimativa.custo_por_execucao_brl)} · {ms(valido.estimativa.duracao_ms)}</span>
              </div>
              <ul className="space-y-0.5 text-xs text-tinta-2">{valido.risco.motivos.map((m) => <li key={m}>• {m}</li>)}</ul>
              <p className="text-xs text-tinta-3">
                {valido.risco.exige_revisao_seguranca ? "Por tocar dados ou ações sensíveis, a publicação passa pela revisão da Segurança." : "Publicação direta: os guardrails da plataforma cobrem este processo."}
              </p>
              {semPermissao && <ul className="space-y-0.5 text-xs text-erro">{Object.values(valido.sem_permissao).map((m) => <li key={m}>• {m}</li>)}</ul>}
            </div>
          )}
        </aside>
      </div>

      <section className="caixa p-5">
        <h2 className="text-lg">Testar no sandbox</h2>
        <p className="mt-1 text-sm text-tinta-3">Roda o rascunho com as suas permissões, sobre sistemas de teste. Nada é publicado.</p>
        <div className="mt-4 flex flex-wrap items-end gap-3">
          {bp.campos.map((c) => (
            <CampoEntrada key={c.id} campo={c} pessoa={pessoa} valor={entrada[c.id] ?? ""} aoMudar={(v) => setEntrada((e) => ({ ...e, [c.id]: v }))} />
          ))}
          <button className="botao-pedra" disabled={!valido || testar.isPending || bp.campos.some((c) => !entrada[c.id])} onClick={() => testar.mutate()}>
            {testar.isPending ? "Executando…" : "Executar teste"}
          </button>
        </div>
        {testar.isError && <p className="mt-2 text-sm text-erro">{(testar.error as Error).message}</p>}
        {exe && <div className="mt-5 border-t border-linha pt-5"><LinhaDoTempo exe={exe} pessoa={pessoa} cotacao={saude.data?.cotacao_dolar ?? 5.52} aoMudar={setExe} /></div>}
      </section>
    </div>
  );
}
