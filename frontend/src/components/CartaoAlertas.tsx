import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { api, type Alerta } from "../api/cliente";
import Carregando from "./falcao/Carregando";
import Vazio from "./falcao/Vazio";
import SeloSeveridade from "./SeloSeveridade";

const MAXIMO = 3;

/**
 * "Seus alertas" no Início: os alertas abertos que a pessoa vê (a mesma regra da página de Alertas, que é a do back), os mais
 * graves primeiro. Só lê: abrir o Início não marca nada como lido. Usa a mesma consulta da página, então os dois se atualizam juntos.
 */
export default function CartaoAlertas() {
  const q = useQuery({ queryKey: ["alertas", true], queryFn: () => api<Alerta[]>("/alertas?abertos=true"), refetchInterval: 15000 });
  const abertos = q.data ?? [];
  const naoLidos = abertos.filter((a) => !a.lido).length;
  // crítico primeiro; dentro de cada gravidade, o que a pessoa ainda não leu vem antes (a API já ordena do mais recente ao mais antigo)
  const ordenados = [...abertos].sort((a, b) =>
    Number(b.severidade === "critico") - Number(a.severidade === "critico") || Number(!b.lido) - Number(!a.lido));
  const mostrados = ordenados.slice(0, MAXIMO);

  return (
    <section className="caixa p-5" aria-labelledby="seus-alertas" data-alvo="cartao-alertas">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <div className="flex items-center gap-3">
          <h2 id="seus-alertas" className="text-lg">Seus alertas</h2>
          {naoLidos > 0 && <span className="selo bg-alerta-fundo text-alerta">{naoLidos} {naoLidos === 1 ? "não lido" : "não lidos"}</span>}
        </div>
        <Link to="/alertas" className="text-sm font-semibold text-pedra-forte">Ver todos</Link>
      </div>

      <Carregando ativo={q.isPending} texto="Carregando os alertas…" tamanho={32} className="mt-3" />
      {q.isSuccess && abertos.length === 0 && <Vazio caixa={false} className="mt-2 px-0 py-2" dica="Sem alertas por enquanto. Se algo sair do normal, ele aparece aqui.">Nenhum alerta aberto. Tudo certo por aqui.</Vazio>}

      {mostrados.length > 0 && (
        <ul className="mt-3 divide-y divide-linha">
          {mostrados.map((a) => (
            <li key={a.id}>
              <Link to={"/alertas?alerta=" + a.id} className="flex flex-wrap items-center gap-x-3 gap-y-1 py-2.5 text-sm hover:bg-papel">
                <SeloSeveridade severidade={a.severidade} />
                {!a.lido && <span className="h-2 w-2 shrink-0 rounded-full bg-falcao" role="img" aria-label="não lido" />}
                <span className="min-w-0 flex-1 font-medium">{a.titulo}</span>
                {a.tratando_por && <span className="selo bg-info-fundo text-info">em tratamento · por {a.tratando_nome}</span>}
              </Link>
            </li>
          ))}
        </ul>
      )}
      {abertos.length > MAXIMO && (
        <p className="mt-2 text-xs text-tinta-3">+{abertos.length - MAXIMO} {abertos.length - MAXIMO === 1 ? "outro alerta aberto" : "outros alertas abertos"}.</p>
      )}
    </section>
  );
}
