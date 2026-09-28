// Music-studio pop-up kinds (studio_play.py, studio_learn.py): piano, drum machine, chord and scale keyboards,
// guitar chord diagrams, playable progressions, circle of fifths, tuning tones, tap tempo, an interval ear-training
// quiz and a note-reading quiz. Every sound is synthesised with WebAudio; each window has its own AudioContext,
// closed (with its timers) as soon as the window is closed or redrawn.
(() => {
    const kinds = (window.jarvisPopupKinds = window.jarvisPopupKinds || {});
    const NS = 'http://www.w3.org/2000/svg';
    const NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B'];
    const BLACK = new Set([1, 3, 6, 8, 10]);
    const hz = (midi) => 440 * 2 ** ((midi - 69) / 12);
    const noteName = (midi) => `${NAMES[((midi % 12) + 12) % 12]}${Math.floor(midi / 12) - 1}`;
    const rand = (n) => { const a = new Uint32Array(1); crypto.getRandomValues(a); return a[0] % n; };

    // ---- per-window sound and clean-up ----------------------------------------------------------------
    function studio(root) {
        const stops = [];
        const s = {
            ctx: null,
            onStop: (fn) => stops.push(fn),
            every(ms, fn) { const id = setInterval(fn, ms); stops.push(() => clearInterval(id)); return id; },
            later(ms, fn) { const id = setTimeout(fn, ms); stops.push(() => clearTimeout(id)); return id; },
            audio() {
                if (!s.ctx) {
                    const ctx = new (window.AudioContext || window.webkitAudioContext)();
                    const soft = ctx.createBiquadFilter();
                    soft.type = 'lowpass';
                    soft.frequency.value = 5000;
                    s.master = ctx.createGain();
                    s.master.gain.value = 0.7;
                    s.master.connect(soft).connect(ctx.destination);
                    s.ctx = ctx;
                    stops.push(() => ctx.close().catch(() => {}));
                }
                if (s.ctx.state === 'suspended') s.ctx.resume();
                return s.ctx;
            },
            // One synth voice with an ADSR envelope. Without dur it holds until release() is called.
            tone(midi, o = {}) {
                const ctx = s.audio(), t = ctx.currentTime + (o.when || 0);
                const { type = 'triangle', vol = 0.2, a = 0.01, d = 0.25, sus = 0.4, r = 0.35 } = o;
                const osc = ctx.createOscillator(), g = ctx.createGain();
                osc.type = type;
                osc.frequency.value = o.freq || hz(midi);
                g.gain.setValueAtTime(0, t);
                g.gain.linearRampToValueAtTime(vol, t + a);
                g.gain.setTargetAtTime(vol * sus, t + a, Math.max(0.01, d / 3));
                osc.connect(g).connect(o.out || s.master);
                osc.start(t);
                let done = false;
                const release = (at) => {
                    if (done) return;
                    done = true;
                    const e = Math.max(at ?? ctx.currentTime, t + a);
                    if (g.gain.cancelAndHoldAtTime) g.gain.cancelAndHoldAtTime(e); else g.gain.cancelScheduledValues(e);
                    g.gain.setTargetAtTime(0, e, Math.max(0.01, r / 4));
                    osc.stop(e + r * 1.5 + 0.05);
                };
                if (o.dur) release(t + o.dur);
                return { release };
            },
            noise() {
                const ctx = s.audio();
                if (!s.noiseBuf) {
                    s.noiseBuf = ctx.createBuffer(1, ctx.sampleRate, ctx.sampleRate);
                    const ch = s.noiseBuf.getChannelData(0);
                    for (let i = 0; i < ch.length; i++) ch[i] = Math.random() * 2 - 1;
                }
                const src = ctx.createBufferSource();
                src.buffer = s.noiseBuf;
                return src;
            },
            chord(midis, o = {}) { midis.forEach((m, i) => s.tone(m, { vol: 0.14, d: 0.6, sus: 0.5, r: 0.5, dur: 1.4, ...o, when: (o.when || 0) + i * (o.spread || 0) })); },
        };
        const stopAll = () => { stops.splice(0).forEach((fn) => { try { fn(); } catch (e) { /* already stopped */ } }); };
        const watch = setInterval(() => {
            if (root.isConnected) return;
            clearInterval(watch);
            stopAll();
        }, 400);
        return s;
    }

    function btn(el, label, fn, cls = '') {
        const b = el('button', `st-btn ${cls}`.trim(), label);
        b.type = 'button';
        b.addEventListener('click', fn);
        return b;
    }
    function row(el, ...kids) { const r = el('div', 'st-row'); r.append(...kids); return r; }
    function range(el, label, min, max, value, step, oninput) {
        const wrap = el('label', 'st-field');
        const input = el('input', 'st-range');
        Object.assign(input, { type: 'range', min, max, value, step });
        const out = el('span', 'st-val', String(value));
        input.addEventListener('input', () => { out.textContent = input.value; oninput(+input.value); });
        wrap.append(el('span', '', label), input, out);
        return { wrap, input, out };
    }
    function svgNode(tag, attrs, text) {
        const n = document.createElementNS(NS, tag);
        for (const [k, v] of Object.entries(attrs)) n.setAttribute(k, v);
        if (text !== undefined) n.textContent = text;
        return n;
    }

    // ---- a piano keyboard drawn with divs ---------------------------------------------------------------
    function keyboard(el, start, count, { highlight = [], onDown, onUp } = {}) {
        const wrap = el('div', 'st-keys');
        const keys = new Map();
        const whites = [];
        for (let m = start; m < start + count; m++) if (!BLACK.has(m % 12)) whites.push(m);
        const w = 100 / whites.length;
        const lit = new Set(highlight);
        for (let m = start; m < start + count; m++) {
            const black = BLACK.has(m % 12);
            const k = el('div', `st-key ${black ? 'black' : 'white'}${lit.has(m) ? ' lit' : ''}`);
            k.setAttribute('role', 'button');
            k.setAttribute('aria-label', noteName(m));
            k.title = noteName(m);
            if (black) {
                const left = whites.indexOf(m - 1) + 1;
                k.style.left = `calc(${left * w}% - ${w * 0.3}%)`;
                k.style.width = `${w * 0.6}%`;
            } else {
                k.style.width = `${w}%`;
                if (m % 12 === 0) k.append(el('span', 'st-key-label', noteName(m)));
            }
            k.addEventListener('pointerdown', (e) => { e.preventDefault(); k.setPointerCapture?.(e.pointerId); onDown?.(m); });
            const up = () => onUp?.(m);
            k.addEventListener('pointerup', up);
            k.addEventListener('pointercancel', up);
            keys.set(m, k);
            wrap.append(k);
        }
        return { el: wrap, press: (m, on) => keys.get(m)?.classList.toggle('down', on) };
    }

    // ---- piano --------------------------------------------------------------------------------------
    const PRESETS = {
        Piano: { type: 'triangle', a: 0.005, d: 0.6, sus: 0.2, r: 0.5 },
        Organ: { type: 'square', a: 0.01, d: 0.1, sus: 0.9, r: 0.08 },
        'Soft pad': { type: 'sine', a: 0.35, d: 0.4, sus: 0.8, r: 1.2 },
        Synth: { type: 'sawtooth', a: 0.02, d: 0.3, sus: 0.5, r: 0.3 },
    };
    const LOWER = 'zsxdcvgbhnjm,';
    const UPPER = 'q2w3er5t6y7ui';

    kinds['studio-piano'] = (card, body, { el }) => {
        const root = el('div', 'st st-piano');
        root.tabIndex = 0;
        const s = studio(root);
        const voice = { ...PRESETS.Piano };
        const held = new Map();
        let start = Math.min(84, Math.max(24, card.data?.start ?? 48));
        const label = el('div', 'st-big', '');
        const status = el('span', 'st-muted', '');
        const on = (m) => {
            if (held.has(m)) return;
            held.set(m, s.tone(m, { ...voice, vol: voice.type === 'triangle' || voice.type === 'sine' ? 0.25 : 0.1 }));
            kb.press(m, true);
            label.textContent = noteName(m);
        };
        const off = (m) => { held.get(m)?.release(); held.delete(m); kb.press(m, false); };
        const allOff = () => [...held.keys()].forEach(off);
        let kb;
        const keysBox = el('div', 'st-keys-box');
        keysBox.addEventListener('pointerdown', () => root.focus({ preventScroll: true }));
        const draw = () => {
            allOff();
            kb = keyboard(el, start, 25, { highlight: card.data?.highlight || [], onDown: on, onUp: off });
            keysBox.replaceChildren(kb.el);
            status.textContent = `${noteName(start)} to ${noteName(start + 24)}`;
        };
        const shift = (n) => { start = Math.min(84, Math.max(24, start + n)); draw(); };
        const sound = el('select', 'st-input');
        Object.keys(PRESETS).forEach((n) => sound.append(Object.assign(el('option', '', n), { value: n })));
        const sliders = [['A', 'a', 0.001, 2], ['D', 'd', 0.01, 2], ['S', 'sus', 0, 1], ['R', 'r', 0.02, 3]]
            .map(([text, key, min, max]) => range(el, text, min, max, voice[key], 0.01, (v) => { voice[key] = v; }));
        sound.addEventListener('change', () => {
            Object.assign(voice, PRESETS[sound.value]);
            sliders.forEach((sl, i) => { const key = ['a', 'd', 'sus', 'r'][i]; sl.input.value = voice[key]; sl.out.textContent = voice[key]; });
        });
        root.addEventListener('keydown', (e) => {
            if (e.target !== root || e.ctrlKey || e.metaKey || e.altKey) return;
            if (e.key === 'ArrowLeft' || e.key === 'ArrowRight') { e.preventDefault(); shift(e.key === 'ArrowLeft' ? -12 : 12); return; }
            const k = e.key.toLowerCase();
            const i = LOWER.indexOf(k) >= 0 ? LOWER.indexOf(k) : UPPER.indexOf(k) >= 0 ? UPPER.indexOf(k) + 12 : -1;
            if (i < 0) return;
            e.preventDefault();
            if (!e.repeat) on(start + i);
        });
        root.addEventListener('keyup', (e) => {
            const k = e.key.toLowerCase();
            const i = LOWER.indexOf(k) >= 0 ? LOWER.indexOf(k) : UPPER.indexOf(k) >= 0 ? UPPER.indexOf(k) + 12 : -1;
            if (i >= 0) off(start + i);
        });
        root.addEventListener('blur', allOff);
        s.onStop(allOff);
        root.append(
            row(el, btn(el, '◀ Octave', () => shift(-12)), status, btn(el, 'Octave ▶', () => shift(12)), label),
            keysBox,
            row(el, el('span', 'st-muted', 'Sound'), sound),
            row(el, ...sliders.map((x) => x.wrap)),
        );
        draw();
        body.append(root);
        root.focus({ preventScroll: true });
    };

    // ---- drum machine -------------------------------------------------------------------------------
    const TRACKS = [['kick', 'Kick'], ['snare', 'Snare'], ['hat', 'Hi-hat'], ['clap', 'Clap']];
    function drumKit(s) {
        const ctx = () => s.audio();
        const env = (node, t, peak, len) => {
            node.gain.setValueAtTime(peak, t);
            node.gain.exponentialRampToValueAtTime(0.001, t + len);
        };
        const noiseHit = (t, filterType, freq, peak, len, q = 1) => {
            const c = ctx(), src = s.noise(), f = c.createBiquadFilter(), g = c.createGain();
            f.type = filterType; f.frequency.value = freq; f.Q.value = q;
            env(g, t, peak, len);
            src.connect(f).connect(g).connect(s.master);
            src.start(t, Math.random() * 0.5);
            src.stop(t + len + 0.02);
            return g;
        };
        return {
            kick(t) {
                const c = ctx(), o = c.createOscillator(), g = c.createGain();
                o.frequency.setValueAtTime(150, t);
                o.frequency.exponentialRampToValueAtTime(42, t + 0.15);
                env(g, t, 0.9, 0.4);
                o.connect(g).connect(s.master);
                o.start(t); o.stop(t + 0.45);
            },
            snare(t) {
                noiseHit(t, 'highpass', 1200, 0.45, 0.18);
                const c = ctx(), o = c.createOscillator(), g = c.createGain();
                o.type = 'triangle'; o.frequency.value = 185;
                env(g, t, 0.35, 0.1);
                o.connect(g).connect(s.master);
                o.start(t); o.stop(t + 0.12);
            },
            hat(t) { noiseHit(t, 'highpass', 7500, 0.22, 0.05); },
            clap(t) {
                [0, 0.012, 0.024].forEach((dt) => noiseHit(t + dt, 'bandpass', 1400, 0.35, 0.03, 1.2));
                noiseHit(t + 0.036, 'bandpass', 1400, 0.3, 0.18, 1.2);
            },
        };
    }

    kinds['studio-drums'] = (card, body, { el, ask }) => {
        const d = card.data || {};
        const root = el('div', 'st st-drums');
        const s = studio(root);
        const kit = drumKit(s);
        const grid = {};
        const cells = {};
        let bpm = 110, step = 0, playing = false, nextTime = 0, timer = null;
        const grid16 = (text) => Array.from({ length: 16 }, (_, i) => (text || '')[i] === 'x');
        const board = el('div', 'st-grid');
        TRACKS.forEach(([key, label]) => {
            const name = btn(el, label, () => kit[key](s.audio().currentTime + 0.01), 'st-track');
            board.append(name);
            cells[key] = [];
            for (let i = 0; i < 16; i++) {
                const c = el('button', `st-step${i % 4 === 0 ? ' beat' : ''}`);
                c.type = 'button';
                c.setAttribute('aria-label', `${label} step ${i + 1}`);
                c.addEventListener('click', () => { grid[key][i] = !grid[key][i]; paint(); });
                cells[key].push(c);
                board.append(c);
            }
        });
        const paint = () => TRACKS.forEach(([key]) => cells[key].forEach((c, i) => c.setAttribute('aria-pressed', String(grid[key][i]))));
        const tempo = range(el, 'BPM', 40, 240, bpm, 1, (v) => { bpm = v; });
        const load = (p) => {
            TRACKS.forEach(([key]) => { grid[key] = grid16(p[key]); });
            if (p.bpm) { bpm = Math.min(240, Math.max(40, p.bpm)); tempo.input.value = bpm; tempo.out.textContent = bpm; }
            paint();
        };
        const lightStep = (i) => TRACKS.forEach(([key]) => cells[key].forEach((c, n) => c.classList.toggle('now', n === i)));
        const schedule = () => {
            const ctx = s.audio();
            while (nextTime < ctx.currentTime + 0.12) {
                const i = step;
                TRACKS.forEach(([key]) => { if (grid[key][i]) kit[key](nextTime); });
                setTimeout(() => { if (playing) lightStep(i); }, Math.max(0, (nextTime - ctx.currentTime) * 1000));
                nextTime += 60 / bpm / 4;
                step = (step + 1) % 16;
            }
        };
        const play = btn(el, '▶ Play', () => {
            playing = !playing;
            play.textContent = playing ? '■ Stop' : '▶ Play';
            play.setAttribute('aria-pressed', String(playing));
            if (playing) {
                step = 0;
                nextTime = s.audio().currentTime + 0.05;
                schedule();
                timer = s.every(25, schedule);
            } else {
                clearInterval(timer);
                lightStep(-1);
            }
        }, 'st-primary');
        const clear = btn(el, 'Clear', () => load({ kick: '', snare: '', hat: '', clap: '' }));
        const pick = el('select', 'st-input');
        pick.append(Object.assign(el('option', '', 'Load a pattern…'), { value: '' }));
        const addGroup = (label, obj, tag) => {
            const names = Object.keys(obj || {});
            if (!names.length) return;
            const g = el('optgroup');
            g.label = label;
            names.forEach((n) => g.append(Object.assign(el('option', '', n), { value: `${tag}:${n}` })));
            pick.append(g);
        };
        addGroup('Your saved patterns', d.saved, 'saved');
        addGroup('Starter beats', d.presets, 'preset');
        const nameBox = el('input', 'st-input st-name');
        Object.assign(nameBox, { type: 'text', placeholder: 'Pattern name', maxLength: 40, value: d.start?.name || '' });
        pick.addEventListener('change', () => {
            const [tag, ...rest] = pick.value.split(':');
            const n = rest.join(':');
            const p = (tag === 'saved' ? d.saved : d.presets)?.[n];
            if (p) { load(p); if (tag === 'saved') nameBox.value = n; }
            pick.value = '';
        });
        const msg = el('div', 'st-msg');
        const save = btn(el, 'Save pattern', () => {
            const name = nameBox.value.replace(/["<>]/g, '').trim();
            if (!name) { msg.textContent = 'Type a name for the pattern first.'; nameBox.focus(); return; }
            const text = TRACKS.map(([key]) => `${key} ${grid[key].map((x) => (x ? 'x' : '.')).join('')}`).join(' ');
            ask(`Save my drum pattern "${name}" at ${bpm} BPM: ${text}`);
            msg.textContent = `Asked Alfred to save ${name}.`;
        });
        root.append(row(el, play, tempo.wrap, clear), board, row(el, pick), row(el, nameBox, save), msg);
        load(d.start || {});
        body.append(root);
    };

    // ---- chord and scale keyboards ------------------------------------------------------------------
    function notesView(card, body, { el, table }) {
        const d = card.data || {};
        const midi = d.midi || [];
        const root = el('div', 'st st-notes');
        const s = studio(root);
        const low = Math.floor(Math.min(...midi, 60) / 12) * 12;
        const count = Math.max(25, Math.ceil((Math.max(...midi, low) - low + 1) / 12) * 12 + 1);
        const kb = keyboard(el, low, count, { highlight: midi, onDown: (m) => { flash(m, 0); s.tone(m, { dur: 0.6 }); } });
        const flash = (m, when) => {
            s.later(when * 1000, () => kb.press(m, true));
            s.later(when * 1000 + 350, () => kb.press(m, false));
        };
        root.append(el('div', 'st-big', `${d.name || ''}  ·  ${(d.notes || []).join(' ')}`));
        const kbBox = el('div', 'st-keys-box');
        kbBox.append(kb.el);
        root.append(kbBox);
        const run = (list, gap) => list.forEach((m, i) => { s.tone(m, { when: i * gap, dur: gap * 0.9 + 0.1, vol: 0.22 }); flash(m, i * gap); });
        if (d.mode === 'chord') {
            root.append(row(el,
                btn(el, '▶ Play chord', () => { s.chord(midi); midi.forEach((m) => flash(m, 0)); }, 'st-primary'),
                btn(el, 'Arpeggio', () => run(midi, 0.28))));
        } else {
            root.append(row(el,
                btn(el, '▶ Up and down', () => run([...midi, ...midi.slice(0, -1).reverse()], 0.32), 'st-primary'),
                btn(el, 'Up', () => run(midi, 0.32))));
        }
        if (d.facts?.length) root.append(table([], d.facts));
        body.append(root);
    }
    kinds['studio-chord'] = notesView;
    kinds['studio-scale'] = notesView;

    // ---- guitar chord diagrams ----------------------------------------------------------------------
    function diagram(shape) {
        const W = 132, H = 170, L = 22, T = 34, gapX = 18, gapY = 24, FRETS = 5;
        const svg = svgNode('svg', { viewBox: `0 0 ${W} ${H}`, class: 'st-fretboard', role: 'img',
            'aria-label': `${shape.name}: ${shape.shape}` });
        const frets = shape.frets;
        const played = frets.filter((f) => f !== null && f > 0);
        const base = played.length && Math.max(...played) > 4 ? Math.min(...played) : 1;
        svg.append(svgNode('text', { x: W / 2, y: 13, 'text-anchor': 'middle', class: 'st-fb-name' }, shape.name));
        for (let i = 0; i < 6; i++) svg.append(svgNode('line', { x1: L + i * gapX, x2: L + i * gapX, y1: T, y2: T + FRETS * gapY, class: 'st-fb-line' }));
        for (let f = 0; f <= FRETS; f++) {
            svg.append(svgNode('line', { x1: L, x2: L + 5 * gapX, y1: T + f * gapY, y2: T + f * gapY,
                class: f === 0 && base === 1 ? 'st-fb-nut' : 'st-fb-line' }));
        }
        if (base > 1) svg.append(svgNode('text', { x: L + 5 * gapX + 6, y: T + gapY / 2 + 4, class: 'st-fb-small' }, `${base}fr`));
        const minFret = played.length ? Math.min(...played) : 0;
        const first = frets.findIndex((f) => f !== null);
        const withMin = frets.map((f, i) => (f === minFret ? i : -1)).filter((i) => i >= 0);
        const lastMin = withMin[withMin.length - 1];
        const barre = minFret > 0 && frets[first] === minFret && withMin.length >= 2
            && frets.slice(first, lastMin + 1).every((f) => f !== null && f >= minFret);
        const y = (f) => T + (f - base + 0.5) * gapY;
        if (barre) {
            svg.append(svgNode('rect', { x: L + first * gapX - 6, y: y(minFret) - 6, width: (lastMin - first) * gapX + 12, height: 12, rx: 6, class: 'st-fb-dot' }));
        }
        frets.forEach((f, i) => {
            const x = L + i * gapX;
            if (f === null) svg.append(svgNode('text', { x, y: T - 8, 'text-anchor': 'middle', class: 'st-fb-small' }, '×'));
            else if (f === 0) svg.append(svgNode('circle', { cx: x, cy: T - 12, r: 4, class: 'st-fb-open' }));
            else if (!(barre && f === minFret)) svg.append(svgNode('circle', { cx: x, cy: y(f), r: 7, class: 'st-fb-dot' }));
        });
        ['E', 'A', 'D', 'G', 'B', 'e'].forEach((n, i) => svg.append(svgNode('text', { x: L + i * gapX, y: H - 4, 'text-anchor': 'middle', class: 'st-fb-small' }, n)));
        return svg;
    }

    kinds['studio-guitar'] = (card, body, { el }) => {
        const shapes = card.data?.shapes || [];
        const root = el('div', 'st st-guitar');
        const s = studio(root);
        const strum = (shape, when = 0, down = true) => {
            const notes = down ? shape.midi : [...shape.midi].reverse();
            notes.forEach((m, i) => s.tone(m, { when: when + i * 0.035, type: 'triangle', vol: 0.18, a: 0.003, d: 1.2, sus: 0.05, r: 0.4, dur: 1.8 }));
        };
        const wall = el('div', 'st-shapes');
        shapes.forEach((shape) => {
            const box = el('div', 'st-shape');
            const svg = diagram(shape);
            svg.addEventListener('click', () => strum(shape));
            box.append(svg, el('div', 'st-muted', `${shape.shape}  ·  ${(shape.notes || []).join(' ')}`),
                btn(el, 'Strum', () => strum(shape)));
            wall.append(box);
        });
        root.append(wall);
        if (shapes.length > 1) {
            root.append(row(el, btn(el, '▶ Play them in turn', () => shapes.forEach((sh, i) => strum(sh, i * 1.6)), 'st-primary')));
        }
        body.append(root);
    };

    // ---- progressions and transposed songs ------------------------------------------------------------
    kinds['studio-chords'] = (card, body, { el }) => {
        const d = card.data || {};
        const chords = d.chords || [];
        const root = el('div', 'st st-chords');
        const s = studio(root);
        let bpm = d.bpm || 90, playing = false, loop = false;
        const tiles = chords.map((c, i) => {
            const t = el('button', 'st-chord');
            t.type = 'button';
            if (c.numeral) t.append(el('span', 'st-numeral', c.numeral));
            t.append(el('span', 'st-chord-name', c.name), el('span', 'st-chord-notes', (c.notes || []).join(' ')));
            if (d.before?.[i]) t.append(el('span', 'st-chord-was', `was ${d.before[i]}`));
            t.addEventListener('click', () => sound(c, 0, 60 / bpm * 2));
            return t;
        });
        let bus = null;
        const sound = (c, when, len, out) => {
            s.chord(c.midi || [], { when, dur: len * 0.95, out });
            if (c.midi?.length) s.tone(c.midi[0] - 12, { when, dur: len * 0.95, type: 'sine', vol: 0.25, sus: 0.6, out });
        };
        const light = (i) => tiles.forEach((t, n) => t.classList.toggle('now', n === i));
        let queue = [];
        const stop = () => {
            playing = false;
            queue.forEach(clearTimeout);
            queue = [];
            bus?.disconnect();
            bus = null;
            light(-1);
            playBtn.textContent = '▶ Play all';
        };
        const playAll = () => {
            const ctx = s.audio(), len = 60 / bpm * 2, t0 = ctx.currentTime + 0.05;
            chords.forEach((c, i) => {
                sound(c, 0.05 + i * len, len, bus);
                queue.push(s.later((t0 - ctx.currentTime + i * len) * 1000, () => light(i)));
            });
            queue.push(s.later(chords.length * len * 1000 + 50, () => { if (playing && loop) playAll(); else stop(); }));
        };
        const playBtn = btn(el, '▶ Play all', () => {
            if (playing) { stop(); return; }
            playing = true;
            playBtn.textContent = '■ Stop';
            bus = s.audio().createGain();
            bus.connect(s.master);
            playAll();
        }, 'st-primary');
        const loopBtn = btn(el, 'Loop', () => { loop = !loop; loopBtn.setAttribute('aria-pressed', String(loop)); });
        loopBtn.setAttribute('aria-pressed', 'false');
        const tempo = range(el, 'BPM', 40, 200, bpm, 1, (v) => { bpm = v; });
        const wall = el('div', 'st-chord-wall');
        wall.append(...tiles);
        root.append(wall, row(el, playBtn, loopBtn, tempo.wrap));
        body.append(root);
    };

    // ---- circle of fifths ---------------------------------------------------------------------------
    kinds['studio-circle'] = (card, body, { el }) => {
        const d = card.data || {};
        const keys = d.keys || [];
        const root = el('div', 'st st-circle');
        const s = studio(root);
        let sel = d.selected || 0, minor = !!d.minor;
        const C = 150, R1 = 145, R2 = 100, R3 = 60;
        const svg = svgNode('svg', { viewBox: '0 0 300 300', class: 'st-circle-svg' });
        const polar = (r, a) => [C + r * Math.sin(a), C - r * Math.cos(a)];
        const wedge = (r0, r1, a0, a1) => {
            const [x0, y0] = polar(r1, a0), [x1, y1] = polar(r1, a1), [x2, y2] = polar(r0, a1), [x3, y3] = polar(r0, a0);
            return `M${x0},${y0} A${r1},${r1} 0 0 1 ${x1},${y1} L${x2},${y2} A${r0},${r0} 0 0 0 ${x3},${y3} Z`;
        };
        const parts = [];
        keys.forEach((k, i) => {
            const a0 = (i - 0.5) * Math.PI / 6, a1 = (i + 0.5) * Math.PI / 6, mid = i * Math.PI / 6;
            [[false, R2, R1, k.major, 18], [true, R3, R2, k.minor, 42]].forEach(([isMinor, r0, r1, label]) => {
                const g = svgNode('g', { class: 'st-wedge', role: 'button', tabindex: '0',
                    'aria-label': `${label} ${isMinor ? 'minor' : 'major'}` });
                g.append(svgNode('path', { d: wedge(r0, r1, a0, a1) }));
                const [tx, ty] = polar((r0 + r1) / 2, mid);
                g.append(svgNode('text', { x: tx, y: ty + 5, 'text-anchor': 'middle', class: isMinor ? 'st-small' : '' }, label));
                const choose = () => { sel = i; minor = isMinor; show(); };
                g.addEventListener('click', choose);
                g.addEventListener('keydown', (e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); choose(); } });
                parts.push({ g, i, isMinor });
                svg.append(g);
            });
        });
        svg.append(svgNode('text', { x: C, y: C + 5, 'text-anchor': 'middle', class: 'st-circle-mid' }, ''));
        const title = el('div', 'st-big');
        const info = el('div', 'st-muted');
        const chordRow = el('div', 'st-chord-wall');
        const show = () => {
            const k = keys[sel];
            if (!k) return;
            parts.forEach((p) => p.g.classList.toggle('sel', p.i === sel && p.isMinor === minor));
            const name = minor ? `${k.minor.slice(0, -1)} minor` : `${k.major} major`;
            svg.lastChild.textContent = minor ? k.minor : k.major;
            title.textContent = name;
            info.textContent = `${k.signature}. Relative ${minor ? 'major' : 'minor'}: ${minor ? k.major : k.minor}.`;
            chordRow.replaceChildren(...(minor ? k.minor_chords : k.major_chords).map((c) => {
                const t = el('button', 'st-chord');
                t.type = 'button';
                t.append(el('span', 'st-numeral', c.numeral), el('span', 'st-chord-name', c.name));
                t.addEventListener('click', () => s.chord(c.midi));
                return t;
            }));
        };
        root.append(svg, title, info, chordRow);
        show();
        body.append(root);
    };

    // ---- tuning tones and single notes --------------------------------------------------------------
    kinds['studio-tuner'] = (card, body, { el, table }) => {
        const d = card.data || {};
        const root = el('div', 'st st-tuner');
        const s = studio(root);
        let voice = null, current = null, sustain = false;
        const buttons = [];
        const stop = () => { voice?.release(); voice = null; current = null; buttons.forEach((b) => b.setAttribute('aria-pressed', 'false')); };
        const play = (tone, b) => {
            const again = current === tone;
            stop();
            if (again && sustain) return;
            voice = s.tone(tone.midi, { freq: tone.freq, type: 'triangle', vol: 0.3, a: 0.02, d: 0.3, sus: 0.8, r: 0.3, dur: sustain ? 0 : 2.5 });
            current = tone;
            if (sustain) b.setAttribute('aria-pressed', 'true');
        };
        const strings = el('div', 'st-strings');
        (d.tones || []).forEach((tone) => {
            const b = el('button', 'st-string');
            b.type = 'button';
            b.append(el('span', 'st-chord-name', tone.label), el('span', 'st-chord-notes', `${tone.freq} Hz`));
            b.addEventListener('click', () => play(tone, b));
            buttons.push(b);
            strings.append(b);
        });
        const hold = btn(el, 'Sustain: off', () => {
            sustain = !sustain;
            hold.textContent = `Sustain: ${sustain ? 'on' : 'off'}`;
            hold.setAttribute('aria-pressed', String(sustain));
            if (!sustain) stop();
        });
        hold.setAttribute('aria-pressed', 'false');
        s.onStop(stop);
        root.append(strings, row(el, hold, btn(el, 'Stop', stop)));
        if (d.facts?.length) root.append(table([], d.facts));
        body.append(root);
    };

    // ---- tap tempo ----------------------------------------------------------------------------------
    const MARKINGS = [[60, 'Largo'], [76, 'Adagio'], [108, 'Andante'], [120, 'Moderato'], [168, 'Allegro'], [Infinity, 'Presto']];
    kinds['studio-tap'] = (card, body, { el, ask }) => {
        const root = el('div', 'st st-tap');
        root.tabIndex = 0;
        const s = studio(root);
        let taps = [], bpm = 0;
        const face = el('div', 'st-face', '--');
        face.setAttribute('aria-live', 'polite');
        const info = el('div', 'st-muted', 'Tap at least twice.');
        const metro = btn(el, 'Metronome at this tempo', () => { if (bpm) ask(`Start a metronome at ${bpm} BPM.`); });
        metro.disabled = true;
        const tap = () => {
            const now = performance.now();
            if (taps.length && now - taps[taps.length - 1] > 2500) taps = [];
            taps = [...taps, now].slice(-9);
            s.tone(96, { dur: 0.03, type: 'square', vol: 0.08, a: 0.001, r: 0.02 });
            if (taps.length < 2) { face.textContent = '--'; info.textContent = 'Keep tapping…'; return; }
            const gaps = taps.slice(1).map((t, i) => t - taps[i]);
            bpm = Math.round(60000 / (gaps.reduce((a, b) => a + b, 0) / gaps.length));
            face.textContent = String(bpm);
            info.textContent = `BPM · ${MARKINGS.find(([max]) => bpm < max)[1]} · ${taps.length} taps`;
            metro.disabled = false;
        };
        const big = btn(el, 'TAP', tap, 'st-tap-btn');
        root.addEventListener('keydown', (e) => {
            if (e.key === ' ' || e.key === 'Enter' || e.key.toLowerCase() === 't') { e.preventDefault(); if (!e.repeat) tap(); }
        });
        const reset = btn(el, 'Reset', () => { taps = []; bpm = 0; face.textContent = '--'; info.textContent = 'Tap at least twice.'; metro.disabled = true; });
        root.append(face, info, big, row(el, reset, metro));
        body.append(root);
        root.focus({ preventScroll: true });
    };

    // ---- ear training -------------------------------------------------------------------------------
    kinds['studio-ear'] = (card, body, { el }) => {
        const intervals = card.data?.intervals || [];
        const root = el('div', 'st st-ear');
        const s = studio(root);
        let q = null, answered = false, right = 0, asked = 0;
        const direction = el('select', 'st-input');
        [['up', 'Rising'], ['down', 'Falling'], ['together', 'Together']].forEach(([v, t]) => direction.append(Object.assign(el('option', '', t), { value: v })));
        const score = el('div', 'st-muted', 'Score: 0 of 0');
        const msg = el('div', 'st-big', 'Press Play to hear an interval.');
        msg.setAttribute('aria-live', 'polite');
        const hear = () => {
            if (!q) return;
            const [a, b] = [q.low, q.low + q.iv.semitones];
            const dir = direction.value;
            if (dir === 'together') { s.tone(a, { dur: 1.4, vol: 0.18 }); s.tone(b, { dur: 1.4, vol: 0.18 }); return; }
            const [first, second] = dir === 'down' ? [b, a] : [a, b];
            s.tone(first, { dur: 0.8, vol: 0.22 });
            s.tone(second, { when: 0.85, dur: 0.9, vol: 0.22 });
        };
        const next = () => {
            q = { iv: intervals[rand(intervals.length)], low: 55 + rand(13) };
            answered = false;
            msg.textContent = 'Which interval was that?';
            answers.forEach((b) => b.classList.remove('right', 'wrong'));
            hear();
        };
        const answers = intervals.map((iv) => btn(el, iv.name, () => {
            if (!q || answered) return;
            answered = true;
            asked += 1;
            const ok = iv.semitones === q.iv.semitones;
            right += ok ? 1 : 0;
            msg.textContent = ok ? `✓ Yes, a ${q.iv.name}.` : `✗ No, it was a ${q.iv.name}.`;
            answers.find((b) => b.textContent === q.iv.name)?.classList.add('right');
            if (!ok) answers[intervals.indexOf(iv)].classList.add('wrong');
            score.textContent = `Score: ${right} of ${asked}`;
        }, 'st-answer'));
        const grid = el('div', 'st-answers');
        grid.append(...answers);
        root.append(row(el, btn(el, '▶ Play new', next, 'st-primary'), btn(el, 'Repeat', hear), direction), msg, grid, score);
        body.append(root);
    };

    // ---- note-reading quiz --------------------------------------------------------------------------
    kinds['studio-staff'] = (card, body, { el }) => {
        const d = card.data || {};
        const notes = d.notes || [];
        const root = el('div', 'st st-staff');
        const s = studio(root);
        let current = null, right = 0, asked = 0, locked = false, withSound = true;
        const W = 260, H = 150, top = 45, gap = 12, x = 170;
        const svg = svgNode('svg', { viewBox: `0 0 ${W} ${H}`, class: 'st-staff-svg', role: 'img', 'aria-label': 'A note on the staff' });
        for (let i = 0; i < 5; i++) svg.append(svgNode('line', { x1: 10, x2: W - 10, y1: top + i * gap, y2: top + i * gap, class: 'st-staff-line' }));
        svg.append(svgNode('text', { x: 16, y: d.clef === 'bass' ? top + 3 * gap + 2 : top + 4 * gap + 8,
            class: `st-clef ${d.clef === 'bass' ? 'bass' : 'treble'}` }, d.clef === 'bass' ? '𝄢' : '𝄞'));
        const noteLayer = svgNode('g', {});
        svg.append(noteLayer);
        const yOf = (pos) => top + 4 * gap - pos * (gap / 2);
        const draw = (n) => {
            noteLayer.replaceChildren();
            for (let p = -2; p >= n.pos; p -= 2) noteLayer.append(svgNode('line', { x1: x - 14, x2: x + 14, y1: yOf(p), y2: yOf(p), class: 'st-staff-line' }));
            for (let p = 10; p <= n.pos; p += 2) noteLayer.append(svgNode('line', { x1: x - 14, x2: x + 14, y1: yOf(p), y2: yOf(p), class: 'st-staff-line' }));
            noteLayer.append(svgNode('ellipse', { cx: x, cy: yOf(n.pos), rx: 8, ry: 6, transform: `rotate(-20 ${x} ${yOf(n.pos)})`, class: 'st-notehead' }));
            const up = n.pos < 4;
            noteLayer.append(svgNode('line', { x1: up ? x + 7.5 : x - 7.5, x2: up ? x + 7.5 : x - 7.5, y1: yOf(n.pos), y2: yOf(n.pos) + (up ? -36 : 36), class: 'st-stem' }));
        };
        const msg = el('div', 'st-big', 'Which note is this?');
        msg.setAttribute('aria-live', 'polite');
        const score = el('div', 'st-muted', 'Score: 0 of 0');
        const next = () => {
            let n;
            do { n = notes[rand(notes.length)]; } while (notes.length > 1 && current && n.name === current.name);
            current = n;
            locked = false;
            msg.textContent = 'Which note is this?';
            draw(n);
        };
        const letters = el('div', 'st-answers st-letters');
        'CDEFGAB'.split('').forEach((letter) => letters.append(btn(el, letter, () => {
            if (!current || locked) return;
            locked = true;
            asked += 1;
            const ok = letter === current.letter;
            right += ok ? 1 : 0;
            msg.textContent = ok ? `✓ Yes, ${current.name}.` : `✗ That was ${current.name}.`;
            score.textContent = `Score: ${right} of ${asked}`;
            if (withSound) s.tone(current.midi, { dur: 0.7, vol: 0.22 });
            s.later(ok ? 800 : 1600, next);
        }, 'st-answer')));
        const sound = btn(el, 'Sound: on', () => { withSound = !withSound; sound.textContent = `Sound: ${withSound ? 'on' : 'off'}`; });
        root.append(svg, msg, letters, row(el, score, sound));
        body.append(root);
        if (notes.length) next();
    };
})();
