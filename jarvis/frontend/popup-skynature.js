// Sky and nature pop-ups (skynature_sky.py): the moon drawn with its phase, a month of moons, a star map of tonight's
// sky and a 24-hour bar of night, blue hour, golden hour and day. Everything is drawn from numbers with textContent.
(() => {
    const kinds = window.jarvisPopupKinds = window.jarvisPopupKinds || {};
    const NS = 'http://www.w3.org/2000/svg';
    const MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];

    function svgEl(parent, tag, attrs, text) {
        const n = document.createElementNS(NS, tag);
        for (const [k, v] of Object.entries(attrs || {})) n.setAttribute(k, v);
        if (text !== undefined) n.textContent = text;
        if (parent) parent.append(n);
        return n;
    }

    // A moon of radius r at (cx, cy): dark disc, then the lit part between the bright limb and the terminator.
    function drawMoon(svg, cx, cy, r, illum, waxing) {
        svgEl(svg, 'circle', { cx, cy, r, class: 'sn-dark' });
        if (illum <= 0.01) return;
        if (illum >= 0.99) {
            svgEl(svg, 'circle', { cx, cy, r, class: 'sn-lit' });
            return;
        }
        const rx = Math.abs(1 - 2 * illum) * r;
        const limb = waxing ? 1 : 0;
        const term = (waxing === (illum < 0.5)) ? 0 : 1;
        svgEl(svg, 'path', {
            d: `M ${cx} ${cy - r} A ${r} ${r} 0 0 ${limb} ${cx} ${cy + r} A ${rx} ${r} 0 0 ${term} ${cx} ${cy - r} Z`,
            class: 'sn-lit',
        });
    }

    function facts(body, el, rows) {
        const dl = el('dl', 'sn-facts');
        for (const [label, value] of rows || []) dl.append(el('dt', '', String(label)), el('dd', '', String(value)));
        body.append(dl);
    }

    kinds['skynature-moon'] = (card, body, { el }) => {
        const data = card.data || {};
        const svg = svgEl(null, 'svg', { viewBox: '0 0 120 120', class: 'sn-moon', role: 'img', 'aria-label': data.name || 'Moon' });
        drawMoon(svg, 60, 60, 52, data.illum || 0, !!data.waxing);
        body.append(svg, el('div', 'sn-name', data.name || ''));
        facts(body, el, data.rows);
    };

    kinds['skynature-moon-cal'] = (card, body, { el, ask }) => {
        const data = card.data || {};
        const grid = el('div', 'sn-cal');
        ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'].forEach((d) => grid.append(el('div', 'sn-cal-head', d)));
        for (let i = 0; i < (data.offset || 0); i++) grid.append(el('div', 'sn-cal-blank'));
        const month = MONTHS.indexOf(data.month) + 1;
        (data.days || []).forEach((day) => {
            const cell = el('button', `sn-cal-day${day.tag ? ' key' : ''}`);
            const svg = svgEl(null, 'svg', { viewBox: '0 0 28 28', class: 'sn-mini' });
            drawMoon(svg, 14, 14, 12, day.illum, day.waxing);
            cell.append(svg, el('span', 'sn-cal-num', String(day.d)));
            if (day.tag) cell.append(el('span', 'sn-cal-tag', day.tag));
            cell.title = `${day.d} ${data.month}: ${Math.round(day.illum * 100)}% lit`;
            const iso = `${data.year}-${String(month).padStart(2, '0')}-${String(day.d).padStart(2, '0')}`;
            cell.addEventListener('click', () => ask(`What's the moon on ${iso}?`));
            grid.append(cell);
        });
        body.append(grid);
    };

    kinds['skynature-starmap'] = (card, body, { el }) => {
        const data = card.data || {};
        const S = 200;
        const svg = svgEl(null, 'svg', { viewBox: `${-S * 1.12} ${-S * 1.12} ${S * 2.24} ${S * 2.24}`, class: 'sn-map', role: 'img',
            'aria-label': `Star map for ${data.place || 'tonight'}` });
        svgEl(svg, 'circle', { r: S, class: `sn-sky${data.twilight ? ' twilight' : ''}` });
        [1 / 3, 2 / 3].forEach((f) => svgEl(svg, 'circle', { r: S * f, class: 'sn-ring' }));
        const at = (x, y) => [x * S, y * S];
        for (const [x1, y1, x2, y2] of data.lines || []) {
            const [a, b] = at(x1, y1), [c, d] = at(x2, y2);
            svgEl(svg, 'line', { x1: a, y1: b, x2: c, y2: d, class: 'sn-line' });
        }
        for (const [x, y, mag, name] of data.stars || []) {
            const [cx, cy] = at(x, y);
            const dot = svgEl(svg, 'circle', { cx, cy, r: Math.max(0.9, 3.6 - mag * 0.9), class: 'sn-star' });
            if (name) {
                dot.append(svgEl(null, 'title', {}, name));
                svgEl(svg, 'text', { x: cx + 5, y: cy - 4, class: 'sn-starname' }, name);
            }
        }
        for (const [name, x, y] of data.labels || []) {
            const [cx, cy] = at(x, y);
            svgEl(svg, 'text', { x: cx, y: cy + 14, 'text-anchor': 'middle', class: 'sn-con' }, name);
        }
        for (const p of data.planets || []) {
            const [cx, cy] = at(p.x, p.y);
            svgEl(svg, 'circle', { cx, cy, r: 4.5, class: 'sn-planet' });
            svgEl(svg, 'text', { x: cx + 7, y: cy + 4, class: 'sn-planetname' }, p.name);
        }
        if (data.moon) {
            const [cx, cy] = at(data.moon.x, data.moon.y);
            drawMoon(svg, cx, cy, 9, data.moon.illum, data.moon.waxing);
        }
        [['N', 0, -1.07], ['S', 0, 1.1], ['E', -1.07, 0.03], ['W', 1.07, 0.03]].forEach(([t, x, y]) => {
            svgEl(svg, 'text', { x: x * S, y: y * S + 4, 'text-anchor': 'middle', class: 'sn-compass' }, t);
        });
        body.append(svg, el('div', 'sn-hint', `${data.place || ''} ${data.when || ''}. Looking up with north at the top, east on the left; the centre is straight overhead.`));
    };

    kinds['skynature-daylight'] = (card, body, { el }) => {
        const data = card.data || {};
        const svg = svgEl(null, 'svg', { viewBox: '0 -20 1440 104', class: 'sn-day', role: 'img', 'aria-label': 'Light through the day' });
        for (const [from, to, kind] of data.bands || []) svgEl(svg, 'rect', { x: from, y: 14, width: to - from, height: 34, class: `sn-band ${kind}` });
        for (let h = 0; h <= 24; h += 3) {
            svgEl(svg, 'text', { x: h * 60, y: 72, 'text-anchor': h === 0 ? 'start' : h === 24 ? 'end' : 'middle', class: 'sn-tick' }, String(h).padStart(2, '0'));
        }
        for (const m of data.marks || []) {
            svgEl(svg, 'line', { x1: m.min, x2: m.min, y1: 8, y2: 54, class: 'sn-mark' });
            svgEl(svg, 'text', { x: m.min, y: 8, 'text-anchor': 'middle', class: 'sn-tick' }, m.label);
        }
        const legend = el('div', 'sn-legend');
        [['night', 'Night'], ['blue', 'Blue hour'], ['golden', 'Golden hour'], ['day', 'Day']].forEach(([k, label]) => {
            const chip = el('span', 'sn-chip');
            chip.append(el('i', `sn-swatch ${k}`), label);
            legend.append(chip);
        });
        body.append(svg, legend);
        facts(body, el, data.rows);
    };
})();
