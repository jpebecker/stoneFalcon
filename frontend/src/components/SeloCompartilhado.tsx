import type { Persona, Processo } from "../api/cliente";

/**
 * O selo "Compartilhado" de um processo que duas áreas dividem. Mostra o sentido para quem olha: quem é dono vê com quem
 * dividiu; quem recebe vê de que área e de quem veio. Quem não tem nada com o compartilhamento (ex.: o CoE de IA) vê com quem é dividido.
 * Sem compartilhamento, não aparece.
 */
export default function SeloCompartilhado({ p, pessoa, className = "" }: { p: Pick<Processo, "area" | "area_nome" | "dono_nome" | "compartilhado_com" | "compartilhado_nomes">; pessoa: Persona; className?: string }) {
  const com = p.compartilhado_nomes ?? [];
  if (com.length === 0) return null;
  const recebe = pessoa.area !== p.area && p.compartilhado_com.includes(pessoa.area);
  const texto = recebe ? `Compartilhado · de ${p.area_nome ?? p.area} · ${(p.dono_nome ?? "").split(" ")[0]}` : `Compartilhado com ${com.join(", ")}`;
  const dica = recebe ? "Este processo é de outra área. Você pode executá-lo e ver o histórico, mas só a área dona o edita."
    : "Este processo também pode ser executado pelas áreas com quem foi compartilhado. Só a área dona o edita.";
  return <span className={"selo bg-info-fundo text-info " + className} title={dica} data-testid="selo-compartilhado">{texto}</span>;
}
