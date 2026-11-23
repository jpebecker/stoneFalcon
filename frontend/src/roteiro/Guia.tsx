import { useEffect, useRef } from "react";
import type { PassoRoteiro } from "../api/cliente";
import { tempoDaFala } from "../components/falcao/Balao";
import { alvoDe, alvoNaTela, destacar, useFalcao } from "../components/falcao/Voo";

const A_CADA_MS = 200;
const ESPERA_MAXIMA_MS = 5000;

/**
 * O falcão como guia do roteiro: quando um passo começa, voa do poleiro até o controle que a pessoa deve usar e diz a ação no balão.
 * Sem alvo no passo, ou com o alvo fora da tela, ele só fala do poleiro; um passo que abre fora do app avisa isso no balão.
 *
 * A tela do passo ainda está carregando quando o passo começa, então espera (até ~5 s) o controle aparecer e, se ele estiver
 * abaixo da dobra, rola até ele. Espera também um voo em curso (o salto curto da barra, ao avançar) acabar. Trocar de passo (Voltar,
 * Avançar, Reiniciar) cancela o que estava pendente e recolhe o balão do passo anterior: o falcão nunca fica apontando para o passo velho.
 * Silenciado: o falcão ainda aponta o controle, só não fala (a ação continua na barra).
 */
export function useGuia(roteiroId: string | undefined, indice: number, passo: PassoRoteiro | null) {
  const { voar, cancelar, falar, calar, emVoo } = useFalcao();
  const voando = useRef(emVoo);
  voando.current = emVoo;
  const guiaNoAr = useRef(false);
  useEffect(() => { if (!emVoo) guiaNoAr.current = false; }, [emVoo]);

  const passoId = passo?.id;
  useEffect(() => {
    if (!roteiroId || !passo) return;
    calar();   // o recado do passo anterior sai de cena
    const texto = passo.acao + (passo.externa ? " (abre em outra aba)" : "");
    const ms = tempoDaFala(texto) + 3000;
    let vivo = true;
    const tempos: number[] = [];
    const depois = (f: () => void, t: number) => { tempos.push(window.setTimeout(() => vivo && f(), t)); };

    if (!passo.alvo || passo.externa) {
      depois(() => falar(texto, { ms }), 400);   // dá tempo de a tela do passo abrir
    } else {
      const nome = passo.alvo;
      const inicio = Date.now();
      const tentar = () => {
        const existe = alvoDe(nome);
        let alvo = alvoNaTela(nome);
        const barra = document.querySelector('[aria-label="Roteiro guiado"]')?.getBoundingClientRect().top ?? innerHeight;
        if (alvo && alvo.getBoundingClientRect().bottom > barra) alvo = null;   // escondido atrás da barra do roteiro: trata como fora da tela
        if (existe && !alvo) existe.scrollIntoView({ block: "center", behavior: "auto" });   // abaixo da dobra: traz para a tela
        if (alvo && !voando.current) {
          guiaNoAr.current = true;
          voar({ de: alvoDe("poleiro"), para: alvo, aoChegar: (chegada) => { destacar(chegada ?? alvo); falar(texto, { alvo, ms }); } });
          return;
        }
        if (Date.now() - inicio >= ESPERA_MAXIMA_MS) { falar(texto, { ms }); return; }   // sem o controle na tela: fala do poleiro
        depois(tentar, A_CADA_MS);
      };
      depois(tentar, A_CADA_MS);
    }
    return () => {
      vivo = false;
      tempos.forEach(clearTimeout);
      if (guiaNoAr.current) { cancelar(); guiaNoAr.current = false; }   // só o voo do guia: o salto da barra segue
    };
    // o passo muda quando muda o roteiro, o índice ou o id (Voltar, Avançar, Reiniciar)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [roteiroId, indice, passoId]);
}
