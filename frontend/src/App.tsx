import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef, useState, type ReactNode } from "react";
import { Link, NavLink, Navigate, Route, Routes, useNavigate } from "react-router-dom";
import { api, definirPerfil, perfilAtual, type Persona, type Saude } from "./api/cliente";
import Avatar from "./components/Avatar";
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
import PluginPagina from "./pages/PluginPagina";
import Plugins from "./pages/Plugins";
import ProcessoDetalhe from "./pages/ProcessoDetalhe";
import ProcessoEditor from "./pages/ProcessoEditor";
import Processos from "./pages/Processos";
import Perguntas from "./pages/Perguntas";
import Revisoes from "./pages/Revisoes";
import RoteiroPagina from "./pages/RoteiroPagina";
import Roteiros from "./pages/Roteiros";
import MapaIAPagina from "./pages/MapaIA";
import PaginaSaude from "./pages/Saude";
import ViaExtensao from "./pages/ViaExtensao";
import { BarraRoteiro, ProvedorRoteiro } from "./roteiro/Controle";
import { useEstadoRoteiro } from "./roteiro/estado";
import { versaoCurta } from "./components/formato";

// O menu e as rotas só leem `pessoa.abas`, que vem do back (a fonte da verdade do acesso por perfil).
const NAV: { aba: string; para: string; rotulo: string }[] = [
  { aba: "inicio", para: "/", rotulo: "Início" },
  { aba: "roteiros", para: "/roteiros", rotulo: "Roteiros" },
  { aba: "painel", para: "/painel", rotulo: "Painel executivo" },
  { aba: "mapa", para: "/mapa", rotulo: "Mapa de IA" },
  { aba: "estudio", para: "/estudio", rotulo: "Estúdio" },
  { aba: "agentes", para: "/agentes", rotulo: "Agentes" },
  { aba: "processos", para: "/processos", rotulo: "Processos" },
  { aba: "plugins", para: "/plugins", rotulo: "Plugins" },
  { aba: "revisoes", para: "/revisoes", rotulo: "Revisões" },
  { aba: "execucoes", para: "/execucoes", rotulo: "Execuções" },
  { aba: "saude", para: "/saude", rotulo: "Saúde" },
  { aba: "financas", para: "/financas", rotulo: "Finanças" },
  { aba: "ferramentas", para: "/ferramentas", rotulo: "Ferramentas" },
  { aba: "auditoria", para: "/auditoria", rotulo: "Auditoria" },
  { aba: "perguntas", para: "/perguntas", rotulo: "Perguntas da Ferramenta" },
];

/** Rota restrita: quem não tem a aba (ex.: endereço digitado) volta ao Início, sem tela quebrada. */
function Guarda({ pessoa, aba, children }: { pessoa: Persona; aba: string; children: ReactNode }) {
  return pessoa.abas.includes(aba) ? <>{children}</> : <Navigate to="/" replace />;
}

