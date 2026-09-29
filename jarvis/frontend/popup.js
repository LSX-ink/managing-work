// Pop-up windows on the Alfred screen. Alfred sends {type: 'popup', card}; see screen.py for the card kinds.
// Windows can be dragged by their title bar, resized from the corner, and closed. Buttons and list items that
// carry a "say" line send it to Alfred as if you had said it.
(() => {
    const MAX_WINDOWS = 8;
    const layer = document.createElement('div');
    layer.id = 'popups';
    document.body.append(layer);
    const windows = new Map();  // card id -> element
    let top = 40;
    let serial = 0;

    const el = (tag, cls, text) => {
        const e = document.createElement(tag);
        if (cls) e.className = cls;
        if (text !== undefined) e.textContent = text;
        return e;
    };
    const ask = (text) => { if (text && window.jarvisAsk) window.jarvisAsk(text); };

    function focus(win) { win.style.zIndex = String(++top); }

    // New windows fill free spots: left, right, then lower down, then cascade on top.
    function place(win) {
        const W = Math.min(460, innerWidth - 24), gap = 16, n = windows.size;
        const cols = Math.max(1, Math.floor((innerWidth - gap) / (W + gap)));
        const order = [0, cols - 1, ...Array.from({ length: Math.max(0, cols - 2) }, (_, i) => i + 1)];
        const col = order[n % cols], row = Math.floor(n / cols) % 2;
        const x = gap + col * ((innerWidth - W - 2 * gap) / Math.max(1, cols - 1 || 1));
        win.style.left = `${Math.round(cols === 1 ? gap / 2 + 4 : x)}px`;
        win.style.top = `${Math.round(Math.min(innerHeight - 160, 84 + row * (innerHeight * 0.42) + Math.floor(n / (cols * 2)) * 28))}px`;
        // Wider windows (periodic table, games) are pulled back so they don't run off the right edge.
        requestAnimationFrame(() => {
            const over = win.offsetLeft + win.offsetWidth - (innerWidth - 8);
            if (over > 0) win.style.left = `${Math.max(8, win.offsetLeft - over)}px`;
        });
    }

    function drag(win, handle) {
        handle.addEventListener('pointerdown', (e) => {
            if (e.target.closest('button')) return;
            focus(win);
            const sx = e.clientX - win.offsetLeft, sy = e.clientY - win.offsetTop;
            const move = (m) => {
                win.style.left = `${Math.min(window.innerWidth - 60, Math.max(-win.offsetWidth + 80, m.clientX - sx))}px`;
                win.style.top = `${Math.min(window.innerHeight - 40, Math.max(0, m.clientY - sy))}px`;
            };
            const up = () => { removeEventListener('pointermove', move); removeEventListener('pointerup', up); };
            addEventListener('pointermove', move);
            addEventListener('pointerup', up);
        });
    }

    function close(win) {
        const back = win.contains(document.activeElement) ? win._opener : null;   // keyboard users land where they were
        windows.delete(win.dataset.id);
        win.querySelectorAll('audio, video').forEach((m) => m.pause());
        win.remove();
        if (back && back.isConnected) back.focus();
    }

    // Other files add kinds here: window.jarvisPopupKinds.name = (card, body, helpers) => { ... }.
    window.jarvisPopupKinds = window.jarvisPopupKinds || {};

    function render(card, body) {
        body.replaceChildren();
        const kind = card.kind;
        const custom = window.jarvisPopupKinds[kind];
        if (custom) {
            if (card.text) body.append(el('div', 'pop-text', card.text));
            custom(card, body, { el, ask, table, chart, image });
            return;
        }
        if (card.text && kind !== 'reader') body.append(el('div', 'pop-text', card.text));
        if (kind === 'list') renderList(card, body);
        else if (kind === 'table') body.append(table(card.columns || [], card.rows || []));
        else if (kind === 'chart') body.append(chart(card.chart || {}));
        else if (kind === 'file') renderFile(card, body);
        else if (kind === 'reader') renderReader(card, body);
        else if (kind === 'image') body.append(image(card.src, card.title));
        else if (kind === 'video') renderVideo(card, body);
        else if (kind === 'timer') renderTimer(card, body);
    }

    function renderList(card, body) {
        const ul = el('ul', 'pop-list');
        for (const item of card.items || []) {
            const li = el('li', item.done ? 'done' : '');
            if (card.checks) {
                const box = el('input');
                box.type = 'checkbox';
                box.checked = item.done;
                box.addEventListener('change', () => { li.classList.toggle('done', box.checked); ask(item.say); });
                li.append(box);
            }
            const label = el(item.say && !card.checks ? 'button' : 'span', 'pop-item', item.label);
            if (item.say && !card.checks) label.addEventListener('click', () => ask(item.say));
            li.append(label);
            ul.append(li);
        }
        if (!ul.children.length) ul.append(el('li', 'pop-empty', 'Nothing here.'));
        body.append(ul);
    }

    function table(columns, rows) {
        const wrap = el('div', 'pop-table');
        const t = el('table');
        if (columns.length) {
            const tr = el('tr');
            columns.forEach((c) => tr.append(el('th', '', c)));
            const head = el('thead');
            head.append(tr);
            t.append(head);
        }
        const tb = el('tbody');
        rows.forEach((r) => { const tr = el('tr'); r.forEach((c) => tr.append(el('td', '', c))); tb.append(tr); });
        t.append(tb);
        wrap.append(t);
        return wrap;
    }

    function chart({ type, labels = [], values = [], unit = '' }) {
        const NS = 'http://www.w3.org/2000/svg';
        const fmt = (v) => `${Math.abs(v) >= 1000 ? Math.round(v).toLocaleString() : +v.toFixed(2)}${unit}`;
        const lo = Math.min(0, ...values), hi = Math.max(0, ...values);
        const widest = Math.max(...[lo, (lo + hi) / 2, hi].map((v) => fmt(v).length));
        const W = 440, H = 220, L = Math.max(44, 12 + widest * 7), B = 36, T = 14, R = 10;
        const svg = document.createElementNS(NS, 'svg');
        svg.setAttribute('viewBox', `0 0 ${W} ${H}`);
        svg.setAttribute('class', 'pop-chart');
        const add = (tag, attrs, text) => {
            const n = document.createElementNS(NS, tag);
            for (const [k, v] of Object.entries(attrs)) n.setAttribute(k, v);
            if (text !== undefined) n.textContent = text;
            svg.append(n);
            return n;
        };
        const max = Math.max(0, ...values), min = Math.min(0, ...values);
        const span = max - min || 1;
        const y = (v) => T + (H - T - B) * (1 - (v - min) / span);
        const step = (W - L - R) / Math.max(1, values.length);
        [min, (min + max) / 2, max].forEach((v) => {
            add('line', { x1: L, x2: W - R, y1: y(v), y2: y(v), class: 'grid' });
            add('text', { x: L - 6, y: y(v) + 4, 'text-anchor': 'end', class: 'axis' }, fmt(v));
        });
        const every = Math.ceil(values.length / 8);
        labels.forEach((label, i) => {
            if (i % every === 0) add('text', { x: L + step * (i + 0.5), y: H - 12, 'text-anchor': 'middle', class: 'axis' }, label);
        });
        if (type === 'line') {
            const pts = values.map((v, i) => `${L + step * (i + 0.5)},${y(v)}`).join(' ');
            add('polyline', { points: pts, class: 'line' });
            values.forEach((v, i) => add('circle', { cx: L + step * (i + 0.5), cy: y(v), r: 3, class: 'dot' })
                .append(Object.assign(document.createElementNS(NS, 'title'), { textContent: `${labels[i]}: ${fmt(v)}` })));
        } else {
            values.forEach((v, i) => {
                const top = Math.min(y(v), y(0)), h = Math.abs(y(v) - y(0));
                add('rect', { x: L + step * i + step * 0.15, y: top, width: step * 0.7, height: Math.max(1, h), class: v < 0 ? 'bar neg' : 'bar' })
                    .append(Object.assign(document.createElementNS(NS, 'title'), { textContent: `${labels[i]}: ${fmt(v)}` }));
            });
        }
        return svg;
    }

    function image(src, alt) {
        const img = el('img', 'pop-image');
        img.src = src;
        img.alt = alt || '';
        img.referrerPolicy = 'no-referrer';
        img.addEventListener('error', () => img.replaceWith(el('div', 'pop-empty', "The picture wouldn't load.")));
        return img;
    }

    async function renderFile(card, body) {
        const mime = card.mime || '';
        if (mime.startsWith('image/')) body.append(image(card.src, card.name));
        else if (mime === 'application/pdf') {
            const frame = el('iframe', 'pop-frame');
            frame.src = card.src;
            frame.title = card.name;
            body.append(frame);
        } else if (mime.startsWith('audio/') || mime.startsWith('video/')) {
            const media = el(mime.startsWith('audio/') ? 'audio' : 'video', 'pop-media');
            media.controls = true;
            media.autoplay = true;
            media.src = card.src;
            body.append(media);
        } else if (mime.startsWith('text/') || mime === 'application/json') {
            try {
                const r = await fetch(card.src);
                const text = await r.text();
                if (mime === 'text/csv') {
                    const rows = text.trim().split(/\r?\n/).slice(0, 300).map((line) => line.split(','));
                    body.append(table(rows[0] || [], rows.slice(1)));
                } else body.append(el('pre', 'pop-pre', text.slice(0, 200000)));
            } catch (e) { body.append(el('div', 'pop-empty', "Couldn't read that file.")); }
        } else {
            body.append(el('div', 'pop-empty', `${card.name} can't be shown here. Use Open on PC.`));
        }
    }

    function renderReader(card, body) {
        if (card.site) body.append(el('div', 'pop-site', card.site));
        if (card.image) body.append(image(card.image, ''));
        const article = el('div', 'pop-reader');
        (card.text || '').split(/\n\n+/).forEach((p) => article.append(el('p', '', p)));
        body.append(article);
    }

    function renderVideo(card, body) {
        const frame = el('iframe', 'pop-frame video');
        frame.src = card.src;
        frame.title = card.title;
        frame.allow = 'autoplay; encrypted-media; picture-in-picture; fullscreen';
        frame.referrerPolicy = 'strict-origin-when-cross-origin';
        body.append(frame);
    }

    function renderTimer(card, body) {
        const face = el('div', 'pop-timer');
        body.append(face);
        const tick = () => {
            if (!face.isConnected) return;
            const now = Date.now();
            let ms = card.ends_at ? card.ends_at - now : now - (card.started_at || now);
            const over = ms < 0;
            ms = Math.abs(ms);
            const s = Math.floor(ms / 1000), h = Math.floor(s / 3600), m = Math.floor(s / 60) % 60;
            face.textContent = `${over ? 'Done ' : ''}${h ? `${h}:` : ''}${String(m).padStart(2, '0')}:${String(s % 60).padStart(2, '0')}`;
            face.classList.toggle('over', over && !!card.ends_at);
            setTimeout(tick, 250);
        };
        tick();
    }

    function show(card) {
        if (card.kind === 'close') {
            for (const win of [...windows.values()]) {
                if (card.all || win.dataset.title.toLowerCase().includes((card.title || '').toLowerCase())) close(win);
            }
            return;
        }
        let win = windows.get(card.id);
        if (!win) {
            if (windows.size >= MAX_WINDOWS) close(windows.values().next().value);
            win = el('section', 'popup');
            win.dataset.id = card.id;
            const bar = el('header', 'pop-bar');
            const title = el('h3', 'pop-title');
            title.id = `pop-title-${++serial}`;
            win.setAttribute('role', 'dialog');
            win.setAttribute('aria-labelledby', title.id);
            win.tabIndex = -1;
            win._opener = document.activeElement;
            const min = el('button', 'pop-btn', '–');
            min.type = 'button';
            min.title = 'Shrink';
            min.setAttribute('aria-label', 'Shrink window');
            min.addEventListener('click', () => win.classList.toggle('shrunk'));
            const x = el('button', 'pop-btn', '×');
            x.type = 'button';
            x.title = 'Close';
            x.setAttribute('aria-label', 'Close window');
            x.addEventListener('click', () => close(win));
            bar.append(title, min, x);
            win.append(bar, el('div', 'pop-body'), el('footer', 'pop-buttons'));
            win.addEventListener('pointerdown', () => focus(win));
            drag(win, bar);
            place(win);
            layer.append(win);
            windows.set(card.id, win);
        }
        win.dataset.kind = card.kind;
        win.dataset.title = card.title;
        win.querySelector('.pop-title').textContent = card.title;
        render(card, win.querySelector('.pop-body'));
        const foot = win.querySelector('.pop-buttons');
        foot.replaceChildren(...(card.buttons || []).map((b) => {
            if (b.download) {
                const link = el('a', 'pop-action', b.label);
                link.href = `${b.download}&download=1`;
                link.download = '';
                return link;
            }
            const btn = el('button', 'pop-action', b.label);
            btn.addEventListener('click', () => ask(b.say));
            return btn;
        }));
        foot.hidden = !foot.children.length;
        win.classList.remove('shrunk');
        focus(win);
        win.classList.remove('arrive');
        void win.offsetWidth;
        win.classList.add('arrive');
    }

    document.addEventListener('jarvis:popup', (e) => show(e.detail));
    addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && !e.target.closest('input:not([type=checkbox], [type=radio], [type=range], [type=button]), textarea, select')) {
            const last = [...windows.values()].sort((a, b) => b.style.zIndex - a.style.zIndex)[0];
            if (last) close(last);
        }
    });
    window.jarvisPopup = show;
})();
