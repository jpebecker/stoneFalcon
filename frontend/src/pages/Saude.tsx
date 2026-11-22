import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { api, type SaudeAgente, type SaudeConector } from "../api/cliente";
import PainelBalanceador from "../components/PainelBalanceador";
import { COR_SAUDE, NOME_SAUDE, ms, pct, reais } from "../components/formato";

function Medidor({ nota, status }: { nota: number; status: string }) {
  const cor = status === "saudavel" ? "rgb(var(--pedra))" : status === "atencao" ? "rgb(var(--alerta))" : "rgb(var(--erro))";
  return (
    <div className="relative h-14 w-14 shrink-0" role="img" aria-label={`Nota de saúde ${nota} de 100`}>
      <svg viewBox="0 0 36 36" className="h-14 w-14 -rotate-90">
        <circle cx="18" cy="18" r="15.5" fill="none" stroke="rgb(var(--linha))" strokeWidth="3.5" />
        <circle cx="18" cy="18" r="15.5" fill="none" stroke={cor} strokeWidth="3.5" strokeLinecap="round"
          strokeDasharray={`${(nota / 100) * 97.4} 97.4`} />
      </svg>
      <span className="absolute inset-0 flex items-center justify-center font-titulo text-base font-semibold">{nota}</span>
    </div>
  );
}

export default function Saude() {
  const ag = useQuery({ queryKey: ["saude-agentes"], queryFn: () => api<SaudeAgente[]>("/saude/agentes"), refetchInterval: 15000 });
  const con = useQuery({ queryKey: ["saude-conectores"], queryFn: () => api<SaudeConector[]>("/saude/conectores"), refetchInterval: 15000 });
  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl">Saúde</h1>
        <p className="mt-1 max-w-2xl text-tinta-2">
          Monitoramento automático: nenhum criador precisa configurar nada. Quando algo degrada, o responsável pelo agente é avisado.
        </p>
      </div>

      <PainelBalanceador />

      <section>
        <h2 className="mb-3 text-lg">Agentes e processos</h2>
        <div className="grid gap-3 lg:grid-cols-2">
          {ag.data?.map((s) => (
            <Link key={s.agente.id} to={(s.agente.tipo === "processo" ? "/processos/" : "/agentes/") + s.agente.id} className="caixa flex gap-4 p-4 transition hover:border-pedra">
              <Medidor nota={s.score.nota} status={s.score.status} />
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                  <h3 className="truncate text-base">{s.agente.nome}</h3>
                  {s.agente.tipo === "processo" && <span className="selo bg-info-fundo text-info">processo</span>}
                  <span className={"selo " + COR_SAUDE[s.score.status]}>{NOME_SAUDE[s.score.status]}</span>
                  {s.agente.estado === "pausado" && <span className="selo bg-alerta-fundo text-alerta">pausado</span>}
                </div>
                <dl className="mt-2 grid grid-cols-4 gap-2 text-xs">
                  <div><dt className="text-tinta-3">Sucesso</dt><dd className="font-semibold">{pct(s.metricas.taxa_sucesso)}</dd></div>
                  <div><dt className="text-tinta-3">Execuções</dt><dd className="font-semibold">{s.metricas.execucoes}</dd></div>
                  <div><dt className="text-tinta-3">p95</dt><dd className="font-semibold">{ms(s.metricas.latencia_p95_ms)}</dd></div>
                  <div><dt className="text-tinta-3">Custo 7d</dt><dd className="font-semibold">{reais(s.metricas.custo_brl)}</dd></div>
                </dl>
                {s.alertas.map((a) => (
                  <p key={a.id} className={"mt-2 text-xs " + (a.severidade === "critico" ? "text-erro" : "text-alerta")}>⚠ {a.titulo}</p>
                ))}
              </div>
            </Link>
          ))}
        </div>
        {ag.data?.length === 0 && <p className="text-tinta-3">Nenhum agente visível.</p>}
      </section>

      <section>
        <h2 className="mb-1 text-lg">Sistemas integrados</h2>
        <p className="mb-3 text-sm text-tinta-3">Verificação sintética e chamadas reais da última hora.</p>
        <div className="caixa divide-y divide-linha">
          {con.data?.map((c) => (
            <div key={c.id} className="flex flex-wrap items-center gap-4 px-4 py-3 text-sm">
              <span className={"selo w-24 justify-center " + COR_SAUDE[c.status]}>{NOME_SAUDE[c.status]}</span>
              <span className="min-w-[200px] flex-1 font-medium">{c.nome}</span>
              <span className="text-tinta-3">{c.chamadas} chamadas · {pct(c.taxa_erro)} erro · típico {ms(c.latencia_tipica_ms)}</span>
              {c.detalhe && <p className="basis-full text-xs text-tinta-2">{c.detalhe}</p>}
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
