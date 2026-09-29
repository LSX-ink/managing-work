// Writing income pop-ups (see writingincome_*.py): result, guide, check, board and meter.
// Text via textContent only; clicks send a line to Alfred.
(() => {
    const kinds = (window.jarvisPopupKinds = window.jarvisPopupKinds || {});
    const note = (el, wrap, text) => {
        if (text) wrap.append(el('div', 'wi-note', text));
    };

    kinds['writingincome-result'] = (card, body, { el }) => {
        const data = card.data || {};
        const wrap = el('div', 'wi-wrap');
        wrap.append(el('div', 'wi-big', data.headline || ''));
        if (data.sub) wrap.append(el('div', 'wi-muted', data.sub));
        if ((data.rows || []).length) {
            const table = el('table', 'wi-table');
            for (const [label, value] of data.rows) {
                const row = el('tr');
                row.append(el('th', 'wi-rowhead', label), el('td', 'wi-val', value));
                table.append(row);
            }
            wrap.append(table);
        }
        for (const n of data.notes || []) note(el, wrap, n);
        body.append(wrap);
    };

    kinds['writingincome-guide'] = (card, body, { el }) => {
        const data = card.data || {};
        const wrap = el('div', 'wi-wrap');
        for (const s of data.sections || []) {
            wrap.append(el('h4', 'wi-head', s.heading));
            for (const line of s.lines || []) wrap.append(el('div', 'wi-line', line));
        }
        note(el, wrap, data.note);
        body.append(wrap);
    };

    const marks = { ok: '✓', warn: '!', fail: '✗', todo: '○' };
    kinds['writingincome-check'] = (card, body, { el }) => {
        const data = card.data || {};
        const wrap = el('div', 'wi-wrap');
        wrap.append(el('div', 'wi-big', data.headline || ''));
        for (const item of data.items || []) {
            const row = el('div', `wi-check ${item.status}`);
            row.append(el('span', 'wi-mark', marks[item.status] || '○'));
            const text = el('div', 'wi-checktext');
            text.append(el('div', 'wi-checklabel', item.label));
            if (item.detail) text.append(el('div', 'wi-muted', item.detail));
            row.append(text);
            wrap.append(row);
        }
        note(el, wrap, data.note);
        body.append(wrap);
    };

    kinds['writingincome-board'] = (card, body, { el, ask }) => {
        const data = card.data || {};
        const wrap = el('div', 'wi-wrap');
        const cols = el('div', 'wi-cols');
        for (const col of data.columns || []) {
            const box = el('div', 'wi-col');
            box.append(el('h4', 'wi-head', col.title));
            for (const c of col.cards || []) {
                const btn = el('button', 'wi-card');
                btn.type = 'button';
                btn.addEventListener('click', () => ask(c.say));
                btn.append(el('div', 'wi-checklabel', c.label));
                if (c.small) btn.append(el('div', 'wi-muted', c.small));
                box.append(btn);
            }
            cols.append(box);
        }
        wrap.append(cols);
        note(el, wrap, data.note);
        body.append(wrap);
    };

    kinds['writingincome-meter'] = (card, body, { el }) => {
        const data = card.data || {};
        const wrap = el('div', 'wi-wrap');
        for (const r of data.rows || []) {
            const line = el('div', 'wi-bar');
            const head = el('div', 'wi-phead');
            head.append(el('span', 'wi-checklabel', r.label), el('span', 'wi-val', r.value));
            const track = el('div', 'wi-track');
            const fill = el('div', 'wi-fill');
            fill.style.width = `${Math.max(0, Math.min(100, Number(r.pct) || 0))}%`;
            track.append(fill);
            line.append(head, track);
            if (r.small) line.append(el('div', 'wi-muted', r.small));
            wrap.append(line);
        }
        note(el, wrap, data.note);
        body.append(wrap);
    };
})();
