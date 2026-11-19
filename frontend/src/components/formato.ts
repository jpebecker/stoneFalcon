const moeda = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL", minimumFractionDigits: 2, maximumFractionDigits: 4 });

/** "8.0.0" -> "8.0", como a versão aparece para as pessoas. */
export const versaoCurta = (v: string) => v.split(".").slice(0, 2).join(".");

export const reais = (v: number) => moeda.format(v);
export const ms = (v: number) => (v >= 1000 ? (v / 1000).toLocaleString("pt-BR", { maximumFractionDigits: 1 }) + " s" : v + " ms");
export const quando = (iso: string) => new Date(iso).toLocaleString("pt-BR", { dateStyle: "short", timeStyle: "short" });

export const NOME_STATUS: Record<string, string> = {
  concluida: "Concluída", em_andamento: "Em andamento", aguardando_aprovacao: "Aguardando você",
  escalada: "Escalada para humano", falhou: "Falhou", concluido: "Concluído", aguardando: "Aguardando",
  escalado: "Escalado", recusado: "Recusado",
};

export const COR_STATUS: Record<string, string> = {
  concluida: "bg-pedra-fundo text-pedra-forte", concluido: "bg-pedra-fundo text-pedra-forte",
  aguardando_aprovacao: "bg-alerta-fundo text-alerta", aguardando: "bg-alerta-fundo text-alerta",
  escalada: "bg-falcao-fundo text-falcao", escalado: "bg-falcao-fundo text-falcao",
  falhou: "bg-erro-fundo text-erro", recusado: "bg-papel text-tinta-2", em_andamento: "bg-info-fundo text-info",
};

export const COR_RISCO: Record<string, string> = {
  baixo: "bg-pedra-fundo text-pedra-forte", medio: "bg-alerta-fundo text-alerta", alto: "bg-falcao-fundo text-falcao",
};

export const NOME_TIPO: Record<string, string> = { ferramenta: "Consulta", agente: "Raciocínio com IA", aprovacao: "Aprovação humana", condicao: "Condição", saida: "Resposta final" };

/** Os blocos da paleta de processos: nome, ícone, cor da borda e a frase que explica o bloco. */
export const BLOCOS: Record<string, { nome: string; icone: string; cor: string; descricao: string }> = {
  entrada: { nome: "Entradas", icone: "▶", cor: "border-l-tinta-3", descricao: "O que a pessoa preenche para iniciar o processo." },
  dados: { nome: "Dados", icone: "▤", cor: "border-l-info", descricao: "Lê dados de um plugin, como uma planilha ou o cadastro do lojista." },
  agente: { nome: "Agente", icone: "✦", cor: "border-l-pedra", descricao: "Um agente de IA faz uma tarefa e entrega o resultado." },
  plugin: { nome: "Ação de plugin", icone: "⚙", cor: "border-l-falcao", descricao: "Faz algo em outro sistema: abrir chamado, registrar numa planilha." },
  aprovacao: { nome: "Aprovação humana", icone: "✋", cor: "border-l-alerta", descricao: "Espera uma pessoa confirmar antes de seguir." },
  condicao: { nome: "Condição", icone: "⑂", cor: "border-l-[#6b5bd0]", descricao: "Segue por um caminho ou outro, conforme uma regra simples." },
  saida: { nome: "Aviso ou resposta", icone: "✉", cor: "border-l-tinta", descricao: "Avisa alguém (ex.: no Slack) ou monta a resposta final." },
};

export const NOME_ESTADO: Record<string, string> = {
  rascunho: "Rascunho", em_revisao: "Em revisão", publicado: "Publicado", pausado: "Pausado", depreciado: "Depreciado",
  rejeitada: "Rejeitada", publicada: "Publicada", substituida: "Substituída",
};
export const COR_ESTADO: Record<string, string> = {
  rascunho: "bg-papel text-tinta-2", em_revisao: "bg-info-fundo text-info", publicado: "bg-pedra-fundo text-pedra-forte",
  publicada: "bg-pedra-fundo text-pedra-forte", pausado: "bg-alerta-fundo text-alerta", depreciado: "bg-erro-fundo text-erro",
  rejeitada: "bg-falcao-fundo text-falcao", substituida: "bg-papel text-tinta-3",
};
export const NOME_RISCO: Record<string, string> = { baixo: "Risco baixo", medio: "Risco médio", alto: "Risco alto" };

