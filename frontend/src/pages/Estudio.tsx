import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import {
  api, type Agente, type AgenteDetalhe, type Blueprint, type Execucao, type Ferramenta, type Persona, type ProcessoBlueprint, type ProcessoPronto, type Saude, type Sugestao, type Validacao,
} from "../api/cliente";
import CampoEntrada from "../components/CampoEntrada";
import FormularioTrabalhador from "../components/FormularioTrabalhador";
import { registrarCtx, usePreenche } from "../roteiro/estado";
import LinhaDoTempo from "../components/LinhaDoTempo";
import { COR_RISCO, reais } from "../components/formato";
import Icone from "../components/Icone";
import { CHAVE_RASCUNHO } from "./ViaExtensao";

type Padrao = { id: string; titulo: string; area: string; exemplo: string };

const NOME_RISCO = { baixo: "Risco baixo", medio: "Risco médio", alto: "Risco alto" };

/** Agente de vários passos (formato antigo): só se converte em processo, não se edita aqui. */
const ehLegado = (bp: Blueprint) => !(bp.passos.length === 1 && bp.passos[0].tipo === "agente");

export default function Estudio({ pessoa }: { pessoa: Persona }) {
  const [descricao, setDescricao] = useState("");
  const [sug, setSug] = useState<Sugestao | null>(null);
  const [bp, setBp] = useState<Blueprint | null>(null);
  const [val, setVal] = useState<Validacao | null>(null);
  const [fluxo, setFluxo] = useState<Blueprint | null>(null);   // o fluxo de vários passos que a descrição sugeriu (vira processo)
  const [processoPronto, setProcessoPronto] = useState<ProcessoPronto | null>(null);   // padrão da galeria: o processo pronto ao lado do trabalhador
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
    let fonte: { tipo: string; url: string } | null = null;
    try {
      const guardado = sessionStorage.getItem(CHAVE_RASCUNHO);
      sessionStorage.removeItem(CHAVE_RASCUNHO);
      const d = guardado ? JSON.parse(guardado) : {};
      texto = d.texto ?? "";
      fonte = d.fonte?.tipo === "planilha" ? d.fonte : null;
    } catch { /* sem armazenamento */ }
    // vindo de uma planilha aberta no navegador: o Estúdio já monta o agente com a planilha como fonte
    if (fonte && texto.trim().length < 15) texto = "Ler a planilha de pedidos de troca de maquininha e tratar o primeiro pedido pendente.";
    if (texto.trim()) { setDescricao(texto); sugerir.mutate({ d: texto, fonte }); }
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
    mutationFn: ({ d, fonte }: { d: string; fonte?: { tipo: string; url: string } | null }) =>
      api<Sugestao>("/estudio/sugerir", { descricao: d, fonte: fonte ?? null }),
    onSuccess: (s) => { setSug(s); setBp(s.trabalhador); setFluxo(s.multipasso ? s.blueprint : null); setProcessoPronto(s.processo ?? null); setExe(null); setEntrada(s.entrada_sugerida ?? {}); },
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
  const legado = !!bp && ehLegado(bp);
  // padrão da galeria: salva o trabalhador (rascunho) e abre o processo pronto com ele no bloco do agente
  const montarProcesso = useMutation({
    mutationFn: async (pronto: ProcessoPronto) => {
      const a = await api<Agente>("/agentes", { blueprint: bp, nota: "Criado a partir de um padrão da galeria." });
      const { blocos, ...resto } = pronto;
      const processo: ProcessoBlueprint = {
        ...resto, roteiro_id: resto.roteiro_id ?? null,
        blocos: blocos.map(({ agente_nome, ...b }) => ({ ...b, ramo: b.ramo ?? null, agente_id: agente_nome ? a.id : b.agente_id ?? null })),
      };
      return { processo, agente: a };
    },
    onSuccess: ({ processo, agente }) => { registrarCtx({ agenteId: agente.id }); qc.invalidateQueries({ queryKey: ["agentes"] }); navegar("/processos/novo", { state: { rascunho: processo } }); },
  });
  const emProcesso = useMutation({
    mutationFn: (f: Blueprint) => api<{ processo: ProcessoBlueprint; agentes: { id: string; nome: string }[] }>("/estudio/em-processo", { blueprint: f }),
    onSuccess: (r) => { qc.invalidateQueries({ queryKey: ["agentes"] }); navegar("/processos/novo", { state: { rascunho: r.processo } }); },
  });
  const converter = useMutation({
    mutationFn: () => api<{ processo: { id: string } }>(`/agentes/${agenteId}/converter-em-processo`, {}),
    onSuccess: (r) => { qc.invalidateQueries({ queryKey: ["agentes"] }); qc.invalidateQueries({ queryKey: ["processos"] }); navegar("/processos/" + r.processo.id); },
  });

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
              onClick={() => sugerir.mutate({ d: descricao, fonte: pre?.fonte ?? null })}>
              {sugerir.isPending ? "Montando o agente…" : "Montar meu agente"}
            </button>
          </div>
          {sugerir.isError && <p className="mt-2 text-sm text-erro">{(sugerir.error as Error).message}</p>}
        </div>
        <div>
          <h2 className="mb-2 text-sm font-semibold uppercase tracking-wide text-tinta-3">Ou comece por um exemplo</h2>
          <div className="grid gap-2 sm:grid-cols-2">
            {padroes.data?.map((p) => (
              <button key={p.id} className="caixa p-3 text-left text-sm transition hover:border-pedra" onClick={() => { setDescricao(p.exemplo); sugerir.mutate({ d: p.exemplo, fonte: null }); }}>
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
          {!agenteId && <button className="botao-claro" onClick={() => { setBp(null); setSug(null); setVal(null); setExe(null); setFluxo(null); setProcessoPronto(null); }}>Recomeçar</button>}
          <button className="botao-claro" disabled={!valido || salvar.isPending || legado} onClick={() => salvar.mutate(false)}>Salvar rascunho</button>
          <button className="botao-pedra" disabled={!valido || salvar.isPending || semPermissao.size > 0 || legado} onClick={() => salvar.mutate(true)}
            title={valido?.risco.exige_revisao_seguranca ? "Vai para a revisão da Segurança antes de ir ao ar" : "Vai ao ar agora"}>
            <Icone nome="publicar" />{valido?.risco.exige_revisao_seguranca ? "Enviar para revisão" : "Publicar"}
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

      {fluxo && !agenteId && (
        <div className="flex flex-wrap items-center justify-between gap-3 rounded-caixa border border-info/30 bg-info-fundo/50 p-4" data-testid="oferta-processo">
          <p className="max-w-3xl text-sm">
            <b>Isto parece um processo de vários passos</b> ({fluxo.passos.length} passos: consultas, agentes e conferências).
            Um agente faz uma tarefa só. Para juntar dados, agentes, aprovações e caminhos diferentes, transforme em um processo: os agentes viram blocos que você ajusta no canvas.
          </p>
          <button className="botao-pedra" disabled={emProcesso.isPending} onClick={() => emProcesso.mutate(fluxo)}>
            {emProcesso.isPending ? "Montando o processo…" : "Transformar em processo"}
          </button>
        </div>
      )}
      {processoPronto && !agenteId && (
        <div className="flex flex-wrap items-center justify-between gap-3 rounded-caixa border border-info/30 bg-info-fundo/50 p-4" data-testid="oferta-processo-pronto">
          <p className="max-w-3xl text-sm">
            <b>Este padrão vem com o processo “{processoPronto.nome}” pronto.</b> O agente só lê e raciocina
            {sug?.acoes_no_processo && sug.acoes_no_processo.length > 0 ? <>; quem age em outros sistemas ({sug.acoes_no_processo.join(", ").toLowerCase()}) é o processo</> : null}.
            Ajuste o agente aqui e, quando quiser, monte o processo: os blocos já vêm com ele.
          </p>
          <button className="botao-pedra" disabled={!valido || montarProcesso.isPending || semPermissao.size > 0} onClick={() => montarProcesso.mutate(processoPronto)}>
            {montarProcesso.isPending ? "Montando o processo…" : "Montar o processo"}
          </button>
        </div>
      )}
      {montarProcesso.isError && <p className="text-sm text-erro">{(montarProcesso.error as Error).message}</p>}
      {emProcesso.isError && <p className="text-sm text-erro">{(emProcesso.error as Error).message}</p>}
      {legado && (
        <div className="rounded-caixa border border-alerta/40 bg-alerta-fundo/60 p-4 text-sm" role="alert" data-testid="aviso-legado">
          <b>Agente de vários passos (formato antigo).</b> Os agentes agora são trabalhadores de um passo só. Ele continua rodando como está, mas não se edita mais aqui:
          converta em um processo, que mantém as mesmas ferramentas, a mesma ordem e as mesmas aprovações.
          <div className="mt-2"><button className="botao-pedra" disabled={converter.isPending} onClick={() => converter.mutate()}>{converter.isPending ? "Convertendo…" : "Converter em processo"}</button></div>
          {converter.isError && <p className="mt-2 text-erro">{(converter.error as Error).message}</p>}
        </div>
      )}

      <div className="grid gap-6 xl:grid-cols-[1fr_360px]">
        <div className="space-y-3">
          {!legado && <FormularioTrabalhador bp={bp} ferramentas={cat.data?.ferramentas ?? []} aoMudar={setBp} />}
          {val && !val.valido && (
            <div className="rounded-caixa border border-erro/30 bg-erro-fundo p-3 text-sm text-erro">
              {val.erros.map((e, i) => <p key={i}>{e}</p>)}
            </div>
          )}
        </div>

        <aside className="space-y-4">
          {valido && !legado && (
            <div className="caixa space-y-4 p-4">
              <div className="flex items-center justify-between">
                <span className={"selo text-sm " + COR_RISCO[valido.risco.nivel]}>{NOME_RISCO[valido.risco.nivel]}</span>
                <span className="text-sm text-tinta-2">≈ {reais(valido.estimativa.custo_por_execucao_brl)} por execução</span>
              </div>
              <ul className="space-y-0.5 text-xs text-tinta-2">{valido.risco.motivos.map((m) => <li key={m}>• {m}</li>)}</ul>
              {semPermissao.size > 0 && <ul className="space-y-0.5 text-xs text-erro">{Object.values(valido.sem_permissao).map((m) => <li key={m}>• {m}</li>)}</ul>}
              <p className="text-xs text-tinta-3">
                {valido.risco.exige_revisao_seguranca
                  ? "Por tocar dados ou ações sensíveis, a publicação passa pela revisão da Segurança."
                  : "Publicação direta: os guardrails da plataforma já cobrem este agente."}
              </p>
              <div className="border-t border-linha pt-3">
                <h3 className="mb-2 text-sm font-semibold">Como o agente vai trabalhar</h3>
                <ol className="space-y-2 text-sm">
                  {valido.explicacao.map((x) => (
                    <li key={x.passo}><span className="text-tinta-2">{x.explicacao}</span></li>
                  ))}
                </ol>
              </div>
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
            <Icone nome="executar" />{testar.isPending ? "Executando…" : "Executar teste"}
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
