// Cliente da API do StoneFalcon. O login é simulado: o perfil escolhido vai no
// cabeçalho X-Usuario (em produção, o token do SSO da empresa).

const CHAVE_PERFIL = "stonefalcon.perfil";

export function perfilAtual(): string | null {
  try {
    return localStorage.getItem(CHAVE_PERFIL);
  } catch {
    return null;
  }
}

export function definirPerfil(id: string | null) {
  try {
    if (id) localStorage.setItem(CHAVE_PERFIL, id);
    else localStorage.removeItem(CHAVE_PERFIL);
  } catch {
    /* navegação privada: segue só na memória */
  }
}

export class ErroApi extends Error {
  constructor(public status: number, mensagem: string) {
    super(mensagem);
  }
}

export async function api<T>(rota: string, corpo?: unknown, metodo?: string): Promise<T> {
  const cabecalhos: Record<string, string> = { "Content-Type": "application/json" };
  const perfil = perfilAtual();
  if (perfil) cabecalhos["X-Usuario"] = perfil;
  const resp = await fetch("/api/v1" + rota, {
    method: metodo ?? (corpo === undefined ? "GET" : "POST"),
    headers: cabecalhos,
    body: corpo === undefined ? undefined : JSON.stringify(corpo),
  });
  const dados = await resp.json().catch(() => ({}));
  if (!resp.ok) {
    const det = (dados as { detail?: unknown }).detail;
    const msg = typeof det === "string" ? det : Array.isArray(det) ? det.map((d) => d.msg).join("; ") : "Erro " + resp.status;
    throw new ErroApi(resp.status, msg);
  }
  return dados as T;
}

// ---------- tipos (espelham o backend) ----------
export type Persona = {
  id: string; nome: string; area: string; area_nome: string; cargo: string; nivel: string; papeis: string[];
  matricula: string; cor: string; descricao: string; roteiro_id: string | null; iniciais: string;
  foto: string; abas: string[];
};

export type Campo = {
  id: string; rotulo: string; tipo: "texto" | "texto_longo" | "lojista" | "colaborador" | "opcao";
  exemplo: string; ajuda: string; opcoes: string[];
};

export type Lojista = { id: string; nome: string; cidade: string; segmento: string; plano: string };
export type Colaborador = { id: string; nome: string; area: string; eu: boolean };

export type Passo = {
  id: string; titulo: string; tipo: "ferramenta" | "agente" | "aprovacao"; depende_de: string[];
  instrucao: string; ferramentas: string[]; modelo: string; max_iteracoes: number;
  ferramenta: string | null; entrada: Record<string, unknown>;
};

export type Blueprint = {
  nome: string; objetivo: string; area: string; instrucoes: string; campos: Campo[];
  passos: Passo[]; limites: { max_custo_brl: number; max_chamadas_modelo: number }; minutos_manual: number;
};

export type Risco = { nivel: "baixo" | "medio" | "alto"; motivos: string[]; exige_revisao_seguranca: boolean };
export type Estimativa = { custo_por_execucao_brl: number; chamadas_modelo: number; por_passo: Record<string, { modelo: string | null; custo_brl: number; modelo_chave?: string; provedor?: string; simulado?: boolean }> };
export type Explicacao = { passo: string; titulo: string; explicacao: string };

export type Sugestao = {
  blueprint: Blueprint; origem: string; explicacao: Explicacao[]; ferramentas_removidas: Record<string, string>;
  alertas: string[]; risco: Risco; estimativa: Estimativa; niveis: string[][]; custo_sugestao_brl: number;
  entrada_sugerida?: Record<string, string>;
  trabalhador: Blueprint;       // v8: o agente único (um trabalhador) que o Estúdio cria a partir do fluxo sugerido
  multipasso: boolean;          // o fluxo é claramente de vários passos: oferece "Transformar em processo"
};

export type Validacao =
  | { valido: false; erros: string[] }
  | { valido: true; erros: []; niveis: string[][]; sem_permissao: Record<string, string>; risco: Risco; estimativa: Estimativa; explicacao: Explicacao[] };

