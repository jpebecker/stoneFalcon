import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link, NavLink, Navigate, Route, Routes } from "react-router-dom";
import { api, definirPerfil, perfilAtual, type Persona, type Saude } from "./api/cliente";
import Marca from "./components/Marca";
import AgenteDetalhe from "./pages/AgenteDetalhe";
import Auditoria from "./pages/Auditoria";
import Alertas from "./pages/Alertas";
import Agentes from "./pages/Agentes";
import Calculadora from "./pages/Calculadora";
import Catalogo from "./pages/Catalogo";
import Entrar from "./pages/Entrar";
import Estudio from "./pages/Estudio";
import ExecucaoDetalhe from "./pages/ExecucaoDetalhe";
import Execucoes from "./pages/Execucoes";
import Extensao from "./pages/Extensao";
import Financas from "./pages/Financas";
import Inicio from "./pages/Inicio";
import Painel from "./pages/Painel";
import Revisoes from "./pages/Revisoes";
import PaginaSaude from "./pages/Saude";

const NAV: { para: string; rotulo: string; papel?: string; papeis?: string[] }[] = [
  { para: "/", rotulo: "Início" },
  { para: "/painel", rotulo: "Painel executivo" },
  { para: "/estudio", rotulo: "Estúdio", papel: "criador" },
  { para: "/agentes", rotulo: "Agentes" },
  { para: "/revisoes", rotulo: "Revisões", papel: "revisor_seguranca" },
  { para: "/execucoes", rotulo: "Execuções" },
  { para: "/saude", rotulo: "Saúde" },
  { para: "/financas", rotulo: "Finanças" },
  { para: "/ferramentas", rotulo: "Ferramentas" },
  { para: "/auditoria", rotulo: "Auditoria", papeis: ["gestor_ia", "revisor_seguranca"] },
];

export default function App() {
  const [perfil, setPerfil] = useState(perfilAtual());
  const qc = useQueryClient();
  const eu = useQuery({ queryKey: ["eu", perfil], queryFn: () => api<Persona>("/eu"), enabled: !!perfil });
  const saude = useQuery({ queryKey: ["saude"], queryFn: () => api<Saude>("/saude") });
  const notif = useQuery({
    queryKey: ["notificacoes", perfil], enabled: !!perfil && !eu.isError, refetchInterval: 15000,
    queryFn: () => api<{ nao_lidos: number; criticos: number }>("/notificacoes/contagem"),
  });

  const trocar = (id: string | null) => {
    definirPerfil(id);
    setPerfil(id);
    qc.clear();
  };

  if (!perfil || eu.isError) return <Entrar aoEntrar={trocar} />;
  const pessoa = eu.data;
  if (location.pathname.startsWith("/extensao")) return pessoa ? <Extensao pessoa={pessoa} aoSair={() => trocar(null)} /> : null;

  return (
    <div className="flex min-h-full">
      <aside className="sticky top-0 flex h-screen w-60 shrink-0 flex-col gap-8 bg-tinta px-4 py-6 text-white">
        <Marca claro />
        <nav className="flex flex-col gap-1" aria-label="Seções">
          {NAV.filter((n) => (!n.papel || pessoa?.papeis.includes(n.papel)) && (!n.papeis || n.papeis.some((x) => pessoa?.papeis.includes(x)))).map((n) => (
            <NavLink key={n.para} to={n.para} end={n.para === "/"}
              className={({ isActive }) => "rounded-lg px-3 py-2 text-sm font-medium transition " +
                (isActive ? "bg-white text-tinta" : "text-white/75 hover:bg-white/10 hover:text-white")}>
              {n.rotulo}
            </NavLink>
          ))}
        </nav>
        <p className="mt-auto text-xs leading-relaxed text-white/45">
          Protótipo acadêmico (UFSC) para o desafio StoneLab. Não é um produto oficial da Stone. Pessoas e dados são fictícios.
        </p>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="sticky top-0 z-10 flex items-center justify-end gap-4 border-b border-linha bg-folha/90 px-8 py-3 backdrop-blur">
          {saude.data && (
            <span title={saude.data.modo === "real" ? "Chamando os modelos de verdade" : "Sem chave da API: respostas de exemplo, custos estimados"}
              className={"selo " + (saude.data.modo === "real" ? "bg-pedra-fundo text-pedra-forte" : "bg-alerta-fundo text-alerta")}>
              {saude.data.modo === "real" ? "Modelos reais" : "Modo simulado"}
            </span>
          )}
          {pessoa && (
            <Link to="/alertas" className="relative rounded-lg p-2 text-tinta-2 hover:bg-papel hover:text-tinta" aria-label={`Alertas: ${notif.data?.nao_lidos ?? 0} não lidos`}>
              <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden="true">
                <path d="M6 8a6 6 0 1 1 12 0c0 7 3 9 3 9H3s3-2 3-9" /><path d="M10.3 21a1.94 1.94 0 0 0 3.4 0" />
              </svg>
              {!!notif.data?.nao_lidos && (
                <span className={"absolute -right-0.5 -top-0.5 min-w-[18px] rounded-full px-1 text-center text-[11px] font-bold text-white " +
                  (notif.data.criticos ? "bg-erro" : "bg-alerta")}>{notif.data.nao_lidos}</span>
              )}
            </Link>
          )}
          {pessoa && (
            <div className="flex items-center gap-3 text-sm">
              <div className="text-right leading-tight">
                <div className="font-semibold">{pessoa.nome}</div>
                <div className="text-xs text-tinta-3">{pessoa.area_nome} · acesso {pessoa.nivel}</div>
              </div>
              <button className="botao-claro py-1.5" onClick={() => trocar(null)}>Trocar perfil</button>
            </div>
          )}
        </header>
        <main className="mx-auto w-full max-w-[1400px] flex-1 px-8 py-8">
          {pessoa && (
            <Routes>
              <Route path="/" element={<Inicio pessoa={pessoa} />} />
              <Route path="/estudio" element={<Estudio pessoa={pessoa} />} />
              <Route path="/agentes" element={<Agentes pessoa={pessoa} />} />
              <Route path="/agentes/:id" element={<AgenteDetalhe pessoa={pessoa} />} />
              <Route path="/revisoes" element={<Revisoes />} />
              <Route path="/saude" element={<PaginaSaude />} />
              <Route path="/alertas" element={<Alertas />} />
              <Route path="/painel" element={<Painel />} />
              <Route path="/auditoria" element={<Auditoria />} />
              <Route path="/financas" element={<Financas pessoa={pessoa} />} />
              <Route path="/financas/calculadora" element={<Calculadora />} />
              <Route path="/execucoes" element={<Execucoes />} />
              <Route path="/execucoes/:id" element={<ExecucaoDetalhe pessoa={pessoa} />} />
              <Route path="/ferramentas" element={<Catalogo pessoa={pessoa} />} />
              <Route path="*" element={<Navigate to="/" />} />
            </Routes>
          )}
        </main>
      </div>
    </div>
  );
}
