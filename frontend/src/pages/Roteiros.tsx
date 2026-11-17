import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Link } from "react-router-dom";
import { api, type Persona, type ResumoRoteiro } from "../api/cliente";
import Avatar from "../components/Avatar";
import { useControle } from "../roteiro/Controle";
import { useEstadoRoteiro } from "../roteiro/estado";

export default function Roteiros() {
  const lista = useQuery({ queryKey: ["roteiros"], queryFn: () => api<ResumoRoteiro[]>("/roteiros") });
  const perfis = useQuery({ queryKey: ["perfis"], queryFn: () => api<Persona[]>("/perfis") });
  const ativo = useEstadoRoteiro();
  const { iniciar } = useControle();
  const [iniciando, setIniciando] = useState<string | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const pessoa = (id: string) => perfis.data?.find((p) => p.id === id);

  const comecar = async (r: ResumoRoteiro) => {
    setIniciando(r.id); setErro(null);
    try { await iniciar(r.id, r.persona); } catch (e) { setErro((e as Error).message); } finally { setIniciando(null); }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl">Roteiros guiados</h1>
        <p className="mt-1 max-w-3xl text-tinta-2">
          Uma jornada por persona: processo de hoje (AS IS), processo com o agente (TO BE), criação, uso e valor medido. Cada roteiro
          reinicia a plataforma no estado exato de que precisa, troca de perfil sozinho e usa entradas pré-determinadas, sem chave da API.
        </p>
      </div>
      {erro && <p className="text-erro">{erro}</p>}
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {lista.data?.map((r) => {
          const p = pessoa(r.persona);
          return (
            <article key={r.id} className={"caixa flex flex-col p-5 " + (ativo?.id === r.id ? "border-pedra" : "")}>
              <div className="flex items-center gap-3">
                {p && <Avatar pessoa={p} tamanho={40} />}
                <div className="min-w-0">
                  <div className="truncate font-titulo text-lg font-semibold leading-tight">{p?.nome ?? r.persona}</div>
                  <div className="truncate text-xs text-tinta-3">{p?.cargo} · {p?.area_nome}</div>
                </div>
                {ativo?.id === r.id && <span className="selo ml-auto bg-pedra-fundo text-pedra-forte">em andamento</span>}
              </div>
              <h2 className="mt-3 text-base">{r.titulo}</h2>
              <p className="mt-1 flex-1 text-sm text-tinta-2">{r.resumo}</p>
              <p className="mt-2 text-xs text-tinta-3">{r.passos} passos · ≈ {r.duracao_min} min</p>
              <div className="mt-3 flex gap-2">
                <button className="botao-pedra flex-1" disabled={!!iniciando} onClick={() => comecar(r)}>
                  {iniciando === r.id ? "Preparando…" : ativo?.id === r.id ? "Recomeçar" : "Iniciar roteiro"}
                </button>
                <Link className="botao-claro" to={"/roteiro/" + r.id}>AS IS × TO BE</Link>
              </div>
            </article>
          );
        })}
      </div>
    </div>
  );
}