export type Ferramenta = {
  id: string; nome: string; descricao: string; modulo: string; modulo_nome: string; classificacao: string;
  areas: string[]; acao: string; exige_aprovacao: boolean; limite_por_minuto: number; ativo: boolean;
  falha: string | null; disponivel_para_mim: boolean; motivo: string; origem: string; plugin: string | null;
  parametros: Record<string, { type: string; description?: string; enum?: string[] }>; obrigatorios: string[];
  campos_saida?: Record<string, string>;
};

export type UsoFerramenta = { conector: string; ok: boolean; erro: string | null; tipo_erro: string | null; latencia_ms: number; mascarados: { tipo: string; rotulo: string; quantidade: number }[]; suspeitas: string[] };

export type RegistroPasso = {
  id: string; titulo: string; tipo: string; status: string; saida: unknown; motivo: string | null; modelo: string | null;
  motivos_modelo: string[]; modelo_chave?: string | null; esforco?: string | null; balanceador?: DecisaoBalanceador | null; provedor?: string | null; modelo_simulado?: boolean | null; reserva?: string; ferramentas: UsoFerramenta[]; iteracoes: number; custo_usd: number;
  duracao_ms: number; duracao_estimada_ms: number;
  pendencia: Pendencia | null;
  bloco?: string | null; agente?: { id: string; nome: string; versao: number } | null;   // v8: passo que veio de um bloco de processo
};

export type Pendencia = { passo: string; tipo: "ferramenta" | "aprovacao"; conector?: string; conector_nome?: string; entrada?: Record<string, unknown>; justificativa?: string | null; titulo?: string };

export type Execucao = {
  id: string; agente_id: string | null; dono_tipo?: "agente" | "processo"; dono_id?: string | null; versao?: number | null; agente_nome: string; area: string; persona: string; status: string;
  motivo: string | null; entrada: Record<string, unknown>; blueprint: Blueprint; passos: Record<string, RegistroPasso>;
  pendencia: Pendencia | null; resultado: string | null; chamadas_modelo: number; tokens_entrada: number;
  tokens_saida: number; custo_usd: number; custo_brl: number; duracao_ms: number; duracao_estimada_ms: number;
  simulado: boolean; inicio: string; fim: string | null;
  resultado_tela?: string; passos_tela?: Record<string, RegistroPasso>;
  rotina?: { rotina: string; origem: string } | null;
};

