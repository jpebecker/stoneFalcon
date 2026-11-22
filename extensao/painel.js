// StoneFalcon · painel lateral. Mostra o copiloto da plataforma (rota /extensao) numa moldura.
// A extensão não tem lógica nem chave: tudo roda na plataforma, com as permissões de quem está logado.
const quadro = document.getElementById('quadro');
const estado = document.getElementById('estado');
let endereco = null, pronto = false, origem = null, pendente = null;   // pendente: trecho esperando a tela ficar pronta

function limpar(no) { while (no.firstChild) no.removeChild(no.firstChild); }
function el(tag, props, filhos) {
  const n = document.createElement(tag);
  Object.assign(n, props || {});
  (filhos || []).forEach((f) => n.appendChild(typeof f === 'string' ? document.createTextNode(f) : f));
  return n;
}

function mostrarEstado(...nos) {
  quadro.hidden = true;
  estado.hidden = false;
  limpar(estado);
  nos.forEach((n) => estado.appendChild(n));
  const m = chrome.runtime.getManifest();
  estado.appendChild(el('p', { className: 'nota', textContent: m.name + ' · versão ' + m.version }));
}

// ---------------------------------------------------------------- primeira execução
function boasVindas() {
  const botao = el('button', { textContent: 'Conectar à plataforma' });
  botao.onclick = async () => {
    await chrome.storage.local.set({ visto: true });
    abrir();
  };
  const opcoes = el('button', { className: 'claro', textContent: 'Trocar o endereço' });
  opcoes.onclick = () => chrome.runtime.openOptionsPage();
  mostrarEstado(
    el('div', { className: 'marca' }, [el('span', { className: 'selo-marca', innerHTML: rostoSvg(32, true) }), el('b', { textContent: 'StoneFalcon' })]),
    el('h1', { textContent: 'Seu copiloto, em qualquer página' }),
    el('ul', { className: 'passos' }, [
      el('li', { textContent: 'Selecione um texto na página.' }),
      el('li', { textContent: 'Clique em “Perguntar ao StoneFalcon”.' }),
      el('li', { textContent: 'O agente certo é sugerido e os campos já vêm preenchidos.' }),
    ]),
    el('p', { className: 'nota', textContent: 'Dados pessoais são mascarados antes de qualquer modelo ver. Tudo roda na plataforma, com as permissões do seu perfil.' }),
    el('p', {}, [botao, opcoes]),
  );
}

// ---------------------------------------------------------------- sem conexão
function semConexao(r) {
  const tentar = el('button', { textContent: 'Tentar de novo' });
  tentar.onclick = abrir;
  const opcoes = el('button', { className: 'claro', textContent: 'Trocar o endereço' });
  opcoes.onclick = () => chrome.runtime.openOptionsPage();
  const endereco_ = el('code', { textContent: endereco });
  mostrarEstado(
    el('h1', { textContent: 'Não consegui conectar' }),
    el('p', { className: 'erro', textContent: r.mensagem }),
    el('p', { textContent: r.dica }),
    el('p', {}, ['Endereço configurado: ', endereco_]),
    el('p', {}, [tentar, opcoes]),
  );
}

async function abrir() {
  pronto = false;
  mostrarEstado(el('h1', { textContent: 'Conectando ao StoneFalcon…' }), el('div', { className: 'carregando', ariaHidden: 'true' }));
  const guardado = await chrome.storage.local.get(['visto']);
  endereco = await sfEndereco();
  if (!guardado.visto) { boasVindas(); return; }
  const r = await sfTestar(endereco);
  if (!r.ok) { semConexao(r); return; }
  origem = new URL(endereco).origin;
  const aviso = (await chrome.storage.session.get('atalhoErro')).atalhoErro;   // o menu do botão direito não conseguiu abrir o Estúdio
  if (aviso && Date.now() - aviso.quando < 15000) { chrome.storage.session.remove('atalhoErro'); semConexao(aviso); return; }
  const dados = await chrome.storage.session.get('trecho');
  const trecho = dados.trecho && Date.now() - dados.trecho.quando < 15000 ? dados.trecho : null;
  if (trecho) chrome.storage.session.remove('trecho');
  const perfil = await sfPerfil();
  // o texto selecionado NUNCA vai no endereço (apareceria nos logs do servidor, sem máscara): vai por mensagem
  pendente = trecho && trecho.texto ? trecho : null;
  quadro.src = endereco + '/extensao' + (perfil ? '?perfil=' + encodeURIComponent(perfil) : '');
  estado.hidden = true;
  quadro.hidden = false;
}

// a fonte vem da tela (iframe): só vale se for mesmo uma planilha reconhecida pela extensão
function fonteValida(f) {
  return f && f.tipo === 'planilha' ? sfFontePlanilha(String(f.url || ''), String(f.titulo || ''), endereco) : null;
}

// Aba ativa é uma planilha? Avisa a tela do painel, que mostra "Criar Agente de IA a partir desta planilha".
async function avisarPlanilha() {
  if (!pronto) return;
  let fonte = null;
  try {
    const [aba] = await chrome.tabs.query({ active: true, currentWindow: true });
    fonte = aba ? sfFontePlanilha(aba.url, aba.title, endereco) : null;
  } catch (e) { /* sem acesso à aba: sem atalho de planilha */ }
  quadro.contentWindow.postMessage({ origem: 'stonefalcon-extensao', planilha: fonte }, origem);
}
chrome.tabs.onActivated.addListener(avisarPlanilha);
chrome.tabs.onUpdated.addListener((id, mudou) => { if (mudou.url || mudou.title || mudou.status === 'complete') avisarPlanilha(); });

function enviar(trecho) {
  quadro.contentWindow.postMessage({ origem: 'stonefalcon-extensao', trecho: trecho.texto, agente: trecho.agente || '' }, origem);
}

// novo trecho selecionado com o painel já aberto
chrome.storage.session.onChanged.addListener((mudancas) => {
  if (mudancas.atalhoErro && mudancas.atalhoErro.newValue) { abrir(); return; }
  const novo = mudancas.trecho && mudancas.trecho.newValue;
  if (!novo || !novo.texto) return;
  if (pronto) { enviar(novo); chrome.storage.session.remove('trecho'); }
  else pendente = novo;
});

// a plataforma avisa quem está logado (para o menu de agentes do botão direito)
window.addEventListener('message', (ev) => {
  if (!origem || ev.origin !== origem || ev.source !== quadro.contentWindow) return;
  const d = ev.data;
  if (d && d.origem === 'stonefalcon-plataforma' && d.tipo === 'pronto') {   // a tela registrou o ouvinte de mensagens
    pronto = true;
    avisarPlanilha();
    if (pendente) { enviar(pendente); pendente = null; }
  }
  if (d && d.origem === 'stonefalcon-plataforma' && d.tipo === 'criar-agente') {   // botão "Criar Agente de IA" do painel
    sfCriarAgente(typeof d.trecho === 'string' ? d.trecho : '', fonteValida(d.fonte)).then((r) => { if (!r.ok) semConexao(r); });
  }
  if (d && d.origem === 'stonefalcon-plataforma' && d.tipo === 'perfil' && typeof d.perfil === 'string' && /^[a-z]{3,20}$/.test(d.perfil)) {
    chrome.storage.local.set({ perfil: d.perfil });
  }
});

// o endereço foi trocado nas opções
chrome.storage.local.onChanged.addListener((mudancas) => { if (mudancas.servidor) abrir(); });

abrir();
