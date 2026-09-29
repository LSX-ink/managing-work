// Niche research pop-ups (see nicheresearch_*.py): sheet, radar, swot, check and board.
// Text via textContent only; clicks send a line to Alfred.
(() => {
    const kinds = (window.jarvisPopupKinds = window.jarvisPopupKinds || {});
    const SVG = 'http://www.w3.org/2000/svg';
    const svg = (name, attrs = {}, text = '') => {
        const node = document.createElementNS(SVG, name);
        for (const [k, v] of Object.entries(attrs)) node.setAttribute(k, v);
        if (text) node.textContent = text;
        return node;
    };
    const note = (el, wrap, text) => {
        if (text) wrap.append(el('div', 'nr-note', text));
    };
    const tappable = (node, say, ask) => {
        if (!say) return;
        node.classList.add('nr-tap');
        node.tabIndex = 0;
        node.addEventListener('click', () => ask(say));
        node.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') ask(say);
        });
    };

    kinds['nicheresearch-sheet'] = (card, body, { el, ask }) => {
        const data = card.data || {};
        const wrap = el('div', 'nr-wrap');
        if (data.headline) wrap.append(el('div', 'nr-big', data.headline));
        for (const s of data.sections || []) {
            wrap.append(el('h4', 'nr-head', s.heading));
            for (const line of s.lines || []) {
                const row = el('div', 'nr-line', line.text);
                tappable(row, line.say, ask);
                wrap.append(row);
            }
        }
        note(el, wrap, data.note);
        body.append(wrap);
    };

    kinds['nicheresearch-radar'] = (card, body, { el }) => {
        const data = card.data || {};
        const axes = data.axes || [];
        const n = axes.length || 1;
        const size = 260;
        const mid = size / 2;
        const radius = 90;
        const point = (i, r) => {
            const a = (Math.PI * 2 * i) / n - Math.PI / 2;
            return [mid + r * Math.cos(a), mid + r * Math.sin(a)];
        };
        const chart = svg('svg', { viewBox: `0 0 ${size} ${size}`, class: 'nr-radar', role: 'img' });
        for (let ring = 1; ring <= 5; ring++) {
            const pts = axes.map((_, i) => point(i, (radius * ring) / 5).join(',')).join(' ');
            chart.append(svg('polygon', { points: pts, class: 'nr-ring' }));
        }
        axes.forEach((label, i) => {
            const [x, y] = point(i, radius);
            chart.append(svg('line', { x1: mid, y1: mid, x2: x, y2: y, class: 'nr-ring' }));
            const [tx, ty] = point(i, radius + 16);
            chart.append(svg('text', { x: tx, y: ty + 4, 'text-anchor': 'middle', class: 'nr-axis' }, label));
        });
        const wrap = el('div', 'nr-wrap');
        const legend = el('div', 'nr-legend');
        (data.series || []).forEach((s, k) => {
            const pts = axes.map((_, i) => point(i, (radius * Math.max(0, Math.min(5, s.values[i] || 0))) / 5).join(',')).join(' ');
            chart.append(svg('polygon', { points: pts, class: `nr-shape nr-s${k % 4}` }));
            legend.append(el('span', `nr-key nr-k${k % 4}`, `${s.name}${s.score != null ? ` (${s.score})` : ''}`));
        });
        wrap.append(chart, legend);
        note(el, wrap, data.note);
        body.append(wrap);
    };

    kinds['nicheresearch-swot'] = (card, body, { el, ask }) => {
        const data = card.data || {};
        const wrap = el('div', 'nr-wrap');
        const grid = el('div', 'nr-swot');
        for (const box of data.boxes || []) {
            const cell = el('div', 'nr-cell');
            cell.append(el('h4', 'nr-head', box.title));
            for (const item of box.items || []) cell.append(el('div', 'nr-line', item));
            if (!(box.items || []).length) cell.append(el('div', 'nr-muted', 'Empty. Tap for prompts.'));
            tappable(cell, box.say, ask);
            grid.append(cell);
        }
        wrap.append(grid);
        body.append(wrap);
    };

    const marks = { ok: '✓', warn: '!', fail: '✗', todo: '○' };
    kinds['nicheresearch-check'] = (card, body, { el, ask }) => {
        const data = card.data || {};
        const wrap = el('div', 'nr-wrap');
        wrap.append(el('div', 'nr-big', data.headline || ''));
        for (const item of data.items || []) {
            const row = el('div', `nr-check ${item.status}`);
            row.append(el('span', 'nr-mark', marks[item.status] || '○'));
            const text = el('div', 'nr-checktext');
            text.append(el('div', 'nr-label', item.label));
            if (item.detail) text.append(el('div', 'nr-muted', item.detail));
            row.append(text);
            tappable(row, item.say, ask);
            wrap.append(row);
        }
        note(el, wrap, data.note);
        body.append(wrap);
    };

    kinds['nicheresearch-board'] = (card, body, { el, ask }) => {
        const data = card.data || {};
        const wrap = el('div', 'nr-wrap');
        const cols = el('div', 'nr-cols');
        for (const col of data.columns || []) {
            const box = el('div', 'nr-col');
            box.append(el('h4', 'nr-head', col.title));
            for (const c of col.cards || []) {
                const btn = el('button', 'nr-card');
                btn.type = 'button';
                btn.addEventListener('click', () => ask(c.say));
                btn.append(el('div', 'nr-label', c.label));
                if (c.small) btn.append(el('div', 'nr-muted', c.small));
                box.append(btn);
            }
            cols.append(box);
        }
        wrap.append(cols);
        note(el, wrap, data.note);
        body.append(wrap);
    };
})();