export type ModeloIA = {
  chave: string; nome: string; provedor: string; provedor_nome: string; simulado: boolean; id_api: string;
  preco_entrada: number; preco_saida: number; preco_cache_leitura: number; limite_preco_padrao: number | null;
  capacidades: { ferramentas: boolean; contexto_longo: boolean; raciocinio: number; esforco_maximo: string };
  fonte_preco: string; data_preco: string; apelidos: string[];
};
export type RegistroModelos = { provedores: { id: string; nome: string; real: boolean }[]; modelos: ModeloIA[] };
export type Comparativo = {
  dias: number; execucoes: number; atual_brl: number; tem_demo: boolean; aviso: string;
  cenarios: { chave: string; modelo: string; provedor: string; provedor_nome: string; simulado: boolean; custo_brl: number; variacao_pct: number | null }[];
};
export type DecisaoBalanceador = {
  esforco: string | null; modo: string; escolhido: string; provedor: string; motivo: string;
  candidatos: { chave: string; nome: string; provedor: string; preco_ref_usd: number; simulado: boolean; descartado: string | null }[];
};
export type CargaBalanceador = {
  passos: number; semente: number; fora: string[]; custo_brl: number; custo_tudo_forte_brl: number; economia_pct: number | null;
  por_nivel: { nivel: string; rotulo: string; passos: number; custo_brl: number }[];
  por_provedor: { provedor: string; nome: string; passos: number; custo_brl: number }[];
  por_modelo: { chave: string; nome: string; provedor: string; passos: number; custo_brl: number }[];
};
export type PoliticaBalanceador = {
  niveis: { id: string; rotulo: string; descricao: string; raciocinio_min: number;
    escolha: { modelo: string; chave: string; provedor: string; modo: string; motivo: string; simulado: boolean } }[];
  regras: { tolerancia_homologado: number; provedor_homologado: string; orcamento_apertado: number; limite_contexto_longo: number };
  provedores: { id: string; nome: string; real: boolean; fora: boolean; modelos: string[] }[];
  ultima_carga: CargaBalanceador | null; pode_simular: boolean; demonstracao: string;
};
export type ExecucaoRecenteMapa = {
  id: string; agente_id: string | null; dono_id?: string; dono_tipo?: string; agente: string; status: string; quando: string; custo_brl: number; rotina: boolean;
  modelos: string[]; demo: boolean; arestas: [string, string, number][];
};
export type NoMapa = {
  id: string; tipo: "criador" | "processo" | "agente" | "modelo" | "ferramenta" | "plugin" | "sistema";
  provedor?: string; provedor_nome?: string; simulado?: boolean; chamadas?: number; coluna: string; rotulo: string;
  detalhe?: string; area?: string; estado?: string; risco?: string; dono?: string; execucoes: number; custo_brl?: number;
  rota?: string; usada_por?: number; integrado?: boolean; externo?: boolean; classificacao?: string; ferramentas?: string[] | number;
};
export type MapaIA = {
  dias: number; colunas: { id: string; rotulo: string }[]; nos: NoMapa[]; ligacoes: { de: string; para: string; volume: number }[];
  totais: { processos: number; agentes: number; modelos: number; plugins: number; ferramentas: number; plataformas: number; execucoes: number }; tem_demo: boolean;
  filtros: { area: string | null; provedor: string | null; areas: string[]; provedores: { id: string; nome: string }[] };
  execucoes_recentes: ExecucaoRecenteMapa[];
};
export type Rotina = {
  id: string; agente_id: string; dono_tipo?: "agente" | "processo"; agente_nome?: string; dono: string; frequencia: "diaria" | "semanal"; dia_semana: number | null;
  hora: number; minuto: number; descricao: string; ativa: boolean; entrada: Record<string, string>; proxima_em: string | null;
  ultima_em: string | null; ultima_execucao_id: string | null; ultimo_resultado: string | null; pode_gerir?: boolean; pode_rodar?: boolean;
};
export type RelogioRotinas = { agora: string; fator: number; demo: boolean; pode_mexer?: boolean; disparadas?: unknown[] };
export type Saude = { ok: boolean; versao: string; modo: "real" | "simulado"; modelos: Record<string, string>; cotacao_dolar: number };

export type Agente = {
  id: string; nome: string; area: string; dono: string; estado: "rascunho" | "em_revisao" | "publicado" | "pausado" | "depreciado";
  versao_publicada: number | null; ultima_versao: number; risco: "baixo" | "medio" | "alto"; compartilhado_com: string[];
  motivo_estado: string | null; criado_em: string; atualizado_em: string;
  execucoes: number; escaladas: number; custo_brl: number; plugins_indisponiveis: { id: string; nome: string }[];
  processos?: number;           // v8: em quantos processos o agente trabalha
  legado?: boolean;             // v8: agente de vários passos (formato antigo): converte em processo
};

export type VersaoAgente = {
  id: string; agente_id: string; numero: number; estado: string; blueprint: Blueprint; nota: string; autor: string;
  criada_em: string; risco: string; revisor: string | null; parecer: string | null; revisada_em: string | null; publicada_em: string | null;
};

export type EventoAuditoria = { seq: number; id: string; tipo: string; quando: string; ator: string; agente_id: string | null; dados: Record<string, unknown> };

export type UsoEmProcesso = { id: string; nome: string; dono: string; area: string; estado: string; as_is: { roteiro_id: string; processo: string; persona: string } | null };
export type AgenteDetalhe = Agente & { versoes: VersaoAgente[]; pode_executar: boolean; historico: EventoAuditoria[]; usado_em?: UsoEmProcesso[] };

