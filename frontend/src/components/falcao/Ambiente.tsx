import { useQuery } from "@tanstack/react-query";
import { useEffect, useRef } from "react";
import { useLocation } from "react-router-dom";
import { api, type Execucao, type Persona } from "../../api/cliente";
import { CONFIG_AMBIENTE } from "./agendador";
import { alvoDe, useFalcao } from "./Voo";

type ApiFalcao = ReturnType<typeof useFalcao>;

// ---------- as rotinas: o que o falcão faz, cada uma ligada a algo real ----------

/** Uma dica curta por página (a mais específica vence). Linguagem simples, uma frase. */
export const DICAS: [string, string][] = [
  ["/processos/", "Dica: o histórico ao lado mostra cada passo da vida deste processo, na trilha de auditoria."],
  ["/agentes/", "Dica: a saúde do agente mostra a taxa de sucesso e os alertas abertos dele."],
  ["/execucoes/", "Dica: cada bloco da linha do tempo mostra o agente que rodou e o que ele fez."],
  ["/processos", "Dica: abra um processo para executar, ver o histórico ou compartilhar com outra área."],
  ["/agentes", "Dica: um agente faz uma tarefa só. Os fluxos são montados em processos."],
  ["/estudio", "Dica: conte o que você faz como contaria a um colega novo; o Estúdio monta o agente."],
  ["/execucoes", "Dica: abra uma execução para ver o que cada bloco fez e quanto custou."],
  ["/alertas", "Dica: assuma um alerta para os outros verem quem está tratando."],
  ["/saude", "Dica: a nota de cada agente e processo cai com alertas abertos e sobe quando eles fecham."],
  ["/revisoes", "Dica: leia o que mudou na versão antes de aprovar; o parecer fica na trilha."],
  ["/painel", "Dica: o painel mostra os cinco critérios da banca, medidos nas execuções."],
  ["/financas", "Dica: o roteador manda o trabalho simples para o modelo mais barato."],
  ["/mapa", "Dica: execute algo em outra aba e veja o mapa acender o caminho sozinho."],
  ["/auditoria", "Dica: a cadeia da trilha confere se algum registro foi alterado."],
  ["/plugins", "Dica: integre um plugin para ele virar passo no Estúdio."],
  ["/ferramentas", "Dica: simule uma falha em um sistema para ver o alerta abrir sozinho."],
  ["/roteiros", "Dica: cada roteiro conta uma jornada pronta, do processo de hoje ao valor medido."],
  ["/perguntas", "Dica: cada pergunta tem uma tela de prova ao lado."],
  ["/", "Dica: o card “Seus alertas” mostra primeiro o que pede atenção."],
];

export function dicaDaPagina(caminho: string): string | null {
  const exato = DICAS.find(([p]) => p === "/" ? caminho === "/" : p.endsWith("/") ? caminho.startsWith(p) : caminho === p || caminho.startsWith(p + "/"));
  return exato ? exato[1] : null;
}

/** As rotinas como funções que recebem a API do falcão, para a tela e a página de teste usarem as mesmas. */
export const rotinas = {
  /** O não lido subiu: o falcão sai do poleiro, vai ao sino e fala uma linha. */
  alertaNovo: (f: ApiFalcao, novos = 1) => f.voar({ de: alvoDe("poleiro"), para: alvoDe("sino"), aoChegar: (chegada) => {
    f.falar(novos > 1 ? `Chegaram ${novos} alertas novos.` : "Chegou um alerta novo.", { alvo: chegada ?? alvoDe("sino") ?? undefined });
  } }),
  /** Parado há um tempo: uma dica da página, do poleiro. */
  dica: (f: ApiFalcao, texto: string) => { f.falar(texto); },
  /** Parado há bastante tempo: se espreguiça e olha em volta no poleiro (sem voo, sem fala). */
  esticar: (f: ApiFalcao) => f.esticar(),
  /** Primeira execução bem-sucedida do dia: uma comemoração curta. */
  primeiraDoDia: (f: ApiFalcao, nome: string) => { f.falar(`Primeira execução do dia, ${nome}! Boa.`); },
};

// ---------- os gatilhos reais ----------
const CHAVE_DIA = "stonefalcon.falcao.comemorou.";
const hoje = () => new Date().toISOString().slice(0, 10);
const jaComemorou = (pessoa: string, memoria: Set<string>): boolean => {
  if (memoria.has(pessoa + hoje())) return true;
  try { return localStorage.getItem(CHAVE_DIA + pessoa) === hoje(); } catch { return false; }
};
const marcarComemorou = (pessoa: string, memoria: Set<string>) => {
  memoria.add(pessoa + hoje());
  try { localStorage.setItem(CHAVE_DIA + pessoa, hoje()); } catch { /* sem armazenamento: vale só nesta sessão */ }
};
const inicioDaSessao = Date.now();

