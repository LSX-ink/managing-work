// The "finance" pop-up kind (finance_store.py): stacked sections of progress bars, big numbers, charts,
// tables and clickable lists. Everything is written with textContent.
(() => {
    window.jarvisPopupKinds = window.jarvisPopupKinds || {};

    function meters(rows, el, ask) {
        const box = el('div', 'fin-meters');
        for (const r of rows || []) {
            const row = el(r.say ? 'button' : 'div', 'fin-meter');
            if (r.say) row.addEventListener('click', () => ask(r.say));
            const head = el('div', 'fin-meter-head');
            head.append(el('span', 'fin-meter-label', r.label), el('span', 'fin-meter-note', r.note || ''));
            const track = el('div', 'fin-track');
            const fill = el('div', 'fin-fill');
            const pct = r.max > 0 ? Math.max(0, Math.min(1, r.value / r.max)) : 0;
            fill.style.width = `${(pct * 100).toFixed(1)}%`;
            if (r.over) row.classList.add('over');
            track.append(fill);
            row.append(head, track);
            box.append(row);
        }
        return box;
    }

    function stats(items, el) {
        const grid = el('div', 'fin-stats');
        for (const s of items || []) {
            const cell = el('div', 'fin-stat');
            cell.append(el('div', 'fin-stat-value', s.value), el('div', 'fin-stat-label', s.label));
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

    window.jarvisPopupKinds.finance = (card, body, { el, ask, table, chart }) => {
        for (const s of (card.data && card.data.sections) || []) {
            const part = el('section', 'fin-section');
            if (s.title) part.append(el('h4', 'fin-title', s.title));
            if (s.type === 'meters') part.append(meters(s.rows, el, ask));
            else if (s.type === 'stats') part.append(stats(s.items, el));
            else if (s.type === 'chart') part.append(chart(s.chart || {}));
            else if (s.type === 'table') part.append(table(s.columns || [], s.rows || []));
            else if (s.type === 'list') part.append(list(s.items, el, ask));
            body.append(part);
        }
    };
})();
