// People pop-up kind (people_book.py): a light family tree. One row per generation, partners side by side,
// lines from parents down to their children. Clicking a name asks Alfred for that person's card.
(() => {
    const kinds = window.jarvisPopupKinds = window.jarvisPopupKinds || {};
    const NS = 'http://www.w3.org/2000/svg';

    kinds['people-tree'] = (card, body, { el, ask }) => {
        const { rows = [], edges = [], partners = [], focus = '' } = card.data || {};
        if (!rows.length) { body.append(el('div', 'pop-empty', 'No family links yet.')); return; }
        const wrap = el('div', 'pt-tree');
        const svg = document.createElementNS(NS, 'svg');
        svg.setAttribute('class', 'pt-lines');
        wrap.append(svg);
        const nodes = new Map();
        rows.forEach((row) => {
            const line = el('div', 'pt-row');
            row.forEach((name) => {
                const node = el('button', `pt-node${name === focus ? ' focus' : ''}`, name);
                node.type = 'button';
                node.title = `Show ${name}'s card`;
                node.addEventListener('click', () => ask(`Show ${name}'s person card.`));
                nodes.set(name, node);
                line.append(node);
            });
            wrap.append(line);
        });
        body.append(wrap);

        const draw = () => {
            svg.replaceChildren();
            const box = wrap.getBoundingClientRect();
            svg.setAttribute('width', wrap.scrollWidth);
            svg.setAttribute('height', wrap.scrollHeight);
            const at = (name) => {
                const r = nodes.get(name).getBoundingClientRect();
                return { x: r.left - box.left + r.width / 2, top: r.top - box.top, bottom: r.bottom - box.top,
                         mid: r.top - box.top + r.height / 2, left: r.left - box.left, right: r.right - box.left };
            };
            const add = (tag, attrs) => {
                const n = document.createElementNS(NS, tag);
                Object.entries(attrs).forEach(([k, v]) => n.setAttribute(k, v));
                svg.append(n);
            };
            partners.forEach(([a, b]) => {
                if (!nodes.has(a) || !nodes.has(b)) return;
                const [p, q] = [at(a), at(b)].sort((m, n) => m.x - n.x);
                if (Math.abs(p.mid - q.mid) < 4) add('line', { x1: p.right, y1: p.mid, x2: q.left, y2: q.mid, class: 'pt-partner' });
            });
            edges.forEach(([parent, child]) => {
                if (!nodes.has(parent) || !nodes.has(child)) return;
                const p = at(parent), c = at(child), bend = (p.bottom + c.top) / 2;
                add('path', { d: `M${p.x},${p.bottom} V${bend} H${c.x} V${c.top}`, class: 'pt-child' });
            });
        };
        requestAnimationFrame(draw);
        if (window.ResizeObserver) new ResizeObserver(() => requestAnimationFrame(draw)).observe(wrap);
    };
})();
