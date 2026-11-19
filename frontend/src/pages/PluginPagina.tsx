// Página de um plugin: o que ele traz e o que muda ao integrar; se está integrado, a visão consolidada
// (agentes, chamadas, custo, saúde) e a janela simulada do sistema externo (Zendesk, Slack, Jira).
import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";
import { api, type ConsolidadoPlugin, type JanelaPlugin, type PedidoPlugin, type Persona, type Plugin } from "../api/cliente";
import ArquivosPlugin from "../components/ArquivosPlugin";
import { COR_SAUDE, NOME_SAUDE, ms, reais } from "../components/formato";
import { AcoesPlugin, CartaoPedidoPlugin, classeSelo, COR_ESTADO_PLUGIN, IconeCategoria, NOME_ESTADO_PLUGIN, SeloDoPlugin } from "../components/Plugin";

function Numero({ rotulo, valor, nota }: { rotulo: string; valor: string; nota?: string }) {
  return (
    <div className="rounded-caixa border border-linha bg-papel p-4">
      <div className="text-xs font-semibold uppercase tracking-wide text-tinta-3">{rotulo}</div>
      <div className="mt-1 font-titulo text-2xl font-semibold text-pedra-forte">{valor}</div>
      {nota && <div className="mt-0.5 text-xs text-tinta-3">{nota}</div>}
    </div>
  );
}