export type Mudanca = { tipo: "adicionado" | "removido" | "alterado"; alvo: string; campo: string | null; antes: unknown; depois: unknown };

export type ItemRevisao = { tipo?: "agente" | "processo"; agente: Agente; versao: VersaoAgente; mudancas: Mudanca[] };

// ---------- processos (v8): fluxos de blocos ----------
export type TipoBloco = "dados" | "agente" | "plugin" | "aprovacao" | "condicao" | "saida";
export type Regra = { fonte: string; operador: "igual" | "contem" | "maior"; valor: string };
export type Bloco = {
  id: string; tipo: TipoBloco; titulo: string; depende_de: string[]; ramo: { condicao: string; valor: "sim" | "nao" } | null;
  agente_id: string | null; ferramenta: string | null; entrada: Record<string, unknown>; regra: Regra | null; texto: string;
};
export type ProcessoBlueprint = {
  nome: string; objetivo: string; area: string; campos: Campo[]; blocos: Bloco[];
  limites: { max_custo_brl: number; max_chamadas_modelo: number }; minutos_manual: number; roteiro_id: string | null;
};
export type Processo = {
  id: string; nome: string; area: string; dono: string; estado: Agente["estado"]; versao_publicada: number | null; ultima_versao: number;
  risco: "baixo" | "medio" | "alto"; compartilhado_com: string[]; motivo_estado: string | null; orcamento_mensal_brl: number;
  roteiro_id: string | null; criado_em: string; atualizado_em: string; execucoes: number; escaladas: number; custo_brl: number;
  as_is: { roteiro_id: string; processo: string; persona: string } | null; agentes: string[];
  agentes_info?: { id: string; nome: string; estado: string; motivo: string | null }[];
  alertas_agentes?: { id: string; nome: string; estado: string; motivo: string | null }[];
};
export type VersaoProcesso = Omit<VersaoAgente, "blueprint" | "agente_id"> & { processo_id: string; blueprint: ProcessoBlueprint };
export type ProcessoDetalhe = Processo & { versoes: VersaoProcesso[]; pode_executar: boolean; pode_editar: boolean; historico: EventoAuditoria[] };
export type AgenteDisponivel = {
  id: string; nome: string; objetivo: string; estado: string; area: string; publicado: boolean; trabalhador: boolean;
  ferramentas: string[]; modelo: string | null; motivo: string | null;
};
export type ValidacaoProcesso =
  | { valido: false; erros: string[]; blocos?: Record<string, string[]> }
  | { valido: true; erros: []; niveis: string[][]; sem_permissao: Record<string, string>; bloqueios: Record<string, string>; risco: Risco;
      estimativa: Estimativa & { duracao_ms: number }; blocos?: Record<string, string[]> };

export type Alerta = {
  id: string; regra: string; severidade: "atencao" | "critico"; agente_id: string | null; conector: string | null;
  titulo: string; detalhe: string; destinatarios: string[]; ocorrencias: number; aberto_em: string; atualizado_em: string;
  resolvido_em: string | null; lido?: boolean;
};

export type MetricasAgente = {
  execucoes: number; concluidas: number; escaladas: number; falhas: number; aguardando: number; taxa_sucesso: number | null;
  latencia_p50_ms: number; latencia_p95_ms: number; custo_brl: number; custo_medio_brl: number;
};

export type SaudeAgente = {
  agente: { id: string; nome: string; area: string; dono: string; estado: string; risco: string };
  metricas: MetricasAgente; score: { nota: number; status: "saudavel" | "atencao" | "critico" }; alertas: Alerta[];
};

export type SaudeConector = {
  id: string; nome: string; modulo: string; status: "ok" | "lento" | "fora"; chamadas: number; erros: number; taxa_erro: number;
  latencia_tipica_ms: number; latencia_p95_ms?: number; detalhe: string | null;
};

