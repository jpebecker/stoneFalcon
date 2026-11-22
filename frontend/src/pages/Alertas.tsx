import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api, type Alerta, type Persona } from "../api/cliente";
import { quando } from "../components/formato";

type Filtro = "abertos" | "tratamento" | "todos";
const FILTROS: [Filtro, string][] = [["abertos", "Abertos"], ["tratamento", "Em tratamento"], ["todos", "Todos"]];

/** O que fazer com um alerta: assumir (com nota), devolver ou executar a ação da regra (a API diz qual, para o seu perfil). */
function Tratamento({ a, pessoa }: { a: Alerta; pessoa: Persona }) {
  const qc = useQueryClient();
  const navegar = useNavigate();
  const [aberto, setAberto] = useState<"assumir" | "acao" | null>(null);
  const [nota, setNota] = useState("");       // a nota de quem assume
  const [motivo, setMotivo] = useState("");   // o motivo da pausa (ação), separado da nota
  const [valor, setValor] = useState("");
  const atualizar = () => {
    for (const k of ["alertas", "notificacoes", "saude-agentes", "processos"]) qc.invalidateQueries({ queryKey: [k] });
    setAberto(null); setNota(""); setMotivo(""); setValor("");
  };
  const assumir = useMutation({ mutationFn: () => api(`/alertas/${a.id}/assumir`, { nota }), onSuccess: atualizar });
  const devolver = useMutation({ mutationFn: () => api(`/alertas/${a.id}/devolver`, {}), onSuccess: atualizar });
  const executar = useMutation({
    mutationFn: () => api<{ rota?: string }>(`/alertas/${a.id}/acao`, { motivo, valor_brl: valor ? Number(valor.replace(",", ".")) : null }),
    onSuccess: (r) => { atualizar(); if (r.rota) navegar(r.rota); },
  });
  if (a.resolvido_em) return null;
  const meu = a.tratando_por === pessoa.id;
  const acao = a.acao;
  const erro = (assumir.error || devolver.error || executar.error) as Error | null;
  const pedeCampo = acao?.pede === "motivo" || acao?.pede === "valor_brl";
  return (
    <div className="mt-3 space-y-2 border-t border-linha pt-3 text-sm">
      <div className="flex flex-wrap items-center gap-2">
        {acao && (
          <button className="botao-pedra" disabled={executar.isPending}
            onClick={() => (pedeCampo && aberto !== "acao" ? setAberto("acao") : executar.mutate())}>
            {executar.isPending ? "Executando…" : acao.rotulo}
          </button>
        )}
        {!a.tratando_por && <button className="botao-claro" onClick={() => setAberto(aberto === "assumir" ? null : "assumir")}>Assumir</button>}
        {a.tratando_por && (meu || pessoa.papeis.includes("gestor_ia")) && (
          <button className="botao-claro" disabled={devolver.isPending} onClick={() => devolver.mutate()}>Devolver</button>
        )}
      </div>
      {aberto === "assumir" && (
        <div className="flex flex-wrap items-end gap-2">
          <label className="min-w-[260px] flex-1">
            <span className="rotulo">Nota curta (opcional)</span>
            <input className="campo" maxLength={300} value={nota} onChange={(e) => setNota(e.target.value)} placeholder="Ex.: falei com a Engenharia, aguardando retorno" />
          </label>
          <button className="botao-pedra" disabled={assumir.isPending} onClick={() => assumir.mutate()}>Confirmar</button>
        </div>
      )}
      {aberto === "acao" && acao && (
        <div className="flex flex-wrap items-end gap-2">
          {acao.pede === "motivo" && (
            <label className="min-w-[260px] flex-1">
              <span className="rotulo">Motivo da pausa (opcional)</span>
              <input className="campo" maxLength={500} value={motivo} onChange={(e) => setMotivo(e.target.value)} placeholder={acao.ajuda ?? ""} />
            </label>
          )}
          {acao.pede === "valor_brl" && (
            <label className="w-56">
              <span className="rotulo">Novo orçamento mensal (R$)</span>
              <input className="campo" inputMode="decimal" value={valor} onChange={(e) => setValor(e.target.value)}
                placeholder={acao.atual != null ? String(acao.atual) : ""} />
            </label>
          )}
          <button className="botao-pedra" disabled={executar.isPending || (acao.pede === "valor_brl" && !valor)} onClick={() => executar.mutate()}>Confirmar</button>
        </div>
      )}
      {erro && <p className="text-erro" role="alert">{erro.message}</p>}
    </div>
  );
}

