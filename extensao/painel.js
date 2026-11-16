// StoneFalcon · painel lateral. Mostra a tela de agentes da plataforma (rota /extensao).
// A extensão não tem lógica nem chave: tudo roda na plataforma, com as permissões de quem está logado.
const quadro = document.getElementById('quadro');
const estado = document.getElementById('estado');
let endereco = null, pronto = false;

async function abrir() {
  endereco = await sfEndereco();
  const saude = await sfTestar(endereco);
  if (!saude) {
    pronto = false;
    quadro.hidden = true;
    estado.hidden = false;
    const local = endereco.indexOf('localhost') >= 0 || endereco.indexOf('127.0.0.1') >= 0;
    estado.innerHTML = '<h1>A plataforma StoneFalcon não respondeu</h1>' +
      '<p>Endereço configurado: <code></code></p>' +
      (local ? '<p>Ligue a plataforma no computador: na pasta do projeto, rode <code>iniciar.bat</code> (Windows) ou <code>sh iniciar.sh</code>.</p>'
             : '<p>Confira se o endereço está certo e se o projeto está no ar.</p>') +
      '<p><button id="tentar">Tentar de novo</button><button id="opcoes" class="claro">Trocar o endereço</button></p>';
    estado.querySelector('code').textContent = endereco;
    document.getElementById('tentar').onclick = abrir;
    document.getElementById('opcoes').onclick = () => chrome.runtime.openOptionsPage();
    return;
  }
  const dados = await chrome.storage.session.get('trecho');
  const trecho = dados.trecho && Date.now() - dados.trecho.quando < 15000 ? dados.trecho.texto : '';
  if (trecho) chrome.storage.session.remove('trecho');
  quadro.src = endereco + '/extensao' + (trecho ? '?trecho=' + encodeURIComponent(trecho.slice(0, 1500)) : '');
  quadro.onload = () => {
    pronto = true;
    if (trecho.length > 1500) enviarTrecho(trecho);   // trechos longos vão por mensagem, não pelo endereço
  };
  estado.hidden = true;
  quadro.hidden = false;
}

function enviarTrecho(texto) {
  quadro.contentWindow.postMessage({ origem: 'stonefalcon-extensao', trecho: texto }, new URL(endereco).origin);
}

// novo trecho selecionado com o painel já aberto
chrome.storage.session.onChanged.addListener((mudancas) => {
  const novo = mudancas.trecho && mudancas.trecho.newValue;
  if (!novo || !novo.texto) return;
  if (pronto) { enviarTrecho(novo.texto); chrome.storage.session.remove('trecho'); }
});

// o endereço foi trocado nas opções
chrome.storage.local.onChanged.addListener((mudancas) => { if (mudancas.servidor) abrir(); });

abrir();
