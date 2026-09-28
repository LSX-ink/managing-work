// Conversation mode pop-ups (modes*.py): the current mode badge with a running clock, a daily check-in chart
// (energy, mood, focus), the quiz scoreboard, a debate summary by round, and the brainstorm board with star and
// remove buttons. Everything is drawn with textContent from plain data.
(() => {
    const kinds = (window.jarvisPopupKinds = window.jarvisPopupKinds || {});
    const NS = 'http://www.w3.org/2000/svg';

    kinds['modes-badge'] = (card, body, { el }) => {
        const d = card.data || {};
        const box = el('div', 'md-badge');
        const clock = el('div', 'md-since');
        box.append(el('div', 'md-dot'), el('div', 'md-label', d.label || ''), el('div', 'md-summary', d.summary || ''), clock);
        body.append(box);
        if (!d.since) return;
        const tick = () => {
            if (!clock.isConnected) return;
            const mins = Math.max(0, Math.floor((Date.now() - d.since) / 60000));
            clock.textContent = mins < 1 ? 'Just started' : `${mins >= 60 ? `${Math.floor(mins / 60)} h ` : ''}${mins % 60} min`;
            setTimeout(tick, 15000);
        };
        requestAnimationFrame(tick);
    };

    kinds['modes-checkin'] = (card, body, { el }) => {
        const { labels = [], series = [] } = card.data || {};
        if (!series.some((s) => (s.values || []).some((v) => typeof v === 'number'))) {
            body.append(el('div', 'pop-empty', 'No check-ins yet.'));
            return;
        }
        const W = 440, H = 210, L = 28, B = 30, T = 12, R = 10;
        const svg = document.createElementNS(NS, 'svg');
        svg.setAttribute('viewBox', `0 0 ${W} ${H}`);
        svg.setAttribute('class', 'pop-chart md-checkin');
        const add = (tag, attrs, text) => {
            const n = document.createElementNS(NS, tag);
            for (const [k, v] of Object.entries(attrs)) n.setAttribute(k, v);
            if (text !== undefined) n.textContent = text;
            svg.append(n);
            return n;
        };
        const y = (v) => T + (H - T - B) * (1 - (v - 1) / 4);
        const step = (W - L - R) / Math.max(1, labels.length);
        const x = (i) => L + step * (i + 0.5);
        [1, 3, 5].forEach((v) => {
            add('line', { x1: L, x2: W - R, y1: y(v), y2: y(v), class: 'grid' });
            add('text', { x: L - 6, y: y(v) + 4, 'text-anchor': 'end', class: 'axis' }, v);
        });
        const every = Math.ceil(labels.length / 7);
        labels.forEach((l, i) => { if (i % every === 0) add('text', { x: x(i), y: H - 10, 'text-anchor': 'middle', class: 'axis' }, l); });
        const legend = el('div', 'md-legend');
        series.forEach((s, n) => {
            const pts = (s.values || []).map((v, i) => (typeof v === 'number' ? [x(i), y(v)] : null));
            let path = '';
            pts.forEach((p, i) => { if (p) path += `${path && pts[i - 1] ? 'L' : 'M'}${p[0]},${p[1]} `; });
            add('path', { d: path.trim(), class: `md-line md-s${n}` });
            pts.forEach((p) => { if (p) add('circle', { cx: p[0], cy: p[1], r: 3, class: `md-dot-s md-s${n}` }); });
            const key = el('span', `md-key md-s${n}`);
            legend.append(key, el('span', 'md-key-label', s.name));
        });
        body.append(svg, legend);
    };

    kinds['modes-scoreboard'] = (card, body, { el }) => {
        const d = card.data || {};
        const top = el('div', 'md-score');
        top.append(el('div', 'md-big', `${d.correct || 0} / ${d.asked || 0}`),
            el('div', 'md-summary', d.finished ? `Final score · ${d.topic}` : `Question ${Math.min((d.asked || 0) + 1, d.total || 0)} of ${d.total || 0}`));
        body.append(top);
        const marks = el('div', 'md-marks');
        for (let i = 0; i < (d.total || 0) && i < 50; i++) {
            const m = (d.marks || [])[i];
            marks.append(el('span', `md-mark ${m === true ? 'right' : m === false ? 'wrong' : ''}`, m === true ? '✓' : m === false ? '✗' : '·'));
        }
        if (marks.children.length) body.append(marks);
        if ((d.recent || []).length) {
            body.append(el('div', 'md-head', 'Recent quizzes'));
            const ul = el('ul', 'md-recent');
            d.recent.forEach((q) => ul.append(el('li', '', `${q.date || ''}  ${q.topic}: ${q.correct}/${q.total}`)));
            body.append(ul);
        }
    };

    kinds['modes-debate'] = (card, body, { el }) => {
        const d = card.data || {};
        body.append(el('div', 'md-motion', d.motion || ''));
        const sides = el('div', 'md-sides');
        sides.append(el('div', 'md-head', `You: ${d.user_side || ''}`), el('div', 'md-head', `Alfred: ${d.alfred_side || ''}`));
        body.append(sides);
        if (!(d.rounds || []).length) { body.append(el('div', 'pop-empty', 'No arguments yet. You open.')); return; }
        d.rounds.forEach((r, i) => {
            body.append(el('div', 'md-round', `Round ${i + 1}`));
            const row = el('div', 'md-sides');
            for (const points of [r.user || [], r.alfred || []]) {
                const ul = el('ul', 'md-points');
                points.forEach((p) => ul.append(el('li', '', p)));
                row.append(ul);
            }
            body.append(row);
        });
    };

    kinds['modes-board'] = (card, body, { el, ask }) => {
        const ideas = (card.data || {}).ideas || [];
        if (!ideas.length) { body.append(el('div', 'pop-empty', 'No ideas yet. Start throwing them out.')); return; }
        const ul = el('ul', 'md-ideas');
        [...ideas].sort((a, b) => b.star - a.star || a.n - b.n).forEach((idea) => {
            const li = el('li', idea.star ? 'starred' : '');
            const star = el('button', 'md-icon', idea.star ? '★' : '☆');
            star.title = idea.star ? 'Unstar' : 'Star';
            star.setAttribute('aria-label', `${star.title} idea ${idea.n}`);
            star.addEventListener('click', () => ask(idea.star_say));
            const remove = el('button', 'md-icon', '×');
            remove.title = 'Remove';
            remove.setAttribute('aria-label', `Remove idea ${idea.n}`);
            remove.addEventListener('click', () => { li.classList.add('going'); ask(idea.remove_say); });
            li.append(star, el('span', 'md-n', `${idea.n}.`), el('span', 'md-idea', idea.text), remove);
            ul.append(li);
        });
        body.append(ul);
    };
})();
