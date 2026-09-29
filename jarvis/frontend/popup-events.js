// Events pop-up kinds (events_*.py): "events-dashboard" (countdown, budget, guests, tasks), "events-timeline"
// (steps working back from a date, or a clock timetable), "events-budget" (planned against spent bars) and
// "events-seating" (tap a guest, then a seat).
(() => {
    const kinds = (window.jarvisPopupKinds = window.jarvisPopupKinds || {});
    const gbp = (n) => `£${Number(n || 0).toLocaleString('en-GB', { maximumFractionDigits: 2 })}`;

    const meter = (el, label, done, total, text) => {
        const row = el('div', 'ev-meter');
        const bar = el('div', 'ev-track');
        const fill = el('div', 'ev-fill');
        fill.style.width = `${total ? Math.min(100, Math.round((done / total) * 100)) : 0}%`;
        if (total && done > total) fill.classList.add('over');
        bar.append(fill);
        row.append(el('span', 'ev-label', label), bar, el('span', 'ev-value', text));
        return row;
    };

    kinds['events-dashboard'] = (card, body, { el, ask }) => {
        const d = card.data || {};
        const g = d.guests || {};
        const head = el('div', 'ev-head');
        const days = Number(d.days);
        head.append(el('div', 'ev-days', days === 0 ? 'Today' : days > 0 ? String(days) : String(-days)),
            el('div', 'ev-days-label', days === 0 ? 'the day is here' : days > 0 ? (days === 1 ? 'day to go' : 'days to go') : 'days ago'),
            el('div', 'ev-when', [d.date, d.place].filter(Boolean).join(' · ')));
        body.append(head);
        const b = d.budget || {};
        body.append(meter(el, 'Budget', b.spent, b.planned, b.planned ? `${gbp(b.spent)} of ${gbp(b.planned)}` : `${gbp(b.spent)} spent`));
        const t = d.tasks || {};
        body.append(meter(el, 'Tasks', t.done, t.total, `${t.done || 0} of ${t.total || 0}`));
        body.append(el('div', 'ev-guests', `Guests: ${d.headcount || 0} coming · ${g.maybe || 0} maybe · ${g.no || 0} no · ${g.pending || 0} waiting`));
        if ((d.next || []).length) {
            body.append(el('div', 'ev-sub', 'Next up'));
            const ul = el('ul', 'ev-next');
            for (const n of d.next) {
                const li = el('li', n.late ? 'late' : '');
                li.append(el('span', 'ev-next-when', n.when), el('span', '', n.text));
                ul.append(li);
            }
            body.append(ul);
        }
    };

    kinds['events-timeline'] = (card, body, { el, ask }) => {
        const { items = [], note = '' } = card.data || {};
        if (note) body.append(el('div', 'ev-note', note));
        if (!items.length) { body.append(el('div', 'pop-empty', 'Nothing on the timeline.')); return; }
        const ol = el('ol', 'ev-line');
        for (const i of items) {
            const li = el('li', `ev-step ${i.state || ''}`);
            const text = el(i.say ? 'button' : 'span', 'ev-step-text', i.text);
            if (i.say) { text.type = 'button'; text.addEventListener('click', () => ask(i.say)); }
            const when = el('div', 'ev-step-when', i.when);
            if (i.date) when.append(el('small', '', i.date));
            li.append(el('span', 'ev-dot', i.state === 'done' ? '✓' : ''), when, text);
            ol.append(li);
        }
        body.append(ol);
    };

    kinds['events-budget'] = (card, body, { el }) => {
        const { rows = [], total = {} } = card.data || {};
        const top = Math.max(1, ...rows.map((r) => Math.max(r.planned, r.spent)));
        const wrap = el('div', 'ev-budget');
        for (const r of rows) {
            const line = el('div', 'ev-cat');
            const over = r.planned && r.spent > r.planned;
            const bars = el('div', 'ev-bars');
            const plan = el('div', 'ev-bar plan');
            plan.style.width = `${(r.planned / top) * 100}%`;
            const spent = el('div', `ev-bar spent${over ? ' over' : ''}`);
            spent.style.width = `${(r.spent / top) * 100}%`;
            bars.append(plan, spent);
            line.append(el('span', 'ev-cat-name', r.cat), bars, el('span', 'ev-cat-num', `${gbp(r.spent)} / ${gbp(r.planned)}`));
            wrap.append(line);
        }
        body.append(wrap);
        body.append(el('div', 'ev-legend', 'Outline: planned. Solid: spent. Striped: over.'));
        body.append(el('div', 'ev-guests', `Total spent ${gbp(total.spent)}` + (total.planned ? ` of ${gbp(total.planned)}` : '')));
    };

    kinds['events-seating'] = (card, body, { el, ask }) => {
        const { event = '', tables = [], unseated = [] } = card.data || {};
        let chosen = '';
        const pool = el('div', 'ev-pool');
        const tableBox = el('div', 'ev-tables');
        const hint = el('div', 'ev-note');
        const setHint = () => { hint.textContent = chosen ? `Now tap a seat for ${chosen}.` : 'Tap a guest, then tap a seat.'; };
        const chips = [];
        for (const n of unseated) {
            const chip = el('button', 'ev-chip', n);
            chip.type = 'button';
            chip.addEventListener('click', () => {
                chosen = chosen === n ? '' : n;
                chips.forEach((c) => c.classList.toggle('on', c.textContent === chosen));
                setHint();
            });
            chips.push(chip);
            pool.append(chip);
        }
        if (!unseated.length) pool.append(el('span', 'ev-note', 'Everyone has a seat.'));
        for (const t of tables) {
            const box = el('div', 'ev-table');
            box.append(el('div', 'ev-table-name', t.name));
            const seats = el('div', 'ev-seats');
            for (const s of t.seats) {
                const seat = el('button', s.guest ? 'ev-seat full' : 'ev-seat', s.guest || String(s.n));
                seat.type = 'button';
                seat.title = `${t.name}, seat ${s.n}` + (s.guest ? `: ${s.guest}` : '');
                seat.addEventListener('click', () => {
                    if (s.guest) ask(`Take ${s.guest} off ${t.name} seat ${s.n} in ${event}.`);
                    else if (chosen) ask(`Seat ${chosen} at ${t.name} seat ${s.n} for ${event}.`);
                });
                seats.append(seat);
            }
            box.append(seats);
            tableBox.append(box);
        }
        setHint();
        body.append(hint, pool, tableBox);
    };
})();
