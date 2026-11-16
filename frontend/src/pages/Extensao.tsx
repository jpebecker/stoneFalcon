// Tela compacta para o painel lateral da extensão: escolher um agente publicado e
// rodá-lo com o trecho selecionado na página. Sem menu lateral; mesmas permissões.
import { useMutation, useQuery } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";
import { api, type Agente, type AgenteDetalhe, type Execucao, type Persona, type Saude } from "../api/cliente";
import LinhaDoTempo from "../components/LinhaDoTempo";
import Marca from "../components/Marca";

const CAMPOS_DE_TEXTO = ["pergunta", "relato", "tema", "consulta", "descricao", "texto"];

export default function Extensao({ pessoa, aoSair }: { pessoa: Persona; aoSair: () => void }) {
  const [trecho, setTrecho] = useState(() => new URLSearchParams(location.search).get("trecho") ?? "");
  const [agenteId, setAgenteId] = useState<string>("");
  const [entrada, setEntrada] = useState<Record<string, string>>({});
  const [exe, setExe] = useState<Execucao | null>(null);
  const saude = useQuery({ queryKey: ["saude"], queryFn: () => api<Saude>("/saude") });
  const agentes = useQuery({ queryKey: ["agentes"], queryFn: () => api<Agente[]>("/agentes") });
  const detalhe = useQuery({ queryKey: ["agente", agenteId], queryFn: () => api<AgenteDetalhe>("/agentes/" + agenteId), enabled: !!agenteId });

  // trechos longos chegam por mensagem da extensão, não pelo endereço
  useEffect(() => {
    const ouvir = (ev: MessageEvent) => {
      // só aceita mensagens da moldura que contém esta tela (o painel lateral da extensão)
      if (ev.source !== window.parent || window.parent === window) return;
      if (ev.data?.origem === "stonefalcon-extensao" && typeof ev.data.trecho === "string") { setTrecho(ev.data.trecho.slice(0, 8000)); setExe(null); }
    };
    window.addEventListener("message", ouvir);
    return () => window.removeEventListener("message", ouvir);
  }, []);

  const executaveis = (agentes.data ?? []).filter((a) => a.estado === "publicado" && (a.area === pessoa.area || a.compartilhado_com.includes(pessoa.area)));
  const campos = useMemo(() => {
    const v = detalhe.data?.versoes.find((x) => x.numero === detalhe.data?.versao_publicada);
    return v?.blueprint.campos_entrada ?? [];
  }, [detalhe.data]);

  // o trecho selecionado vai para o primeiro campo de texto livre do agente
  useEffect(() => {
    const alvo = campos.find((c) => CAMPOS_DE_TEXTO.includes(c));
    if (alvo && trecho) setEntrada((e) => ({ ...e, [alvo]: trecho.slice(0, 3000) }));
  }, [campos, trecho]);

  const executar = useMutation({ mutationFn: () => api<Execucao>(`/agentes/${agenteId}/executar`, { entrada }), onSuccess: setExe });

  return (
    <div className="min-h-full space-y-4 bg-papel p-4">
      <div className="flex items-center justify-between">
        <Marca />
        <button className="text-xs text-tinta-3 hover:text-tinta" onClick={aoSair}>{pessoa.nome.split(" ")[0]} · trocar</button>
      </div>
      {trecho && (
        <div className="caixa p-3 text-sm">
          <div className="rotulo">Trecho selecionado</div>
          <p className="line-clamp-4 text-tinta-2">{trecho}</p>
          <p className="mt-1 text-xs text-tinta-3">Dados pessoais do trecho são mascarados antes de qualquer modelo ver.</p>
        </div>
      )}
      <label className="block">
        <span className="rotulo">Agente</span>
        <select className="campo" value={agenteId} onChange={(e) => { setAgenteId(e.target.value); setEntrada({}); setExe(null); }}>
          <option value="">Escolha um agente da sua área…</option>
          {executaveis.map((a) => <option key={a.id} value={a.id}>{a.nome}</option>)}
        </select>
        {agentes.data && executaveis.length === 0 && <span className="mt-1 block text-xs text-tinta-3">Nenhum agente publicado para a sua área ainda.</span>}
      </label>
      {agenteId && campos.map((c) => (
        <label key={c} className="block">
          <span className="rotulo">{c.replace(/_/g, " ")}</span>
          {CAMPOS_DE_TEXTO.includes(c)
            ? <textarea className="campo min-h-[80px]" value={entrada[c] ?? ""} onChange={(e) => setEntrada({ ...entrada, [c]: e.target.value })} />
            : <input className="campo" value={entrada[c] ?? ""} onChange={(e) => setEntrada({ ...entrada, [c]: e.target.value })} />}
        </label>
      ))}
      {agenteId && (
        <button className="botao-pedra w-full" disabled={executar.isPending || campos.some((c) => !entrada[c])} onClick={() => executar.mutate()}>
          {executar.isPending ? "Executando…" : "Executar"}
        </button>
      )}
      {executar.isError && <p className="text-sm text-erro">{(executar.error as Error).message}</p>}
      {exe && <LinhaDoTempo exe={exe} pessoa={pessoa} cotacao={saude.data?.cotacao_dolar ?? 5.52} aoMudar={setExe} />}
    </div>
  );
}
