// Track-anything pop-up kinds (trackers_*.py): a chart with a goal line and gaps for days not logged, a grid of
// day or week squares (year in pixels, challenge calendar, life in weeks) and a dashboard of mini charts.
(() => {
    const kinds = window.jarvisPopupKinds = window.jarvisPopupKinds || {};
    const NS = 'http://www.w3.org/2000/svg';

    function svgChart({ type = 'line', labels = [], values = [], goal = null, unit = '', max = null }, small = false) {
        const W = small ? 200 : 440, H = small ? 64 : 220;
        const L = small ? 4 : 44, B = small ? 4 : 32, T = small ? 6 : 14, R = small ? 4 : 10;
        const svg = document.createElementNS(NS, 'svg');
        svg.setAttribute('viewBox', `0 0 ${W} ${H}`);
        svg.setAttribute('class', `pop-chart tr-chart${small ? ' tr-mini' : ''}`);
        const add = (tag, attrs, text) => {
            const n = document.createElementNS(NS, tag);
            for (const [k, v] of Object.entries(attrs)) n.setAttribute(k, v);
            if (text !== undefined) n.textContent = text;
            svg.append(n);
            return n;
        };
        const nums = values.filter((v) => typeof v === 'number');
        const hi = Math.max(max ?? 0, goal ?? 0, ...nums, 1), lo = Math.min(0, ...nums);
        const y = (v) => T + (H - T - B) * (1 - (v - lo) / (hi - lo || 1));
        const step = (W - L - R) / Math.max(1, values.length);
        const x = (i) => L + step * (i + 0.5);
        const fmt = (v) => `${+v.toFixed(1)}${unit ? ` ${unit}` : ''}`;
        const tip = (node, i, v) => node.append(Object.assign(document.createElementNS(NS, 'title'),
            { textContent: `${labels[i] || ''}: ${fmt(v)}` }));
        if (!small) {
            [lo, (lo + hi) / 2, hi].forEach((v) => {
                add('line', { x1: L, x2: W - R, y1: y(v), y2: y(v), class: 'grid' });
                add('text', { x: L - 6, y: y(v) + 4, 'text-anchor': 'end', class: 'axis' }, +v.toFixed(1));
            });
            const every = Math.ceil(labels.length / 7);
            labels.forEach((label, i) => {
                if (i % every === 0) add('text', { x: x(i), y: H - 10, 'text-anchor': 'middle', class: 'axis' }, label);
            });
        }
        if (type === 'bar') {
            values.forEach((v, i) => {
                if (typeof v !== 'number') return;
                tip(add('rect', { x: L + step * i + step * 0.15, y: Math.min(y(v), y(0)), width: Math.max(1, step * 0.7),
                    height: Math.max(1, Math.abs(y(v) - y(0))), class: 'bar' }), i, v);
            });
        } else {
            let run = [];
            const flush = () => {
                if (run.length > 1) add('polyline', { points: run.join(' '), class: 'line' });
                run = [];
            };
            values.forEach((v, i) => (typeof v === 'number' ? run.push(`${x(i)},${y(v)}`) : flush()));
            flush();
            values.forEach((v, i) => {
                if (typeof v === 'number') tip(add('circle', { cx: x(i), cy: y(v), r: small ? 1.6 : 3, class: 'dot' }), i, v);
            });
        }
        if (typeof goal === 'number') {
            add('line', { x1: L, x2: W - R, y1: y(goal), y2: y(goal), class: 'tr-goal' });
            if (!small) add('text', { x: W - R - 2, y: y(goal) - 4, 'text-anchor': 'end', class: 'tr-goal-label' }, `goal ${fmt(goal)}`);
        }
        return svg;
    }

    kinds['trackers-chart'] = (card, body, { el, table }) => {
        const data = card.data || {};
        if (!(data.values || []).some((v) => typeof v === 'number')) {
            body.append(el('div', 'pop-empty', 'Nothing logged yet.'));
            return;
        }
        body.append(svgChart(data));
        if ((data.stats || []).length) body.append(table([], data.stats));
    };

    function legend(el, words) {
        const key = el('div', 'tr-legend');
        key.append(el('span', '', words[0] || ''));
        for (let lv = 0; lv <= 5; lv += 1) key.append(el('i', `tr-cell lv${lv}`));
        key.append(el('span', '', words[1] || ''));
        return key;
    }

    kinds['trackers-pixels'] = (card, body, { el }) => {
        const data = card.data || {};
        const grid = el('div', 'tr-grid');
        const detail = el('div', 'tr-detail', '');
        if (data.weeks) {
            const { lived = 0, total = 0, per_row: perRow = 52 } = data.weeks;
            grid.classList.add('tr-weeks');
            grid.style.gridTemplateColumns = `repeat(${perRow}, 1fr)`;
            for (let i = 0; i < total; i += 1) {
                const cell = el('i', `tr-cell ${i < lived ? 'lv5' : 'future'}${i === lived ? ' now' : ''}`);
                cell.title = `Age ${Math.floor(i / perRow)}, week ${(i % perRow) + 1}`;
                grid.append(cell);
            }
        } else {
            const cal = !!data.calendar;
            grid.classList.add(cal ? 'tr-cal' : 'tr-year');
            if (cal) ['M', 'T', 'W', 'T', 'F', 'S', 'S'].forEach((d) => grid.append(el('span', 'tr-day', d)));
            for (let i = 0; i < (data.offset || 0); i += 1) grid.append(el('i', 'tr-cell blank'));
            for (const c of data.cells || []) {
                const cell = el('button', `tr-cell ${c.v === null || c.v === undefined ? 'future' : `lv${c.v}`}${c.n ? ' noted' : ''}`);
                if (cal) cell.textContent = String(Number(c.d.slice(8)));
                cell.title = c.d;
                cell.addEventListener('click', () => {
                    const state = c.t || (c.v === null || c.v === undefined ? 'nothing logged' : 'noted');
                    detail.textContent = `${c.d}: ${state}${c.n ? ` — ${c.n}` : ''}`;
                });
                grid.append(cell);
            }
        }
        body.append(grid, detail, legend(el, data.legend || []));
    };

    kinds['trackers-dashboard'] = (card, body, { el, ask }) => {
        const tiles = (card.data || {}).tiles || [];
        const wrap = el('div', 'tr-dash');
        for (const t of tiles) {
            const tile = el('button', 'tr-tile');
            tile.append(el('div', 'tr-tile-name', t.name), el('div', 'tr-tile-today', t.today));
            if (t.extra) tile.append(el('div', 'tr-tile-extra', t.extra));
            tile.append(svgChart({ type: 'bar', labels: t.labels, values: t.values, goal: t.goal }, true));
            tile.addEventListener('click', () => ask(t.say));
            wrap.append(tile);
        }
        if (!tiles.length) wrap.append(el('div', 'pop-empty', 'Nothing on the dashboard yet.'));
        body.append(wrap);
    };
})();
