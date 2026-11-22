import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef, useState, type ReactNode } from "react";
import { Link, Navigate, Route, Routes, useNavigate } from "react-router-dom";
import { api, definirPerfil, perfilAtual, type Alerta, type Persona, type Saude } from "./api/cliente";
import Avatar from "./components/Avatar";
import Icone from "./components/Icone";
import Ambiente from "./components/falcao/Ambiente";
import Poleiro from "./components/falcao/Poleiro";
import { alvoDe, ProvedorFalcao, useFalcao } from "./components/falcao/Voo";
import Marca from "./components/Marca";
import MenuLateral from "./components/MenuLateral";
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
import PluginCriar from "./pages/PluginCriar";
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

// O menu (components/MenuLateral) e as rotas só leem `pessoa.abas`, que vem do back (a fonte da verdade do acesso por perfil).

/** A frase de boas-vindas: o primeiro nome e quantos alertas abertos a pessoa tem (os não lidos entre eles). */
export function saudar(nome: string, alertas: Alerta[] | null): string {
  const oi = `Olá, ${nome.split(" ")[0]}!`;
  if (alertas === null) return oi;
  const abertos = alertas.length, novos = alertas.filter((a) => !a.lido).length;
  if (abertos === 0) return `${oi} Nenhum alerta aberto por aqui.`;
  const total = `${abertos} ${abertos === 1 ? "alerta aberto" : "alertas abertos"}`;
  return `${oi} Você tem ${total}${novos ? `, ${novos} ${novos === 1 ? "ainda não lido" : "ainda não lidos"}` : ""}.`;
}

/** Rota restrita: quem não tem a aba (ex.: endereço digitado) volta ao Início, sem tela quebrada. */
function Guarda({ pessoa, aba, children }: { pessoa: Persona; aba: string; children: ReactNode }) {
  return pessoa.abas.includes(aba) ? <>{children}</> : <Navigate to="/" replace />;
}

function MenuPessoa({ pessoa, aoTrocar, aoSair }: { pessoa: Persona; aoTrocar: (id: string) => void; aoSair: () => void }) {
  const [aberto, setAberto] = useState(false);
  const caixa = useRef<HTMLDivElement>(null);
  const perfis = useQuery({ queryKey: ["perfis"], queryFn: () => api<Persona[]>("/perfis") });
  const { silenciado, alternarSilencio } = useFalcao();
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
          <div className="flex items-center gap-1.5 px-2 pb-1 pt-1 text-xs font-semibold uppercase tracking-wide text-tinta-3"><Icone nome="trocar" tamanho={14} />Trocar de perfil</div>
          {perfis.data?.map((p) => (
            <button key={p.id} role="menuitem" className={"flex w-full items-center gap-3 rounded-lg px-2 py-1.5 text-left text-sm hover:bg-papel " + (p.id === pessoa.id ? "bg-pedra-fundo/50" : "")}
              onClick={() => { setAberto(false); if (p.id !== pessoa.id) aoTrocar(p.id); }}>
              <Avatar pessoa={p} tamanho={28} />
              <span className="min-w-0"><span className="block truncate font-medium">{p.nome}</span><span className="block truncate text-xs text-tinta-3">{p.cargo}</span></span>
              {p.id === pessoa.id && <span className="ml-auto text-xs text-pedra-forte">você</span>}
            </button>
          ))}
          <div className="mt-1 border-t border-linha pt-1">
            <button role="menuitemcheckbox" aria-checked={silenciado} data-testid="silenciar-falcao" onClick={alternarSilencio}
              title="Sem recados nem aparições por conta própria. Os voos que respondem a uma ação continuam."
              className="flex w-full items-center justify-between gap-2 rounded-lg px-2 py-1.5 text-left text-sm text-tinta-2 hover:bg-papel">
              Silenciar o falcão
              <span className={"selo " + (silenciado ? "bg-pedra-fundo text-pedra-forte" : "bg-papel text-tinta-3")}>{silenciado ? "ligado" : "desligado"}</span>
            </button>
            <button role="menuitem" className="flex w-full items-center gap-2 rounded-lg px-2 py-1.5 text-left text-sm text-tinta-2 hover:bg-papel" onClick={() => { setAberto(false); aoSair(); }}><Icone nome="sair" />Sair para a tela inicial</button>
          </div>
        </div>
      )}
    </div>
  );
}

