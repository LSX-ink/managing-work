// Knowledge base pop-ups (knowledge*.py): a Markdown note with clickable [[links]], #tags and backlinks; the note
// graph (a small force layout in SVG); and a mind map drawn as a radial tree. Everything is built as DOM nodes
// with textContent, never innerHTML.
(() => {
    const kinds = window.jarvisPopupKinds = window.jarvisPopupKinds || {};
    const NS = 'http://www.w3.org/2000/svg';
    const INLINE = /(\[\[[^\[\]\n]+\]\]|\*\*[^*\n]+\*\*|\[[^\]\n]+\]\((?:https?:\/\/)[^\s)]+\)|`[^`\n]+`|(?<![\w#&/\[])#[A-Za-z][\w/-]*|(?<![*\w])\*[^*\n]+\*(?![*\w]))/;

    function svgEl(tag, attrs, text) {
        const n = document.createElementNS(NS, tag);
        for (const [k, v] of Object.entries(attrs || {})) n.setAttribute(k, v);
        if (text !== undefined) n.textContent = text;
        return n;
    }

    // Inline Markdown into a parent element: [[wiki links]], **bold**, *italic*, `code`, [text](https://...), #tags.
    function inline(parent, text, { el, ask }, missing) {
        for (const part of String(text).split(INLINE)) {
            if (!part) continue;
            if (part.startsWith('[[') && part.endsWith(']]')) {
                const inner = part.slice(2, -2);
                const [target, alias] = [inner.split(/[|#]/)[0].trim(), inner.includes('|') ? inner.split('|').pop() : ''];
                const gone = missing.has(target.toLowerCase());
                const link = el('button', `kn-link${gone ? ' missing' : ''}`, (alias || inner.split('|')[0]).trim());
                link.title = gone ? `Create ${target}` : `Open ${target}`;
                link.addEventListener('click', () => ask(gone ? `Create a note called ${target}` : `Open my note ${target}`));
                parent.append(link);
            } else if (part.startsWith('**') && part.endsWith('**') && part.length > 4) {
                parent.append(el('strong', '', part.slice(2, -2)));
            } else if (part.startsWith('`') && part.endsWith('`') && part.length > 2) {
                parent.append(el('code', '', part.slice(1, -1)));
            } else if (/^\[[^\]]+\]\(https?:\/\//.test(part)) {
                const m = part.match(/^\[([^\]]+)\]\(([^)\s]+)\)$/);
                const a = el('a', 'kn-url', m ? m[1] : part);
                if (m) { a.href = m[2]; a.target = '_blank'; a.rel = 'noopener noreferrer'; }
                parent.append(a);
            } else if (/^#[A-Za-z]/.test(part)) {
                const tag = el('button', 'kn-tag', part);
                tag.addEventListener('click', () => ask(`Show my notes tagged ${part}`));
                parent.append(tag);
            } else if (part.startsWith('*') && part.endsWith('*') && part.length > 2) {
                parent.append(el('em', '', part.slice(1, -1)));
            } else parent.append(document.createTextNode(part));
        }
    }

    function markdown(text, helpers, missing) {
        const { el } = helpers;
        const doc = el('div', 'kn-doc');
        let para = null, quote = null, fence = null;
        for (const raw of String(text).split(/\r?\n/)) {
            const line = raw.replace(/\s+$/, '');
            if (fence) {
                if (/^\s*```/.test(line)) fence = null;
                else fence.textContent += `${line}\n`;
                continue;
            }
            if (/^\s*```/.test(line)) { para = quote = null; fence = el('pre', 'kn-pre'); doc.append(fence); continue; }
            const h = line.match(/^(#{1,6})\s+(.*)$/);
            const li = line.match(/^(\s*)([-*+]|\d{1,4}[.)])\s+(.*)$/);
            const q = line.match(/^>\s?(.*)$/);
            if (!line.trim()) { para = quote = null; continue; }
            if (h) {
                para = quote = null;
                const head = el(`h${Math.min(6, h[1].length + 2)}`, 'kn-h');
                inline(head, h[2], helpers, missing);
                doc.append(head);
            } else if (li) {
                para = quote = null;
                const item = el('div', 'kn-li');
                item.style.marginLeft = `${Math.min(6, Math.floor(li[1].replace(/\t/g, '    ').length / 2)) * 16}px`;
                let rest = li[3];
                const task = rest.match(/^\[([ xX])\]\s*(.*)$/);
                if (task) rest = task[2];
                item.append(el('span', 'kn-bullet', task ? (task[1] === ' ' ? '☐' : '☑') : (/\d/.test(li[2]) ? li[2] : '•')));
                const words = el('span');
                inline(words, rest, helpers, missing);
                item.append(words);
                doc.append(item);
            } else if (q) {
                para = null;
                if (!quote) { quote = el('blockquote', 'kn-quote'); doc.append(quote); } else quote.append(el('br'));
                inline(quote, q[1], helpers, missing);
            } else {
                quote = null;
                if (!para) { para = el('p', 'kn-p'); doc.append(para); } else para.append(el('br'));
                inline(para, line.trim(), helpers, missing);
            }
        }
        return doc;
    }

    kinds['knowledge-note'] = (card, body, helpers) => {
        const { el, ask } = helpers;
        const data = card.data || {};
        const missing = new Set((data.missing || []).map((t) => t.toLowerCase()));
        body.append(markdown(data.text || '', helpers, missing));
        const back = el('div', 'kn-backlinks');
        back.append(el('div', 'kn-label', (data.backlinks || []).length ? 'Linked from' : 'No notes link here yet.'));
        for (const title of data.backlinks || []) {
            const b = el('button', 'kn-link', title);
            b.addEventListener('click', () => ask(`Open my note ${title}`));
            back.append(b);
        }
        body.append(back);
    };

    // Force layout: nodes repel, links pull, a little gravity keeps it together. Runs once, then draws.
    function layout(nodes, edges) {
        const n = nodes.length;
        const pos = nodes.map((_, i) => {
            const a = i * 2.39996, r = 30 * Math.sqrt(i + 1);
            return { x: Math.cos(a) * r, y: Math.sin(a) * r, vx: 0, vy: 0 };
        });
        for (let step = 0; step < 300; step++) {
            const heat = 1 - step / 300;
            for (let i = 0; i < n; i++) {
                for (let j = i + 1; j < n; j++) {
                    const dx = pos[i].x - pos[j].x, dy = pos[i].y - pos[j].y;
                    const d2 = Math.max(dx * dx + dy * dy, 25), f = 900 / d2;
                    const d = Math.sqrt(d2);
                    pos[i].vx += (dx / d) * f; pos[i].vy += (dy / d) * f;
                    pos[j].vx -= (dx / d) * f; pos[j].vy -= (dy / d) * f;
                }
            }
            for (const [a, b] of edges) {
                const dx = pos[b].x - pos[a].x, dy = pos[b].y - pos[a].y;
                const d = Math.sqrt(dx * dx + dy * dy) || 1, f = (d - 60) * 0.02;
                pos[a].vx += (dx / d) * f; pos[a].vy += (dy / d) * f;
                pos[b].vx -= (dx / d) * f; pos[b].vy -= (dy / d) * f;
            }
            for (const p of pos) {
                p.vx -= p.x * 0.01; p.vy -= p.y * 0.01;
                p.x += Math.max(-20, Math.min(20, p.vx)) * heat;
                p.y += Math.max(-20, Math.min(20, p.vy)) * heat;
                p.vx *= 0.5; p.vy *= 0.5;
            }
        }
        return pos;
    }

    function fitted(svg, points, pad) {
        const xs = points.map((p) => p.x), ys = points.map((p) => p.y);
        const x0 = Math.min(0, ...xs) - pad, y0 = Math.min(0, ...ys) - pad;
        const w = Math.max(0, ...xs) + pad - x0, h = Math.max(0, ...ys) + pad - y0;
        svg.setAttribute('viewBox', `${x0} ${y0} ${Math.max(w, 1)} ${Math.max(h, 1)}`);
    }

    kinds['knowledge-graph'] = (card, body, { el, ask }) => {
        const data = card.data || {};
        const nodes = data.nodes || [], edges = (data.edges || []).filter(([a, b]) => nodes[a] && nodes[b]);
        if (!nodes.length) { body.append(el('div', 'pop-empty', 'No notes yet.')); return; }
        const pos = layout(nodes, edges);
        const svg = svgEl('svg', { class: 'kn-graph' });
        fitted(svg, pos, 60);
        for (const [a, b] of edges) {
            svg.append(svgEl('line', { x1: pos[a].x, y1: pos[a].y, x2: pos[b].x, y2: pos[b].y, class: 'kn-edge' }));
        }
        nodes.forEach((node, i) => {
            const g = svgEl('g', { class: `kn-node${i === data.focus ? ' focus' : ''}${node.degree ? '' : ' alone'}`, tabindex: '0' });
            g.append(svgEl('circle', { cx: pos[i].x, cy: pos[i].y, r: 4 + Math.min(10, Math.sqrt(node.degree || 0) * 2) }));
            g.append(svgEl('text', { x: pos[i].x, y: pos[i].y - 9, 'text-anchor': 'middle' }, node.title));
            g.append(svgEl('title', {}, `${node.title} (${node.degree} links)`));
            const open = () => ask(`Open my note ${node.title}`);
            g.addEventListener('click', open);
            g.addEventListener('keydown', (e) => { if (e.key === 'Enter') open(); });
            svg.append(g);
        });
        body.append(svg, el('div', 'kn-hint', 'Click a note to open it.'));
    };

    // Radial tree: each branch gets a slice of the circle in proportion to its leaves; rings by depth.
    kinds['knowledge-mindmap'] = (card, body, { el }) => {
        const root = (card.data || {}).root;
        if (!root) return;
        const leaves = (n) => (n.children || []).length ? n.children.reduce((s, c) => s + leaves(c), 0) : 1;
        const RING = 120, placed = [];
        const place = (node, a0, a1, depth, parent) => {
            const mid = (a0 + a1) / 2, r = depth * RING - (depth > 1 ? (depth - 1) * 20 : 0);
            const p = { node, depth, parent, a: mid, x: Math.cos(mid) * r, y: Math.sin(mid) * r };
            placed.push(p);
            const total = leaves(node);
            let start = a0;
            for (const child of node.children || []) {
                const share = ((a1 - a0) * leaves(child)) / total;
                place(child, start, start + share, depth + 1, p);
                start += share;
            }
        };
        place(root, -Math.PI / 2, Math.PI * 1.5, 0, null);
        const svg = svgEl('svg', { class: 'kn-mind' });
        fitted(svg, placed, 110);
        for (const p of placed.filter((q) => q.parent)) {
            const q = p.parent;
            const cx = (Math.cos(p.a) * (q.depth ? Math.hypot(q.x, q.y) : 0) + p.x) / 2;
            const cy = (Math.sin(p.a) * (q.depth ? Math.hypot(q.x, q.y) : 0) + p.y) / 2;
            svg.append(svgEl('path', { d: `M${q.x},${q.y} Q${cx},${cy} ${p.x},${p.y}`, class: `kn-branch d${Math.min(p.depth, 3)}` }));
        }
        for (const p of placed) {
            const right = Math.cos(p.a) >= -0.01;
            const g = svgEl('g', { class: `kn-mnode d${Math.min(p.depth, 3)}` });
            g.append(svgEl('circle', { cx: p.x, cy: p.y, r: p.depth ? Math.max(3, 7 - p.depth) : 10 }));
            g.append(svgEl('text', p.depth ? {
                x: p.x + (right ? 9 : -9), y: p.y + 4, 'text-anchor': right ? 'start' : 'end',
            } : { x: 0, y: 30, 'text-anchor': 'middle' }, p.node.text));
            svg.append(g);
        }
        body.append(svg);
    };
})();
