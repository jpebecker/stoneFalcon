import { useQuery } from "@tanstack/react-query";
import { api, type AgenteDisponivel, type Bloco, type Ferramenta, type ProcessoBlueprint, type Regra } from "../api/cliente";
import { BLOCOS } from "./formato";

type Opcao = { valor: string; rotulo: string };
type Grupo = { grupo: string; opcoes: Opcao[] };

const REF = /^\{\{\s*([^}]+?)\s*\}\}$/;

/** Blocos que vêm antes deste (direta ou indiretamente): só o resultado deles pode ser usado. */
function ancestrais(bp: ProcessoBlueprint, bloco: Bloco): Bloco[] {
  const vistos = new Set<string>();
  const pilha = [...bloco.depende_de];
  while (pilha.length) {
    const id = pilha.pop()!;
    if (vistos.has(id)) continue;
    vistos.add(id);
    pilha.push(...(bp.blocos.find((b) => b.id === id)?.depende_de ?? []));
  }
  return bp.blocos.filter((b) => vistos.has(b.id));
}

/** A lista de onde um valor pode vir: as entradas do processo ou o resultado (inteiro ou um campo) de um bloco anterior. */
function ligacoes(bp: ProcessoBlueprint, bloco: Bloco, ferramentas: Ferramenta[]): Grupo[] {
  const grupos: Grupo[] = [];
  if (bp.campos.length) grupos.push({ grupo: "Entradas do processo", opcoes: bp.campos.map((c) => ({ valor: `entrada.${c.id}`, rotulo: c.rotulo })) });
  const anteriores = ancestrais(bp, bloco);
  if (anteriores.length) {
    grupos.push({ grupo: "Resultado de blocos anteriores", opcoes: anteriores.flatMap((b) => {
      const campos = b.ferramenta ? Object.entries(ferramentas.find((f) => f.id === b.ferramenta)?.campos_saida ?? {}) : [];
      return [
        { valor: `passos.${b.id}.saida`, rotulo: `Resultado completo de “${b.titulo}”` },
        ...campos.map(([c, r]) => ({ valor: `passos.${b.id}.saida.${c}`, rotulo: `${r} de “${b.titulo}”` })),
      ];
    }) });
  }
  return grupos;
}

function SeletorLigacao({ grupos, valor, aoMudar, aria }: { grupos: Grupo[]; valor: string; aoMudar: (v: string) => void; aria: string }) {
  return (
    <select className="campo" value={valor} onChange={(e) => aoMudar(e.target.value)} aria-label={aria}>
      <option value="">Escolha de onde vem…</option>
      {grupos.map((g) => (
        <optgroup key={g.grupo} label={g.grupo}>
          {g.opcoes.map((o) => <option key={o.valor} value={o.valor}>{o.rotulo}</option>)}
        </optgroup>
      ))}
    </select>
  );
}

/** Um valor da ferramenta: escrito na hora ou ligado a uma entrada/resultado, sempre escolhido numa lista. */
function SeletorValor({ param, descricao, obrigatorio, valor, grupos, aoMudar }: {
  param: string; descricao: string; obrigatorio: boolean; valor: unknown; grupos: Grupo[]; aoMudar: (v: unknown) => void;
  enumerado?: string[];
}) {
  const texto = typeof valor === "string" ? valor : valor == null ? "" : String(valor);
  const ref = REF.exec(texto)?.[1] ?? null;
  const ligado = ref !== null;
  return (
    <div className="space-y-1">
      <span className="rotulo">{descricao || param}{obrigatorio && <span className="text-erro"> *</span>}</span>
      <select className="campo" value={ligado ? "ligar" : "escrever"} aria-label={`Origem de ${descricao || param}`}
        onChange={(e) => aoMudar(e.target.value === "ligar" ? "{{?}}" : "")}>
        <option value="escrever">Escrever um valor</option>
        <option value="ligar">Usar um resultado ou uma entrada</option>
      </select>
      {ligado
        ? <SeletorLigacao grupos={grupos} valor={ref === "?" ? "" : ref!} aria={`Resultado para ${descricao || param}`} aoMudar={(v) => aoMudar(v ? `{{${v}}}` : "{{?}}")} />
        : <input className="campo" value={texto} onChange={(e) => aoMudar(e.target.value)} aria-label={`Valor de ${descricao || param}`} />}
    </div>
  );
}

