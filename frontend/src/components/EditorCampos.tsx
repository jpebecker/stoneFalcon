import type { Campo } from "../api/cliente";

const TIPOS: { id: Campo["tipo"]; nome: string }[] = [
  { id: "texto", nome: "Texto curto" }, { id: "texto_longo", nome: "Texto longo" },
  { id: "lojista", nome: "Lojista (busca pelo nome)" }, { id: "colaborador", nome: "Colaborador" },
];

const slug = (t: string) => t.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/^_+|_+$/g, "").slice(0, 30) || "campo";

/** Os campos que a pessoa preenche para rodar o processo. O nome técnico sai do rótulo: ninguém digita `lojista_id`. */
export default function EditorCampos({ campos, aoMudar }: { campos: Campo[]; aoMudar: (c: Campo[]) => void }) {
  const mudar = (i: number, p: Partial<Campo>) => aoMudar(campos.map((c, j) => (j === i ? { ...c, ...p } : c)));
  const rotular = (i: number, rotulo: string) => {
    const usados = new Set(campos.filter((_, j) => j !== i).map((c) => c.id));
    let id = slug(rotulo), n = 2;
    while (usados.has(id)) id = slug(rotulo) + "_" + n++;
    mudar(i, { rotulo, id });
  };
  const novo = () => {
    const usados = new Set(campos.map((c) => c.id));
    let n = campos.length + 1;
    while (usados.has("campo_" + n)) n++;
    aoMudar([...campos, { id: "campo_" + n, rotulo: "Novo campo", tipo: "texto", exemplo: "", ajuda: "", opcoes: [] }]);
  };
  return (
    <div className="space-y-2">
      {campos.map((c, i) => (
        <div key={i} className="flex items-center gap-2">
          <input className="campo" value={c.rotulo} onChange={(e) => rotular(i, e.target.value)} aria-label={`Nome do campo ${i + 1}`} />
          <select className="campo w-56" value={c.tipo} onChange={(e) => mudar(i, { tipo: e.target.value as Campo["tipo"] })} aria-label={`Tipo do campo ${i + 1}`}>
            {TIPOS.map((t) => <option key={t.id} value={t.id}>{t.nome}</option>)}
          </select>
          <button type="button" className="text-xs font-semibold text-erro hover:underline" onClick={() => aoMudar(campos.filter((_, j) => j !== i))}>Remover</button>
        </div>
      ))}
      <button type="button" className="botao-claro py-1.5" onClick={novo}>+ Campo de entrada</button>
    </div>
  );
}
