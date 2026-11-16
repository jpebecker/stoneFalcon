// Endereço da plataforma StoneFalcon. No computador: http://localhost:8765.
// Hospedada: o endereço público do projeto.
const SF_PADRAO = 'http://localhost:8765';

async function sfEndereco() {
  const d = await chrome.storage.local.get('servidor');
  return (d.servidor || SF_PADRAO).replace(/\/+$/, '');
}

async function sfTestar(endereco) {
  const controle = new AbortController();
  const relogio = setTimeout(() => controle.abort(), 6000);
  try {
    const resp = await fetch(endereco + '/api/v1/saude', { signal: controle.signal });
    const dados = await resp.json();
    return dados && dados.ok ? dados : null;
  } catch (e) {
    return null;
  } finally {
    clearTimeout(relogio);
  }
}
