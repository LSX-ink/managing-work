// Calm pop-ups (see calm_*.py): an animated breathing circle with an optional soft tone, a meditation timer with
// start, interval and end bells, and a guided script read step by step with pauses. Sounds are made here with
// Web Audio; everything stops when the window closes. With reduced motion set, the circle doesn't animate.
(() => {
    const kinds = (window.jarvisPopupKinds = window.jarvisPopupKinds || {});
    const reduced = () => matchMedia('(prefers-reduced-motion: reduce)').matches;
    const pad2 = (n) => String(n).padStart(2, '0');
    const mmss = (s) => `${Math.floor(Math.max(0, s) / 60)}:${pad2(Math.floor(Math.max(0, s)) % 60)}`;

    // One quiet audio context per window, closed when the window goes.
    const audio = () => {
        let ctx = null;
        const get = () => {
            if (!ctx) {
                const Ctx = window.AudioContext || window.webkitAudioContext;
                if (!Ctx) return null;
                ctx = new Ctx();
            }
            if (ctx.state === 'suspended') ctx.resume();
            return ctx;
        };
        // A gentle sine that glides between two pitches over `seconds`.
        const glide = (from, to, seconds) => {
            const c = get();
            if (!c) return;
            const osc = c.createOscillator(), gain = c.createGain(), t = c.currentTime;
            osc.type = 'sine';
            osc.frequency.setValueAtTime(from, t);
            osc.frequency.linearRampToValueAtTime(to, t + seconds);
            gain.gain.setValueAtTime(0.0001, t);
            gain.gain.linearRampToValueAtTime(0.05, t + Math.min(0.6, seconds / 3));
            gain.gain.linearRampToValueAtTime(0.0001, t + seconds);
            osc.connect(gain).connect(c.destination);
            osc.start(t);
            osc.stop(t + seconds + 0.05);
        };
        // A soft bell: a few sine partials that fade away slowly.
        const bell = (times = 1) => {
            const c = get();
            if (!c) return;
            for (let n = 0; n < times; n++) {
                const t = c.currentTime + n * 1.8;
                [[220, 0.18], [440, 0.09], [660, 0.05], [990, 0.025]].forEach(([freq, level]) => {
                    const osc = c.createOscillator(), gain = c.createGain();
                    osc.type = 'sine';
                    osc.frequency.value = freq * 1.5;
                    gain.gain.setValueAtTime(level, t);
                    gain.gain.exponentialRampToValueAtTime(0.0001, t + 4);
                    osc.connect(gain).connect(c.destination);
                    osc.start(t);
                    osc.stop(t + 4.1);
                });
            }
        };
        const close = () => { if (ctx) { ctx.close().catch(() => {}); ctx = null; } };
        return { glide, bell, close };
    };

    // Run `tick` every 250 ms until the window is gone, then call `done`.
    const every = (body, tick, done) => {
        const id = setInterval(() => {
            if (!body.isConnected) { clearInterval(id); done(); return; }
            tick();
        }, 250);
        return () => clearInterval(id);
    };

    const button = (el, label, onClick, cls = '') => {
        const b = el('button', `cm-btn ${cls}`.trim(), label);
        b.type = 'button';
        b.addEventListener('click', onClick);
        return b;
    };

    // ---- breathing ----------------------------------------------------------------------------------
    kinds['calm-breathe'] = (card, body, { el }) => {
        const d = card.data || {};
        const phases = (d.phases || []).filter((p) => p.seconds > 0);
        const total = Math.max(1, Number(d.minutes) || 3) * 60;
        const sound = audio();
        const wrap = el('div', 'cm-wrap');
        const circle = el('div', 'cm-circle');
        circle.setAttribute('aria-hidden', 'true');
        const word = el('div', 'cm-word', 'Ready');
        word.setAttribute('aria-live', 'polite');
        const count = el('div', 'cm-count', '');
        const left = el('div', 'cm-muted', `${mmss(total)} left`);
        const tone = el('input');
        tone.type = 'checkbox';
        tone.checked = d.tone !== false;
        const toneLabel = el('label', 'cm-check');
        toneLabel.append(tone, document.createTextNode(' Soft tone'));
        let running = false, index = 0, phaseStart = 0, started = 0;
        const enter = () => {
            const p = phases[index];
            word.textContent = p.label;
            const grow = /\bin\b|sip/i.test(p.label) && !/out/i.test(p.label);
            const shrink = /out|sigh/i.test(p.label);
            circle.style.transitionDuration = reduced() ? '0s' : `${p.seconds}s`;
            if (grow) circle.classList.add('big');
            else if (shrink) circle.classList.remove('big');
            if (tone.checked) sound.glide(grow ? 220 : shrink ? 330 : 275, grow ? 330 : shrink ? 220 : 275, p.seconds);
            phaseStart = performance.now();
        };
        const stop = (message) => {
            running = false;
            go.textContent = 'Start';
            word.textContent = message;
            count.textContent = '';
            circle.classList.remove('big');
        };
        const go = button(el, 'Start', () => {
            if (running) { stop('Ready'); return; }
            running = true;
            go.textContent = 'Stop';
            index = 0;
            started = performance.now();
            enter();
        }, 'primary');
        every(body, () => {
            if (!running) return;
            const now = performance.now();
            const elapsed = (now - started) / 1000;
            left.textContent = `${mmss(total - elapsed)} left`;
            if (elapsed >= total) { if (tone.checked) sound.bell(); stop('Well done. Notice how you feel.'); return; }
            const p = phases[index], into = (now - phaseStart) / 1000;
            count.textContent = String(Math.max(1, Math.ceil(p.seconds - into)));
            if (into >= p.seconds) { index = (index + 1) % phases.length; enter(); }
        }, sound.close);
        wrap.append(el('div', 'cm-blurb', d.blurb || ''), circle, word, count, left, toneLabel, go);
        body.append(wrap);
    };

    // ---- meditation timer ---------------------------------------------------------------------------
    kinds['calm-bells'] = (card, body, { el }) => {
        const d = card.data || {};
        const total = Math.max(1, Number(d.minutes) || 10) * 60;
        const interval = (Number(d.interval) || 0) * 60;
        const sound = audio();
        const wrap = el('div', 'cm-wrap');
        const face = el('div', 'cm-clock', mmss(total));
        const bar = el('div', 'cm-bar');
        const fill = el('span');
        bar.append(fill);
        const note = el('div', 'cm-muted', `${d.start_bell === false ? 'No' : 'Start'} bell${interval ? `, a bell every ${interval / 60} min` : ''}${d.end_bell === false ? '' : ', end bell'}`);
        let running = false, started = 0, nextBell = interval;
        const go = button(el, 'Begin', () => {
            if (running) { running = false; go.textContent = 'Begin'; face.textContent = mmss(total); fill.style.width = '0%'; return; }
            running = true;
            go.textContent = 'Stop';
            started = performance.now();
            nextBell = interval;
            if (d.start_bell !== false) sound.bell();
        }, 'primary');
        every(body, () => {
            if (!running) return;
            const elapsed = (performance.now() - started) / 1000;
            face.textContent = mmss(total - elapsed);
            fill.style.width = `${Math.min(100, (elapsed / total) * 100)}%`;
            if (interval && elapsed >= nextBell && elapsed < total - 1) { sound.bell(); nextBell += interval; }
            if (elapsed >= total) {
                running = false;
                go.textContent = 'Begin';
                face.textContent = 'Done';
                if (d.end_bell !== false) sound.bell(3);
            }
        }, sound.close);
        wrap.append(face, bar, note, go);
        body.append(wrap);
    };

    // ---- guided script ------------------------------------------------------------------------------
    kinds['calm-guide'] = (card, body, { el }) => {
        const steps = (card.data || {}).steps || [];
        const wrap = el('div', 'cm-wrap');
        const counter = el('div', 'cm-muted', `${steps.length} steps`);
        const text = el('div', 'cm-step', 'Get comfortable, then press Begin.');
        text.setAttribute('aria-live', 'polite');
        const bar = el('div', 'cm-bar');
        const fill = el('span');
        bar.append(fill);
        const voice = el('input');
        voice.type = 'checkbox';
        const voiceLabel = el('label', 'cm-check');
        voiceLabel.append(voice, document.createTextNode(' Read aloud with this browser'));
        let index = -1, running = false, paused = false, stepStart = 0, stepLength = 0;
        const show = (i) => {
            index = i;
            const s = steps[i];
            text.textContent = s.text;
            counter.textContent = `Step ${i + 1} of ${steps.length}`;
            stepLength = (s.text.split(/\s+/).length * 0.4 + (Number(s.pause) || 8)) * 1000;
            stepStart = performance.now();
            if (voice.checked && window.speechSynthesis) {
                speechSynthesis.cancel();
                const u = new SpeechSynthesisUtterance(s.text);
                u.rate = 0.85;
                speechSynthesis.speak(u);
            }
        };
        const finish = () => {
            running = false;
            go.textContent = 'Begin again';
            text.textContent = 'All done. Take a moment before you carry on.';
            counter.textContent = 'Finished';
            fill.style.width = '100%';
        };
        const go = button(el, 'Begin', () => { running = true; paused = false; pause.textContent = 'Pause'; go.textContent = 'Restart'; show(0); }, 'primary');
        const pause = button(el, 'Pause', () => {
            if (!running) return;
            paused = !paused;
            pause.textContent = paused ? 'Resume' : 'Pause';
            if (!paused) stepStart = performance.now();
        });
        const back = button(el, 'Back', () => running && index > 0 && show(index - 1));
        const next = button(el, 'Next', () => running && (index + 1 < steps.length ? show(index + 1) : finish()));
        every(body, () => {
            if (!running || paused) return;
            const into = performance.now() - stepStart;
            fill.style.width = `${Math.min(100, (into / stepLength) * 100)}%`;
            if (into >= stepLength) { if (index + 1 < steps.length) show(index + 1); else finish(); }
        }, () => window.speechSynthesis && speechSynthesis.cancel());
        const row = el('div', 'cm-row');
        row.append(back, pause, next);
        wrap.append(counter, text, bar, row, voiceLabel, go);
        body.append(wrap);
    };
})();
