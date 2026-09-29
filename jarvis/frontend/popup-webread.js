// Reading-help pop-up (webread_read.py): a big-text reader that reads a page aloud paragraph by paragraph with the
// voice chosen in Alfred's voice picker (browser speechSynthesis), highlights the paragraph being read, and has
// pause, skip and speed, a reading ruler, text size, line spacing and background tints. Reading stops when the
// window closes. Look settings are remembered in this browser (localStorage) on top of the saved defaults.
(() => {
    const kinds = (window.jarvisPopupKinds = window.jarvisPopupKinds || {});
    const TINTS = { cream: ['#f6efdc', '#2b2416'], blue: ['#dbeaf7', '#10263b'], yellow: ['#fdf3ae', '#2a2500'],
                    white: ['#ffffff', '#111111'], dark: ['#0d121b', '#e6edf7'] };
    const SPEEDS = [0.7, 0.85, 1, 1.2, 1.5];
    const reduced = () => matchMedia('(prefers-reduced-motion: reduce)').matches;
    const clamp = (n, lo, hi) => Math.min(hi, Math.max(lo, n));

    function savedLook() {
        try { return JSON.parse(localStorage.getItem('webread-look') || '{}') || {}; } catch { return {}; }
    }
    function keepLook(look) {
        try { localStorage.setItem('webread-look', JSON.stringify(look)); } catch { /* private window */ }
    }

    // Sentences grouped to about 200 characters: some browser voices stop part-way through long text.
    function chunks(text) {
        const parts = String(text).match(/[^.!?]+[.!?]*\s*/g) || [String(text)];
        const out = [];
        let cur = '';
        for (const p of parts) {
            if (cur && (cur + p).length > 200) { out.push(cur.trim()); cur = ''; }
            cur += p;
        }
        if (cur.trim()) out.push(cur.trim());
        return out;
    }

    kinds['webread-reader'] = (card, body, { el, ask }) => {
        const d = card.data || {};
        const paras = d.paras || [];
        if (!paras.length) { body.append(el('div', 'pop-empty', 'Nothing to read.')); return; }
        const look = { size: 22, spacing: 1.7, tint: 'cream', ruler: false, speed: 1, ...(d.prefs || {}), ...savedLook() };
        const synth = 'speechSynthesis' in window ? window.speechSynthesis : null;
        let idx = clamp(Number(d.start) || 0, 0, paras.length - 1);
        let playing = false, paused = false, run = 0, mouseAt = 0;

        const root = el('div', 'wr');
        const bar = el('div', 'wr-bar');
        const status = el('div', 'wr-status');
        const wrap = el('div', 'wr-wrap');
        const scroller = el('div', 'wr-scroll');
        scroller.tabIndex = 0;
        const ruler = el('div', 'wr-ruler');
        const nodes = paras.map((p, i) => {
            const n = el(p.h ? 'h3' : 'p', 'wr-para' + (p.h ? ' wr-head' : ''), p.t);
            n.addEventListener('click', () => start(i));
            return n;
        });
        scroller.append(...nodes);
        wrap.append(scroller, ruler);

        const button = (label, onclick, title, cls) => {
            const b = el('button', 'wr-btn' + (cls ? ` ${cls}` : ''), label);
            b.type = 'button';
            if (title) { b.title = title; b.setAttribute('aria-label', title); }
            b.addEventListener('click', onclick);
            return b;
        };

        function applyLook() {
            const [bg, fg] = TINTS[look.tint] || TINTS.cream;
            wrap.style.setProperty('--wr-bg', bg);
            wrap.style.setProperty('--wr-fg', fg);
            scroller.style.fontSize = `${look.size}px`;
            scroller.style.lineHeight = String(look.spacing);
            ruler.style.display = look.ruler ? 'block' : 'none';
            ruler.style.height = `${Math.round(look.size * look.spacing * 1.15)}px`;
            rulerBtn.setAttribute('aria-pressed', String(look.ruler));
            rulerBtn.classList.toggle('on', look.ruler);
            tintButtons.forEach(([name, b]) => b.classList.toggle('on', name === look.tint));
            speedSel.value = String(look.speed);
            keepLook(look);
        }

        function setStatus() {
            const state = !synth ? 'Reading aloud isn\'t available in this browser' : paused ? 'Paused' : playing ? 'Reading' : 'Ready';
            status.textContent = `${state}: paragraph ${idx + 1} of ${paras.length}`;
        }

        function mark(i, scroll = true) {
            nodes.forEach((n, k) => n.classList.toggle('wr-cur', k === i));
            idx = i;
            if (scroll) nodes[i].scrollIntoView({ block: 'center', behavior: reduced() ? 'auto' : 'smooth' });
            if (look.ruler && Date.now() - mouseAt > 4000) {
                const top = nodes[i].getBoundingClientRect().top - wrap.getBoundingClientRect().top;
                ruler.style.top = `${Math.max(0, top)}px`;
            }
            setStatus();
        }

        function voice() {
            const v = window.jarvisVoice;
            return v && synth && synth.getVoices().length ? v.pick() : null;
        }

        function speak(i) {
            const mine = ++run;
            synth.cancel();
            mark(i);
            const parts = chunks(paras[i].t);
            const base = Number((window.jarvisVoice && window.jarvisVoice.prefs().rate) || 1) || 1;
            const next = (n) => {
                if (mine !== run || !playing) return;
                if (n >= parts.length) { if (i + 1 < paras.length) speak(i + 1); else finish(); return; }
                const u = new SpeechSynthesisUtterance(parts[n]);
                u.lang = (window.jarvisVoice && window.jarvisVoice.lang()) || 'en-GB';
                const v = voice();
                if (v) u.voice = v;
                u.rate = clamp(base * look.speed, 0.4, 2.2);
                u.pitch = Number((window.jarvisVoice && window.jarvisVoice.prefs().pitch) || 1) || 1;
                u.onend = () => next(n + 1);
                u.onerror = (e) => { if (e.error !== 'interrupted' && e.error !== 'canceled') finish(); };
                synth.speak(u);
            };
            setTimeout(() => next(0), 30);
        }

        function start(i) {
            if (!synth) return;
            playing = true;
            paused = false;
            playBtn.textContent = 'Pause';
            speak(i);
        }

        function stop() {
            run++;
            playing = false;
            paused = false;
            if (synth) synth.cancel();
            playBtn.textContent = 'Read aloud';
            setStatus();
        }

        function finish() {
            stop();
            status.textContent = 'Finished. Press Read aloud to hear it again.';
            idx = 0;
        }

        const playBtn = button('Read aloud', () => {
            if (!playing) { start(idx); return; }
            paused = !paused;
            if (paused) synth.pause(); else synth.resume();
            playBtn.textContent = paused ? 'Resume' : 'Pause';
            setStatus();
        }, 'Read aloud, pause or resume (space)', 'primary');
        const prev = button('Back', () => { const i = Math.max(0, idx - 1); if (playing) start(i); else mark(i); }, 'Previous paragraph (left arrow)');
        const next = button('Skip', () => { const i = Math.min(paras.length - 1, idx + 1); if (playing) start(i); else mark(i); }, 'Next paragraph (right arrow)');
        const stopBtn = button('Stop', stop, 'Stop reading');
        const speedSel = el('select', 'wr-select');
        speedSel.title = 'Reading speed';
        speedSel.setAttribute('aria-label', 'Reading speed');
        SPEEDS.forEach((s) => { const o = el('option', '', s === 1 ? 'Normal speed' : `${s}x speed`); o.value = String(s); speedSel.append(o); });
        speedSel.addEventListener('change', () => { look.speed = Number(speedSel.value); applyLook(); if (playing && !paused) start(idx); });
        const row1 = el('div', 'wr-row');
        row1.append(playBtn, prev, next, stopBtn, speedSel);

        const change = (key, delta, lo, hi, digits = 0) => () => {
            look[key] = Number(clamp(look[key] + delta, lo, hi).toFixed(digits));
            applyLook();
        };
        const rulerBtn = button('Ruler', () => { look.ruler = !look.ruler; applyLook(); if (look.ruler) mark(idx, false); }, 'Reading ruler: dims everything but the line under your pointer');
        const tintButtons = Object.keys(TINTS).map((name) => {
            const b = button('', () => { look.tint = name; applyLook(); }, `${name} background`, 'wr-tint');
            b.style.background = TINTS[name][0];
            return [name, b];
        });
        const savePlace = button('Save my place', () => {
            const where = d.url ? `The link is ${d.url}.` : `The file is ${d.filename} in ${d.folder || 'my memory folders'}.`;
            ask(`Remember my place in ${d.title}: paragraph ${idx + 1} of ${paras.length}. ${where}`);
        }, 'Remember where you stopped');
        const row2 = el('div', 'wr-row');
        row2.append(button('A-', change('size', -2, 14, 48), 'Smaller text'), button('A+', change('size', 2, 14, 48), 'Bigger text'),
                    button('Gap-', change('spacing', -0.2, 1.2, 2.6, 1), 'Less space between lines'),
                    button('Gap+', change('spacing', 0.2, 1.2, 2.6, 1), 'More space between lines'),
                    ...tintButtons.map(([, b]) => b), rulerBtn, savePlace);
        if (!synth) [playBtn, prev, next, stopBtn, speedSel].forEach((c) => { c.disabled = true; });

        wrap.addEventListener('pointermove', (e) => {
            if (!look.ruler) return;
            mouseAt = Date.now();
            const r = wrap.getBoundingClientRect();
            ruler.style.top = `${clamp(e.clientY - r.top - ruler.offsetHeight / 2, 0, r.height - ruler.offsetHeight)}px`;
        });
        scroller.addEventListener('keydown', (e) => {
            if (e.key === ' ') { e.preventDefault(); playBtn.click(); }
            else if (e.key === 'ArrowRight') { e.preventDefault(); next.click(); }
            else if (e.key === 'ArrowLeft') { e.preventDefault(); prev.click(); }
        });

        root.append(row1, row2, status, wrap);
        body.append(root);
        applyLook();
        requestAnimationFrame(() => mark(idx, idx > 0));
        // Stop talking when this window is closed.
        const watch = setInterval(() => { if (!body.isConnected) { clearInterval(watch); run++; if (synth && playing) synth.cancel(); } }, 500);
    };
})();
