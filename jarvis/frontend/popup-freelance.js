// Freelance pop-ups (see freelance_*.py): pipeline board, calculator result, weekly timesheet, meters (retainers,
// capacity, availability) and tick-off checklists. Text via textContent only; clicks send a line to Alfred.
(() => {
    const kinds = (window.jarvisPopupKinds = window.jarvisPopupKinds || {});
    const button = (el, cls, text, onclick) => {
        const b = el('button', cls, text);
        b.type = 'button';
        b.addEventListener('click', onclick);
        return b;
    };
    const bar = (el, pct, over) => {
        const track = el('div', 'fl-track');
        const fill = el('div', `fl-fill${over ? ' over' : ''}`);
        fill.style.width = `${Math.max(0, Math.min(100, pct))}%`;
        track.append(fill);
        return track;
    };
    const note = (el, wrap, text) => {
        if (text) wrap.append(el('div', 'fl-note', text));
    };

    kinds['freelance-board'] = (card, body, { el, ask }) => {
        const data = card.data || {};
        const wrap = el('div', 'fl-wrap');
        const board = el('div', 'fl-board');
        for (const col of data.columns || []) {
            const c = el('div', 'fl-col');
            c.append(el('div', 'fl-colhead', `${col.stage} (${col.count})`), el('div', 'fl-muted', col.value));
            for (const k of col.cards || []) {
                const item = button(el, 'fl-lead', '', () => ask(k.say));
                item.append(el('div', 'fl-name', k.title), el('div', 'fl-muted', [k.client, k.value].filter(Boolean).join(' · ')));
                if (k.follow) item.append(el('div', 'fl-muted', `chase ${k.follow}`));
                c.append(item);
            }
            board.append(c);
        }
        wrap.append(board);
        note(el, wrap, data.note);
        body.append(wrap);
    };

    kinds['freelance-calc'] = (card, body, { el }) => {
        const data = card.data || {};
        const wrap = el('div', 'fl-wrap');
        wrap.append(el('div', 'fl-big', data.headline || ''));
        if (data.sub) wrap.append(el('div', 'fl-muted', data.sub));
        if ((data.rows || []).length) {
            const table = el('table', 'fl-table');
            for (const [label, value] of data.rows) {
                const row = el('tr');
                row.append(el('th', 'fl-rowhead', label), el('td', 'fl-val', value));
                table.append(row);
            }
            wrap.append(table);
        }
        for (const n of data.notes || []) note(el, wrap, n);
        body.append(wrap);
    };

    kinds['freelance-timesheet'] = (card, body, { el }) => {
        const data = card.data || {};
        const wrap = el('div', 'fl-wrap');
        const scroll = el('div', 'fl-scroll');
        const table = el('table', 'fl-table fl-sheet');
        const head = el('tr');
        head.append(el('th', '', ''));
        for (const d of data.days || []) head.append(el('th', 'fl-num', d));
        head.append(el('th', 'fl-num', 'Total'));
        table.append(head);
        const fmt = (h) => (h ? String(h) : '');
        for (const r of data.rows || []) {
            const row = el('tr');
            row.append(el('th', 'fl-rowhead', r.label));
            for (const h of r.hours) row.append(el('td', 'fl-num', fmt(h)));
            row.append(el('td', 'fl-num fl-val', String(r.total)));
            table.append(row);
        }
        const foot = el('tr', 'fl-foot');
        foot.append(el('th', '', 'All'));
        for (const h of data.totals || []) foot.append(el('td', 'fl-num', fmt(h)));
        foot.append(el('td', 'fl-num fl-val', String(data.total)));
        table.append(foot);
        scroll.append(table);
        wrap.append(scroll, el('div', 'fl-muted', `${data.total} hours this week`));
        body.append(wrap);
    };

    kinds['freelance-meter'] = (card, body, { el, ask }) => {
        const data = card.data || {};
        const wrap = el('div', 'fl-wrap');
        for (const r of data.rows || []) {
            const row = el('div', 'fl-mrow');
            const label = r.say ? button(el, 'fl-name fl-link', r.label, () => ask(r.say)) : el('div', 'fl-name', r.label);
            row.append(label, bar(el, r.max ? (100 * r.used) / r.max : 0, r.used > r.max), el('div', 'fl-muted', r.text));
            wrap.append(row);
        }
        note(el, wrap, data.note);
        body.append(wrap);
    };

    kinds['freelance-checklist'] = (card, body, { el, ask }) => {
        const data = card.data || {};
        const wrap = el('div', 'fl-wrap');
        wrap.append(el('div', 'fl-muted', `${data.done} of ${data.total} done`));
        wrap.append(bar(el, data.total ? (100 * data.done) / data.total : 0, false));
        for (const t of data.items || []) {
            const row = button(el, `fl-task${t.done ? ' done' : ''}`, '', () => ask(t.say));
            row.append(el('span', 'fl-tick', t.done ? '✓' : '○'), el('span', 'fl-ttext', t.text));
            wrap.append(row);
        }
        note(el, wrap, data.note);
        body.append(wrap);
    };
})();