export type FinancasAgente = {
  id: string; tipo: "agente" | "processo"; agentes?: { id: string; nome: string; execucoes: number; custo_brl: number }[]; nome: string; area: string; estado: string; minutos_manual: number; execucoes: number; concluidas: number;
  custo_brl: number; ganho_brl: number; horas_liberadas: number; roi: number | null; custo_medio_brl: number;
  orcamento_mensal_brl: number; gasto_mes_brl: number; uso_orcamento: number | null;
};

export type ResumoFinancas = {
  dias: number; tem_demo: boolean; execucoes: number; custo_brl: number; custo_sem_roteador_brl: number;
  economia_roteador_pct: number | null; ganho_brl: number; roi_variavel: number | null;
  por_agente: FinancasAgente[]; por_area: { area: string; execucoes: number; custo_brl: number; ganho_brl: number }[];
  por_provedor: { provedor: string; provedor_nome: string; simulado: boolean; chamadas: number; custo_brl: number }[];
  por_modelo: { chave: string; modelo: string; provedor: string; provedor_nome: string; simulado: boolean; chamadas: number; custo_brl: number }[];
  por_dia: ({ dia: string; execucoes: number; custo_brl: number } & Record<string, number | string>)[];
  premissas?: Record<string, number | boolean>;
};

export type Premissas = Record<string, number | boolean>;

export type Projecao = {
  meses: { mes: number; usuarios_ativos: number; execucoes: number; horas_liberadas: number; custo_tokens: number; custo_fixo: number; beneficio: number; fluxo: number; acumulado: number }[];
  investimento_total: number; custo_fixo_mensal: number; ganho_por_tarefa: number; payback_mes: number | null; vpl: number;
  tir_anual: number | null; roi: number | null; beneficio_total: number; custo_total: number; tokens_participacao: number;
  ponto_de_equilibrio_execucoes_mes: number | null;
};

export type Indicadores = {
  dias: number; tem_demo: boolean; execucoes: number;
  tempo_execucao: { manual_min: number; agente_min: number; revisao_humana_min: number; reducao_pct: number | null };
  custo_operacional: { manual_brl: number; agente_brl: number; economia_por_operacao_brl: number; economia_roteador_pct: number | null };
  produtividade: { tarefas_concluidas: number; horas_liberadas: number; agentes_ativos: number };
  taxa_erros: { agente: number | null; manual_premissa: number; escaladas_ou_falhas: number; acessos_bloqueados: number; dados_mascarados: number };
  roi: { periodo_ganho_brl: number; periodo_custo_brl: number; periodo_roi_variavel: number | null; projecao_payback_mes: number | null; projecao_vpl: number; projecao_roi: number | null; projecao_tir_anual: number | null };
  premissas_usadas: Record<string, number>;
};


// ---------- roteiros e Perguntas da Ferramenta ----------
/** Fluxo de blocos do roteiro: o agente vem pelo NOME (`agente_nome`) e a tela troca pelo id do agente que a pessoa acabou de criar. */
export type ProcessoPronto = Omit<ProcessoBlueprint, "blocos"> & { blocos: (Omit<Bloco, "agente_id"> & { agente_id?: string | null; agente_nome?: string })[] };

export type PassoRoteiro = {
  id: string; titulo: string; perfil: string; rota: string; acao: string; fala: string;
  preenche: { descricao?: string; nome_agente?: string; processo?: ProcessoPronto; entrada?: Record<string, string>; parecer?: string; fonte?: { tipo: string; url: string };
    frequencia?: "semanal" | "diaria"; dia_semana?: number; hora?: string }; externa: boolean;
};

export type AsIs = { minutos: number; hipotese: boolean; dor: string; passos: string[]; erros: string[] };
export type ToBe = { conferencia_min: number; passos: string[]; nota: string };

export type Roteiro = {
  id: string; persona: string; titulo: string; processo: string; resumo: string; duracao_min: number;
  as_is: AsIs; to_be: ToBe; valor: string[]; agente_nome: string | null; passos: PassoRoteiro[]; persona_dados: Persona;
};

