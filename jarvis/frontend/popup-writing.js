// The "writing-studio" pop-up kind (writing_store.py): stacked sections of big numbers, progress bars, charts,
// tables, clickable lists, a character card's facts and text. Everything is written with textContent.
(() => {
    window.jarvisPopupKinds = window.jarvisPopupKinds || {};

    function stats(items, el) {
        const grid = el('div', 'wr-stats');
        for (const s of items || []) {
            const cell = el('div', 'wr-stat');
            cell.append(el('div', 'wr-stat-value', String(s.value ?? '')), el('div', 'wr-stat-label', s.label));
            grid.append(cell);
        }
        return grid;
    }

    function meters(rows, el) {
        const box = el('div', 'wr-meters');
        for (const r of rows || []) {
            const row = el('div', 'wr-meter');
            const head = el('div', 'wr-meter-head');
            head.append(el('span', '', r.label), el('span', 'wr-note', r.note || ''));
            const track = el('div', 'wr-track');
            const fill = el('div', 'wr-fill');
            const pct = r.max > 0 ? Math.max(0, Math.min(1, r.value / r.max)) : 0;
            fill.style.width = `${(pct * 100).toFixed(1)}%`;
            if (pct >= 1) row.classList.add('met');
            track.append(fill);
            row.append(head, track);
            box.append(row);
        }
        return box;
    }

    function list(items, el, ask) {
        const ul = el('ul', 'wr-list');
        for (const item of items || []) {
            const li = el('li');
            const row = el(item.say ? 'button' : 'div', 'wr-item');
            if (item.say) row.addEventListener('click', () => ask(item.say));
            row.append(el('span', 'wr-item-label', item.label));
            if (item.note) row.append(el('span', 'wr-note', item.note));
            li.append(row);
            ul.append(li);
        }
        return ul;
    }

    function fields(items, el) {
        const dl = el('dl', 'wr-fields');
        for (const f of items || []) dl.append(el('dt', '', f.label), el('dd', '', f.value));
        return dl;
    }

    window.jarvisPopupKinds['writing-studio'] = (card, body, { el, ask, table, chart }) => {
        for (const s of (card.data && card.data.sections) || []) {
            const part = el('section', 'wr-section');
            if (s.title) part.append(el('h4', 'wr-title', s.title));
            if (s.type === 'stats') part.append(stats(s.items, el));
            else if (s.type === 'meters') part.append(meters(s.rows, el));
            else if (s.type === 'chart') part.append(chart(s.chart || {}));
            else if (s.type === 'table') part.append(table(s.columns || [], s.rows || []));
            else if (s.type === 'list') part.append(list(s.items, el, ask));
            else if (s.type === 'fields') part.append(fields(s.items, el));
            else if (s.type === 'text') part.append(el('p', 'wr-text', s.text || ''));
            body.append(part);
        }
    };
})();