function MenuPessoa({ pessoa, aoTrocar, aoSair }: { pessoa: Persona; aoTrocar: (id: string) => void; aoSair: () => void }) {
  const [aberto, setAberto] = useState(false);
  const caixa = useRef<HTMLDivElement>(null);
  const perfis = useQuery({ queryKey: ["perfis"], queryFn: () => api<Persona[]>("/perfis") });
  useEffect(() => {
    if (!aberto) return;
    const fora = (e: MouseEvent) => { if (!caixa.current?.contains(e.target as Node)) setAberto(false); };
    const esc = (e: KeyboardEvent) => { if (e.key === "Escape") setAberto(false); };
    document.addEventListener("mousedown", fora); document.addEventListener("keydown", esc);
    return () => { document.removeEventListener("mousedown", fora); document.removeEventListener("keydown", esc); };
  }, [aberto]);
  return (
    <div className="relative" ref={caixa}>
      <button className="flex items-center gap-3 rounded-lg px-2 py-1 text-sm hover:bg-papel" onClick={() => setAberto(!aberto)} aria-haspopup="menu" aria-expanded={aberto}>
        <div className="text-right leading-tight">
          <div className="font-semibold">{pessoa.nome}</div>
          <div className="text-xs text-tinta-3">{pessoa.area_nome} · acesso {pessoa.nivel}</div>
        </div>
        <Avatar pessoa={pessoa} />
      </button>
      {aberto && (
        <div role="menu" className="caixa absolute right-0 top-full z-30 mt-2 w-72 p-2">
          <div className="px-2 pb-1 pt-1 text-xs font-semibold uppercase tracking-wide text-tinta-3">Trocar de perfil</div>
          {perfis.data?.map((p) => (
            <button key={p.id} role="menuitem" className={"flex w-full items-center gap-3 rounded-lg px-2 py-1.5 text-left text-sm hover:bg-papel " + (p.id === pessoa.id ? "bg-pedra-fundo/50" : "")}
              onClick={() => { setAberto(false); if (p.id !== pessoa.id) aoTrocar(p.id); }}>
              <Avatar pessoa={p} tamanho={28} />
              <span className="min-w-0"><span className="block truncate font-medium">{p.nome}</span><span className="block truncate text-xs text-tinta-3">{p.cargo}</span></span>
              {p.id === pessoa.id && <span className="ml-auto text-xs text-pedra-forte">você</span>}
            </button>
          ))}
          <div className="mt-1 border-t border-linha pt-1">
            <button role="menuitem" className="w-full rounded-lg px-2 py-1.5 text-left text-sm text-tinta-2 hover:bg-papel" onClick={() => { setAberto(false); aoSair(); }}>Sair para a tela inicial</button>
          </div>
        </div>
      )}
    </div>
  );
}

