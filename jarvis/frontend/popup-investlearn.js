// Investing basics pop-up kinds (investlearn_*.py): multi-line growth chart, comparison bars, tap-to-flip cards.
// Text only, never innerHTML; clicking a row or card with a say line asks Alfred.
(() => {
    const kinds = (window.jarvisPopupKinds = window.jarvisPopupKinds || {});
    const NS = 'http://www.w3.org/2000/svg';
    const svgEl = (name, attrs = {}) => {
        const node = document.createElementNS(NS, name);
        for (const [k, v] of Object.entries(attrs)) node.setAttribute(k, String(v));
        return node;
    };
    const short = (n, unit) => {
        const a = Math.abs(n);
        const v = a >= 1e6 ? `${(n / 1e6).toFixed(1)}m` : a >= 1e3 ? `${Math.round(n / 1e3)}k` : String(Math.round(n));
        return unit + v;
    };
    const DASH = { solid: '', dashed: '7 4', dotted: '2 4' };
    const SHADES = [1, 0.75, 0.55, 0.9, 0.4, 0.3];

    kinds['investlearn-growth'] = (card, body, { el }) => {
        const { labels = [], series = [], lines = [], note = '', unit = '£' } = card.data || {};
        const W = 340, H = 170, L = 44, R = 8, T = 8, B = 20;
        const all = series.flatMap((s) => s.values);
        const top = Math.max(1, ...all), low = Math.min(0, ...all);
        const n = Math.max(1, labels.length - 1);
        const x = (i) => L + (i / n) * (W - L - R);
        const y = (v) => T + (1 - (v - low) / (top - low || 1)) * (H - T - B);
        const svg = svgEl('svg', { viewBox: `0 0 ${W} ${H}`, class: 'il-chart', role: 'img' });
        svg.append(svgEl('title'));
        svg.firstChild.textContent = card.title;
        for (const f of [0, 0.5, 1]) {
            const v = low + (top - low) * f;
            svg.append(svgEl('line', { x1: L, x2: W - R, y1: y(v), y2: y(v), class: 'il-grid' }));
            const t = svgEl('text', { x: L - 4, y: y(v) + 3, class: 'il-tick', 'text-anchor': 'end' });
            t.textContent = short(v, unit);
            svg.append(t);
        }
        [0, Math.floor(n / 2), n].forEach((i, k) => {
            const t = svgEl('text', { x: x(i), y: H - 5, class: 'il-tick', 'text-anchor': k === 0 ? 'start' : k === 2 ? 'end' : 'middle' });
            t.textContent = labels[i] || '';
            svg.append(t);
        });
        series.forEach((s, k) => {
            const points = s.values.map((v, i) => `${x(i).toFixed(1)},${y(v).toFixed(1)}`).join(' ');
            const line = svgEl('polyline', { points, class: 'il-line', 'stroke-dasharray': DASH[s.style] || '', opacity: SHADES[k % SHADES.length] });
            svg.append(line);
        });
        const legend = el('div', 'il-legend');
        series.forEach((s, k) => {
            const key = el('span', 'il-key');
            const sw = svgEl('svg', { viewBox: '0 0 22 8', class: 'il-swatch' });
            sw.append(svgEl('line', { x1: 0, x2: 22, y1: 4, y2: 4, class: 'il-line', 'stroke-dasharray': DASH[s.style] || '', opacity: SHADES[k % SHADES.length] }));
            const last = s.values[s.values.length - 1];
            key.append(sw, `${s.name}: ${short(last, unit)}`);
            legend.append(key);
        });
        const facts = el('div', 'il-lines');
        for (const line of lines) facts.append(el('div', 'il-fact', line));
        body.append(svg, legend, facts, el('div', 'il-note', note));
    };

    kinds['investlearn-bars'] = (card, body, { el, ask }) => {
        const { rows = [], note = '' } = card.data || {};
        const wrap = el('div', 'il-bars');
        for (const r of rows) {
            const row = el(r.say ? 'button' : 'div', 'il-row');
            if (r.say) {
                row.type = 'button';
                row.addEventListener('click', () => ask(r.say));
            }
            const track = el('div', 'il-track');
            const fill = el('div', r.warn ? 'il-fill il-warn' : 'il-fill');
            fill.style.width = `${r.max ? Math.max(0, Math.min(100, (r.value / r.max) * 100)) : 0}%`;
            track.append(fill);
            row.append(el('div', 'il-label', r.label), track, el('div', 'il-text', r.text || ''));
            wrap.append(row);
        }
        body.append(wrap, el('div', 'il-note', note));
    };

    kinds['investlearn-cards'] = (card, body, { el, ask }) => {
        const { cards = [], note = '' } = card.data || {};
        const wrap = el('div', 'il-cards');
        for (const c of cards) {
            const item = el('button', 'il-card');
            item.type = 'button';
            const front = el('div', 'il-front', c.front);
            const back = el('div', 'il-back', c.back);
            back.hidden = true;
            item.append(front, back);
            item.addEventListener('click', () => {
                back.hidden = !back.hidden;
                item.classList.toggle('il-open', !back.hidden);
                if (c.say && !back.hidden) ask(c.say);
            });
            wrap.append(item);
        }
        body.append(wrap, el('div', 'il-note', note));
    };
})();
