import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, type ItemRevisao, type PedidoPlugin } from "../api/cliente";
import { CartaoPedidoPlugin } from "../components/Plugin";
import ListaMudancas from "../components/ListaMudancas";
import { usePreenche } from "../roteiro/estado";
import { COR_RISCO, NOME_RISCO, quando } from "../components/formato";

function Cartao({ item }: { item: ItemRevisao }) {
  const qc = useQueryClient();
  const [parecer, setParecer] = useState("");
  const pre = usePreenche("revisao");
  useEffect(() => { if (pre?.parecer) setParecer(pre.parecer); }, [pre?.parecer]);
  const decidir = useMutation({
    mutationFn: (aprovar: boolean) => api(`/agentes/${item.agente.id}/revisao`, { aprovar, parecer }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["revisoes"] }); qc.invalidateQueries({ queryKey: ["agentes"] }); },
  });
  const bp = item.versao.blueprint;
  return (
    <article className="caixa space-y-4 p-5">
      <div className="flex flex-wrap items-center gap-3">
        <Link to={"/agentes/" + item.agente.id} className="font-titulo text-xl font-semibold hover:text-pedra-forte">{item.agente.nome}</Link>
        <span className="text-sm text-tinta-3">v{item.versao.numero} · área {item.agente.area} · por {item.versao.autor} em {quando(item.versao.criada_em)}</span>
        <span className={"selo ml-auto " + COR_RISCO[item.versao.risco]}>{NOME_RISCO[item.versao.risco]}</span>
      </div>
      <p className="text-sm text-tinta-2">{bp.objetivo}</p>
      {item.versao.nota && <p className="text-sm"><span className="text-tinta-3">Nota do autor:</span> {item.versao.nota}</p>}
      <div>
        <h3 className="mb-2 text-sm font-semibold">O que muda em relação à versão no ar</h3>
        <ListaMudancas mudancas={item.mudancas} />
      </div>
      <label className="block">
        <span className="rotulo">Parecer (fica na auditoria)</span>
        <textarea className="campo min-h-[70px]" value={parecer} onChange={(e) => setParecer(e.target.value)} />
      </label>
      <div className="flex gap-2">
        <button className="botao-pedra" disabled={!parecer.trim() || decidir.isPending} onClick={() => decidir.mutate(true)}>Aprovar e publicar</button>
        <button className="botao-claro" disabled={!parecer.trim() || decidir.isPending} onClick={() => decidir.mutate(false)}>Rejeitar</button>
      </div>
      {decidir.isError && <p className="text-sm text-erro">{(decidir.error as Error).message}</p>}
    </article>
  );
}

export default function Revisoes() {
  const q = useQuery({ queryKey: ["revisoes"], queryFn: () => api<ItemRevisao[]>("/revisoes") });
  const pedidos = useQuery({ queryKey: ["plugin-pedidos"], queryFn: () => api<PedidoPlugin[]>("/plugins/pedidos") });
  const fila = pedidos.data ?? [];
  return (
    <div className="max-w-4xl space-y-6">
      <div>
        <h1 className="text-3xl">Revisões de segurança</h1>
        <p className="mt-1 text-tinta-2">Toda versão de agente de risco alto passa por aqui antes de ir ao ar. Quem escreveu a versão não pode revisá-la.</p>
      </div>
      {q.isError && <p className="text-erro">{(q.error as Error).message}</p>}
      {q.data?.length === 0 && fila.length === 0 && <p className="caixa p-5 text-tinta-3">Nada esperando revisão.</p>}
      {q.data?.map((item) => <Cartao key={item.versao.id} item={item} />)}
      {fila.length > 0 && (
        <section className="space-y-4" aria-label="Pedidos de integração de plugin">
          <div>
            <h2 className="text-xl">Pedidos de integração de plugin</h2>
            <p className="text-sm text-tinta-2">Plugin com dado confidencial ou restrito só entra no Catálogo depois do seu parecer.</p>
          </div>
          {fila.map((p) => <CartaoPedidoPlugin key={p.id} pedido={p} />)}
        </section>
      )}
    </div>
  );
}