export default function Alertas({ pessoa }: { pessoa: Persona }) {
  const qc = useQueryClient();
  const [filtro, setFiltro] = useState<Filtro>("abertos");
  const soAbertos = filtro !== "todos";   // "em tratamento" filtra os abertos aqui na tela
  const q = useQuery({ queryKey: ["alertas", soAbertos], queryFn: () => api<Alerta[]>("/alertas?abertos=" + soAbertos), refetchInterval: 15000 });
  const ler = useMutation({
    mutationFn: (id: string) => api(`/alertas/${id}/lido`, {}),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["alertas"] }); qc.invalidateQueries({ queryKey: ["notificacoes"] }); },
  });
  const lista = (q.data ?? []).filter((a) => filtro !== "tratamento" || (a.tratando_por && !a.resolvido_em));
  return (
    <div className="max-w-4xl space-y-6">
      <div className="flex items-end justify-between gap-4">
        <div>
          <h1 className="text-3xl">Alertas</h1>
          <p className="mt-1 text-tinta-2">Avisos automáticos sobre os agentes e processos pelos quais você responde. Assuma um alerta para os outros verem quem está tratando; ele fecha sozinho quando o problema some.</p>
        </div>
        <div className="flex rounded-lg border border-linha bg-folha p-0.5 text-sm" role="group" aria-label="Filtrar alertas">
          {FILTROS.map(([v, rotulo]) => (
            <button key={v} onClick={() => setFiltro(v)} aria-pressed={filtro === v}
              className={"rounded-md px-3 py-1 " + (filtro === v ? "bg-tinta text-white" : "text-tinta-2")}>
              {rotulo}
            </button>
          ))}
        </div>
      </div>
      {lista.length === 0 && <p className="caixa p-5 text-tinta-3">{filtro === "tratamento" ? "Nenhum alerta em tratamento." : "Tudo certo por aqui."}</p>}
      <ul className="space-y-3">
        {lista.map((a) => (
          <li key={a.id} className={"caixa border-l-4 p-4 " + (a.resolvido_em ? "border-l-linha opacity-70" : a.severidade === "critico" ? "border-l-erro" : "border-l-alerta")}>
            <div className="flex flex-wrap items-center gap-2">
              <span className={"selo " + (a.severidade === "critico" ? "bg-erro-fundo text-erro" : "bg-alerta-fundo text-alerta")}>
                {a.severidade === "critico" ? "Crítico" : "Atenção"}
              </span>
              {a.resolvido_em && <span className="selo bg-pedra-fundo text-pedra-forte">Resolvido</span>}
              {a.tratando_por && !a.resolvido_em && <span className="selo bg-info-fundo text-info" data-testid="em-tratamento">em tratamento · por {a.tratando_nome}</span>}
              {!a.lido && !a.resolvido_em && <span className="h-2 w-2 rounded-full bg-falcao" aria-label="não lido" />}
              <h2 className="text-base">{a.titulo}</h2>
              <span className="ml-auto text-xs text-tinta-3">{quando(a.aberto_em)}{a.ocorrencias > 1 ? ` · ${a.ocorrencias} atualizações` : ""}</span>
            </div>
            <p className="mt-1.5 text-sm text-tinta-2">{a.detalhe}</p>
            {a.tratando_por && (
              <p className="mt-1.5 text-sm text-tinta-2">
                {a.resolvido_em ? "Tratado por" : "Em tratamento por"} <b>{a.tratando_nome}</b>
                {a.tratando_desde ? ` desde ${quando(a.tratando_desde)}` : ""}{a.tratando_nota ? ` — “${a.tratando_nota}”` : ""}
              </p>
            )}
            <div className="mt-2 flex gap-3 text-sm">
              {a.agente_id && <Link to={"/agentes/" + a.agente_id} className="font-semibold text-pedra-forte">Abrir o agente</Link>}
              {a.processo_id && <Link to={"/processos/" + a.processo_id} className="font-semibold text-pedra-forte">Abrir o processo</Link>}
              {!a.lido && <button className="font-semibold text-tinta-2 hover:text-tinta" onClick={() => ler.mutate(a.id)}>Marcar como lido</button>}
            </div>
            <Tratamento a={a} pessoa={pessoa} />
          </li>
        ))}
      </ul>
    </div>
  );
}
