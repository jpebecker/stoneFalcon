const campo = document.getElementById('servidor');
const resultado = document.getElementById('resultado');
const dica = document.getElementById('dica');
const perfil = document.getElementById('perfil');

sfEndereco().then((e) => { campo.value = e; });

function mostrarPerfil() {
  sfPerfil().then((p) => {
    perfil.textContent = '';
    if (!p) { perfil.textContent = 'Perfil: ainda não escolhido (escolha no painel lateral).'; return; }
    perfil.appendChild(document.createTextNode('Perfil atual: ' + p + '. '));
    const esquecer = document.createElement('button');
    esquecer.type = 'button'; esquecer.className = 'claro'; esquecer.textContent = 'Esquecer o perfil';
    esquecer.onclick = () => chrome.storage.local.remove('perfil').then(mostrarPerfil);
    perfil.appendChild(esquecer);
  });
}
mostrarPerfil();

async function salvar(endereco) {
  endereco = (endereco || '').trim().replace(/\/+$/, '');
  resultado.className = ''; dica.textContent = '';
  if (!/^https?:\/\//.test(endereco)) {
    resultado.className = 'erro'; resultado.textContent = 'O endereço precisa começar com http:// ou https://'; return;
  }
  resultado.textContent = 'Testando…';
  const r = await sfTestar(endereco);
  await chrome.storage.local.set({ servidor: endereco });
  campo.value = endereco;
  if (r.ok) {
    resultado.className = 'ok';
    resultado.textContent = 'Conectado. Servidor em modo ' + (r.dados.modo === 'real' ? 'de modelos reais.' : 'simulado.');
  } else {
    resultado.className = 'erro';
    resultado.textContent = 'Endereço salvo, mas: ' + r.mensagem;
    dica.textContent = r.dica;
  }
}

document.getElementById('form').addEventListener('submit', (ev) => { ev.preventDefault(); salvar(campo.value); });
document.getElementById('local').addEventListener('click', () => salvar(SF_PADRAO));
