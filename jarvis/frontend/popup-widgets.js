// Widgets that pop up on the Alfred screen (card kind "widget", see widgets.py): calculator, unit converter,
// sketch pad, notepad, stopwatch, countdown, pomodoro, world clocks, calendar, dice, coin flip, colour picker,
// metronome, ambient sound, breathing, typing test and picker wheel. Everything runs here in the page; the sketch
// pad and notepad save into a memory folder. Timers and sounds stop when the window closes.
(() => {
    const kinds = (window.jarvisPopupKinds = window.jarvisPopupKinds || {});
    const reduced = () => matchMedia('(prefers-reduced-motion: reduce)').matches;
    const pad2 = (n) => String(n).padStart(2, '0');
    const clock = (ms, tenths) => {
        const t = Math.max(0, ms), s = Math.floor(t / 1000), h = Math.floor(s / 3600), m = Math.floor(s / 60) % 60;
        return `${h ? `${h}:` : ''}${pad2(m)}:${pad2(s % 60)}${tenths ? `.${Math.floor(t / 100) % 10}` : ''}`;
    };
    const rand = (n) => { const a = new Uint32Array(1); crypto.getRandomValues(a); return a[0] % n; };
    const hudColour = (node, name, fallback) => getComputedStyle(node).getPropertyValue(name).trim() || fallback;

    // ---- a tiny safe calculator: numbers, + - * / ^ %, brackets, no eval -------------------------------
    function calc(text) {
        const tokens = String(text).replace(/×/g, '*').replace(/÷/g, '/').replace(/−/g, '-')
            .match(/(?:\d+\.?\d*|\.\d+)(?:e[+-]?\d+)?|[-+*/^%()]|\S/gi) || [];
        let i = 0;
        const peek = () => tokens[i], next = () => tokens[i++];
        const fail = () => { throw new Error('Not a sum'); };
        const primary = () => {
            const t = next();
            if (t === '(') { const v = sum(); if (next() !== ')') fail(); return v; }
            if (t === '-') return -power();
            if (t === '+') return power();
            if (t !== undefined && /^(\d+\.?\d*|\.\d+)(e[+-]?\d+)?$/i.test(t)) return parseFloat(t);
            return fail();
        };
        const percent = () => { let v = primary(); while (peek() === '%') { next(); v /= 100; } return v; };
        const power = () => { const b = percent(); if (peek() === '^') { next(); return b ** power(); } return b; };
        const product = () => {
            let v = power();
            while (peek() === '*' || peek() === '/') v = next() === '*' ? v * power() : v / power();
            return v;
        };
        const sum = () => {
            let v = product();
            while (peek() === '+' || peek() === '-') v = next() === '+' ? v + product() : v - product();
            return v;
        };
        if (!tokens.length) return 0;
        const v = sum();
        if (i < tokens.length || !Number.isFinite(v)) fail();
        return +v.toPrecision(12);
    }

    // ---- unit tables: factor to the base unit (metre, gram, millilitre) -------------------------------
    const UNITS = {
        length: { mm: 0.001, cm: 0.01, m: 1, km: 1000, in: 0.0254, ft: 0.3048, yd: 0.9144, mi: 1609.344 },
        weight: { mg: 0.001, g: 1, kg: 1000, tonne: 1e6, oz: 28.349523125, lb: 453.59237, stone: 6350.29318 },
        volume: {
            ml: 1, l: 1000, tsp: 5, tbsp: 15, 'cup (250 ml)': 250, 'US cup': 236.5882365, 'fl oz': 28.4130625,
            pint: 568.26125, 'US pint': 473.176473, gallon: 4546.09, 'US gallon': 3785.411784,
        },
        temperature: { '°C': 0, '°F': 0, K: 0 },
    };
    const toC = { '°C': (v) => v, '°F': (v) => (v - 32) * 5 / 9, K: (v) => v - 273.15 };
    const fromC = { '°C': (v) => v, '°F': (v) => v * 9 / 5 + 32, K: (v) => v + 273.15 };
    function convert(category, value, from, to) {
        if (category === 'temperature') return fromC[to](toC[from](value));
        return value * UNITS[category][from] / UNITS[category][to];
    }
    window.jarvisWidgets = { calc, convert };

    // ---- helpers shared by the widgets --------------------------------------------------------------
    function kit(root, el) {
        const stops = [];
        const k = {
            onStop: (fn) => stops.push(fn),
            every(ms, fn) { const id = setInterval(fn, ms); stops.push(() => clearInterval(id)); return id; },
            button(label, fn, cls = '') {
                const b = el('button', `wg-btn ${cls}`.trim(), label);
                b.type = 'button';
                b.addEventListener('click', fn);
                return b;
            },
            row(...kids) { const r = el('div', 'wg-row'); r.append(...kids); return r; },
            field(label, input) {
                const l = el('label', 'wg-field');
                l.append(el('span', '', label), input);
                return l;
            },
            input(type, attrs = {}) { const i = el('input', 'wg-input'); i.type = type; Object.assign(i, attrs); return i; },
            select(options, value) {
                const s = el('select', 'wg-input');
                for (const [v, text] of options) { const o = el('option', '', text); o.value = v; s.append(o); }
                if (value !== undefined) s.value = value;
                return s;
            },
            live(cls, text) { const d = el('div', cls, text); d.setAttribute('aria-live', 'polite'); return d; },
            audio() {
                if (!k.ctx) {
                    k.ctx = new (window.AudioContext || window.webkitAudioContext)();
                    stops.push(() => k.ctx.close().catch(() => {}));
                }
                if (k.ctx.state === 'suspended') k.ctx.resume();
                return k.ctx;
            },
            beep(freq = 880, secs = 0.15, when = 0, volume = 0.25) {
                const ctx = k.audio(), t = ctx.currentTime + when;
                const o = ctx.createOscillator(), g = ctx.createGain();
                o.frequency.value = freq;
                g.gain.setValueAtTime(0.0001, t);
                g.gain.exponentialRampToValueAtTime(volume, t + 0.01);
                g.gain.exponentialRampToValueAtTime(0.0001, t + secs);
                o.connect(g).connect(ctx.destination);
                o.start(t);
                o.stop(t + secs + 0.02);
            },
            chime() { [880, 1108.7, 1318.5].forEach((f, n) => k.beep(f, 0.5, n * 0.18, 0.2)); },
        };
        // The window closing (or being redrawn) disconnects root: stop every timer and sound.
        const watch = setInterval(() => {
            if (root.isConnected) return;
            clearInterval(watch);
            stops.forEach((fn) => { try { fn(); } catch (e) { /* already stopped */ } });
        }, 500);
        return k;
    }

    // ---- saving into the memory folders ------------------------------------------------------------
    async function folderIndex(name) {
        const r = await fetch('/memory');
        if (!r.ok) throw new Error("Couldn't read the memory folders.");
        const folders = (await r.json()).folders || [];
        const i = folders.findIndex((f) => f.name.toLowerCase() === String(name || 'Ideas').toLowerCase());
        if (i < 0) throw new Error(`There's no ${name} folder.`);
        return { index: i, name: folders[i].name, folders };
    }
    async function upload(folder, filename, body, type) {
        const { index, name } = await folderIndex(folder);
        const r = await fetch(`/memory/${index}/files/${encodeURIComponent(filename)}`, {
            method: 'PUT', headers: { 'Content-Type': type }, body,
        });
        if (!r.ok) throw new Error((await r.text()) || 'Saving failed.');
        return { folder: name, name: (await r.json()).name };
    }
    function showSaved(folder, name, mime) {
        const path = `${folder}/${name}`;
        if (window.jarvisPopup) {
            window.jarvisPopup({ kind: 'file', id: `file-${path}`.slice(0, 60), title: name, buttons: [],
                src: `/screen/file?path=${encodeURIComponent(path)}`, mime, name });
        }
    }
    const safeFile = (text, fallback) => (String(text || '').replace(/[<>:"/\\|?*\x00-\x1f]/g, '').trim().slice(0, 50) || fallback);
    const stamp = () => { const d = new Date(); return `${d.getFullYear()}-${pad2(d.getMonth() + 1)}-${pad2(d.getDate())} ${pad2(d.getHours())}${pad2(d.getMinutes())}`; };

    // ---- the widgets ---------------------------------------------------------------------------------
    const W = {};

    W.calculator = (d, root, { el }, k) => {
        root.tabIndex = 0;
        root.setAttribute('aria-label', 'Calculator: type a sum and press Enter');
        let expr = d.expression || '';
        const shown = el('div', 'wg-calc-expr');
        const result = k.live('wg-big');
        const update = (final) => {
            shown.textContent = expr || '0';
            try {
                const v = calc(expr);
                result.textContent = expr ? `= ${v.toLocaleString(undefined, { maximumFractionDigits: 10 })}` : '';
                if (final) expr = String(v);
                if (final) shown.textContent = expr;
            } catch (e) { result.textContent = final ? 'Not a sum' : ''; }
        };
        const press = (key) => {
            if (key === 'C') expr = '';
            else if (key === '⌫') expr = expr.slice(0, -1);
            else if (key === '=') return update(true);
            else expr = (expr + key).slice(0, 120);
            update(false);
        };
        const keys = el('div', 'wg-calc-keys');
        ['C', '(', ')', '⌫', '7', '8', '9', '÷', '4', '5', '6', '×', '1', '2', '3', '−', '0', '.', '%', '+', '^', '='].forEach((key) => {
            keys.append(k.button(key, () => press(key === '÷' ? '/' : key === '×' ? '*' : key === '−' ? '-' : key),
                key === '=' ? 'wg-wide wg-primary' : ''));
        });
        root.addEventListener('keydown', (e) => {
            if (e.ctrlKey || e.metaKey || e.altKey) return;
            const map = { Enter: '=', '=': '=', Backspace: '⌫', Delete: 'C', c: 'C', C: 'C', x: '*' };
            const key = map[e.key] || (/^[\d.+\-*/^%()]$/.test(e.key) ? e.key : null);
            if (!key || (e.key === 'Enter' && e.target.tagName === 'BUTTON')) return;
            e.preventDefault();
            press(key);
        });
        root.append(shown, result, keys);
        update(false);
    };

    W.unit_converter = (d, root, { el }, k) => {
        const cat = k.select(Object.keys(UNITS).map((c) => [c, c[0].toUpperCase() + c.slice(1)]), d.category || 'length');
        const value = k.input('number', { value: d.value ?? 1, step: 'any' });
        value.setAttribute('aria-label', 'Value');
        const from = k.select([]), to = k.select([]);
        from.setAttribute('aria-label', 'From unit');
        to.setAttribute('aria-label', 'To unit');
        const out = k.live('wg-big');
        const all = el('ul', 'wg-list');
        const defaults = { length: ['mi', 'km'], weight: ['stone', 'kg'], volume: ['pint', 'ml'], temperature: ['°F', '°C'] };
        const fill = () => {
            const units = Object.keys(UNITS[cat.value]);
            [from, to].forEach((s, n) => {
                s.replaceChildren(...units.map((u) => Object.assign(el('option', '', u), { value: u })));
                s.value = defaults[cat.value][n];
            });
            run();
        };
        const fmt = (v) => (Math.abs(v) >= 1e6 || (Math.abs(v) < 1e-4 && v) ? v.toExponential(4) : +v.toPrecision(6)).toLocaleString();
        const run = () => {
            const v = parseFloat(value.value);
            if (!Number.isFinite(v)) { out.textContent = 'Type a number'; all.replaceChildren(); return; }
            out.textContent = `${fmt(v)} ${from.value} = ${fmt(convert(cat.value, v, from.value, to.value))} ${to.value}`;
            all.replaceChildren(...Object.keys(UNITS[cat.value]).filter((u) => u !== from.value)
                .map((u) => el('li', '', `${fmt(convert(cat.value, v, from.value, u))} ${u}`)));
        };
        const swap = k.button('⇄', () => { [from.value, to.value] = [to.value, from.value]; run(); });
        swap.setAttribute('aria-label', 'Swap units');
        cat.addEventListener('change', fill);
        [value, from, to].forEach((x) => x.addEventListener('input', run));
        root.append(k.row(k.field('Convert', cat)), k.row(value, from, swap, to), out, all);
        fill();
    };

    W.sketch_pad = (d, root, { el }, k) => {
        const PAPER = '#ffffff';
        const canvas = el('canvas', 'wg-canvas');
        canvas.width = 860; canvas.height = 560;
        canvas.setAttribute('aria-label', 'Drawing area');
        const g = canvas.getContext('2d');
        const clear = () => { g.fillStyle = PAPER; g.fillRect(0, 0, canvas.width, canvas.height); };
        clear();
        let colour = '#111111', erasing = false, size = 4, last = null;
        const pos = (e) => { const r = canvas.getBoundingClientRect(); return [(e.clientX - r.left) * canvas.width / r.width, (e.clientY - r.top) * canvas.height / r.height]; };
        canvas.addEventListener('pointerdown', (e) => { e.preventDefault(); canvas.setPointerCapture(e.pointerId); last = pos(e); draw(e); });
        canvas.addEventListener('pointermove', (e) => { if (last) draw(e); });
        ['pointerup', 'pointercancel', 'pointerleave'].forEach((t) => canvas.addEventListener(t, () => { last = null; }));
        function draw(e) {
            const p = pos(e), pressure = e.pointerType === 'pen' && e.pressure ? e.pressure * 2 : 1;
            g.strokeStyle = erasing ? PAPER : colour;
            g.lineWidth = (erasing ? size * 4 : size) * pressure;
            g.lineCap = g.lineJoin = 'round';
            g.beginPath(); g.moveTo(...last); g.lineTo(...p); g.stroke();
            last = p;
        }
        const swatches = el('div', 'wg-swatches');
        const pick = (c, b) => { colour = c; erasing = false; swatches.querySelectorAll('button').forEach((x) => x.setAttribute('aria-pressed', String(x === b))); };
        ['#111111', '#e53935', '#fb8c00', '#fdd835', '#43a047', '#1e88e5', '#8e24aa', '#8d6e63'].forEach((c, n) => {
            const b = k.button('', () => pick(c, b), 'wg-swatch');
            b.style.background = c;
            b.setAttribute('aria-label', `Colour ${c}`);
            b.setAttribute('aria-pressed', String(n === 0));
            swatches.append(b);
        });
        const custom = k.input('color', { value: '#111111' });
        custom.setAttribute('aria-label', 'Any colour');
        custom.addEventListener('input', () => pick(custom.value, null));
        const eraser = k.button('Eraser', () => { erasing = !erasing; eraser.setAttribute('aria-pressed', String(erasing)); });
        eraser.setAttribute('aria-pressed', 'false');
        const width = k.input('range', { min: 1, max: 30, value: size });
        width.setAttribute('aria-label', 'Pen size');
        width.addEventListener('input', () => { size = +width.value; });
        const name = k.input('text', { placeholder: 'Sketch name', maxLength: 50 });
        name.setAttribute('aria-label', 'Sketch name');
        const msg = k.live('wg-msg');
        const save = k.button(`Save to ${d.folder || 'Ideas'}`, () => {
            msg.textContent = 'Saving…';
            canvas.toBlob(async (blob) => {
                try {
                    const saved = await upload(d.folder, `${safeFile(name.value, `Sketch ${stamp()}`)}.png`, blob, 'image/png');
                    msg.textContent = `Saved ${saved.name} in ${saved.folder}.`;
                    showSaved(saved.folder, saved.name, 'image/png');
                } catch (e) { msg.textContent = e.message; }
            }, 'image/png');
        }, 'wg-primary');
        const wipe = k.button('Clear', () => { if (confirm('Clear the whole sketch?')) clear(); });
        root.append(canvas, k.row(swatches, custom), k.row(eraser, width, wipe), k.row(name, save), msg);
    };

    W.notepad = (d, root, { el }, k) => {
        const title = k.input('text', { placeholder: 'Title', maxLength: 50, value: d.title || '' });
        title.setAttribute('aria-label', 'Note title');
        const text = el('textarea', 'wg-input wg-note');
        text.value = d.text || '';
        text.setAttribute('aria-label', 'Note');
        text.placeholder = 'Write here…';
        const count = el('span', 'wg-muted');
        const counter = () => { const t = text.value.trim(); count.textContent = `${t ? t.split(/\s+/).length : 0} words`; };
        text.addEventListener('input', counter);
        counter();
        const folder = k.select([[d.folder || 'Ideas', d.folder || 'Ideas']], d.folder || 'Ideas');
        folder.setAttribute('aria-label', 'Folder');
        folderIndex(d.folder).then(({ folders }) => {
            folder.replaceChildren(...folders.map((f) => Object.assign(el('option', '', f.name), { value: f.name })));
            folder.value = d.folder || 'Ideas';
        }).catch(() => {});
        const msg = k.live('wg-msg');
        const save = async () => {
            if (!text.value.trim()) { msg.textContent = 'Write something first.'; return; }
            msg.textContent = 'Saving…';
            try {
                const saved = await upload(folder.value, `${safeFile(title.value, `Note ${stamp()}`)}.md`, text.value, 'text/markdown');
                msg.textContent = `Saved ${saved.name} in ${saved.folder}.`;
            } catch (e) { msg.textContent = e.message; }
        };
        root.addEventListener('keydown', (e) => { if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 's') { e.preventDefault(); save(); } });
        root.append(title, text, k.row(count, folder, k.button('Save', save, 'wg-primary')), msg);
    };

    W.stopwatch = (d, root, { el }, k) => {
        let start = 0, banked = 0, running = false, laps = [];
        const now = () => banked + (running ? performance.now() - start : 0);
        const face = el('div', 'wg-face', clock(0, true));
        face.setAttribute('role', 'timer');
        const list = el('ol', 'wg-list wg-laps');
        const go = k.button('Start', () => {
            if (running) { banked = now(); running = false; } else { start = performance.now(); running = true; }
            go.textContent = running ? 'Stop' : 'Start';
        }, 'wg-primary');
        const lap = k.button('Lap', () => {
            const t = now(), prev = laps.length ? laps[laps.length - 1] : 0;
            if (!t) return;
            laps.push(t);
            list.prepend(el('li', '', `Lap ${laps.length}: ${clock(t - prev, true)}  (total ${clock(t, true)})`));
        });
        const reset = k.button('Reset', () => { running = false; banked = 0; laps = []; list.replaceChildren(); go.textContent = 'Start'; face.textContent = clock(0, true); });
        k.every(100, () => { if (running) face.textContent = clock(now(), true); });
        root.append(face, k.row(go, lap, reset), list);
    };

    function countdownFace(k, el) {
        const face = el('div', 'wg-face');
        face.setAttribute('role', 'timer');
        return face;
    }

    W.countdown = (d, root, { el }, k) => {
        let total = (d.seconds || 300) * 1000, left = total, endAt = 0, running = false;
        const face = countdownFace(k, el);
        const status = k.live('wg-msg');
        const mins = k.input('number', { min: 0, max: 1440, value: Math.floor(total / 60000) });
        const secs = k.input('number', { min: 0, max: 59, value: Math.floor(total / 1000) % 60 });
        mins.setAttribute('aria-label', 'Minutes');
        secs.setAttribute('aria-label', 'Seconds');
        const draw = () => { face.textContent = clock(Math.ceil(left / 1000) * 1000); face.classList.toggle('over', left <= 0); };
        const set = () => { if (running) return; total = left = ((+mins.value || 0) * 60 + (+secs.value || 0)) * 1000; draw(); };
        [mins, secs].forEach((x) => x.addEventListener('input', set));
        const go = k.button('Start', () => {
            if (running) { left = endAt - Date.now(); running = false; }
            else if (left > 0) { endAt = Date.now() + left; running = true; status.textContent = ''; k.audio(); }
            go.textContent = running ? 'Pause' : 'Start';
        }, 'wg-primary');
        const reset = k.button('Reset', () => { running = false; left = total; go.textContent = 'Start'; status.textContent = ''; draw(); });
        k.every(200, () => {
            if (!running) return;
            left = endAt - Date.now();
            if (left <= 0) { left = 0; running = false; go.textContent = 'Start'; status.textContent = "Time's up!"; k.chime(); setTimeout(() => root.isConnected && k.chime(), 900); }
            draw();
        });
        root.append(face, k.row(k.field('Min', mins), k.field('Sec', secs)), k.row(go, reset), status);
        draw();
        if (d.autostart) go.click();
    };

    W.pomodoro = (d, root, { el }, k) => {
        const lengths = { focus: (d.work || 25) * 60000, break: (d.rest || 5) * 60000 };
        let phase = 'focus', left = lengths.focus, endAt = 0, running = false, done = 0;
        const label = k.live('wg-phase');
        const face = countdownFace(k, el);
        const count = el('div', 'wg-muted');
        const draw = () => {
            label.textContent = phase === 'focus' ? 'Focus' : 'Break';
            face.textContent = clock(Math.ceil(left / 1000) * 1000);
            count.textContent = `Sessions done: ${done}`;
            root.dataset.phase = phase;
        };
        const flip = () => {
            if (phase === 'focus') done++;
            phase = phase === 'focus' ? 'break' : 'focus';
            left = lengths[phase];
            endAt = Date.now() + left;
            draw();
        };
        const go = k.button('Start', () => {
            if (running) { left = endAt - Date.now(); running = false; } else { endAt = Date.now() + left; running = true; k.audio(); }
            go.textContent = running ? 'Pause' : 'Start';
        }, 'wg-primary');
        const skip = k.button('Skip', () => { flip(); if (!running) left = lengths[phase]; draw(); });
        const reset = k.button('Reset', () => { running = false; phase = 'focus'; left = lengths.focus; done = 0; go.textContent = 'Start'; draw(); });
        k.every(250, () => {
            if (!running) return;
            left = endAt - Date.now();
            if (left <= 0) { k.chime(); flip(); }
            draw();
        });
        root.append(label, face, count, k.row(go, skip, reset), el('div', 'wg-muted', `${d.work || 25} minutes focus, ${d.rest || 5} minutes break.`));
        draw();
    };

    W.world_clocks = (d, root, { el }, k) => {
        const list = el('ul', 'wg-list wg-clocks');
        const rows = [{ label: 'Here', zone: undefined }, ...(d.clocks || [])].map((c) => {
            const li = el('li');
            const name = el('span', 'wg-clock-name', c.label);
            const time = el('span', 'wg-clock-time');
            const day = el('span', 'wg-muted');
            li.append(name, time, day);
            list.append(li);
            let fmt, dayFmt;
            try {
                fmt = new Intl.DateTimeFormat('en-GB', { timeZone: c.zone, hour: '2-digit', minute: '2-digit', second: '2-digit' });
                dayFmt = new Intl.DateTimeFormat('en-GB', { timeZone: c.zone, weekday: 'short', day: 'numeric', month: 'short', timeZoneName: 'short' });
            } catch (e) { time.textContent = 'Unknown zone'; }
            return { time, day, fmt, dayFmt };
        });
        const tick = () => {
            const now = new Date();
            rows.forEach((r) => { if (r.fmt) { r.time.textContent = r.fmt.format(now); r.day.textContent = r.dayFmt.format(now); } });
        };
        tick();
        k.every(1000, tick);
        root.append(list);
    };

    W.calendar = (d, root, { el }, k) => {
        const today = new Date();
        let year = d.year || today.getFullYear(), month = (d.month || today.getMonth() + 1) - 1;
        const head = k.live('wg-phase');
        const grid = el('table', 'wg-cal');
        const draw = () => {
            const first = new Date(year, month, 1);
            head.textContent = first.toLocaleDateString('en-GB', { month: 'long', year: 'numeric' });
            const thead = el('thead'), tr = el('tr');
            ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'].forEach((n) => { const th = el('th', '', n); th.scope = 'col'; tr.append(th); });
            thead.append(tr);
            const body = el('tbody');
            const offset = (first.getDay() + 6) % 7, days = new Date(year, month + 1, 0).getDate();
            let row = el('tr');
            for (let n = 0; n < offset; n++) row.append(el('td'));
            for (let day = 1; day <= days; day++) {
                const isToday = day === today.getDate() && month === today.getMonth() && year === today.getFullYear();
                const td = el('td', isToday ? 'today' : '', String(day));
                if (isToday) td.setAttribute('aria-current', 'date');
                row.append(td);
                if (row.children.length === 7) { body.append(row); row = el('tr'); }
            }
            if (row.children.length) { while (row.children.length < 7) row.append(el('td')); body.append(row); }
            grid.replaceChildren(thead, body);
        };
        const move = (n) => { month += n; if (month < 0) { month = 11; year--; } if (month > 11) { month = 0; year++; } draw(); };
        const prev = k.button('‹ Prev', () => move(-1)), next = k.button('Next ›', () => move(1));
        const home = k.button('Today', () => { year = today.getFullYear(); month = today.getMonth(); draw(); });
        root.addEventListener('keydown', (e) => {
            if (e.target.closest('input, textarea')) return;
            if (e.key === 'ArrowLeft' || e.key === 'PageUp') { e.preventDefault(); move(-1); }
            if (e.key === 'ArrowRight' || e.key === 'PageDown') { e.preventDefault(); move(1); }
        });
        root.append(k.row(prev, head, next), grid, k.row(home));
        draw();
    };

    W.dice = (d, root, { el }, k) => {
        const count = k.select([1, 2, 3, 4, 5, 6, 7, 8, 9, 10].map((n) => [n, String(n)]), String(d.count || 1));
        const sides = k.select([4, 6, 8, 10, 12, 20, 100].map((n) => [n, `d${n}`]), String(d.sides || 6));
        const tray = el('div', 'wg-dice');
        const total = k.live('wg-big');
        let rolling = false;
        const roll = () => {
            if (rolling) return;
            const n = +count.value, s = +sides.value;
            const faces = Array.from({ length: n }, () => rand(s) + 1);
            const paint = (vals) => tray.replaceChildren(...vals.map((v) => el('span', 'wg-die', String(v))));
            const finish = () => { rolling = false; paint(faces); total.textContent = n > 1 ? `Total ${faces.reduce((a, b) => a + b, 0)}` : `Rolled ${faces[0]}`; };
            total.textContent = '';
            if (reduced()) return finish();
            rolling = true;
            tray.classList.add('rolling');
            let steps = 0;
            const id = k.every(70, () => {
                paint(faces.map(() => rand(s) + 1));
                if (++steps > 9) { clearInterval(id); tray.classList.remove('rolling'); finish(); }
            });
        };
        root.append(k.row(k.field('Dice', count), k.field('Sides', sides), k.button('Roll', roll, 'wg-primary')), tray, total);
    };

    W.coin_flip = (d, root, { el }, k) => {
        const coin = el('div', 'wg-coin', 'H');
        coin.setAttribute('aria-hidden', 'true');
        const said = k.live('wg-big');
        const tally = el('div', 'wg-muted');
        const score = { Heads: 0, Tails: 0 };
        const flip = () => {
            const side = rand(2) ? 'Heads' : 'Tails';
            score[side]++;
            const show = () => { coin.textContent = side[0]; said.textContent = side; tally.textContent = `Heads ${score.Heads} · Tails ${score.Tails}`; };
            if (reduced()) return show();
            said.textContent = '';
            coin.classList.remove('flip');
            void coin.offsetWidth;
            coin.classList.add('flip');
            setTimeout(show, 600);
        };
        root.append(coin, said, k.row(k.button('Flip', flip, 'wg-primary'), k.button('Reset', () => { score.Heads = score.Tails = 0; tally.textContent = ''; said.textContent = ''; })), tally);
    };

    async function copyText(text) {
        try { await navigator.clipboard.writeText(text); return true; } catch (e) {
            const t = document.createElement('textarea');
            t.value = text;
            t.style.position = 'fixed'; t.style.opacity = '0';
            document.body.append(t);
            t.select();
            let ok = false;
            try { ok = document.execCommand('copy'); } catch (err) { ok = false; }
            t.remove();
            return ok;
        }
    }

    W.colour_picker = (d, root, { el }, k) => {
        const pick = k.input('color', { value: d.colour || '#3fa9ff' });
        pick.setAttribute('aria-label', 'Pick a colour');
        const swatch = el('div', 'wg-colour');
        const msg = k.live('wg-msg');
        const lines = el('div', 'wg-colour-lines');
        const draw = () => {
            const hex = pick.value, [r, g, b] = [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16));
            const max = Math.max(r, g, b) / 255, min = Math.min(r, g, b) / 255, l = (max + min) / 2, c = max - min;
            const s = c ? c / (1 - Math.abs(2 * l - 1)) : 0;
            const hue = !c ? 0 : max === r / 255 ? ((g - b) / 255 / c) % 6 : max === g / 255 ? (b - r) / 255 / c + 2 : (r - g) / 255 / c + 4;
            const values = [hex, `rgb(${r}, ${g}, ${b})`, `hsl(${Math.round((hue * 60 + 360) % 360)}, ${Math.round(s * 100)}%, ${Math.round(l * 100)}%)`];
            swatch.style.background = hex;
            lines.replaceChildren(...values.map((v) => k.row(el('code', '', v), k.button('Copy', async () => {
                msg.textContent = (await copyText(v)) ? `Copied ${v}` : 'Copy failed; select the text instead.';
            }))));
        };
        pick.addEventListener('input', draw);
        root.append(k.row(pick, swatch), lines, msg);
        draw();
    };

    W.metronome = (d, root, { el }, k) => {
        let bpm = d.bpm || 100, beats = 4, running = false, beat = 0, nextAt = 0, timer = null;
        const bpmLabel = k.live('wg-big', `${bpm} BPM`);
        const slider = k.input('range', { min: 30, max: 240, value: bpm });
        slider.setAttribute('aria-label', 'Beats per minute');
        slider.addEventListener('input', () => { bpm = +slider.value; bpmLabel.textContent = `${bpm} BPM`; });
        const bar = k.select([[1, 'No accent'], [2, '2/4'], [3, '3/4'], [4, '4/4'], [6, '6/8']], '4');
        bar.addEventListener('change', () => { beats = +bar.value; });
        const dots = el('div', 'wg-beats');
        const light = (n) => { dots.replaceChildren(...Array.from({ length: beats }, (_, i) => el('span', i === n ? 'on' : ''))); };
        const schedule = () => {
            const ctx = k.audio();
            while (nextAt < ctx.currentTime + 0.12) {
                const n = beat % beats;
                k.beep(n === 0 && beats > 1 ? 1500 : 1000, 0.05, nextAt - ctx.currentTime, 0.35);
                setTimeout(() => light(n), Math.max(0, (nextAt - ctx.currentTime) * 1000));
                nextAt += 60 / bpm;
                beat++;
            }
        };
        const stop = () => { running = false; clearInterval(timer); go.textContent = 'Start'; light(-1); };
        const go = k.button('Start', () => {
            if (running) return stop();
            running = true; beat = 0; nextAt = k.audio().currentTime + 0.05;
            timer = setInterval(schedule, 25);
            go.textContent = 'Stop';
        }, 'wg-primary');
        k.onStop(() => clearInterval(timer));
        root.append(bpmLabel, slider, k.row(k.field('Beat', bar), go), dots);
        light(-1);
    };

    function noiseBuffer(ctx, type) {
        const len = ctx.sampleRate * 4, buf = ctx.createBuffer(1, len, ctx.sampleRate), out = buf.getChannelData(0);
        let b0 = 0, b1 = 0, b2 = 0, b3 = 0, b4 = 0, b5 = 0, b6 = 0, last = 0;
        for (let i = 0; i < len; i++) {
            const w = Math.random() * 2 - 1;
            if (type === 'brown') { last = (last + 0.02 * w) / 1.02; out[i] = last * 3.5; } else if (type === 'pink' || type === 'rain') {
                b0 = 0.99886 * b0 + w * 0.0555179; b1 = 0.99332 * b1 + w * 0.0750759; b2 = 0.969 * b2 + w * 0.153852;
                b3 = 0.8665 * b3 + w * 0.3104856; b4 = 0.55 * b4 + w * 0.5329522; b5 = -0.7616 * b5 - w * 0.016898;
                out[i] = (b0 + b1 + b2 + b3 + b4 + b5 + b6 + w * 0.5362) * 0.11;
                b6 = w * 0.115926;
                if (type === 'rain' && Math.random() < 0.0004) out[i] += (Math.random() - 0.5) * 0.9;  // drops
            } else out[i] = w * 0.5;
        }
        return buf;
    }

    W.ambient_sound = (d, root, { el }, k) => {
        let src = null, gain = null, endsAt = 0;
        const sound = k.select([['rain', 'Rain'], ['white', 'White noise'], ['pink', 'Pink noise'], ['brown', 'Brown noise']], d.sound || 'rain');
        const volume = k.input('range', { min: 0, max: 100, value: 50 });
        const sleep = k.select([[0, 'Off'], [5, '5 min'], [15, '15 min'], [30, '30 min'], [45, '45 min'], [60, '1 hour'], [90, '90 min']], '0');
        if (d.minutes) {
            if (![...sleep.options].some((o) => +o.value === d.minutes)) sleep.append(Object.assign(el('option', '', `${d.minutes} min`), { value: d.minutes }));
            sleep.value = String(d.minutes);
        }
        const status = k.live('wg-msg');
        const level = () => (volume.value / 100) ** 2 * 0.8;
        const stop = () => {
            if (src) { try { src.stop(); } catch (e) { /* already stopped */ } src.disconnect(); src = null; }
            endsAt = 0; go.textContent = 'Play'; status.textContent = '';
        };
        const start = () => {
            stop();
            const ctx = k.audio();
            src = ctx.createBufferSource();
            src.buffer = noiseBuffer(ctx, sound.value);
            src.loop = true;
            gain = ctx.createGain();
            gain.gain.value = level();
            let node = src;
            if (sound.value === 'rain') {
                const hp = ctx.createBiquadFilter(), lp = ctx.createBiquadFilter();
                hp.type = 'highpass'; hp.frequency.value = 400;
                lp.type = 'lowpass'; lp.frequency.value = 6000;
                node.connect(hp); hp.connect(lp); node = lp;
            }
            node.connect(gain).connect(ctx.destination);
            src.start();
            endsAt = +sleep.value ? Date.now() + sleep.value * 60000 : 0;
            go.textContent = 'Stop';
        };
        const go = k.button('Play', () => (src ? stop() : start()), 'wg-primary');
        volume.setAttribute('aria-label', 'Volume');
        volume.addEventListener('input', () => { if (gain) gain.gain.setTargetAtTime(level(), k.audio().currentTime, 0.1); });
        sound.addEventListener('change', () => { if (src) start(); });
        sleep.addEventListener('change', () => { if (src) endsAt = +sleep.value ? Date.now() + sleep.value * 60000 : 0; });
        k.every(1000, () => {
            if (!src || !endsAt) return;
            const left = endsAt - Date.now();
            if (left <= 0) {
                gain.gain.setTargetAtTime(0, k.audio().currentTime, 1.5);
                const old = src;
                src = null;
                setTimeout(() => { try { old.stop(); } catch (e) { /* closed */ } }, 5000);
                endsAt = 0; go.textContent = 'Play'; status.textContent = 'Sleep timer finished.';
            } else status.textContent = `Stops in ${clock(left)}`;
        });
        k.onStop(stop);
        root.append(k.row(k.field('Sound', sound), go), k.field('Volume', volume), k.field('Sleep timer', sleep), status);
    };

    W.breathing = (d, root, { el }, k) => {
        const PATTERNS = {
            box: [['Breathe in', 4, 'in'], ['Hold', 4, 'hold'], ['Breathe out', 4, 'out'], ['Hold', 4, 'hold']],
            '4-7-8': [['Breathe in', 4, 'in'], ['Hold', 7, 'hold'], ['Breathe out', 8, 'out']],
        };
        const pattern = k.select([['box', 'Box 4-4-4-4'], ['4-7-8', '4-7-8']], d.pattern || 'box');
        const circle = el('div', 'wg-breath');
        circle.setAttribute('aria-hidden', 'true');
        const step = k.live('wg-big', 'Ready');
        const secs = el('div', 'wg-face wg-small');
        const cycles = el('div', 'wg-muted');
        let running = false, phase = 0, left = 0, rounds = 0;
        const enter = () => {
            const [words, n, move] = PATTERNS[pattern.value][phase];
            left = n;
            step.textContent = words;
            secs.textContent = String(left);
            circle.style.transitionDuration = reduced() ? '0s' : `${n}s`;
            if (move !== 'hold') circle.classList.toggle('big', move === 'in');
        };
        k.every(1000, () => {
            if (!running) return;
            if (--left > 0) { secs.textContent = String(left); return; }
            phase = (phase + 1) % PATTERNS[pattern.value].length;
            if (!phase) cycles.textContent = `Rounds: ${++rounds}`;
            enter();
        });
        const go = k.button('Start', () => {
            running = !running;
            go.textContent = running ? 'Stop' : 'Start';
            if (running) { phase = 0; enter(); } else { step.textContent = 'Ready'; secs.textContent = ''; circle.classList.remove('big'); }
        }, 'wg-primary');
        pattern.addEventListener('change', () => { if (running) { phase = 0; enter(); } });
        root.append(k.row(k.field('Pattern', pattern), go), circle, step, secs, cycles);
    };

    const SENTENCES = [
        'The quick brown fox jumps over the lazy dog while the kettle boils in the kitchen.',
        'A gentle rain fell over the city as the last train pulled slowly out of the station.',
        'Please remember to water the plants and put the bins out before Thursday morning.',
        'Good habits are built one small step at a time, so start today and keep going.',
        'The museum opens at ten, but the queue for the dinosaur hall starts much earlier.',
        'She packed a flask of tea, two sandwiches and a map before heading up the hill.',
        'Typing quickly is useful, but typing accurately saves far more time in the end.',
        'On clear nights the stars above the countryside look close enough to touch.',
        'Every good cup of coffee begins with fresh beans and water that is not too hot.',
        'The football match went to extra time and the whole pub held its breath.',
    ];

    W.typing_test = (d, root, { el }, k) => {
        let target = '', started = 0, finished = false, last = -1;
        const text = el('p', 'wg-typing');
        const box = el('textarea', 'wg-input');
        box.rows = 3;
        box.setAttribute('aria-label', 'Type the sentence here');
        box.spellcheck = false;
        const result = k.live('wg-big');
        const paint = () => {
            const typed = box.value;
            text.replaceChildren(...[...target].map((c, i) => el('span', i >= typed.length ? '' : typed[i] === c ? 'ok' : 'bad', c)));
        };
        const fresh = () => {
            let n;
            do n = rand(SENTENCES.length); while (n === last && SENTENCES.length > 1);
            last = n;
            target = SENTENCES[n];
            box.value = ''; box.disabled = false; started = 0; finished = false; result.textContent = '';
            paint();
        };
        box.addEventListener('input', () => {
            if (finished) return;
            if (!started) started = performance.now();
            paint();
            if (box.value.length >= target.length) {
                finished = true;
                const mins = Math.max(performance.now() - started, 1000) / 60000;
                const right = [...target].filter((c, i) => box.value[i] === c).length;
                result.textContent = `${Math.round(right / 5 / mins)} WPM · ${Math.round((right / target.length) * 100)}% accurate`;
                box.disabled = true;
            }
        });
        root.append(text, box, result, k.row(k.button('New sentence', () => { fresh(); box.focus(); }, 'wg-primary')));
        fresh();
    };

    W.picker_wheel = (d, root, { el, ask }, k) => {
        const options = el('textarea', 'wg-input');
        options.rows = 3;
        options.value = (d.options && d.options.length ? d.options : ['Pizza', 'Curry', 'Tacos', 'Pasta']).join('\n');
        options.setAttribute('aria-label', 'Options, one per line');
        const canvas = el('canvas', 'wg-wheel');
        canvas.width = canvas.height = 520;
        canvas.setAttribute('role', 'img');
        const result = k.live('wg-big');
        const g = canvas.getContext('2d');
        let angle = 0, spinning = false, picked = '';
        const items = () => options.value.split('\n').map((s) => s.trim()).filter(Boolean).slice(0, 20);
        const draw = () => {
            const list = items(), n = Math.max(1, list.length), R = 250, c = 260;
            const main = hudColour(canvas, '--hud', '#3fa9ff'), bright = hudColour(canvas, '--hud-bright', '#9fd8ff'), bg = hudColour(canvas, '--hud-bg', '#000');
            canvas.setAttribute('aria-label', `Wheel with ${list.join(', ')}`);
            g.clearRect(0, 0, 520, 520);
            list.forEach((label, i) => {
                const a0 = angle + (i / n) * 2 * Math.PI, a1 = angle + ((i + 1) / n) * 2 * Math.PI;
                g.beginPath(); g.moveTo(c, c); g.arc(c, c, R, a0, a1); g.closePath();
                g.fillStyle = i % 2 ? bg : main; g.globalAlpha = i % 2 ? 0.9 : 0.55; g.fill();
                g.globalAlpha = 1; g.strokeStyle = bright; g.lineWidth = 2; g.stroke();
                g.save(); g.translate(c, c); g.rotate((a0 + a1) / 2);
                g.fillStyle = bright; g.font = '600 22px system-ui, sans-serif'; g.textAlign = 'right'; g.textBaseline = 'middle';
                g.fillText(label.length > 18 ? `${label.slice(0, 17)}…` : label, R - 16, 0);
                g.restore();
            });
            g.fillStyle = bright;  // pointer at the top
            g.beginPath(); g.moveTo(c - 14, 2); g.lineTo(c + 14, 2); g.lineTo(c, 34); g.closePath(); g.fill();
        };
        const land = () => {
            const list = items(), n = list.length;
            const at = ((-Math.PI / 2 - angle) % (2 * Math.PI) + 4 * Math.PI) % (2 * Math.PI);
            picked = list[Math.floor(at / (2 * Math.PI / n)) % n];
            result.textContent = picked;
            tell.disabled = false;
        };
        const spin = () => {
            if (spinning || items().length < 2) { if (items().length < 2) result.textContent = 'Add at least two options.'; return; }
            const turn = (4 + rand(4)) * 2 * Math.PI + (rand(3600) / 3600) * 2 * Math.PI;
            result.textContent = ''; tell.disabled = true;
            if (reduced()) { angle += turn; draw(); return land(); }
            spinning = true;
            const from = angle, t0 = performance.now(), ms = 3500;
            const frame = (t) => {
                if (!root.isConnected) return;
                const p = Math.min(1, (t - t0) / ms);
                angle = from + turn * (1 - (1 - p) ** 3);
                draw();
                if (p < 1) requestAnimationFrame(frame); else { spinning = false; land(); }
            };
            requestAnimationFrame(frame);
        };
        const tell = k.button('Tell Alfred', () => { if (picked) ask(`The picker wheel landed on "${picked}". Tell me the result.`); });
        tell.disabled = true;
        options.addEventListener('input', () => { if (!spinning) draw(); });
        root.append(canvas, result, k.row(k.button('Spin', spin, 'wg-primary'), tell), options);
        draw();
    };

    kinds.widget = (card, body, { el, ask, table, chart, image }) => {
        const data = card.data || {};
        const make = W[data.widget];
        const root = el('div', `wg wg-${String(data.widget || '').replace(/_/g, '-')}`);
        body.append(root);
        if (!make) { root.append(el('div', 'pop-empty', "This widget isn't available.")); return; }
        make(data, root, { el, ask, table, chart, image }, kit(root, el));
    };
})();
