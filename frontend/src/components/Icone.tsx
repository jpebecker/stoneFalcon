/**
 * Ícones de linha da interface: grade 24, traço 1,8, pontas redondas, cor = currentColor (mesmo traço do sino).
 * Sempre ao lado de texto visível, nunca no lugar dele; por isso são `aria-hidden`.
 * Sem biblioteca: cada ícone é uma lista de "d" de <path>.
 */
const ICONES = {
  // abas do menu lateral
  inicio: ["M3.5 10.5 12 3.5l8.5 7", "M5.5 9v11h13V9", "M10 20v-5.5h4V20"],
  roteiros: ["M6 15a2 2 0 1 1 0 4 2 2 0 0 1 0-4Z", "M18 5a2 2 0 1 1 0 4 2 2 0 0 1 0-4Z", "M8 17h8a3 3 0 0 0 0-6H8a3 3 0 0 1 0-6h8"],
  painel: ["M4 20h16", "M7 16.5V12", "M12 16.5V6", "M17 16.5V9"],
  mapa: ["M12 3a2.2 2.2 0 1 1 0 4.4A2.2 2.2 0 0 1 12 3Z", "M5 15.6A2.2 2.2 0 1 1 5 20a2.2 2.2 0 0 1 0-4.4Z", "M19 15.6a2.2 2.2 0 1 1 0 4.4 2.2 2.2 0 0 1 0-4.4Z", "M10.9 7.3 6.1 15.8", "M13.1 7.3l4.8 8.5", "M7.2 17.8h9.6"],
  estudio: ["M11 3.5l1.9 4.8 4.8 1.9-4.8 1.9L11 16.9l-1.9-4.8-4.8-1.9 4.8-1.9Z", "M18.5 14.5v5", "M16 17h5"],
  agentes: ["M7 9h10a2 2 0 0 1 2 2v6a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2v-6a2 2 0 0 1 2-2Z", "M12 5.5V9", "M12 3.2a1.1 1.1 0 1 1 0 2.2 1.1 1.1 0 0 1 0-2.2Z", "M9.5 13.2v1.4", "M14.5 13.2v1.4", "M3 13v2", "M21 13v2"],
  processos: ["M4 4h6v6H4Z", "M14 14h6v6h-6Z", "M7 10v4a3 3 0 0 0 3 3h4"],
  plugins: ["M9 3.5V8", "M15 3.5V8", "M6 8h12v3a6 6 0 0 1-12 0Z", "M12 17v3.5"],
  revisoes: ["M12 3 5 6v5.2c0 4.3 2.9 7.8 7 9.8 4.1-2 7-5.5 7-9.8V6Z", "M9 12l2.2 2.2L15.5 10"],
  execucoes: ["M12 3a9 9 0 1 1 0 18 9 9 0 0 1 0-18Z", "M10 8.6v6.8l5.4-3.4Z"],
  saude: ["M3 12h4l2.5-6.5 5 13L17 12h4"],
  financas: ["M4 7h14a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2H5a1 1 0 0 1-1-1Z", "M4 7.5V6a2 2 0 0 1 2-2h10.5", "M16 13.5h.6"],
  ferramentas: ["M14.6 3.6a4.6 4.6 0 0 0-4.2 6.3l-6.3 6.3a2 2 0 0 0 2.8 2.8l6.3-6.3a4.6 4.6 0 0 0 6.3-4.2l-2.7 2.7-2.8-.4-.4-2.8Z"],
  auditoria: ["M9 3.5h6v3H9Z", "M9 5H6.5A1.5 1.5 0 0 0 5 6.5v13A1.5 1.5 0 0 0 6.5 21h11a1.5 1.5 0 0 0 1.5-1.5v-13A1.5 1.5 0 0 0 17.5 5H15", "M8.5 11h7", "M8.5 15h4.5"],
  perguntas: ["M12 3a9 9 0 1 1 0 18 9 9 0 0 1 0-18Z", "M9.6 9.4a2.5 2.5 0 1 1 3.4 2.4c-.7.3-1 .9-1 1.6v.4", "M12 17.2h.01"],
  // ações e estados
  executar: ["M7 5v14l11-7Z"],
  publicar: ["M12 15.5V4", "M7.5 8.5 12 4l4.5 4.5", "M5 15v3.5A1.5 1.5 0 0 0 6.5 20h11a1.5 1.5 0 0 0 1.5-1.5V15"],
  concluido: ["M5 12.5l4.5 4.5L19 7.5"],
  falhou: ["M12 3a9 9 0 1 1 0 18 9 9 0 0 1 0-18Z", "M9 9l6 6", "M15 9l-6 6"],
  atencao: ["M12 4 2.8 19.5h18.4Z", "M12 10v4.5", "M12 17.2h.01"],
  sino: ["M6 8a6 6 0 1 1 12 0c0 7 3 9 3 9H3s3-2 3-9", "M10.3 21a1.94 1.94 0 0 0 3.4 0"],
  trocar: ["M16 3.5 20 7.5l-4 4", "M20 7.5H8", "M8 12.5l-4 4 4 4", "M4 16.5h12"],
  sair: ["M14 4h4a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2h-4", "M10 16.5 14.5 12 10 7.5", "M14.5 12H4"],
} as const;

export type NomeIcone = keyof typeof ICONES;

/** Ícone de linha. 18 px no menu, 16 px (padrão) em botões e selos. */
export default function Icone({ nome, tamanho = 16, className = "" }: { nome: NomeIcone; tamanho?: number; className?: string }) {
  return (
    <svg viewBox="0 0 24 24" width={tamanho} height={tamanho} className={"shrink-0 " + className} fill="none" stroke="currentColor"
      strokeWidth={1.8} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" focusable="false">
      {ICONES[nome].map((d) => <path key={d} d={d} />)}
    </svg>
  );
}
