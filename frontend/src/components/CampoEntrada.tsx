// Campo de entrada de um agente, em linguagem de usuário: ninguém digita `lojista_id`.
//  - lojista:      busca pelo nome ("Padaria Pão Dourado"), o código aparece só como detalhe
//  - colaborador:  "Eu mesmo" já vem marcado; RH pode buscar outra pessoa por nome
//  - opcao:        lista fechada
//  - texto(_longo): texto livre, com exemplo
import { useQuery } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { api, type Campo, type Colaborador, type Lojista, type Persona } from "../api/cliente";

type Props = { campo: Campo; valor: string; aoMudar: (v: string) => void; pessoa: Persona; compacto?: boolean };

function useDebounce<T>(v: T, ms = 200) {
  const [d, setD] = useState(v);
  useEffect(() => { const t = setTimeout(() => setD(v), ms); return () => clearTimeout(t); }, [v, ms]);
  return d;
}

function EscolherLojista({ campo, valor, aoMudar }: Props) {
  const [busca, setBusca] = useState("");
  const q = useDebounce(busca);
  const achados = useQuery({ queryKey: ["lojistas", q], queryFn: () => api<Lojista[]>("/lojistas?q=" + encodeURIComponent(q)) });
  const todos = useQuery({ queryKey: ["lojistas", ""], queryFn: () => api<Lojista[]>("/lojistas") });
  const escolhido = (todos.data ?? []).find((l) => l.id === valor);
  return (
    <div>
      <input className="campo" value={busca} onChange={(e) => setBusca(e.target.value)} aria-label={campo.rotulo}
        placeholder={escolhido ? escolhido.nome : "Buscar pelo nome do lojista…"} />
      {escolhido && (
        <p className="mt-1 text-xs text-pedra-forte">
          ✓ {escolhido.nome} <span className="text-tinta-3">· {escolhido.cidade} · código {escolhido.id}</span>
        </p>
      )}
      {(!escolhido || busca) && (
        <ul className="mt-1 max-h-44 overflow-auto rounded-lg border border-linha bg-folha text-sm">
          {(achados.data ?? []).map((l) => (
            <li key={l.id}>
              <button type="button" className="flex w-full items-center justify-between gap-3 px-3 py-2 text-left hover:bg-papel"
                onClick={() => { aoMudar(l.id); setBusca(""); }}>
                <span className="font-medium">{l.nome}</span>
                <span className="text-xs text-tinta-3">{l.cidade} · {l.id}</span>
              </button>
            </li>
          ))}
          {achados.data?.length === 0 && <li className="px-3 py-2 text-tinta-3">Nenhum lojista com esse nome.</li>}
        </ul>
      )}
    </div>
  );
}

function EscolherColaborador({ campo, valor, aoMudar, pessoa }: Props) {
  const [busca, setBusca] = useState("");
  const q = useDebounce(busca);
  const r = useQuery({ queryKey: ["colaboradores", q, pessoa.id], queryFn: () => api<{ itens: Colaborador[]; pode_buscar_outros: boolean }>("/colaboradores?q=" + encodeURIComponent(q)) });
  const eu = r.data?.itens.find((c) => c.eu);
  // "Eu mesmo" é o padrão: preenche sozinho se ainda não há valor
  useEffect(() => { if (eu && !valor) aoMudar(eu.id); }, [eu, valor, aoMudar]);
  const escolhido = r.data?.itens.find((c) => c.id === valor);
  return (
    <div className="space-y-1.5">
      <div className="flex flex-wrap gap-2">
        {eu && (
          <button type="button" className={"selo px-3 py-1.5 text-sm " + (valor === eu.id ? "bg-pedra text-white" : "bg-papel text-tinta-2")}
            onClick={() => aoMudar(eu.id)}>Eu mesmo ({eu.nome.split(" ")[0]})</button>
        )}
        {r.data?.pode_buscar_outros && (
          <input className="campo max-w-[220px] flex-1" value={busca} onChange={(e) => setBusca(e.target.value)} aria-label={campo.rotulo}
            placeholder="Buscar outra pessoa pelo nome…" />
        )}
      </div>
      {r.data?.pode_buscar_outros && (
        <div className="flex flex-wrap gap-2">
          {r.data.itens.filter((c) => !c.eu).map((c) => (
            <button key={c.id} type="button" className={"selo px-3 py-1.5 text-sm " + (valor === c.id ? "bg-pedra text-white" : "bg-papel text-tinta-2")}
              onClick={() => aoMudar(c.id)}>{c.nome}</button>
          ))}
        </div>
      )}
      {escolhido && <p className="text-xs text-pedra-forte">✓ {escolhido.nome} <span className="text-tinta-3">· {escolhido.area}</span></p>}
      {r.data && !r.data.pode_buscar_outros && <p className="text-xs text-tinta-3">Só a área de Pessoas pode consultar outros colaboradores.</p>}
    </div>
  );
}

export default function CampoEntrada(props: Props) {
  const { campo, valor, aoMudar, compacto } = props;
  return (
    <div className={"block " + (compacto ? "" : "min-w-[200px] flex-1")} role="group" aria-label={campo.rotulo}>
      <span className="rotulo">{campo.rotulo}</span>
      {campo.tipo === "lojista" ? <EscolherLojista {...props} />
        : campo.tipo === "colaborador" ? <EscolherColaborador {...props} />
        : campo.tipo === "opcao" ? (
          <select className="campo" aria-label={campo.rotulo} value={valor} onChange={(e) => aoMudar(e.target.value)}>
            <option value="">Escolha…</option>
            {campo.opcoes.map((o) => <option key={o} value={o}>{o}</option>)}
          </select>
        ) : campo.tipo === "texto_longo" ? (
          <textarea className="campo min-h-[84px]" aria-label={campo.rotulo} value={valor} onChange={(e) => aoMudar(e.target.value)} placeholder={campo.exemplo} />
        ) : (
          <input className="campo" aria-label={campo.rotulo} value={valor} onChange={(e) => aoMudar(e.target.value)} placeholder={campo.exemplo} />
        )}
      {campo.ajuda && campo.tipo !== "lojista" && campo.tipo !== "colaborador" && <span className="mt-1 block text-xs text-tinta-3">{campo.ajuda}</span>}
    </div>
  );
}
