// Copiloto do painel lateral da extensão (rota /extensao). Fica dentro de uma moldura (iframe): a extensão não tem
// lógica nem chave, tudo roda na plataforma com as permissões de quem está logado.
//   trecho selecionado -> sugestão do agente -> campos já preenchidos -> passos -> confirmação inline -> histórico
import { useMutation, useQuery } from "@tanstack/react-query";
import { useCallback, useEffect, useMemo, useState } from "react";
import { api, type AnaliseTrecho, type Execucao, type Persona, type Saude } from "../api/cliente";
import Avatar from "../components/Avatar";
import CampoEntrada from "../components/CampoEntrada";
import Marca from "../components/Marca";
import { COR_STATUS, NOME_STATUS, ms, reais, versaoCurta } from "../components/formato";

type Item = { id: string; agente: string; quando: string; status: string; resultado: string; execId: string };
const CHAVE_HIST = "stonefalcon.extensao.historico";

function lerHistorico(): Item[] {
  try { return JSON.parse(sessionStorage.getItem(CHAVE_HIST) ?? "[]"); } catch { return []; }
}
function gravarHistorico(itens: Item[]) {
  try { sessionStorage.setItem(CHAVE_HIST, JSON.stringify(itens.slice(0, 15))); } catch { /* sem armazenamento */ }
}

// Só fala com a página que nos embute, e só pela origem dela (nunca "*"): o perfil não vai para terceiros.
function origemDoPai(): string | null {
  try {
    const o = location.ancestorOrigins?.[0] || (document.referrer ? new URL(document.referrer).origin : "");
    return o && o !== "null" ? o : null;
  } catch { return null; }
}
function avisarExtensao(msg: Record<string, unknown>) {
  const o = origemDoPai();
  if (window.parent !== window && o) window.parent.postMessage({ origem: "stonefalcon-plataforma", ...msg }, o);
}

