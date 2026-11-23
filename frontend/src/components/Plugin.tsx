// Peças compartilhadas da vitrine e da página de cada plugin: ícone genérico por categoria, selos e as ações de integrar.
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link } from "react-router-dom";
import { api, type PedidoPlugin, type Plugin } from "../api/cliente";
import { quando } from "./formato";

const COR_CLASSE: Record<string, string> = {
  publica: "bg-papel text-tinta-2", interna: "bg-info-fundo text-info",
  confidencial: "bg-alerta-fundo text-alerta", restrita: "bg-falcao-fundo text-falcao",
};
export const classeSelo = (c: string) => COR_CLASSE[c] ?? "bg-papel text-tinta-2";

export const NOME_ESTADO_PLUGIN: Record<Plugin["estado"], string> = {
  disponivel: "Disponível", integrado: "Integrado", aguardando_aprovacao: "Aguardando aprovação",
};
export const COR_ESTADO_PLUGIN: Record<Plugin["estado"], string> = {
  disponivel: "bg-papel text-tinta-2", integrado: "bg-pedra-fundo text-pedra-forte", aguardando_aprovacao: "bg-alerta-fundo text-alerta",
};

// Ícones genéricos por categoria (nada de logo oficial de terceiros).
const ICONES: Record<string, string> = {
  helpdesk: "M4 6h16v10H8l-4 4V6z",                                         // balão de atendimento
  crm: "M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8zM4 20c0-4 4-6 8-6s8 2 8 6",     // pessoa
  chat: "M4 5h16v10H9l-5 4V5zM8 9h8M8 12h5",                                // chat
  trabalho: "M4 5h5v14H4zM10 5h5v9h-5zM16 5h4v6h-4z",                       // quadro
  documentos: "M7 3h7l4 4v14H7zM14 3v4h4M9 12h6M9 16h6",                    // documento
  ti: "M3 5h18v11H3zM8 20h8M12 16v4",                                       // monitor
  rh: "M8 11a3 3 0 1 0 0-6 3 3 0 0 0 0 6zM2 19c0-3 3-5 6-5s6 2 6 5M16 8h6M16 12h6",   // equipe
  observabilidade: "M3 12h4l3-7 4 14 3-7h4",                                // pulso
};

export function IconeCategoria({ categoria, tamanho = 40 }: { categoria: string; tamanho?: number }) {
  return (
    <span aria-hidden="true" className="inline-flex shrink-0 items-center justify-center rounded-xl bg-pedra-fundo text-pedra-forte"
      style={{ width: tamanho, height: tamanho }}>
      <svg viewBox="0 0 24 24" width={tamanho * 0.55} height={tamanho * 0.55} fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
        <path d={ICONES[categoria] ?? ICONES.documentos} />
      </svg>
    </span>
  );
}

export const SeloReal = () => (
  <span className="selo bg-pedra-fundo text-pedra-forte" title="Este plugin funciona de verdade: guarda e lê os seus arquivos">real</span>
);

/** O selo do plugin: "real" quando funciona de verdade, "simulado" nos demais. */
export const SeloDoPlugin = ({ real, interno }: { real?: boolean; interno?: boolean }) => (
  real ? <SeloReal /> : interno ? (
    <span className="inline-flex flex-wrap gap-1">
      <span className="selo bg-alerta-fundo text-alerta" title="Criado pelo pedido Crie o seu plugin: as ferramentas são conceituais">interno · conceitual</span>
      <SeloSimulado />
    </span>
  ) : <SeloSimulado />
);

export const SeloSimulado = () => (
  <span className="selo bg-papel text-tinta-2" title="Protótipo acadêmico: nenhum sistema externo real é chamado">simulado</span>
);

