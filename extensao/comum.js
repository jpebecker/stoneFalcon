// StoneFalcon · peças comuns da extensão.
// Endereço da plataforma: no computador, http://localhost:8765; hospedada, o endereço público do projeto.
const SF_PADRAO = 'http://localhost:8765';

async function sfEndereco() {
  const d = await chrome.storage.local.get('servidor');
  return (d.servidor || SF_PADRAO).replace(/\/+$/, '');
}

async function sfPerfil() {
  const d = await chrome.storage.local.get('perfil');
  return d.perfil || '';
}

// Testa a conexão e diz, em português, o que deu errado.
// Devolve { ok: true, dados } ou { ok: false, tipo, mensagem, dica }.
async function sfTestar(endereco) {
  let url;
  try {
    url = new URL(endereco);
  } catch (e) {
    return { ok: false, tipo: 'endereco', mensagem: 'O endereço não é válido.', dica: 'Comece por http:// ou https://, por exemplo http://localhost:8765.' };
  }
  const controle = new AbortController();
  const relogio = setTimeout(() => controle.abort(), 6000);
  try {
    const resp = await fetch(endereco + '/api/v1/saude', { signal: controle.signal });
    if (!resp.ok) {
      return { ok: false, tipo: 'http', mensagem: 'O servidor respondeu com erro ' + resp.status + '.', dica: 'Confira se o endereço é mesmo o do StoneFalcon.' };
    }
    let dados = null;
    try { dados = await resp.json(); } catch (e) { /* tratado abaixo */ }
    if (!dados || !dados.ok) {
      return { ok: false, tipo: 'outro', mensagem: 'Esse endereço responde, mas não parece ser o StoneFalcon.', dica: 'Confira a porta e o endereço.' };
    }
    return { ok: true, dados: dados };
  } catch (e) {
    if (e && e.name === 'AbortError') {
      return { ok: false, tipo: 'tempo', mensagem: 'O servidor demorou demais para responder.', dica: 'Ele pode estar iniciando. Espere alguns segundos e tente de novo.' };
    }
    const local = url.hostname === 'localhost' || url.hostname === '127.0.0.1';
    return {
      ok: false, tipo: 'recusou',
      mensagem: 'Não consegui falar com ' + url.host + '.',
      dica: local ? 'A plataforma não está ligada neste computador. Rode iniciar.bat (Windows) ou sh iniciar.sh na pasta do projeto.'
                  : 'Confira o endereço, a internet e se o projeto está no ar.',
    };
  } finally {
    clearTimeout(relogio);
  }
}