// ---------------------------------------------------------------- primeira execução
function Boas({ aoEntrar, erro }: { aoEntrar: (id: string) => void; erro: boolean }) {
  const perfis = useQuery({ queryKey: ["perfis"], queryFn: () => api<Persona[]>("/perfis") });
  return (
    <div className="space-y-5 p-5">
      <Marca claro />
      <div>
        <h1 className="text-2xl">Bem-vindo ao copiloto</h1>
        <p className="mt-1 text-sm text-tinta-2">Selecione um texto em qualquer página e peça a um processo ou agente. Dados pessoais são mascarados antes de qualquer modelo ver.</p>
      </div>
      {erro && <p className="rounded-lg bg-erro-fundo p-3 text-sm text-erro">Não reconheci o seu perfil. Escolha quem você é.</p>}
      {perfis.isError && <p className="rounded-lg bg-erro-fundo p-3 text-sm text-erro">Não consegui falar com a plataforma. Ela está ligada?</p>}
      <div>
        <h2 className="rotulo">Quem é você hoje?</h2>
        <ul className="mt-2 space-y-2">
          {perfis.data?.map((p) => (
            <li key={p.id}>
              <button className="caixa flex w-full items-center gap-3 p-3 text-left transition hover:border-pedra" onClick={() => aoEntrar(p.id)}>
                <Avatar pessoa={p} tamanho={36} />
                <span className="min-w-0"><span className="block truncate font-semibold">{p.nome}</span><span className="block truncate text-xs text-tinta-3">{p.cargo} · {p.area_nome}</span></span>
              </button>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------- resultado de uma execução
function Passos({ exe, ao_vivo }: { exe: Execucao; ao_vivo: boolean }) {
  const passos = exe.passos_tela ?? exe.passos;
  const ordem = exe.blueprint.passos.map((p) => p.id).filter((id) => passos[id]);
  const [visiveis, setVisiveis] = useState(ao_vivo ? 0 : ordem.length);
  useEffect(() => {
    if (!ao_vivo) return;
    setVisiveis(0);
    const t = setInterval(() => setVisiveis((v) => { if (v >= ordem.length) { clearInterval(t); return v; } return v + 1; }), 420);
    return () => clearInterval(t);
  }, [exe.id]); // eslint-disable-line react-hooks/exhaustive-deps
  return (
    <ol className="space-y-1.5" aria-live="polite">
      {ordem.map((id, i) => {
        const r = passos[id];
        const pronto = i < visiveis;
        return (
          <li key={id} className={"caixa flex items-center gap-2 px-3 py-2 text-sm transition-opacity " + (pronto ? "opacity-100" : "opacity-40")}>
            <span className={"selo " + (pronto ? COR_STATUS[r.status] : "bg-papel text-tinta-3")}>{pronto ? NOME_STATUS[r.status] ?? r.status : "…"}</span>
            <span className="flex-1">{r.titulo}</span>
            <span className="text-xs text-tinta-3">{pronto ? ms(r.duracao_estimada_ms) : ""}</span>
          </li>
        );
      })}
    </ol>
  );
}

function Resposta({ exe, pessoa, aoMudar, ao_vivo }: { exe: Execucao; pessoa: Persona; aoMudar: (e: Execucao) => void; ao_vivo: boolean }) {
  const [copiado, setCopiado] = useState(false);
  const decidir = useMutation({ mutationFn: (aprovar: boolean) => api<Execucao>(`/execucoes/${exe.id}/decisao`, { aprovar }), onSuccess: aoMudar });
  const texto = exe.resultado_tela ?? exe.resultado ?? "";
  const final = exe.blueprint.passos[exe.blueprint.passos.length - 1].id;
  const dito = (exe.passos_tela ?? exe.passos)[final]?.saida;
  const resposta = texto || (typeof dito === "string" ? dito : "");
  const podeDecidir = exe.status === "aguardando_aprovacao" && pessoa.area === exe.area && (pessoa.id === exe.persona || pessoa.papeis.includes("curador"));
  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-2 text-xs text-tinta-3">
        <span className={"selo " + COR_STATUS[exe.status]}>{NOME_STATUS[exe.status] ?? exe.status}</span>
        <span>{reais(exe.custo_brl)} · {ms(exe.duracao_estimada_ms)}</span>
        {exe.simulado && <span className="selo bg-alerta-fundo text-alerta">simulado</span>}
        {Object.values(exe.passos_tela ?? exe.passos).some((r) => r.reserva) && (
          <span className="selo bg-alerta-fundo text-alerta" title="O modelo falhou e o passo usou a resposta pré-determinada">resposta de reserva</span>
        )}
      </div>
      <Passos exe={exe} ao_vivo={ao_vivo} />
      {exe.status === "aguardando_aprovacao" && exe.pendencia && (
        <div className="rounded-caixa border border-alerta/50 bg-alerta-fundo p-3 text-sm">
          <b>O agente quer: {exe.pendencia.conector_nome ?? exe.pendencia.titulo}</b>
          {exe.pendencia.justificativa && <p className="mt-1 text-tinta-2">{exe.pendencia.justificativa}</p>}
          {podeDecidir ? (
            <div className="mt-2 flex gap-2">
              <button className="botao-pedra py-1.5" disabled={decidir.isPending} onClick={() => decidir.mutate(true)}>Confirmar ação</button>
              <button className="botao-claro py-1.5" disabled={decidir.isPending} onClick={() => decidir.mutate(false)}>Recusar</button>
            </div>
          ) : <p className="mt-1 text-xs text-tinta-3">Só quem disparou o agente, ou um curador da área, pode decidir.</p>}
          {decidir.isError && <p className="mt-1 text-xs text-erro">{(decidir.error as Error).message}</p>}
        </div>
      )}
      {exe.status === "escalada" && exe.motivo && (
        <p className="rounded-caixa border border-falcao/40 bg-falcao-fundo p-3 text-sm"><b>Passei para um humano.</b> {exe.motivo}</p>
      )}
      {resposta && (
        <div className="caixa p-3">
          <div className="mb-1 flex items-center justify-between">
            <span className="rotulo mb-0">Resposta</span>
            <button className="text-xs font-semibold text-pedra-forte" onClick={() => { navigator.clipboard?.writeText(resposta).then(() => { setCopiado(true); setTimeout(() => setCopiado(false), 1500); }).catch(() => {}); }}>
              {copiado ? "Copiado ✓" : "Copiar"}
            </button>
          </div>
          <p className="whitespace-pre-wrap text-sm">{resposta}</p>
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------- painel
export default function Extensao({ pessoa, aoEntrar, aoSair, erroPerfil }: {
  pessoa: Persona | null; aoEntrar: (id: string) => void; aoSair: () => void; erroPerfil: boolean;
}) {
  const [trecho, setTrecho] = useState("");   // o texto chega por mensagem, nunca pelo endereço (iria para os logs)
  const [agenteId, setAgenteId] = useState(() => new URLSearchParams(location.search).get("agente") ?? "");
  const [entrada, setEntrada] = useState<Record<string, string>>({});
  const [exe, setExe] = useState<Execucao | null>(null);
  const [aoVivo, setAoVivo] = useState(false);
  const [historico, setHistorico] = useState<Item[]>(lerHistorico);
  const [verItem, setVerItem] = useState<string | null>(null);
  const [menu, setMenu] = useState(false);
  const [planilha, setPlanilha] = useState<{ tipo: "planilha"; url: string; titulo?: string } | null>(null);   // a aba aberta é uma planilha?

  const saude = useQuery({ queryKey: ["saude"], queryFn: () => api<Saude>("/saude"), refetchInterval: 20000, retry: 0 });
  const perfis = useQuery({ queryKey: ["perfis"], queryFn: () => api<Persona[]>("/perfis"), enabled: menu });
  const analise = useQuery({
    queryKey: ["extensao", "analisar", trecho, pessoa?.id], enabled: !!pessoa,
    queryFn: () => api<AnaliseTrecho>("/extensao/analisar", { trecho }),
  });
  const agentes = analise.data?.agentes ?? [];
  const agente = agentes.find((a) => a.id === agenteId) ?? null;

  // avisa a extensão de quem está logado (para o menu de contexto por agente)
  useEffect(() => { if (pessoa) avisarExtensao({ tipo: "perfil", perfil: pessoa.id }); }, [pessoa?.id]); // eslint-disable-line react-hooks/exhaustive-deps

  // trechos longos chegam por mensagem da extensão, não pelo endereço
  useEffect(() => {
    const ouvir = (ev: MessageEvent) => {
      if (ev.source !== window.parent || window.parent === window) return;   // só a moldura que contém esta tela
      const d = ev.data;
      if (d?.origem !== "stonefalcon-extensao") return;
      if ("planilha" in d) setPlanilha(d.planilha && d.planilha.tipo === "planilha" ? d.planilha : null);
      if (typeof d.trecho === "string") { setTrecho(d.trecho.slice(0, 8000)); setExe(null); setAgenteId(typeof d.agente === "string" ? d.agente : ""); }
    };
    window.addEventListener("message", ouvir);
    avisarExtensao({ tipo: "pronto" });   // agora o texto selecionado já pode ser entregue
    return () => window.removeEventListener("message", ouvir);
  }, []);

  // com o trecho analisado: escolhe o agente sugerido (ou o pedido pelo menu de contexto) e preenche os campos
  useEffect(() => {
    if (!analise.data) return;
    const alvo = agentes.find((a) => a.id === agenteId) ?? agentes.find((a) => a.id === analise.data!.sugerido);
    if (alvo && alvo.id !== agenteId) setAgenteId(alvo.id);
    if (alvo) setEntrada({ ...alvo.preenchido });
  }, [analise.data, agenteId]); // eslint-disable-line react-hooks/exhaustive-deps

  const escolher = useCallback((id: string) => {
    const a = agentes.find((x) => x.id === id);
    setAgenteId(id); setEntrada({ ...(a?.preenchido ?? {}) }); setExe(null);
  }, [agentes]);

  const executar = useMutation({
    mutationFn: () => api<Execucao>(`/${agente?.tipo === "processo" ? "processos" : "agentes"}/${agenteId}/executar`, { entrada }),
    onSuccess: (e) => {
      setExe(e); setAoVivo(true);
      const resultado = e.resultado_tela ?? e.resultado ?? "";
      const itens = [{ id: e.id, agente: e.agente_nome, quando: new Date().toISOString(), status: e.status, resultado, execId: e.id }, ...historico];
      setHistorico(itens); gravarHistorico(itens);
    },
  });

  const faltando = useMemo(() => (agente?.campos ?? []).filter((c) => !entrada[c.id]), [agente, entrada]);
  const conectado = saude.data && !saude.isError;

  if (!pessoa) return <div className="ext-tema min-h-full bg-papel text-tinta"><Boas aoEntrar={aoEntrar} erro={erroPerfil} /></div>;

  return (
    <div className="ext-tema min-h-full bg-papel pb-8 text-tinta">
      <header className="sticky top-0 z-10 flex items-center gap-2 border-b border-linha bg-folha/95 px-4 py-2.5 backdrop-blur">
        <Marca claro />
        <span className={"selo ml-auto " + (conectado ? "bg-pedra-fundo text-pedra-forte" : "bg-erro-fundo text-erro")}
          title={conectado ? "Plataforma conectada" : "Sem conexão com a plataforma"}>
          <span aria-hidden="true">●</span> {conectado ? (saude.data!.modo === "real" ? "Modelos reais" : "Simulado") : "Sem conexão"}
        </span>
        <div className="relative">
          <button className="flex items-center gap-2 rounded-lg px-1 py-0.5 hover:bg-papel" onClick={() => setMenu(!menu)} aria-haspopup="menu" aria-expanded={menu} aria-label={"Perfil: " + pessoa.nome}>
            <Avatar pessoa={pessoa} tamanho={28} />
          </button>
          {menu && (
            <div role="menu" className="caixa absolute right-0 top-full z-20 mt-1 w-60 p-1.5">
              <div className="px-2 py-1 text-xs text-tinta-3">{pessoa.nome} · {pessoa.cargo}</div>
              {perfis.data?.filter((p) => p.id !== pessoa.id).map((p) => (
                <button key={p.id} role="menuitem" className="flex w-full items-center gap-2 rounded-lg px-2 py-1.5 text-left text-sm hover:bg-papel" onClick={() => { setMenu(false); setExe(null); setAgenteId(""); aoEntrar(p.id); }}>
                  <Avatar pessoa={p} tamanho={22} />{p.nome}
                </button>
              ))}
              <button role="menuitem" className="w-full rounded-lg px-2 py-1.5 text-left text-xs text-tinta-3 hover:bg-papel" onClick={aoSair}>Sair</button>
            </div>
          )}
        </div>
      </header>

      {!conectado && saude.isError && (
        <div className="m-4 rounded-caixa border border-erro/40 bg-erro-fundo p-3 text-sm">
          <b>A plataforma não respondeu.</b> Ligue o StoneFalcon no computador e tente de novo.
          <button className="botao-claro mt-2 w-full py-1.5" onClick={() => saude.refetch()}>Tentar de novo</button>
        </div>
      )}

      <div className="space-y-4 p-4">
        {/* atalho para criar um agente: só para quem tem a aba Estúdio (a lista de abas vem do back) */}
        {pessoa.abas.includes("estudio") ? (
          <div className="space-y-2">
            {planilha && (
              <button className="botao-pedra w-full" onClick={() => avisarExtensao({ tipo: "criar-agente", trecho: "", fonte: planilha })}
                title="Abre o Estúdio numa aba nova, com a planilha já configurada como fonte">
                Criar Agente de IA a partir desta planilha
              </button>
            )}
            <button className={planilha ? "botao-claro w-full" : "botao-pedra w-full"} onClick={() => avisarExtensao({ tipo: "criar-agente", trecho })}
              title="Abre o Estúdio numa aba nova, já no seu perfil">
              Criar Agente de IA{trecho ? " com este trecho" : ""}
            </button>
          </div>
        ) : (
          <p role="note" className="caixa p-3 text-sm text-tinta-2">
            Seu perfil não cria agentes.{" "}
            <a href="/" target="_blank" rel="noreferrer" className="font-semibold text-pedra-forte underline">Ir ao Início</a>
          </p>
        )}
        {trecho ? (
          <section className="caixa p-3 text-sm" aria-label="Trecho selecionado">
            <div className="flex items-center justify-between"><span className="rotulo mb-0">Trecho selecionado</span>
              <button className="text-xs text-tinta-3 hover:text-tinta" onClick={() => { setTrecho(""); setExe(null); }}>limpar</button></div>
            <p className="mt-1 line-clamp-4 text-tinta-2">{trecho}</p>
            <p className="mt-1 text-xs text-tinta-3">Dados pessoais são mascarados antes de qualquer modelo ver.</p>
          </section>
        ) : (
          <section className="caixa border-dashed p-4 text-center text-sm text-tinta-2">
            <p className="font-semibold">Nada selecionado ainda</p>
            <p className="mt-1 text-xs text-tinta-3">Selecione um texto na página e clique em “Perguntar ao StoneFalcon”. Ou escolha um agente abaixo e digite.</p>
          </section>
        )}

        {analise.isPending && <div className="space-y-2" aria-busy="true"><div className="h-14 animate-pulse rounded-caixa bg-folha" /><div className="h-24 animate-pulse rounded-caixa bg-folha" /></div>}
        {analise.isError && <p className="rounded-caixa bg-erro-fundo p-3 text-sm text-erro">{(analise.error as Error).message}</p>}
        {analise.data && agentes.length === 0 && (
          <p className="caixa p-4 text-sm text-tinta-2">Nenhum processo ou agente publicado para a sua área ainda. Crie um no Estúdio da plataforma.</p>
        )}

        {agentes.length > 0 && (
          <section className="space-y-2">
            {analise.data?.sugerido && agente?.id === analise.data.sugerido && (
              <p className="text-xs font-semibold text-pedra-forte">✦ Sugestão pelo trecho: {agente.nome}</p>
            )}
            <label className="block">
              <span className="rotulo">Processo ou agente</span>
              <select className="campo" value={agenteId} onChange={(e) => escolher(e.target.value)}>
                <option value="">Escolha um processo ou agente da sua área…</option>
                {(["processo", "agente"] as const).map((tipo) => agentes.some((a) => a.tipo === tipo) && (
                  <optgroup key={tipo} label={tipo === "processo" ? "Processos" : "Agentes"}>
                    {agentes.filter((a) => a.tipo === tipo).map((a) => <option key={a.id} value={a.id}>{a.nome}</option>)}
                  </optgroup>
                ))}
              </select>
            </label>
            {agente && <p className="text-xs text-tinta-3">{agente.objetivo}</p>}
          </section>
        )}

        {agente && (
          <section className="space-y-3">
            {agente.detectado.length > 0 && (
              <ul className="flex flex-wrap gap-1.5">{agente.detectado.map((d) => <li key={d} className="selo bg-pedra-fundo text-pedra-forte">detectei · {d}</li>)}</ul>
            )}
            {agente.campos.map((c) => (
              <CampoEntrada key={c.id} campo={c} pessoa={pessoa} compacto valor={entrada[c.id] ?? ""}
                aoMudar={(v) => setEntrada((e) => ({ ...e, [c.id]: v }))} />
            ))}
            <button className="botao-pedra w-full" disabled={executar.isPending || faltando.length > 0} onClick={() => executar.mutate()}>
              {executar.isPending ? "Executando…" : faltando.length ? "Preencha: " + faltando.map((c) => c.rotulo.toLowerCase()).join(", ") : agente?.tipo === "processo" ? "Executar processo" : "Executar agente"}
            </button>
            {executar.isError && <p className="text-sm text-erro">{(executar.error as Error).message}</p>}
          </section>
        )}

        {executar.isPending && <div className="h-20 animate-pulse rounded-caixa bg-folha" aria-busy="true" />}
        {exe && <Resposta exe={exe} pessoa={pessoa} ao_vivo={aoVivo} aoMudar={(e) => { setAoVivo(false); setExe(e); }} />}

        {historico.length > 0 && (
          <section aria-label="Histórico da sessão">
            <div className="flex items-center justify-between"><h2 className="rotulo mb-0">Nesta sessão</h2>
              <button className="text-xs text-tinta-3 hover:text-tinta" onClick={() => { setHistorico([]); gravarHistorico([]); }}>limpar</button></div>
            <ul className="mt-2 space-y-1.5">
              {historico.map((h) => (
                <li key={h.id} className="caixa p-2.5 text-sm">
                  <button className="flex w-full items-center gap-2 text-left" onClick={() => setVerItem(verItem === h.id ? null : h.id)} aria-expanded={verItem === h.id}>
                    <span className={"selo " + COR_STATUS[h.status]}>{NOME_STATUS[h.status] ?? h.status}</span>
                    <span className="flex-1 truncate">{h.agente}</span>
                    <span className="text-xs text-tinta-3">{new Date(h.quando).toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" })}</span>
                  </button>
                  {verItem === h.id && <p className="mt-2 whitespace-pre-wrap border-t border-linha pt-2 text-xs text-tinta-2">{h.resultado || "Sem texto de resposta."}</p>}
                </li>
              ))}
            </ul>
          </section>
        )}
        {conectado && <p className="pt-2 text-center text-[11px] text-tinta-3">StoneFalcon {versaoCurta(saude.data!.versao)}</p>}
      </div>
    </div>
  );
}
