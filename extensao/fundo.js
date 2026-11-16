// StoneFalcon · serviço de fundo da extensão.
// A extensão não tem lógica de IA: abre a tela de agentes da plataforma no painel
// lateral e entrega o trecho selecionado na página.

chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.create({ id: 'sf-perguntar', title: 'Usar um agente do StoneFalcon com este trecho', contexts: ['selection'] });
  chrome.sidePanel.setPanelBehavior({ openPanelOnActionClick: true }).catch(() => {});
});

function guardarTrecho(texto) {
  return chrome.storage.session.set({ trecho: { texto: (texto || '').slice(0, 8000), quando: Date.now() } });
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
  if (info.menuItemId !== 'sf-perguntar' || !tab) return;
  guardarTrecho(info.selectionText);
  abrirPainel(tab.id);
});

// clique no botão flutuante da página
chrome.runtime.onMessage.addListener((msg, remetente) => {
  if (!msg || msg.tipo !== 'sf-abrir' || !remetente.tab) return;
  guardarTrecho(msg.trecho);
  abrirPainel(remetente.tab.id);
});
