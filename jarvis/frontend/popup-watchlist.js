// The "watchlist" pop-up kind (watchlist_store.py): poster tiles, progress bars, a goal ring, big numbers, charts,
// tables and clickable lists. Everything is written with textContent; pictures load only from https links.
(() => {
    window.jarvisPopupKinds = window.jarvisPopupKinds || {};
    const NS = 'http://www.w3.org/2000/svg';

    function gallery(tiles, el, ask) {
        const grid = el('div', 'wl-gallery');
        for (const t of tiles || []) {
            const tile = el(t.say ? 'button' : 'div', 'wl-tile');
            const poster = el('div', `wl-poster tone${(t.tone || 0) % 6}`);
            poster.append(el('span', '', t.title || '?'));
            if (typeof t.image === 'string' && t.image.startsWith('https://')) {
                const img = el('img');
                img.src = t.image;
                img.alt = '';
                img.loading = 'lazy';
                img.referrerPolicy = 'no-referrer';
                img.addEventListener('error', () => img.remove());
                poster.append(img);
            }
            if (t.badge) poster.append(el('span', 'wl-badge', t.badge));
            tile.append(poster, el('span', 'wl-tile-title', t.title || ''));
            if (t.stars) tile.append(el('span', 'wl-stars', t.stars));
            if (t.subtitle) tile.append(el('span', 'wl-tile-sub', t.subtitle));
            if (t.say) {
                tile.title = t.say;
                tile.addEventListener('click', () => ask(t.say));
            }
            grid.append(tile);
        }
        if (!grid.children.length) grid.append(el('div', 'pop-empty', 'Nothing here yet.'));
        return grid;
    }

    function meters(rows, el, ask) {
        const box = el('div', 'wl-meters');
        for (const r of rows || []) {
            const row = el(r.say ? 'button' : 'div', 'wl-meter');
            if (r.say) row.addEventListener('click', () => ask(r.say));
            const head = el('div', 'wl-meter-head');
            head.append(el('span', '', r.label), el('span', 'wl-meter-note', r.note || ''));
            const track = el('div', 'wl-track');
            const fill = el('div', 'wl-fill');
            const pct = r.max > 0 ? Math.max(0, Math.min(1, r.value / r.max)) : 0;
            fill.style.width = `${(pct * 100).toFixed(1)}%`;
            track.append(fill);
            row.append(head, track);
            box.append(row);
        }
        return box;
    }

    function ring(s, el) {
        const box = el('div', 'wl-ring');
        const svg = document.createElementNS(NS, 'svg');
        svg.setAttribute('viewBox', '0 0 120 120');
        const R = 50, C = 2 * Math.PI * R;
        const pct = s.max > 0 ? Math.max(0, Math.min(1, s.value / s.max)) : 0;
        const add = (tag, attrs, text) => {
            const n = document.createElementNS(NS, tag);
            for (const [k, v] of Object.entries(attrs)) n.setAttribute(k, v);
            if (text !== undefined) n.textContent = text;
            svg.append(n);
        };
        add('circle', { cx: 60, cy: 60, r: R, class: 'track' });
        add('circle', {
            cx: 60, cy: 60, r: R, class: 'fill', transform: 'rotate(-90 60 60)',
            'stroke-dasharray': C.toFixed(1), 'stroke-dashoffset': (C * (1 - pct)).toFixed(1),
        });
        add('text', { x: 60, y: 68 }, `${s.value}/${s.max}`);
        box.append(svg, el('div', 'wl-ring-label', s.label || ''));
        if (s.note) box.append(el('div', 'wl-ring-note', s.note));
        return box;
    }

    function stats(items, el) {
        const grid = el('div', 'wl-stats');
        for (const s of items || []) {
            const cell = el('div', 'wl-stat');
            cell.append(el('div', 'wl-stat-value', s.value), el('div', 'wl-stat-label', s.label));
            grid.append(cell);
        }
        return grid;
    }

    function list(items, el, ask) {
        const ul = el('ul', 'pop-list');
        for (const item of items || []) {
            const li = el('li');
            const label = el(item.say ? 'button' : 'span', 'pop-item', item.label);
            if (item.say) label.addEventListener('click', () => ask(item.say));
            li.append(label);
            ul.append(li);
        }
        return ul;
    }

    window.jarvisPopupKinds.watchlist = (card, body, { el, ask, table, chart }) => {
        for (const s of (card.data && card.data.sections) || []) {
            const part = el('section', 'wl-section');
            if (s.title) part.append(el('h4', 'wl-title', s.title));
            if (s.type === 'gallery') part.append(gallery(s.tiles, el, ask));
            else if (s.type === 'meters') part.append(meters(s.rows, el, ask));
            else if (s.type === 'ring') part.append(ring(s, el));
            else if (s.type === 'stats') part.append(stats(s.items, el));
            else if (s.type === 'chart') part.append(chart(s.chart || {}));
            else if (s.type === 'table') part.append(table(s.columns || [], s.rows || []));
            else if (s.type === 'list') part.append(list(s.items, el, ask));
            else if (s.type === 'text') part.append(el('p', 'wl-text', s.text || ''));
            body.append(part);
        }
    };
})();
