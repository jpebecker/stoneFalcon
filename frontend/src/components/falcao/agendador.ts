/**
 * Agendador do comportamento ambiente do falcão (v8.3): as coisas que ele faz sozinho, cada uma ligada a algo real. Um agendador só
 * decide por todas as rotinas, para elas nunca se juntarem e a tela nunca encher de falcão. As regras (DESIGN.md, seção 8):
 *
 *  - teto de frequência: no máximo UM comportamento ambiente a cada `capMs`;
 *  - nunca enquanto a pessoa digita, com um diálogo aberto, durante um voo, com um balão na tela ou com um roteiro guiado ativo;
 *  - desligado com movimento reduzido e com o falcão silenciado.
 *
 * Uma rotina que não pode rodar agora espera (até `validadeMs`) e tenta de novo no próximo tique; a de maior prioridade vai primeiro.
 */
export interface Rotina {
  /** A mesma `id` substitui a rotina que ainda espera (ex.: "alerta" três vezes seguidas vira uma só). */
  id: string;
  /** Maior vai primeiro. */
  prio: number;
  /** Quanto tempo vale esperar a vez antes de desistir (a notícia de um alerta novo envelhece). */
  validadeMs?: number;
  executar: () => void;
}

/** Os ajustes do agendador. Mutável de propósito: a página de teste do falcão zera o teto para o revisor ver cada rotina. */
export const CONFIG_AMBIENTE = { capMs: 3 * 60_000, tiqueMs: 4_000, ociosoDicaMs: 60_000, ociosoEsticarMs: 40_000 };

export const movimentoReduzido = () => typeof matchMedia === "function" && matchMedia("(prefers-reduced-motion: reduce)").matches;

/** O foco está num campo de texto (ou o que a pessoa edita): ninguém interrompe quem digita. */
export function digitando(): boolean {
  const el = document.activeElement as HTMLElement | null;
  if (!el || el === document.body) return false;
  return el.isContentEditable || el.tagName === "TEXTAREA" || el.tagName === "SELECT"
    || (el.tagName === "INPUT" && !["checkbox", "radio", "button", "submit", "range"].includes((el as HTMLInputElement).type));
}

/** Há um diálogo, modal ou menu aberto por cima da tela. */
export const dialogoAberto = () => !!document.querySelector('dialog[open], [role="dialog"], [aria-modal="true"], [role="menu"]');
