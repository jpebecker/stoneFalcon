import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { api, type Persona } from "../api/cliente";
import Avatar from "../components/Avatar";
import Marca from "../components/Marca";
import { useControle } from "../roteiro/Controle";

const PAPEL: Record<string, string> = {
  criador: "cria agentes", curador: "aprova conhecimento", revisor_seguranca: "revisa segurança",
  engenharia: "mantém o catálogo", gestor_ia: "vê custos e auditoria",
};

export default function Entrar({ aoEntrar, aviso }: { aoEntrar: (id: string) => void; aviso?: string }) {
  const perfis = useQuery({ queryKey: ["perfis"], queryFn: () => api<Persona[]>("/perfis") });
  const { iniciar } = useControle();
  const [iniciando, setIniciando] = useState<string | null>(null);
  const [erro, setErro] = useState<string | null>(null);

  const comRoteiro = async (p: Persona) => {
    if (!p.roteiro_id) return;
    setIniciando(p.id); setErro(null);
    try { await iniciar(p.roteiro_id, p.id); } catch (e) { setErro((e as Error).message); } finally { setIniciando(null); }
  };

  return (
    <div className="flex min-h-full items-center justify-center px-6 py-14">
      <div className="w-full max-w-5xl">
        <Marca />
        {aviso && <p role="alert" className="mt-6 rounded-caixa border border-alerta/40 bg-alerta-fundo p-3 text-sm text-alerta">{aviso}</p>}
        <h1 className="mt-8 text-4xl">Quem é você hoje?</h1>
        <p className="mt-3 max-w-2xl text-tinta-2">
          Cada pessoa vê a plataforma pelo seu trabalho: o que cria, o que governa, o que mede. Escolha um perfil para entrar,
          ou inicie o <b>roteiro guiado</b> dele: a mesma jornada, do mesmo jeito, sempre.
        </p>
        {perfis.isError && <p className="mt-4 text-erro">Não consegui falar com o servidor. Ele está ligado?</p>}
        {erro && <p className="mt-4 text-erro">{erro}</p>}
        <div className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {perfis.data?.map((p) => (
            <article key={p.id} className="caixa flex flex-col p-5 transition hover:border-pedra">
              <div className="flex items-center gap-3">
                <Avatar pessoa={p} tamanho={48} />
                <div className="min-w-0">
                  <h2 className="truncate text-lg leading-tight">{p.nome}</h2>
                  <div className="truncate text-sm text-tinta-2">{p.cargo} · {p.area_nome}</div>
                </div>
              </div>
              <p className="mt-3 flex-1 text-sm text-tinta-2">{p.descricao}</p>
              <div className="mt-3 flex flex-wrap gap-1.5">
                {p.papeis.filter((x) => PAPEL[x]).map((x) => <span key={x} className="selo bg-papel text-tinta-2">{PAPEL[x]}</span>)}
                <span className="selo bg-info-fundo text-info">acesso {p.nivel}</span>
              </div>
              <div className="mt-4 flex gap-2">
                <button className="botao-claro flex-1" onClick={() => aoEntrar(p.id)}>Entrar</button>
                <button className="botao-pedra flex-1" disabled={!!iniciando} onClick={() => comRoteiro(p)}>
                  {iniciando === p.id ? "Preparando…" : "Iniciar roteiro"}
                </button>
              </div>
            </article>
          ))}
        </div>
        <p className="mt-8 text-xs text-tinta-3">Login simulado de demonstração. Em produção, o acesso vem do SSO da empresa. Pessoas e dados são fictícios.</p>
      </div>
    </div>
  );
}