export type ResumoRoteiro = { id: string; persona: string; titulo: string; processo: string; resumo: string; duracao_min: number; passos: number; apresentacao?: boolean };

export type LinhaResultado = {
  criterio: string; unidade: string; as_is: number | null; to_be: number | null; delta_pct: number | null;
  origem_as_is: string; origem_to_be: string; melhor: "menor" | "maior";
};

export type ResultadoRoteiro = {
  roteiro: string; titulo: string; processo: string; agente: { id: string; nome: string; estado: string; tipo?: "agente" | "processo" } | null;
  execucao: { id: string; status: string; custo_brl: number; duracao_min: number; simulado: boolean } | null;
  origem: "medido" | "estimado"; linhas: LinhaResultado[]; ganho_por_tarefa_brl: number; aviso: string | null;
  indicadores: { nome: string; valor: number | null; unidade: string; origem: string; detalhe: string }[];
  rotina?: { agendas: string[]; execucoes_feitas: number; execucoes_por_mes: number; ganho_mensal_brl: number; origem: string } | null;
};

export type Consolidado = {
  processos: {
    roteiro: string; persona: string; processo: string; as_is_min: number; to_be_min: number; reducao_pct: number | null;
    custo_tokens_brl: number; ganho_por_tarefa_brl: number; origem_to_be: string; origem_as_is: string;
    calculadora: { minutos_por_tarefa: number; minutos_revisao_humana: number; custo_por_execucao: number };
  }[];
  totais: { as_is_min: number; to_be_min: number; reducao_pct: number | null; ganho_por_rodada_brl: number };
  premissas: { custo_hora: number; aproveitamento: number; taxa_erro_manual: number };
};

export type PerguntaFerramenta = {
  id: string; persona: string; tema: string; pergunta: string; resposta: string;
  prova: { perfil: string; rota: string; rotulo: string; roteiro: string; passo: string | null };
};

export type AnaliseTrecho = {
  agentes: {
    id: string; tipo: "processo" | "agente"; nome: string; objetivo: string; risco: string; pontuacao: number; campos: Campo[];
    preenchido: Record<string, string>; detectado: string[];
  }[];
  sugerido: string | null; lojista: { id: string; nome: string } | null; colaborador: { id: string; nome: string } | null;
};


// ---------- marketplace de plugins (simulado) ----------
export type FerramentaPlugin = {
  id: string; nome: string; descricao: string; acao: "leitura" | "escrita"; classificacao: string; exige_aprovacao: boolean;
  nivel_suficiente: boolean; disponivel_para_mim: boolean;
};

export type ArquivoPlugin = {
  id: string; nome: string; formato: "csv" | "xlsx"; classificacao: string; areas: string[]; areas_nomes: string[]; dono: string; dono_nome: string;
  colunas: string[]; total_linhas: number; tamanho_bytes: number; versao: number; criado_em: string; atualizado_em: string; atualizado_por: string;
  demo: boolean; exige_confirmacao_para_escrever: boolean; pode_remover?: boolean; previa?: Record<string, string | number>[]; previa_limite?: number;
};
export type LimitesArquivos = { bytes: number; linhas: number; colunas: number; formatos: string[]; meu_nivel: string; classificacoes: string[] };

export type PedidoMeu = { id: string; estado: "pendente" | "aprovado" | "recusado" | "registrado"; parecer: string | null; revisor: string | null };

export type Plugin = {
  id: string; nome: string; categoria: string; categoria_nome: string; descricao: string; simulado: boolean; real?: boolean; interno?: boolean; janela: boolean;
  classificacao: string; sensivel: boolean; areas: string[]; areas_nomes: string[];
  estado: "disponivel" | "integrado" | "aguardando_aprovacao"; vale_para_minha_area: boolean;
  ferramentas: FerramentaPlugin[]; exige_aprovacao_para_integrar: boolean; integrado_por: string | null; integrado_em: string | null;
  pode_integrar: boolean; pode_pedir: boolean; pode_remover: boolean;
  pedido_pendente: { id: string; solicitante: string; meu: boolean; pode_decidir: boolean } | null; meu_pedido: PedidoMeu | null;
};

