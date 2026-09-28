// Cooking pop-up kinds (cooking.py): hands-free cook mode one step at a time, several kitchen timers side by side
// with chimes (in the page only, apart from Alfred's own timers), and the batch cooking plan's two tables.
(() => {
    const kinds = window.jarvisPopupKinds = window.jarvisPopupKinds || {};

    const isTop = (node) => {
        const win = node.closest('.popup');
        if (!win) return false;
        const z = (w) => Number(w.style.zIndex) || 0;
        return [...document.querySelectorAll('.popup')].every((w) => w === win || z(w) <= z(win));
    };

    kinds['cooking-steps'] = (card, body, { el, ask }) => {
        const { recipe = '', steps = [], ingredients = [], start = 0 } = card.data || {};
        if (!steps.length) { body.append(el('div', 'pop-empty', 'No steps saved for this recipe.')); return; }
        let at = Math.min(Math.max(0, start), steps.length - 1);
        const box = el('div', 'ck-steps');
        const count = el('div', 'ck-count'), text = el('div', 'ck-text'), dots = el('div', 'ck-dots');
        const row = el('div', 'ck-controls');
        const back = el('button', 'pop-action', '◀ Back'), next = el('button', 'pop-action', 'Next ▶');
        const read = el('button', 'pop-action', 'Read this step'), timer = el('button', 'pop-action');
        const show = el('button', 'pop-action', 'Ingredients');
        row.append(back, next, read, timer, show);
        const list = el('ul', 'ck-ingredients');
        ingredients.forEach((i) => list.append(el('li', '', i)));
        list.hidden = true;
        box.append(count, text, dots, row, list);
        body.append(box);
        steps.forEach((_, i) => {
            const d = el('button', 'ck-dot');
            d.title = `Step ${i + 1}`;
            d.addEventListener('click', () => { at = i; draw(); });
            dots.append(d);
        });

        const draw = () => {
            const step = steps[at];
            count.textContent = `${recipe}: step ${at + 1} of ${steps.length}`;
            text.textContent = step.text;
            [...dots.children].forEach((d, i) => d.classList.toggle('on', i === at));
            back.disabled = at === 0;
            next.textContent = at === steps.length - 1 ? 'Finished ✓' : 'Next ▶';
            timer.hidden = !step.minutes;
            timer.textContent = step.minutes ? `Timer ${+step.minutes.toFixed(1)} min` : '';
        };
        back.addEventListener('click', () => { if (at > 0) { at -= 1; draw(); } });
        next.addEventListener('click', () => {
            if (at < steps.length - 1) { at += 1; draw(); return; }
            ask(`I've just cooked ${recipe}; log that I made it today.`);
        });
        read.addEventListener('click', () => ask(`Read this cooking step aloud, word for word: step ${at + 1} of ${recipe}. ${steps[at].text}`));
        timer.addEventListener('click', () => {
            const m = steps[at].minutes;
            if (m) ask(`Set a timer for ${Math.round(m * 60)} seconds called ${recipe} step ${at + 1}.`);
        });
        show.addEventListener('click', () => { list.hidden = !list.hidden; });

        const keys = (e) => {
            if (!box.isConnected) { removeEventListener('keydown', keys); return; }
            if (e.target.closest && e.target.closest('input, textarea') || !isTop(box)) return;
            if (e.key === 'ArrowRight') { next.click(); e.preventDefault(); }
            if (e.key === 'ArrowLeft') { back.click(); e.preventDefault(); }
        };
        addEventListener('keydown', keys);
        draw();
    };

    // ---- Kitchen timers: state lives here so the window can be updated without losing running timers.
    const boards = new Map();  // card id -> {timers: [...], seen: Set of keys}
    let audio = null;
    function chime() {
        try {
            audio = audio || new (window.AudioContext || window.webkitAudioContext)();
            [880, 1175, 1568].forEach((freq, i) => {
                const osc = audio.createOscillator(), gain = audio.createGain();
                const at = audio.currentTime + i * 0.22;
                osc.type = 'sine';
                osc.frequency.value = freq;
                gain.gain.setValueAtTime(0.0001, at);
                gain.gain.exponentialRampToValueAtTime(0.3, at + 0.02);
                gain.gain.exponentialRampToValueAtTime(0.0001, at + 0.6);
                osc.connect(gain).connect(audio.destination);
                osc.start(at);
                osc.stop(at + 0.65);
            });
        } catch (e) { /* no sound available */ }
    }
    const clock = (ms) => {
        const s = Math.max(0, Math.ceil(ms / 1000)), h = Math.floor(s / 3600), m = Math.floor(s / 60) % 60;
        return `${h ? `${h}:` : ''}${String(m).padStart(2, '0')}:${String(s % 60).padStart(2, '0')}`;
    };

    kinds['cooking-timers'] = (card, body, { el }) => {
        const board = boards.get(card.id) || { timers: [], seen: new Set() };
        boards.set(card.id, board);
        const addTimer = (name, seconds) => board.timers.push({
            name, total: seconds * 1000, endsAt: Date.now() + seconds * 1000, left: 0, paused: false, done: false, rang: 0,
        });
        for (const t of (card.data || {}).timers || []) {
            if (t.key && board.seen.has(t.key)) continue;
            if (t.key) board.seen.add(t.key);
            addTimer(t.name, t.seconds);
        }

        const grid = el('div', 'ck-timers');
        const form = el('form', 'ck-add');
        const name = el('input'), mins = el('input'), add = el('button', 'pop-action', 'Add timer');
        name.placeholder = 'Name';
        name.maxLength = 30;
        mins.type = 'number';
        mins.min = '0.1';
        mins.step = 'any';
        mins.placeholder = 'Minutes';
        form.append(name, mins, add);
        form.addEventListener('submit', (e) => {
            e.preventDefault();
            const m = parseFloat(mins.value);
            if (!(m > 0 && m <= 1440)) { mins.focus(); return; }
            addTimer(name.value.trim() || `Timer ${board.timers.length + 1}`, Math.round(m * 60));
            name.value = ''; mins.value = '';
            draw();
        });
        body.append(grid, form);

        const tiles = new Map();
        function tile(t) {
            const box = el('div', 'ck-timer');
            const label = el('div', 'ck-timer-name', t.name), face = el('div', 'ck-timer-face');
            const bar = el('div', 'ck-bar'), fill = el('div', 'ck-fill');
            bar.append(fill);
            const row = el('div', 'ck-timer-buttons');
            const pause = el('button', 'pop-btn ck-small', 'Pause'), plus = el('button', 'pop-btn ck-small', '+1 min');
            const cancel = el('button', 'pop-btn ck-small', 'Cancel');
            pause.addEventListener('click', () => {
                if (t.done) { t.rang = 99; return; }
                if (t.paused) { t.endsAt = Date.now() + t.left; t.paused = false; } else { t.left = t.endsAt - Date.now(); t.paused = true; }
                update();
            });
            plus.addEventListener('click', () => {
                if (t.done) { t.done = false; t.rang = 0; t.endsAt = Date.now(); }
                if (t.paused) t.left += 60000; else t.endsAt += 60000;
                t.total += 60000;
                update();
            });
            cancel.addEventListener('click', () => { board.timers.splice(board.timers.indexOf(t), 1); draw(); });
            row.append(pause, plus, cancel);
            box.append(label, face, bar, row);
            return { box, face, fill, pause };
        }
        function draw() {
            grid.replaceChildren();
            tiles.clear();
            for (const t of board.timers) { const x = tile(t); tiles.set(t, x); grid.append(x.box); }
            if (!board.timers.length) grid.append(el('div', 'pop-empty', 'No timers yet. Add one below.'));
            update();
        }
        function update() {
            const now = Date.now();
            for (const [t, x] of tiles) {
                const left = t.paused ? t.left : t.endsAt - now;
                if (!t.paused && !t.done && left <= 0) t.done = true;
                if (t.done && t.rang < 3 && now - (t.lastRing || 0) > 4000) { t.rang += 1; t.lastRing = now; chime(); }
                x.face.textContent = t.done ? 'Done' : clock(left);
                x.fill.style.width = `${Math.min(100, 100 * (1 - Math.max(0, left) / t.total))}%`;
                x.pause.textContent = t.done ? 'Stop' : t.paused ? 'Resume' : 'Pause';
                x.box.classList.toggle('done', t.done);
                x.box.classList.toggle('paused', t.paused);
            }
        }
        const tick = () => { if (!grid.isConnected) return; update(); setTimeout(tick, 250); };
        draw();
        tick();
    };

    kinds['cooking-batch'] = (card, body, { el, table }) => {
        const { shopping = {}, order = {} } = card.data || {};
        body.append(el('h4', 'ck-heading', 'Cooking order'), table(order.columns || [], order.rows || []));
        body.append(el('h4', 'ck-heading', 'Shopping for all of it'), table(shopping.columns || [], shopping.rows || []));
    };
})();