function EditorEntrada({ f, bloco, grupos, aoMudar }: { f: Ferramenta; bloco: Bloco; grupos: Grupo[]; aoMudar: (b: Bloco) => void }) {
  return (
    <div className="space-y-3">
      {Object.entries(f.parametros).map(([nome, p]) => {
        const valor = bloco.entrada[nome];
        if (p.enum) {
          return (
            <label key={nome} className="block">
              <span className="rotulo">{p.description || nome}{f.obrigatorios.includes(nome) && <span className="text-erro"> *</span>}</span>
              <select className="campo" value={typeof valor === "string" && !REF.test(valor) ? valor : ""} aria-label={p.description || nome}
                onChange={(e) => aoMudar({ ...bloco, entrada: { ...bloco.entrada, [nome]: e.target.value } })}>
                <option value="">Escolha…</option>
                {p.enum.map((o) => <option key={o} value={o}>{o}</option>)}
              </select>
            </label>
          );
        }
        return (
          <SeletorValor key={nome} param={nome} descricao={p.description ?? ""} obrigatorio={f.obrigatorios.includes(nome)} valor={valor} grupos={grupos}
            aoMudar={(v) => aoMudar({ ...bloco, entrada: { ...bloco.entrada, [nome]: v } })} />
        );
      })}
    </div>
  );
}

/** Escolhe o plugin e a ação: só aparece o que a pessoa pode usar; o que não pode vem desabilitado, com o motivo. */
function SeletorFerramenta({ bloco, ferramentas, filtro, aoMudar }: {
  bloco: Bloco; ferramentas: Ferramenta[]; filtro: (f: Ferramenta) => boolean; aoMudar: (b: Bloco) => void;
}) {
  const lista = ferramentas.filter(filtro);
  const origens = [...new Set(lista.map((f) => f.origem))];
  const indisponiveis = lista.filter((f) => !f.disponivel_para_mim);
  const escolhida = ferramentas.find((f) => f.id === bloco.ferramenta);
  return (
    <div className="space-y-2">
      <span className="rotulo">Plugin e ação</span>
      <select className="campo" value={bloco.ferramenta ?? ""} aria-label="Ferramenta do bloco"
        onChange={(e) => aoMudar({ ...bloco, ferramenta: e.target.value || null, entrada: {} })}>
        <option value="">Escolha o plugin e a ação…</option>
        {origens.map((o) => (
          <optgroup key={o} label={o}>
            {lista.filter((f) => f.origem === o).map((f) => (
              <option key={f.id} value={f.id} disabled={!f.disponivel_para_mim}>{f.nome}{!f.disponivel_para_mim ? " — sem permissão" : ""}</option>
            ))}
          </optgroup>
        ))}
      </select>
      {escolhida && <p className="text-xs text-tinta-3">{escolhida.descricao}</p>}
      {indisponiveis.length > 0 && (
        <details className="rounded-lg bg-papel p-2 text-xs text-tinta-2">
          <summary className="cursor-pointer font-semibold">{indisponiveis.length} ação(ões) que você não pode usar</summary>
          <ul className="mt-1 space-y-1">{indisponiveis.map((f) => <li key={f.id}><b>{f.nome}:</b> {f.motivo}</li>)}</ul>
        </details>
      )}
      <p className="text-[11px] text-tinta-3">Plugins que não estão integrados não aparecem: integre-os na aba Plugins.</p>
    </div>
  );
}

const OPERADORES: { id: Regra["operador"]; nome: string }[] = [
  { id: "igual", nome: "é igual a" }, { id: "contem", nome: "contém" }, { id: "maior", nome: "é maior que" },
];

