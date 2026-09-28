// Kids (kids_*.py): big friendly pop-ups for a sticker chart with rewards, pocket money jars, a reading
// certificate, a visual timer (a shrinking coloured circle with big numbers and a chime) and a drawing pad with
// big colour buttons and stamps. Tapping a square on the sticker chart asks Alfred to give that star. The timer
// and drawing pad run here in the page and stop once their window closes or is redrawn.
(() => {
    const kinds = window.jarvisPopupKinds = window.jarvisPopupKinds || {};
    const NS = 'http://www.w3.org/2000/svg';
    const COLOURS = {
        red: '#ef5350', orange: '#ffa726', yellow: '#ffee58', green: '#66bb6a', blue: '#42a5f5',
        purple: '#ab47bc', pink: '#f06292',
    };
    const svg = (tag, attrs = {}, parent) => {
        const n = document.createElementNS(NS, tag);
        for (const [k, v] of Object.entries(attrs)) n.setAttribute(k, v);
        if (parent) parent.append(n);
        return n;
    };
    const button = (el, label, fn, cls = '') => {
        const b = el('button', `kd-btn ${cls}`.trim(), label);
        b.type = 'button';
        b.addEventListener('click', fn);
        return b;
    };
    // Repeats fn every ms until root leaves the page.
    const every = (root, ms, fn) => {
        const id = setInterval(() => (root.isConnected ? fn() : clearInterval(id)), ms);
        return id;
    };
    let audio;
    function chime() {
        try {
            audio = audio || new (window.AudioContext || window.webkitAudioContext)();
            if (audio.state === 'suspended') audio.resume();
            [784, 988, 1175, 1568].forEach((f, n) => {
                const t = audio.currentTime + n * 0.2, o = audio.createOscillator(), g = audio.createGain();
                o.frequency.value = f;
                g.gain.setValueAtTime(0.0001, t);
                g.gain.exponentialRampToValueAtTime(0.25, t + 0.02);
                g.gain.exponentialRampToValueAtTime(0.0001, t + 0.6);
                o.connect(g).connect(audio.destination);
                o.start(t);
                o.stop(t + 0.65);
            });
        } catch (e) { /* no sound on this device */ }
    }

    // ---- sticker chart and rewards ------------------------------------------------------------------
    function rewards(d, el, ask) {
        const box = el('div', 'kd-rewards');
        if (!d.rewards.length) box.append(el('div', 'pop-empty', 'No rewards yet. Say "a trip to the park at 10 stars".'));
        for (const r of d.rewards) {
            const row = el('div', 'kd-reward');
            const top = el('div', 'kd-reward-top');
            top.append(el('span', 'kd-reward-name', r.name), el('span', 'kd-reward-count', `${r.have} / ${r.need} ★`));
            const bar = el('div', 'kd-bar');
            const fill = el('div', 'kd-bar-fill');
            fill.style.width = `${Math.min(100, Math.round((r.have / r.need) * 100))}%`;
            bar.setAttribute('role', 'progressbar');
            bar.setAttribute('aria-valuemin', '0');
            bar.setAttribute('aria-valuemax', String(r.need));
            bar.setAttribute('aria-valuenow', String(r.have));
            bar.setAttribute('aria-label', r.name);
            bar.append(fill);
            row.append(top, bar);
            if (r.have >= r.need) row.append(button(el, `Claim ${r.name}!`, () => ask(`${d.child} is claiming the reward ${r.name}.`), 'kd-go'));
            box.append(row);
        }
        return box;
    }

    kinds['kids-stars'] = (card, body, { el, ask }) => {
        const d = card.data || {};
        const head = el('div', 'kd-head');
        head.append(el('div', 'kd-big', `★ ${d.week}`), el('div', 'kd-sub', `this week · ${d.balance} to spend`));
        body.append(head);
        if (d.view === 'rewards') { body.append(rewards(d, el, ask)); return; }
        const grid = el('div', 'kd-grid');
        grid.style.gridTemplateColumns = `minmax(90px, 1.4fr) repeat(7, minmax(34px, 1fr))`;
        grid.append(el('div', 'kd-corner'));
        d.days.forEach((day, i) => grid.append(el('div', `kd-day${i === d.today ? ' today' : ''}`, day)));
        if (!d.grid.length) {
            const none = el('div', 'pop-empty kd-none', 'No goals yet. Say "Mia\'s goals are brushing teeth and tidying up".');
            grid.append(none);
        }
        for (const row of d.grid) {
            grid.append(el('div', 'kd-goal', row.goal));
            row.cells.forEach((n, i) => {
                const label = n ? '★'.repeat(Math.min(n, 3)) + (n > 3 ? `${n}` : '') : '';
                const b = button(el, label, () => ask(row.goal === 'Other stars'
                    ? `Give ${d.child} a star on ${d.dates[i]}.`
                    : `Give ${d.child} a star for ${row.goal} on ${d.dates[i]}.`), `kd-cell${n ? ' on' : ''}${i === d.today ? ' today' : ''}`);
                b.setAttribute('aria-label', `${row.goal}, ${d.days[i]}: ${n} stars. Add a star.`);
                grid.append(b);
            });
        }
        body.append(grid);
        if (d.rewards.length) body.append(el('h4', 'kd-h', 'Rewards'), rewards(d, el, ask));
    };

    // ---- pocket money jars --------------------------------------------------------------------------
    kinds['kids-jars'] = (card, body, { el }) => {
        const kids = (card.data || {}).children || [];
        const top = Math.max(1, ...kids.flatMap((k) => k.jars.map((j) => j.amount)));
        for (const k of kids) {
            const box = el('div', 'kd-kid');
            const head = el('div', 'kd-head');
            head.append(el('div', 'kd-big', `${k.child} · ${k.total}`), el('div', 'kd-sub', `${k.weekly} a week`));
            const jars = el('div', 'kd-jars');
            for (const j of k.jars) {
                const jar = el('div', `kd-jar kd-${j.jar}`);
                const glass = el('div', 'kd-glass');
                const fill = el('div', 'kd-fill');
                fill.style.height = `${Math.max(3, Math.round((Math.max(0, j.amount) / top) * 100))}%`;
                glass.append(fill);
                jar.append(el('div', 'kd-jar-amount', j.text), glass, el('div', 'kd-jar-name', j.jar));
                jars.append(jar);
            }
            box.append(head, jars);
            if (k.recent.length) {
                const list = el('ul', 'kd-recent');
                k.recent.forEach((r) => list.append(el('li', '', `${r.date}  ${r.text}`)));
                box.append(list);
            }
            body.append(box);
        }
    };

    // ---- reading certificate ------------------------------------------------------------------------
    kinds['kids-certificate'] = (card, body, { el }) => {
        const d = card.data || {};
        const cert = el('div', 'kd-cert');
        cert.append(el('div', 'kd-cert-stars', '★ ★ ★ ★ ★'), el('div', 'kd-cert-kicker', 'Certificate of achievement'),
            el('div', 'kd-cert-award', d.award), el('div', 'kd-cert-small', 'proudly awarded to'),
            el('div', 'kd-cert-name', d.child), el('div', 'kd-cert-small', `for reading ${d.books} books`));
        if ((d.titles || []).length) cert.append(el('div', 'kd-cert-titles', d.titles.join(' · ')));
        cert.append(el('div', 'kd-cert-date', d.date));
        body.append(cert);
    };

    // ---- visual timer -------------------------------------------------------------------------------
    kinds['kids-timer'] = (card, body, { el }) => {
        const d = card.data || {};
        const colour = COLOURS[d.colour] || COLOURS.blue;
        const people = d.people || [];
        let who = 0, total = Math.max(1, d.seconds || 60), left = total * 1000, running = true, last = Date.now(), rang = false;
        const face = svg('svg', { viewBox: '0 0 200 200', class: 'kd-clock', role: 'img' });
        svg('circle', { cx: 100, cy: 100, r: 92, class: 'kd-clock-back' }, face);
        const wedge = svg('path', { fill: colour }, face);
        const disc = svg('circle', { cx: 100, cy: 100, r: 92, fill: colour }, face);
        const name = el('div', 'kd-turn');
        const digits = el('div', 'kd-digits');
        digits.setAttribute('aria-live', 'off');
        const status = el('div', 'kd-sub');
        status.setAttribute('aria-live', 'polite');
        const pause = button(el, 'Pause', () => { running = !running; last = Date.now(); pause.textContent = running ? 'Pause' : 'Go'; });
        const restart = button(el, 'Restart', () => start(who));
        const more = button(el, '+1 min', () => { left += 60000; total += 60; rang = false; status.textContent = ''; });
        const next = button(el, 'Next turn', () => start(who + 1), 'kd-go');
        next.hidden = true;
        const row = el('div', 'kd-row');
        row.append(pause, restart, more, next);
        body.append(el('div', 'kd-label', d.label || 'Timer'), name, face, digits, status, row);

        function start(n) {
            who = people.length ? n % people.length : 0;
            left = total * 1000; running = true; last = Date.now(); rang = false;
            pause.textContent = 'Pause'; next.hidden = true; status.textContent = '';
            name.textContent = people.length ? `${people[who]}'s turn` : '';
            draw();
        }
        function draw() {
            const frac = Math.max(0, Math.min(1, left / (total * 1000)));
            disc.style.display = frac >= 0.999 ? '' : 'none';
            wedge.style.display = frac >= 0.999 || frac <= 0 ? 'none' : '';
            const a = frac * 2 * Math.PI, x = 100 + 92 * Math.sin(a), y = 100 - 92 * Math.cos(a);
            wedge.setAttribute('d', `M100 100 L100 8 A92 92 0 ${frac > 0.5 ? 1 : 0} 0 ${200 - x} ${y} Z`);
            const s = Math.ceil(left / 1000), m = Math.floor(s / 60);
            digits.textContent = `${m}:${String(s % 60).padStart(2, '0')}`;
            face.setAttribute('aria-label', `${digits.textContent} left`);
        }
        every(body, 200, () => {
            const now = Date.now();
            if (running) left = Math.max(0, left - (now - last));
            last = now;
            draw();
            if (left <= 0 && !rang) {
                rang = true; running = false;
                chime();
                setTimeout(() => body.isConnected && chime(), 1300);
                status.textContent = people.length > 1 ? `Time's up! Next: ${people[(who + 1) % people.length]}` : "Time's up!";
                next.hidden = people.length < 2;
            }
        });
        start(0);
    };

    // ---- drawing pad --------------------------------------------------------------------------------
    const STAMPS = {
        star(g, x, y, r) {
            g.beginPath();
            for (let i = 0; i < 10; i++) {
                const a = (Math.PI / 5) * i - Math.PI / 2, rr = i % 2 ? r * 0.45 : r;
                g.lineTo(x + rr * Math.cos(a), y + rr * Math.sin(a));
            }
            g.closePath(); g.fill();
        },
        heart(g, x, y, r) {
            g.beginPath();
            g.moveTo(x, y + r * 0.9);
            g.bezierCurveTo(x - r * 1.4, y - r * 0.1, x - r * 0.6, y - r * 1.1, x, y - r * 0.4);
            g.bezierCurveTo(x + r * 0.6, y - r * 1.1, x + r * 1.4, y - r * 0.1, x, y + r * 0.9);
            g.fill();
        },
        circle(g, x, y, r) { g.beginPath(); g.arc(x, y, r, 0, Math.PI * 2); g.fill(); },
        square(g, x, y, r) { g.fillRect(x - r, y - r, r * 2, r * 2); },
        flower(g, x, y, r) {
            for (let i = 0; i < 6; i++) {
                const a = (Math.PI / 3) * i;
                g.beginPath(); g.arc(x + r * 0.55 * Math.cos(a), y + r * 0.55 * Math.sin(a), r * 0.42, 0, Math.PI * 2); g.fill();
            }
            const keep = g.fillStyle;
            g.fillStyle = '#ffd54f';
            g.beginPath(); g.arc(x, y, r * 0.35, 0, Math.PI * 2); g.fill();
            g.fillStyle = keep;
        },
        smiley(g, x, y, r) {
            g.beginPath(); g.arc(x, y, r, 0, Math.PI * 2); g.fill();
            const keep = g.fillStyle;
            g.fillStyle = '#111111'; g.strokeStyle = '#111111'; g.lineWidth = Math.max(2, r / 8);
            g.beginPath(); g.arc(x - r * 0.35, y - r * 0.25, r * 0.12, 0, Math.PI * 2); g.fill();
            g.beginPath(); g.arc(x + r * 0.35, y - r * 0.25, r * 0.12, 0, Math.PI * 2); g.fill();
            g.beginPath(); g.arc(x, y + r * 0.05, r * 0.5, 0.15 * Math.PI, 0.85 * Math.PI); g.stroke();
            g.fillStyle = keep;
        },
    };
    const STAMP_ICONS = { star: '★', heart: '♥', circle: '●', square: '■', flower: '✿', smiley: '☺' };
    const PAINTS = ['#111111', '#e53935', '#fb8c00', '#fdd835', '#43a047', '#1e88e5', '#8e24aa', '#f06292', '#8d6e63', '#ffffff'];

    async function saveDrawing(folder, filename, blob) {
        const r = await fetch('/memory');
        if (!r.ok) throw new Error("Couldn't read the memory folders.");
        const folders = (await r.json()).folders || [];
        const i = folders.findIndex((f) => f.name.toLowerCase() === String(folder || 'Ideas').toLowerCase());
        if (i < 0) throw new Error(`There's no ${folder} folder.`);
        const put = await fetch(`/memory/${i}/files/${encodeURIComponent(filename)}`, {
            method: 'PUT', headers: { 'Content-Type': 'image/png' }, body: blob,
        });
        if (!put.ok) throw new Error((await put.text()) || 'Saving failed.');
        return { folder: folders[i].name, name: (await put.json()).name };
    }

    kinds['kids-draw'] = (card, body, { el }) => {
        const d = card.data || {};
        const canvas = el('canvas', 'kd-canvas');
        canvas.width = 860; canvas.height = 560;
        canvas.setAttribute('aria-label', 'Drawing area');
        const g = canvas.getContext('2d');
        const wipe = () => { g.fillStyle = '#ffffff'; g.fillRect(0, 0, canvas.width, canvas.height); };
        wipe();
        let colour = PAINTS[1], size = 14, stamp = '', last = null;
        const undo = [];
        const remember = () => { undo.push(g.getImageData(0, 0, canvas.width, canvas.height)); if (undo.length > 15) undo.shift(); };
        const pos = (e) => { const r = canvas.getBoundingClientRect(); return [(e.clientX - r.left) * canvas.width / r.width, (e.clientY - r.top) * canvas.height / r.height]; };
        canvas.addEventListener('pointerdown', (e) => {
            e.preventDefault();
            remember();
            const p = pos(e);
            if (stamp) { g.fillStyle = colour; STAMPS[stamp](g, p[0], p[1], size * 2.2); return; }
            canvas.setPointerCapture(e.pointerId);
            last = p;
            line(p);
        });
        canvas.addEventListener('pointermove', (e) => { if (last) line(pos(e)); });
        ['pointerup', 'pointercancel', 'pointerleave'].forEach((t) => canvas.addEventListener(t, () => { last = null; }));
        function line(p) {
            g.strokeStyle = colour; g.lineWidth = size; g.lineCap = g.lineJoin = 'round';
            g.beginPath(); g.moveTo(...last); g.lineTo(...p); g.stroke();
            last = p;
        }
        const press = (group, chosen) => group.querySelectorAll('button').forEach((b) => b.setAttribute('aria-pressed', String(b === chosen)));
        const paints = el('div', 'kd-paints');
        PAINTS.forEach((c, n) => {
            const b = button(el, '', () => { colour = c; press(paints, b); }, 'kd-paint');
            b.style.background = c;
            b.setAttribute('aria-label', c === '#ffffff' ? 'White, like a rubber' : `Colour ${c}`);
            b.setAttribute('aria-pressed', String(n === 1));
            paints.append(b);
        });
        const tools = el('div', 'kd-tools');
        const pen = button(el, '✎', () => { stamp = ''; press(tools, pen); }, 'kd-tool');
        pen.setAttribute('aria-label', 'Pen');
        pen.setAttribute('aria-pressed', 'true');
        tools.append(pen);
        for (const [key, icon] of Object.entries(STAMP_ICONS)) {
            const b = button(el, icon, () => { stamp = key; press(tools, b); }, 'kd-tool');
            b.setAttribute('aria-label', `${key} stamp`);
            b.setAttribute('aria-pressed', 'false');
            tools.append(b);
        }
        const sizes = el('div', 'kd-sizes');
        [['Small', 6], ['Medium', 14], ['Big', 28]].forEach(([label, n]) => {
            const b = button(el, label, () => { size = n; press(sizes, b); }, 'kd-size');
            b.setAttribute('aria-pressed', String(n === size));
            sizes.append(b);
        });
        const msg = el('div', 'kd-sub');
        msg.setAttribute('aria-live', 'polite');
        const back = button(el, 'Undo', () => { if (undo.length) g.putImageData(undo.pop(), 0, 0); });
        const clear = button(el, 'Clear', () => { if (confirm('Start a new picture?')) { remember(); wipe(); } });
        const save = button(el, `Save to ${d.folder || 'Ideas'}`, () => {
            msg.textContent = 'Saving…';
            const t = new Date(), pad = (n) => String(n).padStart(2, '0');
            const name = `${d.child || 'Drawing'} ${t.getFullYear()}-${pad(t.getMonth() + 1)}-${pad(t.getDate())} ${pad(t.getHours())}${pad(t.getMinutes())}.png`
                .replace(/[<>:"/\\|?*\x00-\x1f]/g, '');
            canvas.toBlob(async (blob) => {
                try {
                    const saved = await saveDrawing(d.folder, name, blob);
                    msg.textContent = `Saved ${saved.name} in ${saved.folder}. Lovely!`;
                } catch (e) { msg.textContent = e.message; }
            }, 'image/png');
        }, 'kd-go');
        const row = el('div', 'kd-row');
        row.append(back, clear, save);
        body.append(canvas, paints, tools, sizes, row, msg);
    };
})();
