// Seller calculator pop-ups (see sellercalc_*.py): result, platform compare, fee table, bars and guide.
// Text via textContent only; clicks send a line to Alfred.
(() => {
    const kinds = (window.jarvisPopupKinds = window.jarvisPopupKinds || {});
    const money = (n) => `${n < 0 ? '-' : ''}£${Math.abs(Number(n)).toLocaleString('en-GB', { maximumFractionDigits: 2, minimumFractionDigits: Number.isInteger(Number(n)) ? 0 : 2 })}`;
    const note = (el, wrap, text) => {
        if (text) wrap.append(el('div', 'sx-note', text));
    };

    kinds['sellercalc-result'] = (card, body, { el }) => {
        const data = card.data || {};
        const wrap = el('div', 'sx-wrap');
        wrap.append(el('div', 'sx-big', data.headline || ''));
        if (data.sub) wrap.append(el('div', 'sx-muted', data.sub));
        if ((data.rows || []).length) {
            const table = el('table', 'sx-table');
            for (const [label, value] of data.rows) {
                const row = el('tr');
                row.append(el('th', 'sx-rowhead', label), el('td', 'sx-val', value));
                table.append(row);
            }
            wrap.append(table);
        }
        for (const n of data.notes || []) note(el, wrap, n);
        body.append(wrap);
    };

    kinds['sellercalc-compare'] = (card, body, { el, ask }) => {
        const data = card.data || {};
        const wrap = el('div', 'sx-wrap');
        wrap.append(el('div', 'sx-muted', `Selling at ${money(data.price)}, item cost ${money(data.cost)}. Rates checked ${data.checked}.`));
        const rows = data.rows || [];
        const peak = Math.max(1, ...rows.map((r) => Math.abs(r.net)));
        for (const r of rows) {
            const line = el('button', `sx-plat${r.best ? ' best' : ''}`);
            line.type = 'button';
            line.addEventListener('click', () => ask(r.say));
            const head = el('div', 'sx-phead');
            head.append(el('span', 'sx-pname', r.name + (r.best ? ' (best)' : '')), el('span', 'sx-pnet', money(r.net)));
            const track = el('div', 'sx-track');
            const fill = el('div', `sx-fill${r.net < 0 ? ' loss' : ''}`);
            fill.style.width = `${Math.min(100, (100 * Math.abs(r.net)) / peak)}%`;
            track.append(fill);
            const small = `fees ${money(r.fees)} · postage ${money(r.postage)} · margin ${r.margin}%${r.note ? ` · ${r.note}` : ''}`;
            line.append(head, track, el('div', 'sx-muted', small));
            wrap.append(line);
        }
        note(el, wrap, data.note);
        body.append(wrap);
    };

    kinds['sellercalc-fees'] = (card, body, { el, ask }) => {
        const data = card.data || {};
        const wrap = el('div', 'sx-wrap');
        wrap.append(el('div', 'sx-muted', `Approximate rates, last looked over ${data.checked}. Fees change: check each site.`));
        for (const r of data.rows || []) {
            const item = el('div', 'sx-fee');
            const name = el('button', 'sx-name', r.name);
            name.type = 'button';
            name.addEventListener('click', () => ask(r.say));
            item.append(name, el('div', 'sx-val', r.fee + ((r.mine || []).length ? ' (yours)' : '')), el('div', 'sx-muted', r.note));
            wrap.append(item);
        }
        note(el, wrap, data.note);
        body.append(wrap);
    };

    kinds['sellercalc-bars'] = (card, body, { el }) => {
        const data = card.data || {};
        const wrap = el('div', 'sx-wrap');
        for (const r of data.rows || []) {
            const line = el('div', 'sx-bar');
            const head = el('div', 'sx-phead');
            head.append(el('span', 'sx-pname', r.label), el('span', 'sx-pnet', r.value));
            const track = el('div', 'sx-track');
            const fill = el('div', 'sx-fill');
            fill.style.width = `${r.pct}%`;
            track.append(fill);
            line.append(head, track);
            if (r.small) line.append(el('div', 'sx-muted', r.small));
            wrap.append(line);
        }
        note(el, wrap, data.note);
        body.append(wrap);
    };

    kinds['sellercalc-guide'] = (card, body, { el }) => {
        const data = card.data || {};
        const wrap = el('div', 'sx-wrap');
        for (const s of data.sections || []) {
            wrap.append(el('h4', 'sx-head', s.heading));
            for (const line of s.lines || []) wrap.append(el('div', 'sx-line', line));
        }
        note(el, wrap, data.note);
        body.append(wrap);
    };
})();
