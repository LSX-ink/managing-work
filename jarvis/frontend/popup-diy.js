// DIY pop-ups (diy_*.py): a floor plan drawn to scale from a room's measurements (kind "diy-plan") and a
// step-by-step how-to guide with a safety box and tick boxes (kind "diy-guide"). Ticks in the guide stay in the page.
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

    // ---- floor plan ---------------------------------------------------------------------------------
    kinds['diy-plan'] = (card, body, { el }) => {
        const d = card.data || {};
        const L = Math.max(0.5, num(d.length, 3)), W = Math.max(0.5, num(d.width, 3));
        const pad = 34, scale = Math.min(520 / L, 400 / W);
        const px = (m) => m * scale;
        const root = svg('svg', {
            viewBox: `0 0 ${px(L) + pad * 2} ${px(W) + pad * 2}`, class: 'diy-plan', role: 'img',
            'aria-label': `Floor plan of ${d.name}, ${L} by ${W} metres`,
        });
        const g = svg('g', { transform: `translate(${pad} ${pad})` }, root);
        svg('rect', { x: 0, y: 0, width: px(L), height: px(W), class: 'diy-floor' }, g);
        // Grid lines every metre.
        for (let i = 1; i < L; i++) svg('line', { x1: px(i), y1: 0, x2: px(i), y2: px(W), class: 'diy-grid' }, g);
        for (let i = 1; i < W; i++) svg('line', { x1: 0, y1: px(i), x2: px(L), y2: px(i), class: 'diy-grid' }, g);
        for (const it of d.items || []) {
            const x = px(num(it.x)), y = px(num(it.y)), w = px(num(it.w)), h = px(num(it.d));
            const item = svg('g', {}, g);
            svg('title', {}, item).textContent = `${it.name}: ${it.w} x ${it.d} m`;
            svg('rect', { x, y, width: w, height: h, rx: 3, class: 'diy-item' }, item);
            const t = svg('text', { x: x + w / 2, y: y + h / 2, class: 'diy-item-label', 'text-anchor': 'middle', 'dominant-baseline': 'middle' }, item);
            t.textContent = String(it.name).slice(0, Math.max(3, Math.floor(w / 6)));
        }
        svg('rect', { x: 0, y: 0, width: px(L), height: px(W), class: 'diy-walls' }, g);
        const opening = (o, kind) => {
            const horiz = o.wall === 'north' || o.wall === 'south';
            const a = px(num(o.offset)), b = a + px(num(o.width));
            const fixed = o.wall === 'north' || o.wall === 'west' ? 0 : (horiz ? px(W) : px(L));
            const pts = horiz ? [a, fixed, b, fixed] : [fixed, a, fixed, b];
            svg('line', { x1: pts[0], y1: pts[1], x2: pts[2], y2: pts[3], class: `diy-${kind}` }, g);
            if (kind === 'door') {
                // A quarter-circle showing the door's swing into the room.
                const r = b - a, sgn = o.wall === 'north' || o.wall === 'west' ? 1 : -1;
                const p = horiz
                    ? `M ${a} ${fixed} L ${a} ${fixed + sgn * r} A ${r} ${r} 0 0 ${sgn > 0 ? 0 : 1} ${b} ${fixed}`
                    : `M ${fixed} ${a} L ${fixed + sgn * r} ${a} A ${r} ${r} 0 0 ${sgn > 0 ? 1 : 0} ${fixed} ${b}`;
                svg('path', { d: p, class: 'diy-swing' }, g);
            }
        };
        (d.windows || []).forEach((o) => opening(o, 'window'));
        (d.doors || []).forEach((o) => opening(o, 'door'));
        const dim = (x, y, text, rot) => {
            const t = svg('text', { x, y, class: 'diy-dim', 'text-anchor': 'middle' }, g);
            t.textContent = text;
            if (rot) t.setAttribute('transform', `rotate(-90 ${x} ${y})`);
        };
        dim(px(L) / 2, -12, `${L} m`);
        dim(-14, px(W) / 2, `${W} m`, true);
        svg('text', { x: px(L) + 2, y: -12, class: 'diy-dim', 'text-anchor': 'end' }, g).textContent = 'N ↑';
        body.append(root);
        const key = el('div', 'diy-key');
        key.append(el('span', 'diy-key-door', 'Door'), el('span', 'diy-key-window', 'Window'), el('span', 'diy-key-item', 'Furniture'));
        body.append(key);
        body.append(el('div', 'diy-note', `${(L * W).toFixed(1)} m² floor, ${num(d.height, 2.4)} m ceiling. Each square is one metre.`));
    };

    // ---- how-to guide -------------------------------------------------------------------------------
    kinds['diy-guide'] = (card, body, { el }) => {
        const d = card.data || {};
        const steps = d.steps || [];
        const meta = el('div', 'diy-meta');
        meta.append(el('span', 'diy-chip', `About ${d.minutes} min`), el('span', 'diy-chip', String(d.level || '')));
        body.append(meta);
        if ((d.safety || []).length) {
            const box = el('div', 'diy-safety');
            box.setAttribute('role', 'note');
            box.append(el('div', 'diy-safety-h', 'Safety first'));
            const ul = el('ul');
            for (const s of d.safety) ul.append(el('li', '', s));
            box.append(ul);
            body.append(box);
        }
        if ((d.tools || []).length) {
            body.append(el('div', 'diy-h', 'You will need'));
            body.append(el('div', 'diy-tools', d.tools.join(', ')));
        }
        body.append(el('div', 'diy-h', 'Steps'));
        const bar = el('div', 'diy-bar');
        const fill = el('div', 'diy-bar-fill');
        bar.append(fill);
        const count = el('div', 'diy-count');
        const list = el('ol', 'diy-steps');
        const update = () => {
            const n = list.querySelectorAll('input:checked').length;
            fill.style.width = `${steps.length ? Math.round((n / steps.length) * 100) : 0}%`;
            count.textContent = n === steps.length && n ? 'All done' : `${n} of ${steps.length} steps done`;
        };
        steps.forEach((s, i) => {
            const li = el('li');
            const box = el('input');
            box.type = 'checkbox';
            box.id = `${card.id}-${i}`;
            const label = el('label', '', s);
            label.htmlFor = box.id;
            box.addEventListener('change', () => { li.classList.toggle('done', box.checked); update(); });
            li.append(box, label);
            list.append(li);
        });
        body.append(bar, count, list);
        update();
        if (d.pro) body.append(el('div', 'diy-pro', `Call a professional if: ${d.pro}`));
    };
})();
