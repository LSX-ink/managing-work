// Creator business pop-ups (see creatorbiz_*.py): brand deal pipeline board, rate card estimate, invoice list and contract
// checklist. Text is set with textContent; clicks send a line to Alfred, so Python stays the one true copy.
(() => {
    const kinds = (window.jarvisPopupKinds = window.jarvisPopupKinds || {});

    kinds['creatorbiz-pipeline'] = (card, body, { el, ask }) => {
        const data = card.data || {};
        const stages = data.stages || [];
        const cards = data.cards || [];
        const board = el('div', 'cb-board');
        stages.forEach((stage, index) => {
            const mine = cards.filter((c) => c.stage === stage);
            if (!mine.length && ['paid', 'declined', 'delivered'].includes(stage)) return;
            const col = el('section', 'cb-col');
            col.append(el('h4', 'cb-col-title', `${stage} · ${mine.length}`));
            for (const c of mine) {
                const item = el('div', 'cb-card');
                const name = el('button', 'cb-name', c.label);
                name.type = 'button';
                name.addEventListener('click', () => ask(`Show my ${c.label} brand deal`));
                item.append(name);
                if (c.fee) item.append(el('div', 'cb-muted', c.fee));
                if (c.follow_up) item.append(el('div', 'cb-muted', `Follow up ${c.follow_up}`));
                const next = stages[index + 1];
                if (next && !['paid', 'invoiced', 'declined'].includes(stage) && next !== 'declined') {
                    const go = el('button', 'cb-move', `→ ${next}`);
                    go.type = 'button';
                    go.addEventListener('click', () => ask(`Move my ${c.label} brand deal to ${next}`));
                    item.append(go);
                }
                col.append(item);
            }
            board.append(col);
        });
        body.append(board);
    };

    kinds['creatorbiz-ratecard'] = (card, body, { el, ask }) => {
        const data = card.data || {};
        const wrap = el('div', 'cb-rate');
        wrap.append(el('div', 'cb-muted', `Typical views ${Number(data.views || 0).toLocaleString('en-GB')}`));
        const table = el('table', 'cb-table');
        for (const r of data.rows || []) {
            const row = el('tr');
            row.append(el('td', '', r.format), el('td', 'cb-price', `£${r.low} to £${r.high}`));
            table.append(row);
        }
        wrap.append(table);
        const extras = el('ul', 'cb-extras');
        for (const e of data.extras || []) extras.append(el('li', '', e));
        wrap.append(extras, el('div', 'cb-note', data.note || ''));
        body.append(wrap);
    };

    kinds['creatorbiz-invoices'] = (card, body, { el, ask }) => {
        const data = card.data || {};
        const wrap = el('div', 'cb-inv');
        wrap.append(el('div', 'cb-owed', `Still owed: ${data.owed || '£0'}`));
        for (const i of data.invoices || []) {
            const row = el('div', `cb-inv-row ${i.status}`);
            const name = el('button', 'cb-name', `${i.number} · ${i.brand}`);
            name.type = 'button';
            name.addEventListener('click', () => ask(`Show invoice ${i.number}`));
            row.append(name, el('span', 'cb-muted', `${i.total} · due ${i.due}`), el('span', `cb-badge ${i.status}`, i.status));
            if (i.status !== 'paid') {
                const paid = el('button', 'cb-move', 'mark paid');
                paid.type = 'button';
                paid.addEventListener('click', () => ask(`Invoice ${i.number} has been paid`));
                row.append(paid);
            }
            wrap.append(row);
        }
        body.append(wrap);
    };

    kinds['creatorbiz-checklist'] = (card, body, { el, ask }) => {
        const data = card.data || {};
        const wrap = el('div', 'cb-check');
        for (const i of data.items || []) {
            const row = el('label', 'cb-check-row' + (i.ticked ? ' ticked' : ''));
            const box = el('input');
            box.type = 'checkbox';
            box.checked = !!i.ticked;
            if (data.brand) {
                box.addEventListener('change', () =>
                    ask(`${box.checked ? 'Tick' : 'Untick'} ${i.key} on the ${data.brand} contract checklist`));
            } else {
                box.disabled = true;
            }
            const text = el('span', 'cb-check-text');
            text.append(el('strong', '', i.title), el('span', 'cb-muted', i.help));
            row.append(box, text);
            wrap.append(row);
        }
        wrap.append(el('div', 'cb-note', data.note || ''));
        body.append(wrap);
    };
})();
