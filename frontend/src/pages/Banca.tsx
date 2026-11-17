// Modo apresentador: perguntas prováveis da banca, por persona e por tema, com a tela que serve de prova.
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { api, type PerguntaBanca, type Persona } from "../api/cliente";
import { useControle } from "../roteiro/Controle";

export default function Banca() {
  const [params, setParams] = useSearchParams();
  const persona = params.get("persona") ?? "";
  const tema = params.get("tema") ?? "";
  const navegar = useNavigate();
  const { mostrarProva } = useControle();
  const [aberta, setAberta] = useState<string | null>(null);
  const perfis = useQuery({ queryKey: ["perfis"], queryFn: () => api<Persona[]>("/perfis") });
  const q = useQuery({
    queryKey: ["perguntas", persona, tema],
    queryFn: () => api<{ temas: Record<string, string>; perguntas: PerguntaBanca[] }>(
      "/perguntas?" + new URLSearchParams({ ...(persona ? { persona } : {}), ...(tema ? { tema } : {}) })),
  });
  const temas = useQuery({ queryKey: ["perguntas", "", ""], queryFn: () => api<{ temas: Record<string, string>; perguntas: PerguntaBanca[] }>("/perguntas") });
  const mudar = (k: string, v: string) => { const p = new URLSearchParams(params); if (v) p.set(k, v); else p.delete(k); setParams(p, { replace: true }); };
  const nomeTema = temas.data?.temas ?? {};

  return (
    <div className="space-y-6 pb-24">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-3xl">Perguntas da banca</h1>
          <p className="mt-1 max-w-3xl text-tinta-2">
            Perguntas prováveis, com a resposta curta (até 30 s) e a tela que serve de prova. “Mostrar na tela” troca de perfil e abre a tela; use <kbd className="rounded border border-linha bg-folha px-1.5 text-xs">Alt</kbd>+<kbd className="rounded border border-linha bg-folha px-1.5 text-xs">B</kbd> de qualquer lugar.
          </p>
        </div>
        <button className="botao-claro" onClick={() => navegar(-1)}>← Voltar à demonstração</button>
      </div>

      <div className="space-y-2">
        <div className="flex flex-wrap gap-2" role="group" aria-label="Filtrar por persona">
          <button className={"selo px-3 py-1.5 text-sm " + (!persona ? "bg-tinta text-white" : "bg-papel text-tinta-2")} onClick={() => mudar("persona", "")}>Todas as personas</button>
          {perfis.data?.map((p) => (
            <button key={p.id} className={"selo px-3 py-1.5 text-sm " + (persona === p.id ? "bg-tinta text-white" : "bg-papel text-tinta-2")}
              onClick={() => mudar("persona", p.id)}>{p.nome.split(" ")[0]}</button>
          ))}
        </div>
        <div className="flex flex-wrap gap-2" role="group" aria-label="Filtrar por tema">
          <button className={"selo px-3 py-1.5 text-sm " + (!tema ? "bg-pedra text-white" : "bg-pedra-fundo text-pedra-forte")} onClick={() => mudar("tema", "")}>Todos os temas</button>
          {Object.entries(nomeTema).map(([k, v]) => (
            <button key={k} className={"selo px-3 py-1.5 text-sm " + (tema === k ? "bg-pedra text-white" : "bg-pedra-fundo text-pedra-forte")} onClick={() => mudar("tema", k)}>{v}</button>
          ))}
        </div>
      </div>

      {q.data?.perguntas.length === 0 && <p className="caixa p-5 text-tinta-3">Nenhuma pergunta com esses filtros.</p>}
      <ul className="space-y-3">
        {q.data?.perguntas.map((p) => {
          const quem = perfis.data?.find((x) => x.id === p.persona);
          const aberto = aberta === p.id || q.data!.perguntas.length <= 5;
          return (
            <li key={p.id} className="caixa p-5">
              <button className="flex w-full items-start gap-3 text-left" onClick={() => setAberta(aberta && aberta === p.id ? null : p.id)} aria-expanded={aberto}>
                <span className="selo shrink-0 bg-papel text-tinta-2">{quem?.nome.split(" ")[0] ?? p.persona}</span>
                <span className="flex-1 font-titulo text-lg font-semibold leading-snug">{p.pergunta}</span>
                <span className="selo shrink-0 bg-pedra-fundo text-pedra-forte">{nomeTema[p.tema] ?? p.tema}</span>
              </button>
              {aberto && (
                <div className="mt-3 space-y-3 border-t border-linha pt-3">
                  <p className="text-tinta">{p.resposta}</p>
                  <div className="flex flex-wrap items-center gap-3">
                    <button className="botao-pedra" onClick={() => mostrarProva(p.prova)}>Mostrar na tela</button>
                    <span className="text-sm text-tinta-3">Prova: {p.prova.rotulo} · perfil {p.prova.perfil}</span>
                  </div>
                </div>
              )}
            </li>
          );
        })}
      </ul>
    </div>
  );
}