/** Integrar, pedir, remover: o que a pessoa pode fazer com este plugin agora (a regra vem do back). */
export function AcoesPlugin({ p, aoMudar }: { p: Plugin; aoMudar?: () => void }) {
  const qc = useQueryClient();
  const [aviso, setAviso] = useState<string | null>(null);
  const depois = () => {
    qc.invalidateQueries({ queryKey: ["plugins"] }); qc.invalidateQueries({ queryKey: ["plugin"] });
    qc.invalidateQueries({ queryKey: ["ferramentas"] }); qc.invalidateQueries({ queryKey: ["plugin-pedidos"] });
    qc.invalidateQueries({ queryKey: ["agentes"] }); qc.invalidateQueries({ queryKey: ["notificacoes"] });
    aoMudar?.();
  };
  const integrar = useMutation({
    mutationFn: () => api<{ resultado: string }>(`/plugins/${p.id}/integrar`, {}),
    onSuccess: (r) => { setAviso(r.resultado === "pedido" ? "Pedido enviado à Segurança. Você recebe o resultado nos alertas." : null); depois(); },
  });
  const pedir = useMutation({
    mutationFn: () => api(`/plugins/${p.id}/pedir`, {}),
    onSuccess: () => { setAviso("Pedido registrado. Quem integra plugins vai ver."); depois(); },
  });
  const remover = useMutation({
    mutationFn: () => api(`/plugins/${p.id}/integracao`, undefined, "DELETE"),
    onSuccess: () => { setAviso(null); depois(); },
  });
  const erro = (integrar.error ?? pedir.error ?? remover.error) as Error | null;
  const rotuloIntegrar = p.exige_aprovacao_para_integrar ? "Integrar (pede aprovação)" : "Integrar";
  return (
    <div className="space-y-2">
      <div className="flex flex-wrap items-center gap-2">
        {p.estado === "integrado" && <Link to={"/plugins/" + p.id} className="botao-pedra">Abrir</Link>}
        {p.pode_integrar && (
          <button className="botao-pedra" data-alvo="acao-integrar" disabled={integrar.isPending} onClick={() => { setAviso(null); integrar.mutate(); }}>
            {integrar.isPending ? "Integrando…" : rotuloIntegrar}
          </button>
        )}
        {p.pode_pedir && (
          <button className="botao-claro" disabled={pedir.isPending} onClick={() => { setAviso(null); pedir.mutate(); }}>
            {pedir.isPending ? "Enviando…" : "Pedir integração"}
          </button>
        )}
        {p.pode_remover && (
          <button className="botao-claro text-erro" disabled={remover.isPending}
            onClick={() => confirm("Remover a integração de " + p.nome + "? As ferramentas saem do Catálogo e os agentes que as usam ficam sinalizados.") && remover.mutate()}>
            Remover integração
          </button>
        )}
        {p.estado === "aguardando_aprovacao" && (
          <span className="text-sm text-alerta">
            {p.pedido_pendente?.meu ? "Seu pedido espera o parecer." : p.pedido_pendente?.pode_decidir ? "Pedido de " + p.pedido_pendente.solicitante + " espera a sua decisão." : "Pedido de " + (p.pedido_pendente?.solicitante ?? "alguém") + " na fila da Segurança."}
          </span>
        )}
      </div>
      {aviso && <p className="text-sm text-pedra-forte" role="status">{aviso}</p>}
      {erro && <p className="text-sm text-erro" role="alert">{erro.message}</p>}
    </div>
  );
}

/** Pedido de integração de plugin sensível: o parecer de quem decide (Segurança; o CoE de IA nos pedidos da própria Segurança). */
export function CartaoPedidoPlugin({ pedido }: { pedido: PedidoPlugin }) {
  const qc = useQueryClient();
  const [parecer, setParecer] = useState("");
  const decidir = useMutation({
    mutationFn: (aprovar: boolean) => api(`/plugins/pedidos/${pedido.id}/decisao`, { aprovar, parecer }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["plugin-pedidos"] }); qc.invalidateQueries({ queryKey: ["plugins"] }); qc.invalidateQueries({ queryKey: ["plugin"] }); qc.invalidateQueries({ queryKey: ["ferramentas"] }); qc.invalidateQueries({ queryKey: ["notificacoes"] }); },
  });
  return (
    <article className="caixa space-y-4 border-info/30 p-5" aria-label={"Pedido de integração: " + pedido.plugin_nome}>
      <div className="flex flex-wrap items-center gap-3">
        <Link to={"/plugins/" + pedido.plugin_id} className="font-titulo text-xl font-semibold hover:text-pedra-forte">Integrar {pedido.plugin_nome}</Link>
        <SeloSimulado />
        <span className="text-sm text-tinta-3">pedido de {pedido.solicitante_nome} · área {pedido.area_nome} em {quando(pedido.criado_em)}</span>
        <span className={"selo ml-auto " + classeSelo(pedido.classificacao)}>{pedido.classificacao}</span>
      </div>
      <p className="text-sm"><span className="text-tinta-3">Motivo:</span> {pedido.motivo}</p>
      <div>
        <h3 className="mb-1 text-sm font-semibold">Ferramentas que entram no Catálogo</h3>
        <ul className="flex flex-wrap gap-2">
          {pedido.ferramentas.map((f) => <li key={f.id} className="selo bg-papel text-tinta-2">{f.nome} · {f.acao}</li>)}
        </ul>
      </div>
      {!pedido.pode_decidir ? (
        <p className="rounded-lg bg-alerta-fundo p-3 text-sm text-alerta">
          {pedido.e_meu ? "Você fez este pedido: quem pede não decide (quatro olhos). O CoE de IA dá o parecer." : "Este pedido espera o parecer de outra pessoa."}
        </p>
      ) : (
        <>
          <label className="block">
            <span className="rotulo">Parecer (fica na auditoria e aparece para quem pediu)</span>
            <textarea className="campo min-h-[70px]" value={parecer} onChange={(e) => setParecer(e.target.value)} />
          </label>
          <div className="flex gap-2">
            <button className="botao-pedra" disabled={!parecer.trim() || decidir.isPending} onClick={() => decidir.mutate(true)}>Aprovar e integrar</button>
            <button className="botao-claro" disabled={!parecer.trim() || decidir.isPending} onClick={() => decidir.mutate(false)}>Recusar</button>
          </div>
        </>
      )}
      {decidir.isError && <p className="text-sm text-erro">{(decidir.error as Error).message}</p>}
    </article>
  );
}
