// StoneFalcon · serviço de fundo da extensão.
// A extensão não tem lógica de IA: abre o copiloto da plataforma no painel lateral e entrega o trecho
// selecionado. O menu do botão direito lista os agentes que a pessoa logada pode usar.
importScripts('comum.js');

const MENU_RAIZ = 'sf-raiz';
const MENU_GERAL = 'sf-geral';
const PREFIXO_AGENTE = 'sf-agente:';
const MENU_CRIAR_TRECHO = 'sf-criar-trecho';
const MENU_CRIAR = 'sf-criar';

// montarMenu pode ser pedido várias vezes ao mesmo tempo (instalação, perfil, endereço): uma por vez,
// senão duas execuções criam o mesmo id e o Chrome recusa a segunda.
let fila = Promise.resolve();
function montarMenu() {
  fila = fila.then(montar).catch((e) => console.warn('StoneFalcon: menu não montou:', e && e.message));
  return fila;
}

chrome.runtime.onInstalled.addListener(() => {
  chrome.sidePanel.setPanelBehavior({ openPanelOnActionClick: true }).catch(() => {});
  montarMenu();
});
chrome.runtime.onStartup.addListener(montarMenu);
// perfil ou endereço mudou: o menu de agentes precisa ser refeito
chrome.storage.local.onChanged.addListener((mudancas) => { if (mudancas.perfil || mudancas.servidor) montarMenu(); });

async function agentesDoPerfil() {
  const perfil = await sfPerfil();
  if (!perfil) return [];
  try {
    const endereco = await sfEndereco();
    const resp = await fetch(endereco + '/api/v1/extensao/analisar', {
      method: 'POST', headers: { 'Content-Type': 'application/json', 'X-Usuario': perfil }, body: JSON.stringify({ trecho: '' }),
    });
    if (!resp.ok) return [];
    return ((await resp.json()).agentes || []).slice(0, 8);
  } catch (e) {
    return [];
  }
}

// Só quem tem a aba Estúdio cria agentes; a lista de abas vem da plataforma (fonte única das permissões).
async function criaAgentes() {
  const perfil = await sfPerfil();
  if (!perfil) return false;
  try {
    const resp = await fetch((await sfEndereco()) + '/api/v1/eu', { headers: { 'X-Usuario': perfil } });
    return resp.ok && ((await resp.json()).abas || []).includes('estudio');
  } catch (e) {
    return false;
  }
}

function criar(item) {
  chrome.contextMenus.create(item, () => void chrome.runtime.lastError);   // lê o erro para o Chrome não reclamar
}

async function montar() {
  await chrome.contextMenus.removeAll();
  criar({ id: MENU_RAIZ, title: 'StoneFalcon', contexts: ['selection'] });
  criar({ id: MENU_GERAL, parentId: MENU_RAIZ, title: 'Perguntar ao StoneFalcon (sugerir o processo ou agente)', contexts: ['selection'] });
  const agentes = await agentesDoPerfil();
  for (const a of agentes) {
    criar({ id: PREFIXO_AGENTE + a.id, parentId: MENU_RAIZ, title: (a.tipo === 'processo' ? 'Processo: ' : 'Agente: ') + a.nome, contexts: ['selection'] });
  }
  if (await criaAgentes()) {
    criar({ id: MENU_CRIAR_TRECHO, parentId: MENU_RAIZ, title: 'Criar Agente de IA com este trecho', contexts: ['selection'] });
    criar({ id: MENU_CRIAR, title: 'StoneFalcon: Criar Agente de IA', contexts: ['page', 'action'] });
  }
}

// Abre o Estúdio (passe de uso único). Se falhar, o painel lateral mostra o diagnóstico.
async function criarAgente(tab, trecho) {
  const fonte = tab ? sfFontePlanilha(tab.url, tab.title, await sfEndereco()) : null;
  const r = await sfCriarAgente(trecho, fonte);
  if (r.ok) return;
  await chrome.storage.session.set({ atalhoErro: Object.assign({ quando: Date.now() }, r) });
  if (tab && tab.id !== undefined) abrirPainel(tab.id);
}

function guardarTrecho(texto, agente) {
  return chrome.storage.session.set({ trecho: { texto: (texto || '').slice(0, 8000), agente: agente || '', quando: Date.now() } });
}

// Abrir o painel exige o gesto do usuário, então nada pode ser aguardado (await) antes.
function abrirPainel(tabId) {
  try {
    chrome.sidePanel.open({ tabId: tabId }).catch((e) => console.warn('StoneFalcon: painel não abriu:', e.message));
  } catch (e) {
    console.warn('StoneFalcon: painel não abriu:', e.message);
  }
}

// clique com o botão direito em um texto selecionado
chrome.contextMenus.onClicked.addListener((info, tab) => {
  if (typeof info.menuItemId !== 'string') return;
  if (info.menuItemId === MENU_CRIAR_TRECHO || info.menuItemId === MENU_CRIAR) {
    criarAgente(tab, info.menuItemId === MENU_CRIAR_TRECHO ? info.selectionText : '');
    return;
  }
  if (!tab) return;
  const id = info.menuItemId;
  if (id !== MENU_GERAL && !id.startsWith(PREFIXO_AGENTE)) return;
  guardarTrecho(info.selectionText, id.startsWith(PREFIXO_AGENTE) ? id.slice(PREFIXO_AGENTE.length) : '');
  abrirPainel(tab.id);
});

// clique no botão flutuante da página
chrome.runtime.onMessage.addListener((msg, remetente) => {
  if (!msg || msg.tipo !== 'sf-abrir' || !remetente.tab) return;
  guardarTrecho(msg.trecho, '');
  abrirPainel(remetente.tab.id);
});
