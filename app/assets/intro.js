(() => {
  const HTML = __HTML__;
  const FRAG = __FRAG__;
  const VER = '__VER__';

  const win = window.parent;
  const doc = win.document;

  const prev = win.__eur;
  if (prev && prev.ver === VER && prev.mode === 'tool') return;
  if (prev && prev.destroy) prev.destroy();

  const reduce = win.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const S = { ver: VER, mode: 'intro' };
  win.__eur = S;

  const canvas = doc.createElement('canvas');
  canvas.className = 'eur-bg';
  doc.body.prepend(canvas);

  const root = doc.createElement('div');
  root.className = 'eur-intro is-locked';
  root.innerHTML = HTML;
  doc.body.append(root);

  // el loader queda por encima de todo durante el arranque
  const loader = doc.querySelector('.loader');
  if (loader) doc.body.append(loader);

  const secA = root.querySelector('#sec-a');

  // contexto webgl a resolucion nativa para que el grano sea muy fino
  const gl = canvas.getContext('webgl', { antialias: true, alpha: false, powerPreference: 'high-performance' });
  const loc = {};
  if (gl) {
    const shader = (type, src) => {
      const s = gl.createShader(type);
      gl.shaderSource(s, src);
      gl.compileShader(s);
      return s;
    };
    const prog = gl.createProgram();
    gl.attachShader(prog, shader(gl.VERTEX_SHADER, 'attribute vec2 p;void main(){gl_Position=vec4(p,0.,1.);}'));
    gl.attachShader(prog, shader(gl.FRAGMENT_SHADER, FRAG));
    gl.linkProgram(prog);
    gl.useProgram(prog);
    const buf = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, buf);
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 3, -1, -1, 3]), gl.STATIC_DRAW);
    const pl = gl.getAttribLocation(prog, 'p');
    gl.enableVertexAttribArray(pl);
    gl.vertexAttribPointer(pl, 2, gl.FLOAT, false, 0, 0);
    ['uRes', 'uT', 'uP', 'uCalm', 'uMotion'].forEach((n) => { loc[n] = gl.getUniformLocation(prog, n); });
  }

  function measureToolGeometry() {
    const titleEl = doc.querySelector('.title');
    const titleWrap = titleEl ? titleEl.parentElement : null;
    const ehabEl = doc.querySelector('.title .t-ehab');
    const panelEl = doc.querySelector('.panel-lateral');
    const panelWrap = panelEl ? panelEl.parentElement : null;
    const rootStyle = doc.documentElement.style;

    if (titleEl && titleWrap) {
      const tRect = titleWrap.getBoundingClientRect();
      const tLeft = tRect.left;
      const tTop = tRect.top;
      const tHeight = titleEl.offsetHeight || 160;
      const scale = Math.min(0.48, Math.max(0.28, 76 / tHeight));
      rootStyle.setProperty('--title-tx', Math.round(20 - tLeft) + 'px');
      rootStyle.setProperty('--title-ty', Math.round(20 - tTop) + 'px');
      rootStyle.setProperty('--title-scale', scale.toFixed(4));
    }

    if (ehabEl) {
      const ehabW = ehabEl.offsetWidth;
      if (ehabW > 0) {
        rootStyle.setProperty('--ehab-shift', '-' + Math.round(ehabW - 4) + 'px');
      }
    }

    if (panelEl && panelWrap) {
      const pRect = panelWrap.getBoundingClientRect();
      const pLeft = pRect.left;
      const pTop = pRect.top;
      const fullH = Math.max(380, win.innerHeight - 112 - 18);
      const offH = Math.min(390, Math.max(310, win.innerHeight - pTop - 24));
      const clipB = Math.max(0, fullH - offH);

      rootStyle.setProperty('--panel-full-h', Math.round(fullH) + 'px');
      rootStyle.setProperty('--panel-clip-b', Math.round(clipB) + 'px');
      rootStyle.setProperty('--panel-tx', Math.round(20 - pLeft) + 'px');
      rootStyle.setProperty('--panel-ty', Math.round(112 - pTop) + 'px');

      const webrtcTop = Math.max(320, Math.min(Math.round(pTop), win.innerHeight - 80));
      rootStyle.setProperty('--webrtc-off-top', webrtcTop + 'px');
    }
  }

  function resize() {
    const dpr = Math.min(win.devicePixelRatio || 1, 2);
    canvas.width = Math.max(2, Math.floor(win.innerWidth * dpr));
    canvas.height = Math.max(2, Math.floor(win.innerHeight * dpr));
    if (gl) gl.viewport(0, 0, canvas.width, canvas.height);
    fit();
    measureToolGeometry();
  }

  // ajustamos la palabra del hero al ancho completo entre margenes
  function fit() {
    const words = root.querySelectorAll('.hero-word .w');
    const pad = parseFloat(win.getComputedStyle(root).getPropertyValue('--pad')) || 32;
    words[0].style.fontSize = '100px';
    const w = words[0].getBoundingClientRect().width;
    if (!w) return;
    const size = 100 * (win.innerWidth - pad * 2 + 8) / w;
    words.forEach((el) => { el.style.fontSize = size + 'px'; });
  }

  // progresion continua de 0 a 2 a lo largo de todo el recorrido del scroll
  function pFor(y) {
    const maxScroll = Math.max(1, root.scrollHeight - root.clientHeight);
    return Math.min(2, Math.max(0, (y / maxScroll) * 2));
  }

  let P = 0;
  let calm = 0;
  let tween = null;
  let last = performance.now();
  const t0 = last;
  const ease = (x) => (x < 0.5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2);

  const fallback = [[238, 32, 20], [40, 90, 160], [210, 70, 30]];
  function paintFallback() {
    const i = Math.min(1, Math.floor(P));
    const f = P - i;
    const c = fallback[i].map((v, k) => Math.round(v + (fallback[Math.min(2, i + 1)][k] - v) * f));
    canvas.style.background = 'rgb(' + c.join(',') + ')';
  }

  function frame(now) {
    S.raf = win.requestAnimationFrame(frame);
    const dt = Math.min(0.05, (now - last) / 1000);
    last = now;

    if (tween) {
      const k = Math.min(1, (now - tween.start) / tween.dur);
      P = tween.from + (tween.to - tween.from) * ease(k);
      if (k >= 1) {
        tween = null;
        reveal();
      }
    } else if (S.mode === 'intro') {
      P += (pFor(root.scrollTop) - P) * (1 - Math.exp(-dt * 4.2));
    } else {
      P += (2 - P) * (1 - Math.exp(-dt * 4.2));
    }
    const calmTo = S.mode === 'tool' || S.mode === 'leaving' ? 1 : 0;
    calm += (calmTo - calm) * (1 - Math.exp(-dt * 2));

    if (gl) {
      gl.uniform2f(loc.uRes, canvas.width, canvas.height);
      gl.uniform1f(loc.uT, (now - t0) / 1000);
      gl.uniform1f(loc.uP, P);
      gl.uniform1f(loc.uCalm, calm);
      gl.uniform1f(loc.uMotion, reduce ? 0 : 1);
      gl.drawArrays(gl.TRIANGLES, 0, 3);
    } else {
      paintFallback();
    }
  }

  const io = new win.IntersectionObserver((entries) => {
    entries.forEach((e) => { if (e.isIntersecting) e.target.classList.add('in'); });
  }, { root, threshold: 0.15 });
  root.querySelectorAll('.rv-i').forEach((el) => io.observe(el));

  function onScroll() {
    root.classList.toggle('is-scrolled', root.scrollTop > 40);
  }

  function goTool() {
    if (S.mode !== 'intro') return;
    if (P > 1.95) {
      reveal();
      return;
    }
    S.mode = 'skipping';
    root.classList.add('is-skipping', 'is-locked');
    const dur = reduce ? 1 : 2600 * Math.max(0.35, (2 - P) / 2);
    tween = { from: P, to: 2, start: performance.now(), dur };
  }

  function reveal() {
    S.mode = 'leaving';
    root.classList.add('is-leaving');
    doc.body.classList.add('eur-tool');
    measureToolGeometry();
    win.setTimeout(() => {
      root.classList.add('is-gone');
      S.mode = 'tool';
      measureToolGeometry();
    }, 1100);
  }

  function openTutorial() {
    if (S.mode !== 'tool') return;
    doc.body.classList.remove('eur-tool');
    root.classList.remove('is-gone', 'is-skipping', 'is-locked');
    void root.offsetWidth;
    root.classList.remove('is-leaving');
    root.scrollTop = 0;
    S.mode = 'intro';
  }

  function copyText(text) {
    return new Promise((resolve) => {
      const fallback = () => {
        try {
          const ta = doc.createElement('textarea');
          ta.value = text;
          ta.style.position = 'fixed';
          ta.style.opacity = '0';
          doc.body.appendChild(ta);
          ta.focus();
          ta.select();
          doc.execCommand('copy');
          ta.remove();
        } catch (e) {}
        resolve();
      };
      if (win.navigator && win.navigator.clipboard && win.navigator.clipboard.writeText) {
        win.navigator.clipboard.writeText(text).then(resolve).catch(fallback);
      } else {
        fallback();
      }
    });
  }

  function onClick(e) {
    const el = e.target.closest && e.target.closest('[data-act]');
    if (!el) return;
    const act = el.getAttribute('data-act');
    if (act === 'tutorial') root.scrollTo({ top: secA.offsetTop, behavior: reduce ? 'auto' : 'smooth' });
    else if (act === 'tool') goTool();
    else if (act === 'open-tutorial') openTutorial();
    else if (act === 'copy') {
      const cmd = el.getAttribute('data-cmd');
      if (cmd) {
        copyText(cmd).then(() => {
          el.classList.add('is-copied');
          const tag = el.querySelector('.lib-status');
          if (tag) tag.textContent = 'Copiado';
          win.setTimeout(() => {
            el.classList.remove('is-copied');
            if (tag) tag.textContent = 'Copiar';
          }, 1800);
        }).catch(() => {});
      }
    }
  }

  function setupWebRtcEnhancer() {
    function injectIntoIframe(ifr) {
      if (!ifr) return false;
      let d = null;
      try { d = ifr.contentDocument || ifr.contentWindow?.document; } catch (e) { return false; }
      if (!d || !d.body) return false;
      if (d.__webrtc_enhanced) return true;
      d.__webrtc_enhanced = true;

      const s = d.createElement('style');
      s.textContent = `
        html, body {
          background: transparent !important;
          margin: 0 !important;
          padding: 0 !important;
          overflow: hidden !important;
          scrollbar-width: none !important;
          -ms-overflow-style: none !important;
          border: 0 !important;
          outline: 0 !important;
          color: #f3f0e8 !important;
        }
        html::-webkit-scrollbar,
        body::-webkit-scrollbar,
        *::-webkit-scrollbar {
          display: none !important;
          width: 0 !important;
          height: 0 !important;
        }
        /* Cuando esta apagada: ocultar por completo el recuadro negro y el icono de video muerto */
        body:not(.is-streaming):not(.is-closing-stream) .css-1neg7ek,
        body:not(.is-streaming):not(.is-closing-stream) .MuiPaper-root,
        body:not(.is-streaming):not(.is-closing-stream) svg[data-testid="VideoLabelIcon"] {
          display: none !important;
          height: 0 !important;
          margin: 0 !important;
          padding: 0 !important;
        }
        body:not(.is-streaming):not(.is-closing-stream) #root,
        body:not(.is-streaming):not(.is-closing-stream) .css-0 {
          display: flex !important;
          justify-content: flex-start !important;
          align-items: center !important;
          background: transparent !important;
          margin: 0 !important;
          padding: 0 !important;
          width: 100% !important;
          height: 100% !important;
        }
        body:not(.is-streaming):not(.is-closing-stream) .css-gg4vpm {
          position: relative !important;
          width: 296px !important;
          height: 96px !important;
          display: flex !important;
          align-items: center !important;
          justify-content: flex-start !important;
          padding: 0 !important;
          margin: 0 !important;
          border: 0 !important;
          outline: 0 !important;
          box-shadow: none !important;
          background: transparent !important;
        }

        /* Boton SELECT DEVICE: forma de gota organica que rodea al boton circular con mayor grosor abajo */
        body:not(.is-streaming):not(.is-closing-stream) .css-gg4vpm button.MuiButton-colorInherit,
        body:not(.is-streaming):not(.is-closing-stream) .css-gg4vpm button.MuiButton-textInherit {
          position: absolute !important;
          inset: 0 !important;
          width: 100% !important;
          height: 100% !important;
          margin: 0 !important;
          z-index: 1 !important;
          background: #0d0d14 !important;
          border: 1.5px solid rgba(243, 240, 232, 0.26) !important;
          border-radius: 48px 24px 36px 54px / 48px 20px 48px 52px !important;
          display: flex !important;
          flex-direction: column !important;
          justify-content: flex-end !important;
          align-items: flex-end !important;
          padding: 0 24px 16px 86px !important;
          cursor: pointer !important;
          box-sizing: border-box !important;
          overflow: hidden !important;
          font-family: "Geo", ui-monospace, monospace !important;
          font-size: 13px !important;
          letter-spacing: .12em !important;
          text-transform: uppercase !important;
          color: #f3f0e8 !important;
        }
        body:not(.is-streaming):not(.is-closing-stream) .css-gg4vpm button.MuiButton-colorInherit::before {
          content: "DISPOSITIVO //";
          display: block !important;
          font-family: "Geo", ui-monospace, monospace !important;
          font-size: 10px !important;
          letter-spacing: .16em !important;
          color: rgba(243, 240, 232, 0.45) !important;
          margin-bottom: 2px !important;
          pointer-events: none !important;
        }
        body:not(.is-streaming):not(.is-closing-stream) .css-gg4vpm button.MuiButton-colorInherit:hover {
          background: #14141e !important;
          border-color: rgba(243, 240, 232, 0.6) !important;
        }
        body:not(.is-streaming):not(.is-closing-stream) .css-gg4vpm button.MuiButton-colorInherit:focus-visible {
          outline: 2px solid #f3f0e8 !important;
          outline-offset: 3px !important;
        }

        /* Boton START: circular rojo situado a la izquierda dentro de la gota */
        body:not(.is-streaming):not(.is-closing-stream) .css-gg4vpm button.MuiButton-containedPrimary {
          position: absolute !important;
          left: 14px !important;
          top: 14px !important;
          width: 58px !important;
          height: 58px !important;
          min-width: 58px !important;
          min-height: 58px !important;
          border-radius: 50% !important;
          background: #ff2314 !important;
          border: 2px solid #ff2314 !important;
          color: #f3f0e8 !important;
          font-family: "Geo", ui-monospace, monospace !important;
          font-size: 13px !important;
          font-weight: 700 !important;
          letter-spacing: .12em !important;
          text-transform: uppercase !important;
          padding: 0 !important;
          margin: 0 !important;
          display: flex !important;
          align-items: center !important;
          justify-content: center !important;
          z-index: 10 !important;
          box-shadow: 0 0 0 3.5px #0d0d14, 0 0 0 5px rgba(243, 240, 232, 0.22) !important;
          cursor: pointer !important;
        }
        body:not(.is-streaming):not(.is-closing-stream) .css-gg4vpm button.MuiButton-containedPrimary:hover {
          background: #e01b0d !important;
          border-color: #e01b0d !important;
        }
        body:not(.is-streaming):not(.is-closing-stream) .css-gg4vpm button.MuiButton-containedPrimary:focus-visible {
          outline: 2px solid #f3f0e8 !important;
          outline-offset: 3px !important;
        }

        /* Menu de seleccion de dispositivo: acorde a la forma de la gota y diseno de la web */
        #root > .css-ikzlcq {
          background: #0d0d14 !important;
          border: 1.5px solid rgba(243, 240, 232, 0.28) !important;
          border-radius: 36px 20px 32px 46px / 32px 18px 40px 48px !important;
          padding: 24px !important;
          box-sizing: border-box !important;
          color: #f3f0e8 !important;
          font-family: "Geo", ui-monospace, monospace !important;
          display: flex !important;
          flex-direction: column !important;
          gap: 18px !important;
          width: 100% !important;
          max-width: 520px !important;
          margin: 0 !important;
          box-shadow: 0 16px 40px rgba(0, 0, 0, 0.7) !important;
        }
        #root > .css-ikzlcq::before {
          content: "CONFIGURACIÓN DE DISPOSITIVOS";
          display: block !important;
          font-family: "Geo", ui-monospace, monospace !important;
          font-size: 11px !important;
          letter-spacing: .16em !important;
          text-transform: uppercase !important;
          color: #ff2314 !important;
          padding-bottom: 8px !important;
          border-bottom: 1px solid rgba(243, 240, 232, 0.15) !important;
        }
        #root > .css-ikzlcq > .css-ikzlcq {
          display: flex !important;
          flex-direction: row !important;
          align-items: flex-start !important;
          gap: 18px !important;
          background: transparent !important;
          border: 0 !important;
          padding: 0 !important;
          margin: 0 !important;
          box-shadow: none !important;
        }
        .css-b6x1oe {
          width: 170px !important;
          height: 125px !important;
          background: #000000 !important;
          border: 1px solid rgba(243, 240, 232, 0.2) !important;
          border-radius: 10px !important;
          overflow: hidden !important;
          flex: 0 0 170px !important;
          display: flex !important;
          align-items: center !important;
          justify-content: center !important;
        }
        .css-b6x1oe video {
          width: 100% !important;
          height: 100% !important;
          object-fit: cover !important;
          background: #000000 !important;
        }
        .css-xoj6fk {
          flex: 1 1 auto !important;
          display: flex !important;
          flex-direction: column !important;
          gap: 14px !important;
        }
        .css-ikzlcq .MuiFormControl-root {
          margin: 0 !important;
          width: 100% !important;
        }
        .css-ikzlcq label,
        .css-ikzlcq .MuiInputLabel-root {
          font-family: "Geo", ui-monospace, monospace !important;
          font-size: 12px !important;
          letter-spacing: .12em !important;
          text-transform: uppercase !important;
          color: rgba(243, 240, 232, 0.7) !important;
          position: static !important;
          transform: none !important;
          margin-bottom: 6px !important;
          display: block !important;
        }
        .css-ikzlcq .MuiInputBase-root {
          background: #14141e !important;
          border: 1px solid rgba(243, 240, 232, 0.28) !important;
          border-radius: 6px !important;
          min-height: 40px !important;
          height: 40px !important;
          position: relative !important;
          box-sizing: border-box !important;
          display: flex !important;
          align-items: center !important;
        }
        .css-ikzlcq .MuiInputBase-root::before,
        .css-ikzlcq .MuiInputBase-root::after {
          display: none !important;
        }
        .css-ikzlcq .MuiInputBase-root:focus-within {
          border-color: #ff2314 !important;
        }
        .css-ikzlcq select,
        .css-ikzlcq .MuiNativeSelect-select,
        .css-ikzlcq .MuiInputBase-input {
          background: transparent !important;
          color: #f3f0e8 !important;
          font-family: "Geo", ui-monospace, monospace !important;
          font-size: 14px !important;
          letter-spacing: .06em !important;
          min-height: 38px !important;
          height: 38px !important;
          line-height: 38px !important;
          padding: 0 34px 0 12px !important;
          border: 0 !important;
          border-radius: 6px !important;
          width: 100% !important;
          box-sizing: border-box !important;
          outline: none !important;
          cursor: pointer !important;
          display: block !important;
        }
        .css-ikzlcq .MuiNativeSelect-icon {
          color: rgba(243, 240, 232, 0.8) !important;
          right: 10px !important;
          top: calc(50% - 12px) !important;
          pointer-events: none !important;
        }
        .css-ikzlcq option {
          background: #0d0d14 !important;
          color: #f3f0e8 !important;
        }
        .css-ikzlcq .MuiPaper-root,
        .css-ikzlcq .MuiAlert-root {
          background: rgba(255, 35, 20, 0.08) !important;
          border: 1px solid rgba(255, 35, 20, 0.35) !important;
          color: #f3f0e8 !important;
          font-family: "Geo", ui-monospace, monospace !important;
          font-size: 13px !important;
          letter-spacing: .06em !important;
          padding: 12px 14px !important;
          border-radius: 6px !important;
        }
        #root > .css-ikzlcq > .MuiBox-root {
          display: flex !important;
          justify-content: flex-end !important;
          width: 100% !important;
          margin-top: 4px !important;
        }
        #root > .css-ikzlcq button.MuiButton-containedPrimary {
          position: static !important;
          width: auto !important;
          height: auto !important;
          min-width: 0 !important;
          min-height: 0 !important;
          border-radius: 18px !important;
          padding: 7px 26px !important;
          background: #ff2314 !important;
          border: 1px solid #ff2314 !important;
          color: #f3f0e8 !important;
          font-family: "Geo", ui-monospace, monospace !important;
          font-size: 13px !important;
          font-weight: 600 !important;
          letter-spacing: .12em !important;
          text-transform: uppercase !important;
          cursor: pointer !important;
          box-shadow: none !important;
        }
        #root > .css-ikzlcq button.MuiButton-containedPrimary:hover {
          background: #e01b0d !important;
          border-color: #e01b0d !important;
        }

        /* Cuando esta activa o cerrando: negro puro sin ningun borde ni delineado */
        body.is-streaming,
        body.is-streaming #root,
        body.is-streaming #root > div,
        body.is-streaming .css-0,
        body.is-closing-stream,
        body.is-closing-stream #root,
        body.is-closing-stream #root > div,
        body.is-closing-stream .css-0 {
          display: flex !important;
          flex-direction: column !important;
          background: #000000 !important;
          width: 100% !important;
          height: 100vh !important;
          margin: 0 !important;
          padding: 0 !important;
          border: 0 !important;
          outline: 0 !important;
          box-shadow: none !important;
        }
        body.is-streaming .css-1neg7ek,
        body.is-streaming .MuiPaper-root,
        body.is-closing-stream .css-1neg7ek,
        body.is-closing-stream .MuiPaper-root {
          display: flex !important;
          align-items: center !important;
          justify-content: center !important;
          background: #000000 !important;
          flex: 1 1 0 !important;
          min-height: 0 !important;
          width: 100% !important;
          height: 100% !important;
          margin: 0 !important;
          padding: 0 !important;
          border: 0 !important;
          outline: 0 !important;
          box-shadow: none !important;
          border-radius: 0 !important;
        }
        body.is-streaming video,
        body.is-closing-stream video {
          display: block !important;
          width: 100% !important;
          height: 100% !important;
          max-height: none !important;
          object-fit: contain !important;
          background: #000000 !important;
          border: 0 !important;
          outline: 0 !important;
          box-shadow: none !important;
        }
        video::-webkit-media-controls,
        video::-webkit-media-controls-enclosure,
        video::-webkit-media-controls-panel {
          display: none !important;
          opacity: 0 !important;
        }
        body.is-streaming .css-gg4vpm,
        body.is-closing-stream .css-gg4vpm {
          display: flex !important;
          justify-content: flex-end !important;
          align-items: center !important;
          gap: 12px !important;
          padding: 12px 24px !important;
          margin: 0 !important;
          background: #000000 !important;
          border: 0 !important;
          outline: 0 !important;
          box-shadow: none !important;
          flex: 0 0 auto !important;
        }
      `;
      d.head.appendChild(s);

      const colWrapper = ifr.closest('[data-testid="column"]') || ifr.parentElement;

      let wasStreaming = false;
      let closeTimer = null;

      function applyStreamingState(isStreaming) {
        if (isStreaming === wasStreaming) return;
        if (isStreaming) {
          if (closeTimer) {
            win.clearTimeout(closeTimer);
            closeTimer = null;
          }
          d.body.classList.remove('is-closing-stream');
          if (colWrapper) colWrapper.classList.remove('cam-closing');
          win.scrollTo({ top: 0, behavior: 'auto' });
          const appView = doc.querySelector('[data-testid="stAppViewContainer"]');
          if (appView) appView.scrollTop = 0;
          measureToolGeometry();
        } else if (wasStreaming && colWrapper) {
          d.body.classList.add('is-closing-stream');
          colWrapper.classList.add('cam-closing');
          closeTimer = win.setTimeout(() => {
            d.body.classList.remove('is-closing-stream');
            colWrapper.classList.remove('cam-closing');
            closeTimer = null;
          }, 850);
        }
        wasStreaming = isStreaming;

        d.body.classList.toggle('is-streaming', isStreaming);
        if (colWrapper) colWrapper.classList.toggle('cam-active', isStreaming);
        doc.body.classList.toggle('rehab-cam-active', isStreaming);

        const statusLabel = doc.querySelector('.panel-status');
        if (statusLabel) {
          statusLabel.textContent = isStreaming ? 'En directo' : 'En espera';
        }
      }

      let pendingStartUntil = 0;

      function updateState() {
        const vid = d.querySelector('video');
        if (vid) {
          if (vid.hasAttribute('controls')) vid.removeAttribute('controls');
          vid.controls = false;
          vid.disablePictureInPicture = true;
        }
        const hasDoneBtn = Array.from(d.querySelectorAll('button')).some((b) => /done/i.test(b.textContent || ''));
        const isDeviceModal = hasDoneBtn || !!d.querySelector('.css-ikzlcq, select, [id*="device-select"]');

        const stopBtn = Array.from(d.querySelectorAll('button')).find((b) => /stop/i.test(b.textContent || ''));
        const isStreaming = !isDeviceModal && (!!stopBtn || (!!vid && !d.querySelector('button.MuiButton-containedPrimary')) || performance.now() < pendingStartUntil);

        ifr.classList.toggle('device-modal-open', isDeviceModal);
        applyStreamingState(isStreaming);
      }

      d.addEventListener('click', (ev) => {
        const btn = ev.target.closest && ev.target.closest('button');
        if (!btn) return;
        const txt = (btn.textContent || '').trim();
        if (/^start$/i.test(txt)) {
          pendingStartUntil = performance.now() + 3000;
          applyStreamingState(true);
        } else if (/^stop$/i.test(txt)) {
          pendingStartUntil = 0;
          applyStreamingState(false);
        } else if (/select device/i.test(txt)) {
          ifr.classList.add('device-modal-open');
        } else if (/done/i.test(txt)) {
          ifr.classList.remove('device-modal-open');
        }
      }, true);

      measureToolGeometry();
      updateState();
      const mo = new d.defaultView.MutationObserver(updateState);
      mo.observe(d.body, { childList: true, subtree: true, characterData: true });

      return true;
    }

    const iv = win.setInterval(() => {
      const ifr = doc.querySelector('iframe[title*="webrtc"]');
      if (ifr) injectIntoIframe(ifr);
    }, 350);

    return () => win.clearInterval(iv);
  }

  // telemetria: lee el nodo oculto que publica app.py y vuelca los datos en el panel
  function setupLiveTelemetry() {
    const txt = (sel, v) => { const el = doc.querySelector(sel); if (el && el.textContent !== v) el.textContent = v; };
    const f = (v, u) => (v === null || v === undefined ? '--' + (u || '') : v + (u || ''));
    const vec = (a) => (a ? a[0].toFixed(2) + ' ' + a[1].toFixed(2) + ' ' + a[2].toFixed(2) : '--');
    let lastRaw = '';
    function tick() {
      const node = doc.querySelector('.eur-live');
      if (!node) return;
      const raw = node.getAttribute('data-json') || '';
      if (raw === lastRaw) return;
      lastRaw = raw;
      let d = null;
      try { d = JSON.parse(raw); } catch (e) { return; }
      if (!d || !d.live) return;
      const slots = doc.querySelectorAll('.panel-lateral .slot-v');
      if (slots.length >= 3) {
        const a = f(d.angulo, '\u00b0');
        const r = f(d.rom, '\u00b0');
        if (slots[0].textContent !== a) slots[0].textContent = a;
        if (slots[1].textContent !== r) slots[1].textContent = r;
        if (slots[2].textContent !== String(d.reps)) slots[2].textContent = String(d.reps);
      }
      const k = (key) => '.panel-live [data-k="' + key + '"]';
      txt(k('fps'), f(d.fps));
      txt(k('lat'), f(d.lat, ' ms'));
      txt(k('res'), d.res || '--');
      txt(k('lado'), d.lado || '--');
      txt(k('fase'), d.fase || '--');
      txt(k('vis'), f(d.vis, '/33'));
      txt(k('v-hombro'), vec(d.vec && d.vec.hombro));
      txt(k('v-codo'), vec(d.vec && d.vec.codo));
      txt(k('v-muneca'), vec(d.vec && d.vec.muneca));
      const log = doc.querySelector(k('log'));
      if (log) {
        const next = (d.log || []).slice().reverse();
        if (log.getAttribute('data-sig') !== next.join('|')) {
          log.setAttribute('data-sig', next.join('|'));
          log.textContent = '';
          next.forEach((line) => {
            const li = doc.createElement('li');
            li.textContent = line;
            log.appendChild(li);
          });
        }
      }
    }
    const iv = win.setInterval(tick, 200);
    return () => win.clearInterval(iv);
  }

  const cleanupEnhancer = setupWebRtcEnhancer();
  const cleanupLive = setupLiveTelemetry();

  const anim = loader && loader.getAnimations
    ? loader.getAnimations().find((a) => a.animationName === 'loader-out')
    : null;
  const wait = anim ? Math.max(0, 4300 - Number(anim.currentTime || 0)) : 0;
  win.setTimeout(() => root.classList.add('is-ready'), wait);
  win.setTimeout(() => root.classList.remove('is-locked'), wait + 900);

  root.addEventListener('scroll', onScroll, { passive: true });
  doc.addEventListener('click', onClick);
  win.addEventListener('resize', resize);
  if (doc.fonts && doc.fonts.ready) doc.fonts.ready.then(resize);
  resize();
  S.raf = win.requestAnimationFrame(frame);

  S.destroy = () => {
    win.cancelAnimationFrame(S.raf);
    if (cleanupEnhancer) cleanupEnhancer();
    if (cleanupLive) cleanupLive();
    doc.removeEventListener('click', onClick);
    win.removeEventListener('resize', resize);
    doc.body.classList.remove('eur-tool', 'rehab-cam-active');
    root.remove();
    canvas.remove();
  };
})();