export default function App() {
  // a extensão abre /extensao?perfil=<id>: entra direto como essa pessoa
  if (location.pathname.startsWith("/extensao")) {
    const p = new URLSearchParams(location.search).get("perfil");
    // só dentro da moldura da extensão/helpdesk: abrir o endereço direto não troca o perfil de ninguém
    if (p && window.parent !== window && /^[a-z]{3,20}$/.test(p)) definirPerfil(p);
  }
  const [perfil, setPerfil] = useState(perfilAtual());
  const qc = useQueryClient();
  const navegar = useNavigate();
  const roteiroAtivo = useEstadoRoteiro();
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

  const pessoa = eu.data;
  const podePerguntas = !!pessoa?.abas.includes("perguntas");

  // atalho do modo apresentador: Alt+B abre as Perguntas da Ferramenta de qualquer tela (só para quem tem a aba)
  useEffect(() => {
    if (!podePerguntas) return;
    const tecla = (e: KeyboardEvent) => {
      if (e.altKey && e.key.toLowerCase() === "b" && perfilAtual() && !location.pathname.startsWith("/extensao")) { e.preventDefault(); navegar("/perguntas"); }
    };
    window.addEventListener("keydown", tecla);
    return () => window.removeEventListener("keydown", tecla);
  }, [navegar, podePerguntas]);

  if (location.pathname.startsWith("/extensao")) {
    if (perfil && eu.isPending) return <div className="ext-tema min-h-full bg-papel p-6 text-sm text-tinta-2" aria-busy="true">Conectando…</div>;
    return <Extensao pessoa={perfil && !eu.isError ? pessoa ?? null : null} aoEntrar={(id) => trocar(id)} aoSair={() => trocar(null)}
      erroPerfil={!!perfil && eu.isError} />;
  }
  if (location.pathname === "/via-extensao") {
    return <ProvedorRoteiro trocar={trocar}><ViaExtensao aoEntrar={trocar} /></ProvedorRoteiro>;
  }
  if (!perfil || eu.isError) {
    return <ProvedorRoteiro trocar={trocar}><Entrar aoEntrar={trocar} /></ProvedorRoteiro>;
  }

  return (
    <ProvedorRoteiro trocar={trocar}>
      <div className="flex min-h-full">
        <aside className="sticky top-0 flex h-screen w-60 shrink-0 flex-col gap-8 bg-tinta px-4 py-6 text-white">
          <Marca claro />
          <nav className="flex flex-col gap-1" aria-label="Seções">
            {NAV.filter((n) => pessoa?.abas.includes(n.aba)).map((n) => (
              <NavLink key={n.para} to={n.para} end={n.para === "/"}
                className={({ isActive }) => "rounded-lg px-3 py-2 text-sm font-medium transition " +
                  (isActive ? "bg-white text-tinta" : "text-white/75 hover:bg-white/10 hover:text-white")}>
                {n.rotulo}
              </NavLink>
            ))}
          </nav>
          <p className="mt-auto text-xs leading-relaxed text-white/45">
            <span className="mb-1 block font-semibold text-white/70" data-testid="versao">StoneFalcon {saude.data ? versaoCurta(saude.data.versao) : ""}</span>
            Protótipo acadêmico (UFSC) para o desafio StoneLab. Não é um produto oficial da Stone. Pessoas e dados são fictícios.
          </p>
        </aside>

        <div className="flex min-w-0 flex-1 flex-col">
          <header className="sticky top-0 z-20 flex items-center justify-end gap-4 border-b border-linha bg-folha/90 px-8 py-3 backdrop-blur">
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
            {pessoa && <MenuPessoa pessoa={pessoa} aoTrocar={(id) => { trocar(id); navegar("/"); }} aoSair={() => trocar(null)} />}
          </header>
          <main className={"mx-auto w-full max-w-[1400px] flex-1 px-8 py-8 " + (roteiroAtivo ? "pb-32" : "")}>
            {pessoa && (
              <Routes>
                <Route path="/" element={<Inicio pessoa={pessoa} />} />
                <Route path="/roteiros" element={<Guarda pessoa={pessoa} aba="roteiros"><Roteiros /></Guarda>} />
                <Route path="/roteiro/:id" element={<RoteiroPagina pessoa={pessoa} />} />
                <Route path="/mapa" element={<Guarda pessoa={pessoa} aba="mapa"><MapaIAPagina /></Guarda>} />
                <Route path="/perguntas" element={<Guarda pessoa={pessoa} aba="perguntas"><Perguntas /></Guarda>} />
                <Route path="/plugins" element={<Guarda pessoa={pessoa} aba="plugins"><Plugins /></Guarda>} />
                <Route path="/plugins/:id" element={<Guarda pessoa={pessoa} aba="plugins"><PluginPagina pessoa={pessoa} /></Guarda>} />
                <Route path="/estudio" element={<Guarda pessoa={pessoa} aba="estudio"><Estudio pessoa={pessoa} /></Guarda>} />
                <Route path="/agentes" element={<Agentes pessoa={pessoa} />} />
                <Route path="/agentes/:id" element={<AgenteDetalhe pessoa={pessoa} />} />
                <Route path="/processos" element={<Guarda pessoa={pessoa} aba="processos"><Processos pessoa={pessoa} /></Guarda>} />
                <Route path="/processos/novo" element={<Guarda pessoa={pessoa} aba="estudio"><ProcessoEditor pessoa={pessoa} /></Guarda>} />
                <Route path="/processos/:id" element={<Guarda pessoa={pessoa} aba="processos"><ProcessoDetalhe pessoa={pessoa} /></Guarda>} />
                <Route path="/processos/:id/editar" element={<Guarda pessoa={pessoa} aba="estudio"><ProcessoEditor pessoa={pessoa} /></Guarda>} />
                <Route path="/revisoes" element={<Guarda pessoa={pessoa} aba="revisoes"><Revisoes /></Guarda>} />
                <Route path="/saude" element={<PaginaSaude />} />
                <Route path="/alertas" element={<Alertas />} />
                <Route path="/painel" element={<Guarda pessoa={pessoa} aba="painel"><Painel /></Guarda>} />
                <Route path="/auditoria" element={<Guarda pessoa={pessoa} aba="auditoria"><Auditoria /></Guarda>} />
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
      <BarraRoteiro />
    </ProvedorRoteiro>
  );
}