/**
 * Liga as rotinas ambiente ao que acontece de verdade: o não lido do sino subindo, o tempo sem mexer na tela e a primeira execução
 * do dia. (As dicas dos estados vazios vêm do próprio `Vazio`.) Quem decide se pode rodar agora é o agendador do falcão.
 */
export function useAmbiente({ pessoa, naoLidos }: { pessoa: Persona | undefined; naoLidos: number | undefined }) {
  const falcao = useFalcao();
  useEffect(() => { (window as unknown as { __ambiente?: typeof CONFIG_AMBIENTE }).__ambiente = CONFIG_AMBIENTE; }, []);   // a revisão ajusta o teto pelo console
  const f = useRef(falcao);
  f.current = falcao;
  const { pathname } = useLocation();
  const caminho = useRef(pathname);
  caminho.current = pathname;

  // 1) alerta novo: só quando o não lido SOBE em relação ao que a pessoa já viu (a primeira leitura não conta)
  const anterior = useRef<{ pessoa: string; n: number } | null>(null);
  useEffect(() => {
    if (!pessoa || naoLidos === undefined) return;
    const antes = anterior.current;
    anterior.current = { pessoa: pessoa.id, n: naoLidos };
    if (!antes || antes.pessoa !== pessoa.id || naoLidos <= antes.n) return;
    const novos = naoLidos - antes.n;
    f.current.pedirAmbiente({ id: "alerta", prio: 3, validadeMs: CONFIG_AMBIENTE.capMs + 30_000,   // espera a janela do teto acabar, se caiu dentro dela
       executar: () => rotinas.alertaNovo(f.current, novos) });
  }, [pessoa, naoLidos]);

  // 2) parado: dica da página e, mais raro, o poleiro se espreguiça
  const ultimaAcao = useRef(Date.now());
  const dicasDadas = useRef(new Set<string>());
  useEffect(() => {
    const mexeu = () => { ultimaAcao.current = Date.now(); };
    const eventos = ["pointerdown", "pointermove", "keydown", "wheel", "touchstart", "scroll"] as const;
    eventos.forEach((e) => window.addEventListener(e, mexeu, { passive: true, capture: true }));
    const t = window.setInterval(() => {
      const parado = Date.now() - ultimaAcao.current;
      if (parado >= CONFIG_AMBIENTE.ociosoDicaMs) {
        const atual = caminho.current;
        const dica = dicasDadas.current.has(atual) ? null : dicaDaPagina(atual);
        if (dica) f.current.pedirAmbiente({ id: "dica", prio: 0, validadeMs: 20_000, executar: () => { dicasDadas.current.add(atual); rotinas.dica(f.current, dica); } });
      }
      if (parado >= CONFIG_AMBIENTE.ociosoEsticarMs && Math.random() < 0.15) {
        f.current.pedirAmbiente({ id: "esticar", prio: -1, validadeMs: 10_000, executar: () => rotinas.esticar(f.current) });
      }
    }, CONFIG_AMBIENTE.tiqueMs);
    return () => { eventos.forEach((e) => window.removeEventListener(e, mexeu, { capture: true })); clearInterval(t); };
  }, []);

  // 3) primeira execução bem-sucedida do dia: uma execução DESTA sessão, da própria pessoa, de verdade (não histórico, não rotina agendada)
  const memoria = useRef(new Set<string>());
  const execs = useQuery({
    queryKey: ["execucoes-ambiente", pessoa?.id], enabled: !!pessoa, refetchInterval: 20_000,
    queryFn: () => api<Execucao[]>("/execucoes?limite=30"),
  });
  useEffect(() => {
    if (!pessoa || !execs.data || jaComemorou(pessoa.id, memoria.current)) return;
    const feita = execs.data.some((e) => e.persona === pessoa.id && e.status === "concluida" && !e.demo && !e.rotina
      && e.agente_id !== "sandbox" && e.dono_id !== "sandbox" && new Date(e.inicio).getTime() >= inicioDaSessao - 5_000);
    if (!feita) return;
    f.current.pedirAmbiente({ id: "primeira-do-dia", prio: 2, validadeMs: 180_000, executar: () => {
      marcarComemorou(pessoa.id, memoria.current);
      rotinas.primeiraDoDia(f.current, pessoa.nome.split(" ")[0]);
    } });
  }, [pessoa, execs.data]);
}

/** Monta o gancho dentro da área logada (precisa do roteador e do provedor do falcão). */
export default function Ambiente({ pessoa, naoLidos }: { pessoa: Persona | undefined; naoLidos: number | undefined }) {
  useAmbiente({ pessoa, naoLidos });
  return null;
}