function Janela({ nome, janela }: { nome: string; janela: JanelaPlugin }) {
  return (
    <section className="caixa overflow-hidden" aria-label={"Janela simulada de " + nome}>
      <div className="flex flex-wrap items-center gap-2 border-b border-linha bg-papel px-5 py-3">
        <h2 className="text-lg">{janela.titulo}</h2>
        <span className="selo bg-papel text-tinta-2 ring-1 ring-linha">janela simulada de {nome} · dados fictícios</span>
      </div>
      <div className="p-5">
        {janela.tipo === "fila" && (
          <ul className="space-y-3">
            {janela.itens.map((c) => (
              <li key={c.id} className="rounded-lg border border-linha p-3">
                <div className="flex flex-wrap items-center gap-2 text-sm">
                  <b>#{c.id}</b><span className="font-medium">{c.assunto}</span>
                  <span className={"selo " + (c.status === "respondido" ? "bg-pedra-fundo text-pedra-forte" : "bg-alerta-fundo text-alerta")}>{c.status}</span>
                  <span className="selo bg-papel text-tinta-2">prioridade {c.prioridade}</span>
                  <span className="ml-auto text-xs text-tinta-3">{c.solicitante}</span>
                </div>
                <p className="mt-1 text-sm text-tinta-2">{c.mensagem}</p>
                {c.respostas.map((r, i) => (
                  <div key={i} className="mt-2 rounded-lg bg-pedra-fundo/60 p-2.5 text-sm">
                    <div className="text-xs font-semibold text-pedra-forte">{r.autor}</div>{r.texto}
                  </div>
                ))}
              </li>
            ))}
          </ul>
        )}
        {janela.tipo === "canais" && (
          <div className="space-y-4">
            {janela.canais.filter((c) => c.mensagens.length > 0 || c.canal === "#logistica").map((c) => (
              <div key={c.canal}>
                <h3 className="font-mono text-sm font-semibold">{c.canal}</h3>
                {c.mensagens.length === 0 && <p className="mt-1 text-sm text-tinta-3">Nenhuma mensagem ainda.</p>}
                <ul className="mt-1 space-y-2">
                  {c.mensagens.map((m) => (
                    <li key={m.id} className="rounded-lg bg-papel p-3 text-sm">
                      <div className="text-xs font-semibold text-tinta-3">{m.autor}</div>{m.texto}
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        )}
        {janela.tipo === "quadro" && (
          <div className="grid gap-3 sm:grid-cols-3">
            {janela.colunas.map((col) => (
              <div key={col.nome} className="rounded-lg bg-papel p-3">
                <h3 className="text-xs font-semibold uppercase tracking-wide text-tinta-3">{col.nome} · {col.itens.length}</h3>
                <ul className="mt-2 space-y-2">
                  {col.itens.map((i) => (
                    <li key={i.id} className="rounded-md border border-linha bg-folha p-2 text-sm"><b className="mr-1">{i.id}</b>{i.titulo}</li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        )}
      </div>
    </section>
  );
}

function Consolidado({ id }: { id: string }) {
  const q = useQuery({ queryKey: ["plugin", id, "consolidado"], queryFn: () => api<ConsolidadoPlugin>(`/plugins/${id}/consolidado`), refetchInterval: 8000 });
  if (q.isError) return <p className="text-erro">{(q.error as Error).message}</p>;
  const c = q.data;
  if (!c) return <p className="text-tinta-3">Carregando…</p>;
  const n = c.numeros;
  return (
    <>
      <section className="caixa space-y-4 p-6">
        <div className="flex flex-wrap items-center gap-3">
          <h2 className="text-xl">Visão consolidada</h2>
          <span className={"selo " + COR_SAUDE[c.saude.status]}>{NOME_SAUDE[c.saude.status]}</span>
          <span className="text-xs text-tinta-3">números das execuções da demonstração, últimos 30 dias (inclui testes no Estúdio)</span>
        </div>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <Numero rotulo="Agentes que usam" valor={String(n.agentes)} />
          <Numero rotulo="Chamadas no mês" valor={String(n.chamadas_mes)} nota={n.erros ? n.erros + " com erro de sistema" : "sem erro de sistema"} />
          <Numero rotulo="Custo das execuções" valor={reais(n.custo_brl)} nota={n.execucoes + " execução(ões) com o plugin; o plugin em si não gasta token"} />
          <Numero rotulo="Latência p95" valor={n.chamadas_mes ? ms(n.latencia_p95_ms) : "—"} />
        </div>
        {!c.nivel_suficiente && (
          <p className="rounded-lg bg-alerta-fundo p-3 text-sm text-alerta">
            O seu nível de acesso não cobre a classificação deste plugin ({c.plugin.classificacao}): você vê só os números agregados,
            sem o conteúdo do sistema externo.
          </p>
        )}
        {c.nivel_suficiente && !c.area_permitida && c.plugin.janela && (
          <p className="rounded-lg bg-alerta-fundo p-3 text-sm text-alerta">
            Este plugin é homologado para {c.plugin.areas_nomes.join(", ")}: de outra área, você vê só os números agregados,
            sem o conteúdo do sistema externo.
          </p>
        )}
        {c.saude.alertas.map((a) => (
          <div key={a.id} role="alert" className={"rounded-lg p-3 text-sm " + (a.severidade === "critico" ? "bg-erro-fundo text-erro" : "bg-alerta-fundo text-alerta")}>
            <b>{a.titulo}</b><div>{a.detalhe}</div>
            <Link to="/alertas" className="font-semibold underline">Ver alertas</Link>
          </div>
        ))}
        <div className="overflow-x-auto">
          <table className="w-full min-w-[640px] text-sm">
            <thead><tr className="border-b border-linha text-left text-xs uppercase tracking-wide text-tinta-3">
              <th className="py-2 pr-3">Ferramenta</th><th className="pr-3">Chamadas</th><th className="pr-3">Erros</th><th className="pr-3">Latência típica</th><th>p95</th>
            </tr></thead>
            <tbody>
              {c.saude.por_ferramenta.map((t) => (
                <tr key={t.id} className="border-b border-linha">
                  <td className="py-2 pr-3 font-medium">{t.nome}{t.falha && <span className="selo ml-2 bg-erro-fundo text-erro">falha simulada: {t.falha}</span>}</td>
                  <td className="pr-3">{t.chamadas}</td><td className="pr-3">{t.erros}</td><td className="pr-3">{ms(t.latencia_tipica_ms)}</td>
                  <td>{t.chamadas ? ms(t.latencia_p95_ms) : "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="flex flex-wrap gap-2 border-t border-linha pt-4">
          <Link className="botao-claro" to="/saude">Saúde dos agentes e sistemas</Link>
          <Link className="botao-claro" to="/ferramentas">Catálogo de ferramentas</Link>
        </div>
      </section>

      <section className="caixa p-6">
        <h2 className="text-lg">Agentes que usam este plugin</h2>
        {c.agentes.length === 0 && <p className="mt-2 text-sm text-tinta-3">{c.agentes_ocultos ? "Os agentes que o usam são de outras áreas." : "Nenhum agente usa as ferramentas deste plugin ainda. Crie um no Estúdio."}</p>}
        <ul className="mt-2 divide-y divide-linha">
          {c.agentes.map((a) => (
            <li key={a.id} className="flex items-center gap-3 py-2 text-sm">
              <Link to={"/agentes/" + a.id} className="font-medium hover:text-pedra-forte">{a.nome}</Link>
              <span className="text-tinta-3">área {a.area}</span>
              <span className="ml-auto text-tinta-2">{a.chamadas} chamada(s)</span>
            </li>
          ))}
        </ul>
        {c.agentes_ocultos > 0 && c.agentes.length > 0 && <p className="mt-2 text-xs text-tinta-3">+ {c.agentes_ocultos} agente(s) de outras áreas, contados nos números acima.</p>}
      </section>

      {c.janela && <Janela nome={c.plugin.nome} janela={c.janela} />}
    </>
  );
}

export default function PluginPagina({ pessoa }: { pessoa: Persona }) {
  const { id = "" } = useParams();
  const q = useQuery({ queryKey: ["plugin", id], queryFn: () => api<Plugin>("/plugins/" + id) });
  // quem decide o pedido pendente fora da aba Revisões (o CoE de IA, nos pedidos da Segurança) decide aqui mesmo
  const decidir = !!q.data?.pedido_pendente?.pode_decidir;
  const pedidos = useQuery({ queryKey: ["plugin-pedidos"], queryFn: () => api<PedidoPlugin[]>("/plugins/pedidos"), enabled: decidir });
  const pedido = pedidos.data?.find((x) => x.id === q.data?.pedido_pendente?.id);
  if (q.isError) return <p className="text-erro">{(q.error as Error).message}</p>;
  const p = q.data;
  if (!p) return <p className="text-tinta-3">Carregando…</p>;
  return (
    <div className="space-y-6 pb-24">
      <Link to="/plugins" className="text-sm text-tinta-3 hover:text-tinta">← Plugins</Link>
      <div className="flex flex-wrap items-start gap-4">
        <IconeCategoria categoria={p.categoria} tamanho={56} />
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <h1 className="text-3xl">{p.nome}</h1><SeloDoPlugin real={p.real} />
            <span className={"selo " + COR_ESTADO_PLUGIN[p.estado]}>{NOME_ESTADO_PLUGIN[p.estado]}</span>
            <span className={"selo " + classeSelo(p.classificacao)}>{p.classificacao}</span>
          </div>
          <p className="mt-1 text-tinta-2">{p.categoria_nome} · {p.descricao}</p>
          <p className={"mt-1 text-sm " + (p.vale_para_minha_area ? "text-pedra-forte" : "text-tinta-3")}>
            {p.vale_para_minha_area ? "✓ Vale para a sua área" : "✕ Não é homologado para a sua área"} · áreas: {p.areas_nomes.join(", ")}
          </p>
        </div>
        <AcoesPlugin p={p} />
      </div>

      {decidir && pedido && <CartaoPedidoPlugin pedido={pedido} />}

      {p.meu_pedido?.estado === "recusado" && p.estado === "disponivel" && (
        <p className="rounded-lg bg-erro-fundo p-3 text-sm text-erro" role="status">
          Seu pedido foi recusado{p.meu_pedido.revisor ? " por " + p.meu_pedido.revisor : ""}: {p.meu_pedido.parecer}
        </p>
      )}
      {p.meu_pedido?.estado === "registrado" && p.estado === "disponivel" && (
        <p className="rounded-lg bg-papel p-3 text-sm text-tinta-2" role="status">Você já registrou o pedido de integração deste plugin.</p>
      )}

      <section className="caixa p-6">
        <h2 className="text-lg">O que este plugin traz</h2>
        <p className="mt-1 text-sm text-tinta-3">{p.real ? "Este plugin funciona de verdade: as ferramentas abaixo leem e escrevem nos arquivos enviados, com o mesmo contrato do Catálogo." : "O plugin nunca é executado: só as ferramentas abaixo, com o mesmo contrato do Catálogo."}</p>
        <div className="mt-3 overflow-x-auto">
          <table className="w-full min-w-[640px] text-sm">
            <thead><tr className="border-b border-linha text-left text-xs uppercase tracking-wide text-tinta-3">
              <th className="py-2 pr-3">Ferramenta</th><th className="pr-3">Tipo</th><th className="pr-3">Classificação</th><th className="pr-3">Confirmação humana</th><th>Para você</th>
            </tr></thead>
            <tbody>
              {p.ferramentas.map((f) => (
                <tr key={f.id} className="border-b border-linha align-top">
                  <td className="py-3 pr-3"><div className="font-medium">{f.nome}</div><div className="text-xs text-tinta-3">{f.descricao}</div></td>
                  <td className="pr-3">{f.acao === "escrita" ? "escrita" : "leitura"}</td>
                  <td className="pr-3"><span className={"selo " + classeSelo(f.classificacao)}>{f.classificacao}</span></td>
                  <td className="pr-3">{f.exige_aprovacao ? "exige" : "não exige"}</td>
                  <td>{f.nivel_suficiente ? <span className="text-pedra-forte">nível suficiente</span> : <span className="text-erro">seu nível ({pessoa.nivel}) não cobre</span>}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {p.estado !== "integrado" && (
        <section className="caixa p-6">
          <h2 className="text-lg">O que muda ao integrar</h2>
          <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-tinta-2">
            <li>As ferramentas acima entram no <Link to="/ferramentas" className="font-semibold text-pedra-forte">Catálogo</Link> com a origem “plugin {p.nome}”.</li>
            <li>Elas viram passo no Estúdio para quem tem a área e o nível de acesso exigidos; cada chamada roda com as permissões de quem dispara o agente.</li>
            <li>A integração entra na trilha de auditoria; a página do plugin passa a mostrar quem usa, chamadas, custo e saúde.</li>
            {p.sensivel
              ? <li><b>Dado {p.classificacao}:</b> integrar vira um pedido na fila de Revisões da Segurança (quatro olhos), com parecer.</li>
              : <li>Dado {p.classificacao}: criadores da área e a Engenharia integram direto.</li>}
          </ul>
        </section>
      )}

      {p.estado === "integrado" && p.id === "arquivos" && <ArquivosPlugin pessoa={pessoa} />}
      {p.estado === "integrado" && <Consolidado id={p.id} />}
    </div>
  );
}
