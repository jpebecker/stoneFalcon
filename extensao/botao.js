// StoneFalcon · botão flutuante colocado nas páginas.
(function () {
  if (window.top !== window || document.getElementById('stonefalcon-botao')) return;
  // não aparece dentro do próprio app do StoneFalcon
  if (document.title === 'StoneFalcon' && document.getElementById('raiz')) return;

  const botao = document.createElement('button');
  botao.id = 'stonefalcon-botao';
  botao.type = 'button';
  botao.title = 'Abrir o StoneFalcon (leva junto o texto selecionado)';
  botao.setAttribute('aria-label', 'Abrir o StoneFalcon');
  botao.innerHTML = '<svg viewBox="0 0 40 40" width="26" height="26" aria-hidden="true">' +
    '<path fill="#1FB37A" d="M6 8h28l-3.5 8h-21z"/><path fill="#E8F3EE" d="M11 18.5h18l-3 7H14z"/><path fill="#E0428F" d="M15.2 28h9.6L20 35z"/></svg>';
  botao.addEventListener('click', () => {
    const trecho = String(window.getSelection ? window.getSelection() : '').trim();
    try {
      chrome.runtime.sendMessage({ tipo: 'sf-abrir', trecho: trecho });
    } catch (e) {
      // a extensão foi recarregada: a página precisa ser atualizada para o botão voltar a funcionar
      botao.title = 'Atualize a página para usar o StoneFalcon de novo';
    }
  });
  document.documentElement.appendChild(botao);
})();