/** Painel lateral: configura o bloco selecionado, em linguagem de quem monta o processo. */
export default function PainelBloco({ bp, bloco, ferramentas, problemas, aoMudar, aoRemover }: {
  bp: ProcessoBlueprint; bloco: Bloco; ferramentas: Ferramenta[]; problemas: string[]; aoMudar: (b: Bloco) => void; aoRemover: () => void;
}) {
  const info = BLOCOS[bloco.tipo];
  const agentes = useQuery({ queryKey: ["processos", "agentes-disponiveis"], queryFn: () => api<AgenteDisponivel[]>("/processos/agentes-disponiveis") });
  const escolhido = agentes.data?.find((a) => a.id === bloco.agente_id);
  const grupos = ligacoes(bp, bloco, ferramentas);
  const ferramenta = ferramentas.find((f) => f.id === bloco.ferramenta);
  const modoAviso = bloco.tipo === "saida" && !!bloco.ferramenta;
  // resposta final: "texto antes" + "mostrar o resultado de" (a referência fica por baixo, a pessoa só escolhe da lista)
  const refFinal = /(\{\{[^}]+\}\})\s*$/.exec(bloco.texto)?.[1] ?? "";
  const antes = bloco.texto.replace(/\n?\{\{[^}]+\}\}\s*$/, "");
  const comporFinal = (a: string, r: string) => aoMudar({ ...bloco, texto: (a && r ? a + "\n" : a) + r });
  const regra: Regra = bloco.regra ?? { fonte: "", operador: "igual", valor: "" };
  const ramos = bp.blocos.filter((b) => b.ramo?.condicao === bloco.id);

  return (
    <div className="caixa space-y-4 p-4" data-testid="painel-bloco">
      <div className="flex items-center justify-between">
        <span className="text-xs font-semibold uppercase tracking-wide text-tinta-3"><span aria-hidden="true">{info.icone}</span> {info.nome}</span>
        <button className="text-xs font-semibold text-erro hover:underline" onClick={aoRemover}>Remover bloco</button>
      </div>
      <p className="text-xs text-tinta-3">{info.descricao}</p>
      <label className="block">
        <span className="rotulo">Título</span>
        <input className="campo" value={bloco.titulo} onChange={(e) => aoMudar({ ...bloco, titulo: e.target.value })} />
      </label>

      {bloco.tipo === "agente" && (
        <div>
          <span className="rotulo">Agente que faz esta tarefa</span>
          <select className="campo" value={bloco.agente_id ?? ""} onChange={(e) => aoMudar({ ...bloco, agente_id: e.target.value || null })} aria-label="Agente do bloco">
            <option value="">Escolha um agente…</option>
            {agentes.data?.map((a) => (
              <option key={a.id} value={a.id} disabled={!a.trabalhador}>
                {a.nome}{!a.publicado ? " (rascunho)" : ""}{!a.trabalhador ? " — formato antigo" : ""}
              </option>
            ))}
          </select>
          {escolhido && (
            <div className="mt-2 space-y-1 rounded-lg bg-papel p-2 text-xs text-tinta-2">
              <p>{escolhido.objetivo}</p>
              <p>Ferramentas: {escolhido.ferramentas.length ? escolhido.ferramentas.join(", ") : "nenhuma"} · modelo {escolhido.modelo === "auto" ? "automático" : escolhido.modelo}</p>
              {!escolhido.publicado && <p className="text-alerta">Ainda é rascunho: dá para testar, mas só publica o processo depois de publicar o agente.</p>}
            </div>
          )}
          {agentes.data?.some((a) => !a.trabalhador) && <p className="mt-1 text-xs text-tinta-3">Agentes de vários passos (formato antigo) não aparecem como opção: converta-os em processo.</p>}
          <p className="mt-2 text-xs text-tinta-3">O agente recebe as entradas do processo e o resultado dos blocos que vêm antes dele.</p>
        </div>
      )}

      {(bloco.tipo === "dados" || bloco.tipo === "plugin" || modoAviso) && (
        <>
          <SeletorFerramenta bloco={bloco} ferramentas={ferramentas} aoMudar={aoMudar}
            filtro={(f) => bloco.tipo === "dados" ? f.acao === "leitura" : modoAviso || bloco.tipo === "saida" ? f.acao === "escrita" : true} />
          {ferramenta && <EditorEntrada f={ferramenta} bloco={bloco} grupos={grupos} aoMudar={aoMudar} />}
        </>
      )}

      {bloco.tipo === "saida" && (
        <div className="space-y-3">
          <div className="flex gap-4 text-sm" role="radiogroup" aria-label="O que este bloco faz">
            <label className="flex items-center gap-1.5"><input type="radio" checked={!modoAviso} onChange={() => aoMudar({ ...bloco, ferramenta: null, entrada: {}, texto: "" })} /> Resposta final</label>
            <label className="flex items-center gap-1.5"><input type="radio" checked={modoAviso} onChange={() => aoMudar({ ...bloco, ferramenta: "enviar_notificacao", entrada: {}, texto: "" })} /> Avisar alguém</label>
          </div>
          {!modoAviso && (
            <>
              <label className="block">
                <span className="rotulo">Texto da resposta</span>
                <textarea className="campo min-h-[70px]" value={antes} onChange={(e) => comporFinal(e.target.value, refFinal)} aria-label="Texto da resposta final" />
              </label>
              <div>
                <span className="rotulo">Mostrar também o resultado de</span>
                <SeletorLigacao grupos={grupos} valor={REF.exec(refFinal)?.[1] ?? ""} aria="Resultado a mostrar na resposta"
                  aoMudar={(v) => comporFinal(antes, v ? `{{${v}}}` : "")} />
              </div>
            </>
          )}
        </div>
      )}

      {bloco.tipo === "condicao" && (
        <div className="space-y-3">
          <div>
            <span className="rotulo">O que verificar</span>
            <SeletorLigacao grupos={grupos} valor={regra.fonte} aria="O que a condição verifica" aoMudar={(v) => aoMudar({ ...bloco, regra: { ...regra, fonte: v } })} />
          </div>
          <div className="grid grid-cols-[1fr_1fr] gap-2">
            <label className="block">
              <span className="rotulo">Regra</span>
              <select className="campo" value={regra.operador} aria-label="Operador da regra" onChange={(e) => aoMudar({ ...bloco, regra: { ...regra, operador: e.target.value as Regra["operador"] } })}>
                {OPERADORES.map((o) => <option key={o.id} value={o.id}>{o.nome}</option>)}
              </select>
            </label>
            <label className="block">
              <span className="rotulo">Valor</span>
              <input className="campo" value={regra.valor} aria-label="Valor da regra" onChange={(e) => aoMudar({ ...bloco, regra: { ...regra, valor: e.target.value } })} />
            </label>
          </div>
          <p className="text-xs text-tinta-3">
            Ligue a saída <b className="text-pedra-forte">sim</b> (de cima) e a saída <b className="text-falcao">não</b> (de baixo) aos próximos blocos. O caminho que não for escolhido aparece como “pulado” na execução.
          </p>
          {ramos.length > 0 && (
            <ul className="text-xs text-tinta-2">{ramos.map((r) => <li key={r.id}>se {r.ramo!.valor === "sim" ? "sim" : "não"} → {r.titulo}</li>)}</ul>
          )}
        </div>
      )}

      {bloco.tipo === "aprovacao" && <p className="text-xs text-tinta-2">A execução para aqui até uma pessoa confirmar. Use o título para dizer o que ela está confirmando.</p>}

      {bloco.depende_de.length > 0 && <p className="text-xs text-tinta-3">Espera por: {bloco.depende_de.map((d) => bp.blocos.find((b) => b.id === d)?.titulo ?? d).join(", ")}. Para mudar, arraste no canvas ou selecione a seta e apague.</p>}
      {problemas.length > 0 && <ul className="space-y-0.5 text-xs text-erro" role="alert">{problemas.map((p) => <li key={p}>• {p}</li>)}</ul>}
    </div>
  );
}
