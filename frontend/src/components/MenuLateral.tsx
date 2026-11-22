import { useEffect, useState } from "react";
import { NavLink, useLocation } from "react-router-dom";
import Icone, { type NomeIcone } from "./Icone";

interface Item { aba: string; para: string; rotulo: string; icone: NomeIcone }
interface Grupo { id: string; rotulo: string; itens: Item[] }

const INICIO: Item = { aba: "inicio", para: "/", rotulo: "Início", icone: "inicio" };

// Só apresentação: quem pode ver cada aba vem de `pessoa.abas` (back). Aqui só se decide em que grupo ela aparece.
const GRUPOS: Grupo[] = [
  { id: "construir", rotulo: "Construir", itens: [
    { aba: "estudio", para: "/estudio", rotulo: "Estúdio", icone: "estudio" },
    { aba: "agentes", para: "/agentes", rotulo: "Agentes", icone: "agentes" },
    { aba: "processos", para: "/processos", rotulo: "Processos", icone: "processos" },
    { aba: "plugins", para: "/plugins", rotulo: "Plugins", icone: "plugins" },
    { aba: "ferramentas", para: "/ferramentas", rotulo: "Ferramentas", icone: "ferramentas" },
  ] },
  { id: "acompanhar", rotulo: "Acompanhar", itens: [
    { aba: "execucoes", para: "/execucoes", rotulo: "Execuções", icone: "execucoes" },
    { aba: "saude", para: "/saude", rotulo: "Saúde", icone: "saude" },
    { aba: "revisoes", para: "/revisoes", rotulo: "Revisões", icone: "revisoes" },
  ] },
  { id: "gestao", rotulo: "Gestão e valor", itens: [
    { aba: "painel", para: "/painel", rotulo: "Painel executivo", icone: "painel" },
    { aba: "financas", para: "/financas", rotulo: "Finanças", icone: "financas" },
    { aba: "mapa", para: "/mapa", rotulo: "Mapa de IA", icone: "mapa" },
    { aba: "auditoria", para: "/auditoria", rotulo: "Auditoria", icone: "auditoria" },
  ] },
  { id: "apresentacao", rotulo: "Apresentação", itens: [
    { aba: "roteiros", para: "/roteiros", rotulo: "Roteiros", icone: "roteiros" },
    { aba: "perguntas", para: "/perguntas", rotulo: "Perguntas da Ferramenta", icone: "perguntas" },
  ] },
];

const CHAVE = "stonefalcon.menu.grupo";
const lerGuardado = (): string | null => { try { return localStorage.getItem(CHAVE); } catch { return null; } };
const guardar = (id: string | null) => { try { if (id) localStorage.setItem(CHAVE, id); else localStorage.removeItem(CHAVE); } catch { /* sem armazenamento: o menu funciona igual */ } };

/** Grupo da rota atual (mesma regra de prefixo do NavLink; as telas de um roteiro pertencem a Roteiros). */
function grupoDaRota(caminho: string, grupos: Grupo[]): string | null {
  const rota = caminho.startsWith("/roteiro/") ? "/roteiros" : caminho;
  const g = grupos.find((x) => x.itens.some((i) => rota === i.para || rota.startsWith(i.para + "/")));
  return g?.id ?? null;
}

const classeItem = ({ isActive }: { isActive: boolean }) =>
  "flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm font-medium transition " +
  (isActive ? "bg-white text-tinta" : "text-white/75 hover:bg-white/10 hover:text-white");

/**
 * Menu lateral: Início e quatro grupos sanfonados (um aberto por vez). O grupo da página atual abre sozinho a cada
 * navegação. Grupo sem aba permitida some; grupo com uma só aba vira link simples. Rola por dentro se a janela for baixa.
 */
export default function MenuLateral({ abas }: { abas: string[] }) {
  const { pathname } = useLocation();
  const grupos = GRUPOS
    .map((g) => ({ ...g, itens: g.itens.filter((i) => abas.includes(i.aba)) }))
    .filter((g) => g.itens.length > 0);
  const sanfonas = grupos.filter((g) => g.itens.length > 1);
  const doCaminho = grupoDaRota(pathname, sanfonas);
  const [aberto, setAberto] = useState<string | null>(() => doCaminho ?? lerGuardado());

  // navegar (menu, roteiro, endereço digitado, retorno do falcão) abre o grupo da página; telas sem grupo (Início, Alertas) mantêm o atual
  useEffect(() => { if (doCaminho) { setAberto(doCaminho); guardar(doCaminho); } }, [doCaminho, pathname]);

  const alternar = (id: string) => { const novo = aberto === id ? null : id; setAberto(novo); guardar(novo); };

  return (
    <nav className="-mx-1 flex min-h-0 flex-1 flex-col gap-1 overflow-y-auto px-1" aria-label="Seções">
      {abas.includes(INICIO.aba) && (
        <NavLink to={INICIO.para} end data-alvo={"aba-" + INICIO.aba} className={classeItem}>
          <Icone nome={INICIO.icone} tamanho={18} />{INICIO.rotulo}
        </NavLink>
      )}
      {grupos.map((g) => {
        if (g.itens.length === 1) {
          const i = g.itens[0];
          return (
            <NavLink key={i.aba} to={i.para} data-alvo={"aba-" + i.aba} className={classeItem}>
              <Icone nome={i.icone} tamanho={18} />{i.rotulo}
            </NavLink>
          );
        }
        const aberta = aberto === g.id;
        const dentro = doCaminho === g.id;
        return (
          <div key={g.id} className="flex flex-col gap-1">
            <button type="button" id={"grupo-" + g.id} data-alvo={"grupo-" + g.id} onClick={() => alternar(g.id)}
              aria-expanded={aberta} aria-controls={"painel-" + g.id}
              className={"flex w-full items-center justify-between rounded-lg px-3 py-2 text-left text-sm font-semibold transition hover:bg-white/10 hover:text-white " +
                (dentro ? "text-white" : "text-white/75")}>
              {g.rotulo}
              <Icone nome="seta" tamanho={16} className={"transition-transform motion-reduce:transition-none " + (aberta ? "rotate-180" : "")} />
            </button>
            <div id={"painel-" + g.id} role="group" aria-labelledby={"grupo-" + g.id} hidden={!aberta} className={aberta ? "flex flex-col gap-1 pl-2" : "hidden"}>
              {g.itens.map((i) => (
                <NavLink key={i.aba} to={i.para} data-alvo={"aba-" + i.aba} data-alvo-recuo={"grupo-" + g.id} className={classeItem}>
                  <Icone nome={i.icone} tamanho={18} />{i.rotulo}
                </NavLink>
              ))}
            </div>
          </div>
        );
      })}
    </nav>
  );
}
