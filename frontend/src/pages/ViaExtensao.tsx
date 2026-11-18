// Chegada pela extensão ("Criar Agente de IA"): troca o passe de uso único pela pessoa e leva ao Estúdio.
// O endereço só leva o passe (60 s, vale uma vez): nem o perfil nem o texto selecionado vão nele.
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, type Persona } from "../api/cliente";
import Entrar from "./Entrar";

export const CHAVE_RASCUNHO = "stonefalcon.rascunho";
type Troca = { pessoa: Persona; rascunho: string; fonte: unknown };

// o React em desenvolvimento roda o efeito duas vezes e o passe só vale uma: a troca fica guardada por passe
const trocas = new Map<string, Promise<Troca>>();

export default function ViaExtensao({ aoEntrar }: { aoEntrar: (id: string) => void }) {
  const navegar = useNavigate();
  const [aviso, setAviso] = useState<string | null>(null);

  useEffect(() => {
    const passe = new URLSearchParams(location.search).get("passe");
    if (!passe) { setAviso("Faltou o acesso da extensão. Escolha seu perfil ou peça de novo pela extensão."); return; }
    if (!trocas.has(passe)) trocas.set(passe, api<Troca>("/extensao/passe/trocar", { passe }));
    trocas.get(passe)!.then((t) => {
      try { sessionStorage.setItem(CHAVE_RASCUNHO, JSON.stringify({ texto: t.rascunho, fonte: t.fonte })); } catch { /* sem armazenamento */ }
      aoEntrar(t.pessoa.id);
      navegar("/estudio", { replace: true });   // o passe sai do endereço
    }).catch((e: Error) => setAviso(e.message));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (!aviso) return <div className="p-10 text-tinta-2" aria-busy="true">Abrindo o Estúdio…</div>;
  return <Entrar aviso={aviso} aoEntrar={(id) => { aoEntrar(id); navegar("/", { replace: true }); }} />;
}
