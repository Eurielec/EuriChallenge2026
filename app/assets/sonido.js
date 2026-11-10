(() => {
  const topWin = window.parent || window;
  if (topWin.__eur_audio) return;
  topWin.__eur_audio = true;

  const AudioCtx = window.AudioContext || window.webkitAudioContext || topWin.AudioContext || topWin.webkitAudioContext;
  if (!AudioCtx) return;
  let played = false;

  function play() {
    if (played) return;
    played = true;
    try {
      const ctx = new AudioCtx();
      const run = () => {
        const now = ctx.currentTime;
        const master = ctx.createGain();
        master.gain.setValueAtTime(0.75, now);
        master.connect(ctx.destination);

        const beep = ctx.createOscillator();
        const beepGain = ctx.createGain();
        beep.frequency.setValueAtTime(1244.5, now);
        beepGain.gain.setValueAtTime(0, now);
        beepGain.gain.linearRampToValueAtTime(0.35, now + 0.006);
        beepGain.gain.exponentialRampToValueAtTime(0.0001, now + 0.32);
        beep.connect(beepGain);
        beepGain.connect(master);
        beep.start(now);
        beep.stop(now + 0.35);

        const notes = [
          [77.78, 'sine', 0.32, 0], [116.54, 'triangle', 0.22, -4],
          [155.56, 'sine', 0.25, 4], [174.61, 'triangle', 0.18, -3],
          [233.08, 'sine', 0.22, 3], [293.66, 'sine', 0.16, -5],
          [392.0, 'sine', 0.15, 5], [466.16, 'sine', 0.1, 2],
        ];
        const filter = ctx.createBiquadFilter();
        filter.type = 'lowpass';
        filter.Q.setValueAtTime(2.2, now);
        filter.frequency.setValueAtTime(240, now);
        filter.frequency.exponentialRampToValueAtTime(2800, now + 1.8);
        filter.frequency.exponentialRampToValueAtTime(600, now + 4.5);

        const pad = ctx.createGain();
        pad.gain.setValueAtTime(0.0001, now);
        pad.gain.linearRampToValueAtTime(0.44, now + 1.3);
        pad.gain.setValueAtTime(0.44, now + 2.8);
        pad.gain.exponentialRampToValueAtTime(0.0001, now + 4.7);

        notes.forEach(([f, type, gain, detune]) => {
          const osc = ctx.createOscillator();
          const g = ctx.createGain();
          osc.type = type;
          osc.frequency.setValueAtTime(f, now);
          osc.detune.setValueAtTime(detune, now);
          g.gain.setValueAtTime(gain, now);
          osc.connect(g);
          g.connect(filter);
          osc.start(now + 0.04);
          osc.stop(now + 4.9);
        });
        filter.connect(pad);

        const echo = ctx.createGain();
        echo.gain.value = 0.35;
        [0.026, 0.04].forEach((time) => {
          const d = ctx.createDelay();
          d.delayTime.value = time;
          pad.connect(d);
          d.connect(echo);
        });
        pad.connect(master);
        echo.connect(master);
      };
      if (ctx.state === 'suspended') ctx.resume().then(run).catch(() => {});
      else run();
    } catch (e) {}
  }

  play();

  // si el navegador bloquea el autoplay, suena en la primera interaccion
  const pDoc = topWin.document;
  const unlock = () => {
    play();
    pDoc.removeEventListener('pointerdown', unlock);
    pDoc.removeEventListener('keydown', unlock);
  };
  pDoc.addEventListener('pointerdown', unlock, { passive: true });
  pDoc.addEventListener('keydown', unlock, { passive: true });
})();

