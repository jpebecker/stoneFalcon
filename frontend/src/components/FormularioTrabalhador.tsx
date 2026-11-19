import { useQuery } from "@tanstack/react-query";
import { api, type Blueprint, type Ferramenta, type Passo, type RegistroModelos } from "../api/cliente";
import EditorCampos from "./EditorCampos";

/** O agente é UM trabalhador de IA reutilizável: o que faz, que ferramentas pode usar, qual modelo, o que preenchem para
 *  usá-lo e os limites. O fluxo de vários passos mora nos Processos. */
export default function FormularioTrabalhador({ bp, ferramentas, aoMudar, somenteLeitura }: {
  bp: Blueprint; ferramentas: Ferramenta[]; aoMudar: (bp: Blueprint) => void; somenteLeitura?: boolean;
}) {
  const registro = useQuery({ queryKey: ["modelos"], queryFn: () => api<RegistroModelos>("/modelos"), staleTime: 60_000 });
  const modelos = registro.data?.modelos ?? [];
  const passo = bp.passos[0];
  const mudarPasso = (p: Partial<Passo>) => aoMudar({ ...bp, passos: [{ ...passo, ...p }] });
  const atual = modelos.find((m) => m.chave === passo.modelo || m.apelidos.includes(passo.modelo))?.chave ?? passo.modelo;
  const usd = (v: number) => v.toLocaleString("pt-BR", { maximumFractionDigits: 3 });
  const disponiveis = ferramentas.filter((f) => f.disponivel_para_mim);
  return (
    <fieldset disabled={somenteLeitura} className="caixa space-y-5 p-5" data-testid="form-trabalhador">
      <label className="block">
        <span className="rotulo">O que este agente faz</span>
        <textarea className="campo min-h-[110px]" value={passo.instrucao} onChange={(e) => mudarPasso({ instrucao: e.target.value })}
          aria-label="O que o agente faz" />
        <span className="mt-1 block text-xs text-tinta-3">Escreva como pediria a um colega: o que olhar, o que decidir e como entregar.</span>
      </label>
      <label className="block">
        <span className="rotulo">Regras da área (tom, o que nunca fazer)</span>
        <textarea className="campo min-h-[60px]" value={bp.instrucoes} onChange={(e) => aoMudar({ ...bp, instrucoes: e.target.value })} aria-label="Regras da área" />
      </label>
      <div className="grid gap-5 md:grid-cols-2">
        <div>
          <span className="rotulo">Modelo</span>
          <select className="campo" value={atual} onChange={(ev) => mudarPasso({ modelo: ev.target.value })} aria-label="Modelo do agente">
            <option value="auto">Automático (o balanceador escolhe o mais barato que dá conta)</option>
            {registro.data?.provedores.map((p) => (
              <optgroup key={p.id} label={p.nome + (p.real ? "" : " · simulado")}>
                {modelos.filter((m) => m.provedor === p.id).map((m) => (
                  <option key={m.chave} value={m.chave}>{m.nome} · US$ {usd(m.preco_entrada)} / {usd(m.preco_saida)} por milhão{m.simulado ? " · simulado" : ""}</option>
                ))}
              </optgroup>
            ))}
          </select>
        </div>
        <div className="grid grid-cols-2 gap-3">
          <label className="block">
            <span className="rotulo">Custo máximo por execução (R$)</span>
            <input type="number" min={0.01} step={0.5} className="campo" value={bp.limites.max_custo_brl} aria-label="Custo máximo por execução"
              onChange={(e) => aoMudar({ ...bp, limites: { ...bp.limites, max_custo_brl: Number(e.target.value) || 0.01 } })} />
          </label>
          <label className="block">
            <span className="rotulo">Chamadas ao modelo (máx.)</span>
            <input type="number" min={1} max={100} className="campo" value={bp.limites.max_chamadas_modelo} aria-label="Máximo de chamadas ao modelo"
              onChange={(e) => aoMudar({ ...bp, limites: { ...bp.limites, max_chamadas_modelo: Math.max(1, Number(e.target.value) || 1) } })} />
          </label>
        </div>
      </div>
      <div>
        <span className="rotulo">Ferramentas que pode usar</span>
        <div className="grid gap-1 sm:grid-cols-2">
          {disponiveis.map((f) => (
            <label key={f.id} className="flex items-start gap-2 text-sm">
              <input type="checkbox" className="mt-1 accent-[rgb(var(--pedra))]" checked={passo.ferramentas.includes(f.id)}
                onChange={(e) => mudarPasso({ ferramentas: e.target.checked ? [...passo.ferramentas, f.id] : passo.ferramentas.filter((x) => x !== f.id) })} />
              <span>{f.nome}{f.exige_aprovacao && <span className="ml-1 text-xs text-alerta">(pede confirmação)</span>}</span>
            </label>
          ))}
        </div>
      </div>
      <div>
        <span className="rotulo">O que quem usa este agente preenche</span>
        <EditorCampos campos={bp.campos} aoMudar={(campos) => aoMudar({ ...bp, campos })} />
      </div>
      <label className="block">
        <span className="rotulo">Tempo da tarefa feita à mão (min)</span>
        <input type="number" min={0} className="campo w-28" value={bp.minutos_manual} onChange={(e) => aoMudar({ ...bp, minutos_manual: Number(e.target.value) || 0 })} />
        <span className="mt-1 block text-xs text-tinta-3">Base para medir o retorno do agente.</span>
      </label>
    </fieldset>
  );
}
