// "Crie o seu plugin": a pessoa nomeia uma ferramenta de mercado, cola a descrição PÚBLICA e a plataforma rascunha a especificação interna.
import { useMutation, useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api, type EspecPlugin, type PedidoPluginInterno, type RascunhoPlugin, type RegrasPluginInterno } from "../api/cliente";
import { reais } from "../components/formato";
import Icone from "../components/Icone";
import { usePreenche } from "../roteiro/estado";

const AREAS: [string, string][] = [
  ["atendimento", "Atendimento"], ["risco", "Prevenção a Fraudes"], ["pessoas", "Pessoas (RH)"], ["logistica", "Logística"],
  ["engenharia", "Engenharia de Plataforma"], ["gestao", "CoE de IA"],
];

export default function PluginCriar() {
  const navegar = useNavigate();
  const regras = useQuery({ queryKey: ["plugins-internos-regras"], queryFn: () => api<RegrasPluginInterno>("/plugins-internos/regras") });
  const pre = usePreenche("criarplugin")?.plugin;     // roteiro guiado: o pedido já vem preenchido
  const [marca, setMarca] = useState(pre?.ferramenta_mercado ?? "");
  const [descricao, setDescricao] = useState(pre?.descricao_publica ?? "");
  const [finalidade, setFinalidade] = useState(pre?.finalidade ?? "");
  const [areas, setAreas] = useState<string[]>(pre?.areas ?? []);
  const [classificacao, setClassificacao] = useState(pre?.classificacao ?? "interna");
  const [aceita, setAceita] = useState(!!pre);
  const [spec, setSpec] = useState<EspecPlugin | null>(null);
  const [avisos, setAvisos] = useState<string[]>([]);
  const corpo = { ferramenta_mercado: marca, descricao_publica: descricao, finalidade, areas, classificacao, aceita_aviso_publico: aceita };

  const rascunhar = useMutation({
    mutationFn: () => api<RascunhoPlugin>("/plugins-internos/rascunho", corpo),
    onSuccess: (r) => { setSpec(r.spec); setAvisos(r.spec.avisos ?? []); },
  });
  const enviar = useMutation({
    mutationFn: () => api<PedidoPluginInterno>("/plugins-internos", { ...corpo, spec }),
    onSuccess: () => navegar("/plugins?pedido=enviado"),
  });

  if (regras.data && !regras.data.pode_pedir) {
    return (
      <div className="space-y-4">
        <Link to="/plugins" className="text-sm text-tinta-3 hover:text-tinta">← Plugins</Link>
        <p className="caixa p-5 text-tinta-2" role="alert">Só criadores e a Engenharia pedem um plugin novo. Peça a alguém do seu time com esse papel.</p>
      </div>
    );
  }
  const mudarFerramenta = (i: number, parcial: Partial<EspecPlugin["ferramentas"][number]>) =>
    setSpec((s) => s && { ...s, ferramentas: s.ferramentas.map((f, j) => (j === i ? { ...f, ...parcial } : f)) });
  const n = spec?.comprar_ou_construir;

  return (
    <div className="space-y-6 pb-24">
      <Link to="/plugins" className="text-sm text-tinta-3 hover:text-tinta">← Plugins</Link>
      <div>
        <h1 className="text-3xl">Crie o seu plugin</h1>
        <p className="mt-1 max-w-3xl text-tinta-2">
          Nomeie uma ferramenta do mercado de que a empresa precisa e cole a descrição pública das funcionalidades. A plataforma rascunha a
          especificação de um plugin <b>interno</b>, com nome e ícone genéricos e uma conta de comprar × construir. Você edita e envia para a analista de IA.
        </p>
      </div>
      <p className="rounded-lg border border-alerta/40 bg-alerta-fundo/60 p-3 text-sm" role="note">
        <b>Só informação pública.</b> {regras.data?.aviso_publico}
      </p>

      <section className="caixa space-y-4 p-6" aria-label="Pedido">
        <label className="block">
          <span className="rotulo">Ferramenta do mercado</span>
          <input className="campo max-w-md" value={marca} onChange={(e) => setMarca(e.target.value)} maxLength={80} placeholder="Ex.: o nome da ferramenta de agenda que o time conhece" />
        </label>
        <label className="block">
          <span className="rotulo">Descrição pública das funcionalidades</span>
          <textarea className="campo min-h-32" value={descricao} onChange={(e) => setDescricao(e.target.value)} maxLength={regras.data?.max_descricao ?? 6000}
            placeholder="Cole aqui o texto da página de funcionalidades ou um trecho da documentação aberta." />
          <span className="text-xs text-tinta-3">{descricao.length}/{regras.data?.max_descricao ?? 6000} letras (mínimo {regras.data?.min_descricao ?? 40})</span>
        </label>
        <label className="block">
          <span className="rotulo">Para que a empresa precisa</span>
          <textarea className="campo" rows={2} value={finalidade} onChange={(e) => setFinalidade(e.target.value)} maxLength={600} />
        </label>
        <div className="flex flex-wrap gap-6">
          <fieldset>
            <legend className="rotulo">Quais áreas vão usar</legend>
            <div className="flex flex-wrap gap-x-3 gap-y-1 text-sm">
              {AREAS.map(([id, nome]) => (
                <label key={id} className="flex items-center gap-1">
                  <input type="checkbox" checked={areas.includes(id)} onChange={(e) => setAreas((a) => (e.target.checked ? [...a, id] : a.filter((x) => x !== id)))} /> {nome}
                </label>
              ))}
            </div>
            <span className="text-xs text-tinta-3">A sua área entra sozinha.</span>
          </fieldset>
          <label className="block">
            <span className="rotulo">Sensibilidade dos dados</span>
            <select className="campo" value={classificacao} onChange={(e) => setClassificacao(e.target.value)}>
              {["publica", "interna", "confidencial", "restrita"].map((c) => <option key={c} value={c}>{c}</option>)}
            </select>
          </label>
        </div>
        <label className="flex items-start gap-2 text-sm">
          <input type="checkbox" className="mt-1" checked={aceita} onChange={(e) => setAceita(e.target.checked)} />
          <span>Confirmo que o texto colado é informação pública, sem logotipos, marcas de terceiros nem código.</span>
        </label>
        <button className="botao-pedra" disabled={rascunhar.isPending || !marca.trim() || !descricao.trim() || !finalidade.trim() || !aceita} onClick={() => rascunhar.mutate()}>
          {rascunhar.isPending ? "Montando o rascunho…" : spec ? "Gerar o rascunho de novo" : "Gerar rascunho da especificação"}
        </button>
        {rascunhar.isError && <p className="text-sm text-erro" role="alert">{(rascunhar.error as Error).message}</p>}
      </section>

      {spec && (
        <section className="caixa space-y-5 p-6" aria-label="Rascunho da especificação" data-testid="rascunho-plugin">
          <div className="flex flex-wrap items-center gap-2">
            <h2 className="text-lg">Rascunho da especificação</h2>
            <span className="selo bg-papel text-tinta-2">plugin interno · conceitual</span>
            <span className="selo bg-papel text-tinta-2">categoria: {spec.categoria}</span>
          </div>
          {avisos.map((a) => <p key={a} className="rounded-lg bg-alerta-fundo p-3 text-sm text-alerta" role="status">{a}</p>)}
          <label className="block">
            <span className="rotulo">Nome genérico do plugin</span>
            <input className="campo max-w-md" value={spec.nome} onChange={(e) => setSpec({ ...spec, nome: e.target.value })} />
          </label>
          <label className="block">
            <span className="rotulo">Resumo</span>
            <textarea className="campo" rows={2} value={spec.resumo} onChange={(e) => setSpec({ ...spec, resumo: e.target.value })} />
          </label>
          <div>
            <span className="rotulo">Ferramentas propostas</span>
            <ul className="mt-1 space-y-2">
              {spec.ferramentas.map((f, i) => (
                <li key={f.id} className="rounded-lg border border-linha p-3 text-sm">
                  <div className="flex flex-wrap items-center gap-2">
                    <input className="campo max-w-xs" value={f.nome} onChange={(e) => mudarFerramenta(i, { nome: e.target.value })} aria-label="Nome da ferramenta" />
                    <select className="campo w-auto" value={f.acao} onChange={(e) => mudarFerramenta(i, { acao: e.target.value as "leitura" | "escrita" })} aria-label="Tipo">
                      <option value="leitura">leitura</option><option value="escrita">escrita</option>
                    </select>
                    <span className="selo bg-papel text-tinta-2">{f.classificacao}</span>
                    {f.acao === "escrita" && f.exige_confirmacao && <span className="selo bg-alerta-fundo text-alerta">pede confirmação humana</span>}
                    <button className="botao-claro ml-auto py-1" disabled={spec.ferramentas.length <= 1}
                      onClick={() => setSpec({ ...spec, ferramentas: spec.ferramentas.filter((_, j) => j !== i) })}>Remover</button>
                  </div>
                  <input className="campo mt-2" value={f.descricao} onChange={(e) => mudarFerramenta(i, { descricao: e.target.value })} aria-label="Descrição" />
                  <p className="mt-1 text-xs text-tinta-3">Entradas: {f.entradas.map((x) => x.nome).join(", ")} · Saída: {f.saida}</p>
                </li>
              ))}
            </ul>
          </div>
          <div className="grid gap-4 md:grid-cols-2">
            <div>
              <span className="rotulo">Áreas e dados</span>
              <p className="text-sm text-tinta-2">{spec.areas.join(", ")} · dado {spec.classificacao}</p>
              <span className="rotulo mt-3">Riscos</span>
              <ul className="list-disc space-y-1 pl-5 text-sm text-tinta-2">{spec.riscos.map((r) => <li key={r}>{r}</li>)}</ul>
            </div>
            {n && (
              <div className="rounded-lg bg-papel p-4 text-sm" data-testid="comprar-ou-construir">
                <span className="rotulo">Comprar × construir (3 anos)</span>
                <p>Comprar: <b>{reais(n.custo_3_anos_comprar_brl)}</b> ({reais(n.licenca_anual_brl)} por ano para ≈ {n.usuarios_estimados} pessoas)</p>
                <p>Construir: <b>{reais(n.custo_3_anos_construir_brl)}</b> ({reais(n.construir_inicial_brl)} para construir + {reais(n.operar_por_ano_brl)} por ano)</p>
                <p className="mt-1 font-semibold text-pedra-forte">Tende a compensar {n.recomendacao}</p>
                <ul className="mt-2 list-disc space-y-0.5 pl-5 text-xs text-tinta-3">{n.premissas.map((p) => <li key={p}>{p}</li>)}</ul>
              </div>
            )}
          </div>
          <div className="flex flex-wrap items-center gap-3 border-t border-linha pt-4">
            <button className="botao-pedra" disabled={enviar.isPending} onClick={() => enviar.mutate()}><Icone nome="publicar" />{enviar.isPending ? "Enviando…" : "Enviar para a analista de IA"}</button>
            <span className="text-xs text-tinta-3">O pedido vai para a fila da Helena (analista de IA) e você acompanha o estado na aba Plugins.</span>
          </div>
          {enviar.isError && <p className="text-sm text-erro" role="alert">{(enviar.error as Error).message}</p>}
        </section>
      )}
    </div>
  );
}