export const NOME_EVENTO: Record<string, string> = {
  passe_extensao_emitido: "Acesso pela extensão pedido", passe_extensao_usado: "Acesso pela extensão usado",
  agente_criado: "Criado", agente_modificado: "Modificado", agente_enviado_revisao: "Enviado para revisão da Segurança",
  revisao_aprovada: "Revisão aprovada", revisao_rejeitada: "Revisão rejeitada", agente_publicado: "Publicado",
  agente_pausado: "Pausado", agente_retomado: "Retomado", agente_depreciado: "Depreciado",
  agente_compartilhado: "Compartilhado", processo_criado: "Criado", processo_modificado: "Modificado",
  processo_enviado_revisao: "Enviado para revisão da Segurança", processo_publicado: "Publicado", processo_pausado: "Pausado",
  processo_retomado: "Retomado", processo_depreciado: "Depreciado", processo_compartilhado: "Compartilhado", execucao_escalada: "Execução escalada", execucao_negada: "Execução negada",
  execucao_iniciada: "Execução iniciada", execucao_concluida: "Execução concluída", execucao_falhou: "Execução falhou",
  execucao_aguardando_aprovacao: "Execução esperando confirmação", aprovacao_concedida: "Ação confirmada por humano",
  aprovacao_recusada: "Ação recusada por humano", ferramenta_executada: "Ferramenta usada", ferramenta_negada: "Ferramenta negada",
  ferramenta_erro: "Ferramenta com erro", ferramenta_aguardando_aprovacao: "Ferramenta pediu confirmação",
  alerta_aberto: "Alerta aberto", alerta_resolvido: "Alerta resolvido", conector_falha_injetada: "Falha simulada no sistema",
  conector_normalizado: "Sistema normalizado", orcamento_definido: "Orçamento definido", estudio_sugestao: "Agente sugerido no Estúdio",
  plugin_integrado: "Plugin integrado", plugin_removido: "Plugin removido", plugin_pedido_criado: "Integração de plugin pedida à Segurança",
  plugin_pedido_registrado: "Integração de plugin pedida (registrada)", plugin_pedido_aprovado: "Integração de plugin aprovada",
  plugin_pedido_recusado: "Integração de plugin recusada",
  historico_demo_gerado: "Histórico de demonstração gerado", historico_demo_apagado: "Histórico de demonstração apagado",
};

export const COR_SAUDE: Record<string, string> = {
  saudavel: "bg-pedra-fundo text-pedra-forte", atencao: "bg-alerta-fundo text-alerta", critico: "bg-erro-fundo text-erro",
  ok: "bg-pedra-fundo text-pedra-forte", lento: "bg-alerta-fundo text-alerta", fora: "bg-erro-fundo text-erro",
};
export const NOME_SAUDE: Record<string, string> = {
  saudavel: "Saudável", atencao: "Atenção", critico: "Crítico", ok: "Normal", lento: "Lento", fora: "Com falha",
};
export const pct = (v: number | null) => (v == null ? "—" : Math.round(v * 100) + "%");

const inteiroBRL = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL", maximumFractionDigits: 0 });
export const reaisCurto = (v: number) => {
  const a = Math.abs(v);
  if (a >= 1_000_000) return (v < 0 ? "-" : "") + "R$ " + (a / 1_000_000).toLocaleString("pt-BR", { maximumFractionDigits: 1 }) + " mi";
  if (a >= 10_000) return (v < 0 ? "-" : "") + "R$ " + (a / 1000).toLocaleString("pt-BR", { maximumFractionDigits: 0 }) + " mil";
  return inteiroBRL.format(v);
};
export const num = (v: number) => v.toLocaleString("pt-BR", { maximumFractionDigits: 1 });
