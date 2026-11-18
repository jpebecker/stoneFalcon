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

// Atalho "Criar Agente de IA": pede à plataforma um passe de uso único (60 s) para o perfil desta extensão e abre o
// Estúdio numa aba nova. Nem o perfil nem o texto selecionado vão no endereço: o texto vai no corpo do pedido.
// Devolve { ok: true } ou { ok: false, tipo, mensagem, dica } (o mesmo formato de sfTestar).
// Planilha aberta na aba? O Google Sheets desenha a grade sem texto selecionável comum, então o menu do botão direito não
// recebe as células: a extensão lê só o ENDEREÇO da aba (nunca o conteúdo) e a plataforma importa a versão publicada na web.
// Devolve { tipo: 'planilha', url, titulo } ou null.
function sfFontePlanilha(url, titulo, endereco) {
  if (!url) return null;
  try {
    const u = new URL(url);
    const google = u.protocol === 'https:' && u.hostname === 'docs.google.com' && u.pathname.startsWith('/spreadsheets/d/');
    const local = u.origin === new URL(endereco).origin && u.pathname.replace(/\/+$/, '') === '/demo/planilha';
    if (google || local) return { tipo: 'planilha', url: u.origin + u.pathname + u.search, titulo: (titulo || '').slice(0, 120) };
  } catch (e) { /* endereço inválido: não é planilha */ }
  return null;
}

async function sfCriarAgente(trecho, fonte) {
  const endereco = await sfEndereco();
  const teste = await sfTestar(endereco);                    // servidor desligado, endereço errado, demora: mesmo diagnóstico do painel
  if (!teste.ok) return teste;
  const perfil = await sfPerfil();
  if (!perfil) {
    return { ok: false, tipo: 'perfil', mensagem: 'Você ainda não escolheu o seu perfil.', dica: 'Abra o painel do StoneFalcon, entre com o seu perfil e tente de novo.' };
  }
  let resp;
  try {
    resp = await fetch(endereco + '/api/v1/extensao/passe', {
      method: 'POST', headers: { 'Content-Type': 'application/json', 'X-Usuario': perfil },
      body: JSON.stringify({ trecho: (trecho || '').slice(0, 8000), fonte: fonte || null }),
    });
  } catch (e) {
    return { ok: false, tipo: 'recusou', mensagem: 'Não consegui falar com a plataforma.', dica: 'Confira se ela continua ligada e tente de novo.' };
  }
  if (resp.status === 403) {
    return { ok: false, tipo: 'sem_estudio', mensagem: 'Seu perfil não cria agentes.', dica: 'Só quem tem o Estúdio cria agentes. O Início da plataforma continua disponível.' };
  }
  if (!resp.ok) {
    return { ok: false, tipo: 'http', mensagem: 'A plataforma respondeu com erro ' + resp.status + '.', dica: 'Tente de novo em instantes.' };
  }
  const dados = await resp.json();
  await chrome.tabs.create({ url: endereco + '/via-extensao?passe=' + encodeURIComponent(dados.passe) });
  return { ok: true };
}