export type EspecFerramenta = {
  id: string; nome: string; acao: "leitura" | "escrita"; descricao: string; entradas: { nome: string; descricao: string }[]; saida: string;
  classificacao: string; exige_confirmacao: boolean;
};
export type EspecPlugin = {
  nome: string; categoria: string; resumo: string; capacidades: string[]; ferramentas: EspecFerramenta[]; classificacao: string; areas: string[];
  riscos: string[]; avisos?: string[];
  comprar_ou_construir: { usuarios_estimados: number; licenca_anual_brl: number; construir_inicial_brl: number; operar_por_ano_brl: number;
    custo_3_anos_comprar_brl: number; custo_3_anos_construir_brl: number; recomendacao: "comprar" | "construir"; premissas: string[] };
};
export type RascunhoPlugin = { spec: EspecPlugin; origem: string; aviso_publico: string; suspeitas: string[] };
export type RegrasPluginInterno = { pode_pedir: boolean; aviso_publico: string; max_descricao: number; min_descricao: number; max_ferramentas: number };
export type DecisaoPluginInterno = { por: string; por_nome?: string; aprovar: boolean; parecer: string; quando: string };
export type PedidoPluginInterno = {
  id: string; estado: "aguardando_analista" | "aguardando_seguranca" | "aprovado" | "publicado" | "recusado" | "removido"; solicitante: string;
  solicitante_nome: string; area: string; finalidade: string; areas: string[]; classificacao: string; spec: EspecPlugin; plugin_id: string | null;
  criado_em: string; atualizado_em: string; meu: boolean; ferramenta_mercado?: string; descricao_publica?: string; pode_decidir?: boolean;
  etapa?: "analista" | "seguranca" | null; exige_seguranca?: boolean; estimativa?: EspecPlugin["comprar_ou_construir"];
  decisao_analista: DecisaoPluginInterno | null; decisao_seguranca: DecisaoPluginInterno | null;
};

export type PedidoPlugin = {
  id: string; plugin_id: string; plugin_nome: string; categoria_nome: string; classificacao: string;
  ferramentas: { id: string; nome: string; acao: string }[]; solicitante: string; solicitante_nome: string; area_nome: string;
  motivo: string; estado: string; parecer: string | null; revisor_nome: string | null; criado_em: string; e_meu: boolean;
  pode_decidir: boolean;
};

export type JanelaPlugin =
  | { tipo: "fila"; titulo: string; itens: { id: string; assunto: string; solicitante: string; prioridade: string; status: string; mensagem: string; respostas: { autor: string; texto: string }[] }[] }
  | { tipo: "canais"; titulo: string; canais: { canal: string; mensagens: { id: string; texto: string; autor: string }[] }[] }
  | { tipo: "quadro"; titulo: string; colunas: { nome: string; itens: { id: string; titulo: string; projeto: string }[] }[] }
  | { tipo: "vazio"; titulo: string };

export type ConsolidadoPlugin = {
  plugin: Plugin; simulado: boolean; nivel_suficiente: boolean; area_permitida: boolean;
  numeros: { agentes: number; chamadas_mes: number; erros: number; custo_brl: number; execucoes: number; latencia_p95_ms: number };
  saude: {
    status: "ok" | "lento" | "fora";
    alertas: { id: string; regra: string; severidade: string; titulo: string; detalhe: string; conector: string }[];
    por_ferramenta: { id: string; nome: string; acao: string; chamadas: number; erros: number; taxa_erro: number; latencia_tipica_ms: number; latencia_p95_ms: number; falha: string | null }[];
  };
  agentes: { id: string; nome: string; area: string; estado: string; chamadas: number }[]; agentes_ocultos: number;
  janela: JanelaPlugin | null;
};
