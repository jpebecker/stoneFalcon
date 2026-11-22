// StoneFalcon · botão que aparece nas páginas só quando há texto selecionado.
// Vive num shadow DOM, então o estilo da página não o desfigura (nem o contrário).
(function () {
  if (window.top !== window || document.getElementById('stonefalcon-botao')) return;
  // não aparece dentro do próprio app do StoneFalcon
  if (document.title === 'StoneFalcon' && document.getElementById('raiz')) return;

  const hospedeiro = document.createElement('div');
  hospedeiro.id = 'stonefalcon-botao';
  hospedeiro.style.cssText = 'all:initial;position:absolute;z-index:2147483600;display:none;';
  const raiz = hospedeiro.attachShadow({ mode: 'closed' });
  raiz.innerHTML =
    '<style>' +
    'button{all:initial;display:inline-flex;align-items:center;gap:8px;box-sizing:border-box;cursor:pointer;' +
    'font:600 13px/1 "Segoe UI",system-ui,sans-serif;color:#E8F3EE;background:#10201A;border:1px solid #2D3F37;' +
    'border-radius:10px;padding:8px 12px 8px 8px;box-shadow:0 6px 18px rgba(16,32,26,.35);transition:transform .12s ease}' +
    'button:hover{transform:translateY(-1px);background:#16302A}' +
    'button:focus-visible{outline:3px solid #1FB37A;outline-offset:2px}' +
    '@media (prefers-reduced-motion:reduce){button{transition:none}}' +
    '</style>' +
    '<button type="button" aria-label="Perguntar ao StoneFalcon sobre o texto selecionado">' +
    rostoSvg(22, true) + '<span>Perguntar ao StoneFalcon</span></button>';
  const botao = raiz.querySelector('button');
  document.documentElement.appendChild(hospedeiro);

  let trecho = '';
  function selecao() {
    const s = window.getSelection ? window.getSelection() : null;
    return s ? String(s).trim() : '';
  }
  function posicionar() {
    const s = window.getSelection();
    trecho = selecao();
    if (!trecho || !s.rangeCount) { hospedeiro.style.display = 'none'; return; }
    const r = s.getRangeAt(0).getBoundingClientRect();
    if (!r.width && !r.height) { hospedeiro.style.display = 'none'; return; }
    hospedeiro.style.display = 'block';
    const largura = 220;
    const esquerda = Math.min(window.scrollX + r.right - largura + 40, window.scrollX + document.documentElement.clientWidth - largura - 12);
    hospedeiro.style.left = Math.max(window.scrollX + 8, esquerda) + 'px';
    hospedeiro.style.top = (window.scrollY + r.bottom + 8) + 'px';
  }
  let espera = null;
  function agendar() { clearTimeout(espera); espera = setTimeout(posicionar, 80); }
  document.addEventListener('selectionchange', agendar);
  document.addEventListener('mouseup', agendar);
  document.addEventListener('keyup', agendar);

  // mouse down no botão não pode desfazer a seleção antes do clique
  botao.addEventListener('mousedown', (e) => e.preventDefault());
  botao.addEventListener('click', () => {
    const texto = trecho || selecao();
    try {
      chrome.runtime.sendMessage({ tipo: 'sf-abrir', trecho: texto });
      hospedeiro.style.display = 'none';
    } catch (e) {
      // a extensão foi recarregada: a página precisa ser atualizada para o botão voltar a funcionar
      botao.querySelector('span').textContent = 'Atualize a página para usar de novo';
    }
  });
})();
