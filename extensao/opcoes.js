const campo = document.getElementById('servidor');
const resultado = document.getElementById('resultado');

sfEndereco().then((e) => { campo.value = e; });

async function salvar(endereco) {
  endereco = (endereco || '').trim().replace(/\/+$/, '');
  if (!/^https?:\/\//.test(endereco)) { resultado.textContent = 'O endereço precisa começar com http:// ou https://'; return; }
  resultado.textContent = 'Testando…';
  const saude = await sfTestar(endereco);
  await chrome.storage.local.set({ servidor: endereco });
  campo.value = endereco;
  resultado.textContent = saude
    ? 'Endereço salvo. Servidor encontrado, em modo ' + (saude.modo === 'real' ? 'de modelos reais.' : 'simulado.')
    : 'Endereço salvo, mas o servidor não respondeu agora. Confira se ele está ligado.';
}

document.getElementById('form').addEventListener('submit', (ev) => { ev.preventDefault(); salvar(campo.value); });
document.getElementById('local').addEventListener('click', () => salvar(SF_PADRAO));
