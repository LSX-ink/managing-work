// Photography pop-ups (photo_*.py): depth of field, field of view and crop diagrams ("photo-dof", "photo-fov",
// "photo-crop"), a shot list with tick boxes ("photo-shots"), a project progress grid ("photo-progress") and a
// composition example with guide lines drawn over a picture ("photo-grid").
(() => {
    const kinds = window.jarvisPopupKinds = window.jarvisPopupKinds || {};
    const NS = 'http://www.w3.org/2000/svg';
    const svg = (tag, attrs = {}, parent) => {
        const n = document.createElementNS(NS, tag);
        for (const [k, v] of Object.entries(attrs)) n.setAttribute(k, v);
        if (parent) parent.append(n);
        return n;
    };
    const num = (v, d = 0) => (Number.isFinite(Number(v)) ? Number(v) : d);
    const text = (parent, x, y, str, cls, anchor = 'middle') => {
        const t = svg('text', { x, y, class: cls || 'photo-label', 'text-anchor': anchor }, parent);
        t.textContent = str;
        return t;
    };
    const metres = (m) => (m < 10 ? `${m.toFixed(2)} m` : `${m.toFixed(1)} m`);

    const facts = (body, el, rows) => {
        const dl = el('dl', 'photo-facts');
        for (const [k, v] of rows || []) {
            dl.append(el('dt', '', String(k)), el('dd', '', String(v)));
        }
        body.append(dl);
    };

    // ---- depth of field -----------------------------------------------------------------------------
    kinds['photo-dof'] = (card, body, { el }) => {
        const d = card.data || {};
        const focus = num(d.focus, 1), near = num(d.near, focus), far = d.far === null ? null : num(d.far, focus);
        const max = far === null ? focus * 2.2 : Math.max(far * 1.25, focus * 1.3);
        const W = 440, H = 120, x0 = 40, x1 = W - 16;
        const px = (m) => x0 + (Math.min(m, max) / max) * (x1 - x0);
        const root = svg('svg', { viewBox: `0 0 ${W} ${H}`, class: 'photo-svg', role: 'img',
            'aria-label': `Sharp from ${metres(near)} to ${far === null ? 'infinity' : metres(far)}, focused at ${metres(focus)}` });
        svg('rect', { x: x0, y: 40, width: x1 - x0, height: 30, class: 'photo-track' }, root);
        svg('rect', { x: px(near), y: 40, width: px(far === null ? max : far) - px(near), height: 30, class: 'photo-sharp' }, root);
        svg('path', { d: 'M8 46 h18 l6 -6 h10 v30 h-10 l-6 -6 h-18 z', class: 'photo-camera' }, root);
        svg('line', { x1: px(focus), y1: 30, x2: px(focus), y2: 80, class: 'photo-focus' }, root);
        text(root, px(focus), 24, `focus ${metres(focus)}`);
        text(root, px(near), 96, metres(near), 'photo-label', near > max * 0.8 ? 'end' : 'middle');
        text(root, far === null ? x1 - 4 : px(far), 96, far === null ? 'infinity' : metres(far), 'photo-label', far === null ? 'end' : 'middle');
        if (far === null) svg('path', { d: `M${x1 - 30} 55 h26 m-6 -5 l6 5 l-6 5`, class: 'photo-arrow' }, root);
        text(root, (px(near) + px(far === null ? max : far)) / 2, 60, 'sharp', 'photo-label photo-strong');
        body.append(root);
        facts(body, el, d.facts);
    };

    // ---- field of view ------------------------------------------------------------------------------
    kinds['photo-fov'] = (card, body, { el }) => {
        const d = card.data || {};
        const angle = Math.min(170, Math.max(2, num(d.angle, 40)));
        const half = (angle / 2) * Math.PI / 180, R = 150, cx = 150, cy = 170;
        const root = svg('svg', { viewBox: '0 0 300 190', class: 'photo-svg photo-fov', role: 'img',
            'aria-label': `Field of view ${angle} degrees` });
        const ex = R * Math.sin(half), ey = R * Math.cos(half);
        const wide = angle > 100;
        svg('path', { d: `M${cx} ${cy} L${cx - ex} ${cy - ey} A${R} ${R} 0 0 1 ${cx + ex} ${cy - ey} Z`, class: 'photo-wedge' }, root);
        svg('path', { d: `M${cx - 10} ${cy + 12} h20 l-4 -10 h-12 z`, class: 'photo-camera' }, root);
        text(root, cx, cy - R * 0.45, `${angle.toFixed(0)}°`, 'photo-label photo-big');
        if (!wide) text(root, cx, cy - ey - 6, `${num(d.width).toFixed(1)} m across at ${metres(num(d.distance))}`);
        body.append(root);
        facts(body, el, d.facts);
    };

    // ---- crop ---------------------------------------------------------------------------------------
    kinds['photo-crop'] = (card, body, { el }) => {
        const d = card.data || {};
        const w = Math.max(1, num(d.width, 3)), h = Math.max(1, num(d.height, 2));
        const scale = Math.min(300 / w, 200 / h);
        const root = svg('svg', { viewBox: `0 0 ${w * scale + 8} ${h * scale + 8}`, class: 'photo-svg photo-crop', role: 'img',
            'aria-label': `Crop ${d.cw} by ${d.ch} inside ${w} by ${h}` });
        svg('rect', { x: 4, y: 4, width: w * scale, height: h * scale, class: 'photo-full' }, root);
        svg('rect', { x: 4 + num(d.x) * scale, y: 4 + num(d.y) * scale, width: num(d.cw) * scale, height: num(d.ch) * scale,
            class: 'photo-keep' }, root);
        text(root, 4 + (num(d.x) + num(d.cw) / 2) * scale, 4 + (num(d.y) + num(d.ch) / 2) * scale, `${d.cw} x ${d.ch}`, 'photo-label photo-strong');
        body.append(root);
        facts(body, el, d.facts);
    };

    // ---- shot list ----------------------------------------------------------------------------------
    kinds['photo-shots'] = (card, body, { el, ask }) => {
        const d = card.data || {};
        const shots = d.shots || [];
        const bar = el('div', 'photo-bar'), fill = el('div', 'photo-bar-fill');
        bar.append(fill);
        const count = el('div', 'photo-count');
        const list = el('ul', 'photo-shots');
        const update = () => {
            const n = list.querySelectorAll('input:checked').length;
            fill.style.width = `${shots.length ? Math.round((n / shots.length) * 100) : 0}%`;
            count.textContent = n === shots.length && n ? 'Every shot captured' : `${n} of ${shots.length} shots done`;
        };
        shots.forEach((s, i) => {
            const li = el('li', s.done ? 'done' : '');
            const box = el('input');
            box.type = 'checkbox';
            box.checked = !!s.done;
            box.id = `${card.id}-${i}`;
            const label = el('label', '', `${s.n}. ${s.text}`);
            label.htmlFor = box.id;
            box.addEventListener('change', () => { li.classList.toggle('done', box.checked); update(); if (s.say) ask(s.say); });
            li.append(box, label);
            list.append(li);
        });
        if (!shots.length) list.append(el('li', 'pop-empty', 'No shots yet.'));
        body.append(bar, count, list);
        update();
    };

    // ---- project progress ---------------------------------------------------------------------------
    kinds['photo-progress'] = (card, body, { el }) => {
        const d = card.data || {};
        const cells = d.cells || [];
        const done = num(d.done), target = Math.max(1, num(d.target, cells.length));
        body.append(el('div', 'photo-pct', `${Math.round((done / target) * 100)}%`));
        const grid = el('div', 'photo-cells');
        grid.setAttribute('role', 'img');
        grid.setAttribute('aria-label', `${done} of ${target} photos`);
        cells.forEach((on, i) => {
            const cell = el('span', on ? 'photo-cell on' : 'photo-cell', '');
            cell.title = `${d.kind === 'daily' ? 'Day' : 'Photo'} ${i + 1}`;
            grid.append(cell);
        });
        body.append(grid);
        if (target > cells.length) body.append(el('div', 'photo-count', `Showing the first ${cells.length} of ${target}.`));
        facts(body, el, d.facts);
        for (const n of d.notes || []) body.append(el('div', 'photo-note', n));
    };

    // ---- composition example ------------------------------------------------------------------------
    const W = 300, H = 200;
    const line = (g, x1, y1, x2, y2) => svg('line', { x1, y1, x2, y2, class: 'photo-guide' }, g);
    const dot = (g, x, y, r = 6, cls = 'photo-subject') => svg('circle', { cx: x, cy: y, r, class: cls }, g);
    const scene = (g, opts = {}) => {
        const horizon = opts.horizon ?? H * 0.62;
        svg('rect', { x: 0, y: 0, width: W, height: H, class: 'photo-sky' }, g);
        svg('rect', { x: 0, y: horizon, width: W, height: H - horizon, class: 'photo-ground' }, g);
    };
    const OVERLAYS = {
        thirds(g) {
            scene(g, { horizon: H * 2 / 3 });
            for (const f of [1 / 3, 2 / 3]) { line(g, W * f, 0, W * f, H); line(g, 0, H * f, W, H * f); }
            dot(g, W * 2 / 3, H / 3, 9);
            for (const x of [W / 3, W * 2 / 3]) for (const y of [H / 3, H * 2 / 3]) dot(g, x, y, 3, 'photo-point');
        },
        golden(g) {
            scene(g, { horizon: H * 0.618 });
            for (const f of [0.382, 0.618]) { line(g, W * f, 0, W * f, H); line(g, 0, H * f, W, H * f); }
            dot(g, W * 0.618, H * 0.382, 9);
        },
        leading(g) {
            scene(g, { horizon: H * 0.45 });
            svg('path', { d: `M${W * 0.05} ${H} L${W * 0.5} ${H * 0.45} L${W * 0.95} ${H}`, class: 'photo-road' }, g);
            line(g, W * 0.05, H, W * 0.5, H * 0.45); line(g, W * 0.95, H, W * 0.5, H * 0.45);
            line(g, W * 0.3, H, W * 0.5, H * 0.45); line(g, W * 0.7, H, W * 0.5, H * 0.45);
            dot(g, W * 0.5, H * 0.45, 6);
        },
        symmetry(g) {
            scene(g);
            line(g, W / 2, 0, W / 2, H);
            svg('path', { d: `M${W * 0.3} ${H * 0.62} L${W * 0.5} ${H * 0.25} L${W * 0.7} ${H * 0.62} Z`, class: 'photo-subject' }, g);
            svg('path', { d: `M${W * 0.3} ${H * 0.62} L${W * 0.5} ${H * 0.99} L${W * 0.7} ${H * 0.62} Z`, class: 'photo-mirror' }, g);
        },
        framing(g) {
            scene(g);
            svg('path', { d: `M0 0 H${W} V${H} H0 Z M${W * 0.2} ${H * 0.18} V${H * 0.85} H${W * 0.8} V${H * 0.18} Z`, class: 'photo-frame', 'fill-rule': 'evenodd' }, g);
            dot(g, W / 2, H * 0.55, 9);
        },
        diagonal(g) {
            scene(g);
            line(g, 0, H, W, 0);
            svg('path', { d: `M0 ${H} L${W * 0.5} ${H * 0.5} L${W} 0`, class: 'photo-road' }, g);
            dot(g, W * 0.7, H * 0.3, 8);
        },
        spiral(g) {
            scene(g);
            svg('path', { d: `M${W * 0.72} ${H * 0.4} C${W * 0.72} ${H * 0.2} ${W * 0.45} ${H * 0.2} ${W * 0.4} ${H * 0.45} `
                + `C${W * 0.38} ${H * 0.75} ${W * 0.1} ${H * 0.85} ${W * 0.04} ${H * 0.5}`, class: 'photo-spiral' }, g);
            dot(g, W * 0.72, H * 0.4, 8);
        },
        negative(g) {
            scene(g, { horizon: H * 0.85 });
            dot(g, W * 0.78, H * 0.78, 7);
            svg('rect', { x: 8, y: 8, width: W * 0.62, height: H * 0.6, class: 'photo-space' }, g);
        },
        fill(g) {
            scene(g);
            dot(g, W / 2, H / 2, H * 0.44);
            dot(g, W * 0.4, H * 0.42, 8, 'photo-point');
        },
        layers(g) {
            scene(g, { horizon: H * 0.5 });
            svg('path', { d: `M0 ${H * 0.5} L${W * 0.3} ${H * 0.3} L${W * 0.6} ${H * 0.5} Z`, class: 'photo-far' }, g);
            svg('rect', { x: W * 0.4, y: H * 0.62, width: W * 0.2, height: H * 0.14, class: 'photo-mid' }, g);
            dot(g, W * 0.15, H * 0.9, 16);
            text(g, W * 0.85, H * 0.15, 'far', 'photo-label'); text(g, W * 0.85, H * 0.7, 'middle', 'photo-label'); text(g, W * 0.15, H * 0.75, 'near', 'photo-label');
        },
        odds(g) {
            scene(g);
            [[0.3, 0.6, 12], [0.5, 0.45, 9], [0.7, 0.62, 14]].forEach(([x, y, r]) => dot(g, W * x, H * y, r));
        },
        pattern(g) {
            scene(g);
            for (let i = 0; i < 5; i++) for (let j = 0; j < 3; j++) {
                const odd = i === 3 && j === 1;
                if (odd) svg('rect', { x: 30 + i * 50, y: 30 + j * 55, width: 30, height: 30, class: 'photo-subject' }, g);
                else svg('circle', { cx: 45 + i * 50, cy: 45 + j * 55, r: 15, class: 'photo-mirror' }, g);
            }
        },
    };
    kinds['photo-grid'] = (card, body, { el }) => {
        const d = card.data || {};
        const root = svg('svg', { viewBox: `0 0 ${W} ${H}`, class: 'photo-svg photo-comp', role: 'img', 'aria-label': `${d.name} example` });
        (OVERLAYS[d.overlay] || OVERLAYS.thirds)(svg('g', {}, root));
        svg('rect', { x: 0.5, y: 0.5, width: W - 1, height: H - 1, class: 'photo-border' }, root);
        body.append(root);
        body.append(el('div', 'photo-how', String(d.how || '')));
        body.append(el('div', 'photo-tip', `Tip: ${d.tip || ''}`));
    };
})();