/** A camada de voo do falcão envolve tudo: entrada, área logada e painel da extensão. */
export default function App() {
  return <ProvedorFalcao><AppInterno /></ProvedorFalcao>;
}

function AppInterno() {
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
  // entrar (pela tela de entrada ou trocando pelo menu do avatar) sempre abre o Início da persona,
  // qualquer que seja a tela em que a pessoa anterior estava
  const entrarNoInicio = (id: string) => { trocar(id); navegar("/"); };
  // entrar pela roda: voo de boas-vindas até a marca do menu (só aqui; trocar de pessoa pelo menu não faz festa)
  const { voar, falar } = useFalcao();
  const boasVindas = useRef(false);
  const entrarPelaRoda = (id: string) => { boasVindas.current = true; entrarNoInicio(id); };
  const pessoa = eu.data;
  useEffect(() => {
    if (!boasVindas.current || !perfil || !pessoa) return;
    boasVindas.current = false;
    // o falcão chega ao poleiro e cumprimenta pelo primeiro nome, com uma frase sobre o dia (os alertas abertos)
    const saudacao = api<Alerta[]>("/alertas?abertos=true").then((l) => saudar(pessoa.nome, l), () => saudar(pessoa.nome, null));
    const reduzido = matchMedia("(prefers-reduced-motion: reduce)").matches;
    window.setTimeout(async () => {
      const texto = await saudacao;
      if (reduzido) falar(texto);   // movimento reduzido: sem voo de chegada, só o recado
      else voar({ de: { x: window.innerWidth * 0.62, y: window.innerHeight * 0.5 }, para: alvoDe("poleiro"), sobre: true, aoChegar: () => { falar(texto); } });
    }, 350);
  }, [perfil, pessoa, voar, falar]);

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
    return <ProvedorRoteiro trocar={trocar}><Entrar aoEntrar={entrarPelaRoda} /></ProvedorRoteiro>;
  }

  return (
    <ProvedorRoteiro trocar={trocar}>
      <div className="flex min-h-full">
        <aside className="sticky top-0 flex h-screen w-60 shrink-0 flex-col gap-6 bg-tinta px-4 py-6 text-white">
          <div className="relative">
            <Marca claro />
            <Poleiro className="absolute -right-1 -top-1" />
          </div>
          <MenuLateral abas={pessoa?.abas ?? []} />
          <p className="shrink-0 text-xs leading-relaxed text-white/45">
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
              <Link to="/alertas" data-alvo="sino" className="relative rounded-lg p-2 text-tinta-2 hover:bg-papel hover:text-tinta" aria-label={`Alertas: ${notif.data?.nao_lidos ?? 0} não lidos`}>
                <Icone nome="sino" tamanho={20} />
                {!!notif.data?.nao_lidos && (
                  <span className={"absolute -right-0.5 -top-0.5 min-w-[18px] rounded-full px-1 text-center text-[11px] font-bold text-white " +
                    (notif.data.criticos ? "bg-erro" : "bg-alerta")}>{notif.data.nao_lidos}</span>
                )}
              </Link>
            )}
            {pessoa && <MenuPessoa pessoa={pessoa} aoTrocar={entrarNoInicio} aoSair={() => trocar(null)} />}
          </header>
          <main className={"mx-auto w-full max-w-[1400px] flex-1 px-8 py-8 " + (roteiroAtivo ? "pb-32" : "")}>
            {pessoa && (
              <Routes>
                <Route path="/" element={<Inicio pessoa={pessoa} />} />
                <Route path="/roteiros" element={<Guarda pessoa={pessoa} aba="roteiros"><Roteiros /></Guarda>} />
                <Route path="/roteiro/:id" element={<RoteiroPagina pessoa={pessoa} />} />
                <Route path="/mapa" element={<Guarda pessoa={pessoa} aba="mapa"><MapaIAPagina /></Guarda>} />
                <Route path="/perguntas" element={<Guarda pessoa={pessoa} aba="perguntas"><Perguntas /></Guarda>} />
                <Route path="/plugins" element={<Guarda pessoa={pessoa} aba="plugins"><Plugins pessoa={pessoa} /></Guarda>} />
                <Route path="/plugins/criar" element={<Guarda pessoa={pessoa} aba="plugins"><PluginCriar /></Guarda>} />
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
                <Route path="/alertas" element={<Alertas pessoa={pessoa} />} />
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
      <Ambiente pessoa={pessoa} naoLidos={notif.data?.nao_lidos} />
      <BarraRoteiro />
    </ProvedorRoteiro>
  );
}
