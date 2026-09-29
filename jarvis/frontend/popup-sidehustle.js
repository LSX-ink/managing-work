// Side hustle pop-ups (see sidehustle_*.py): idea cards, comparison, calculator result, 30-day plan checklist, goal meter,
// weekly hours, monthly review and red-flag check. Text via textContent only; clicks send a line to Alfred.
(() => {
    const kinds = (window.jarvisPopupKinds = window.jarvisPopupKinds || {});
    const button = (el, cls, text, onclick) => {
        const b = el('button', cls, text);
        b.type = 'button';
        b.addEventListener('click', onclick);
        return b;
    };
    const bar = (el, pct, cls = '') => {
        const track = el('div', 'sh-track');
        const fill = el('div', `sh-fill ${cls}`);
        fill.style.width = `${Math.max(0, Math.min(100, pct))}%`;
        track.append(fill);
        return track;
    };
    const note = (el, wrap, text) => {
        if (text) wrap.append(el('div', 'sh-note', text));
    };

    kinds['sidehustle-ideas'] = (card, body, { el, ask }) => {
        const data = card.data || {};
        const wrap = el('div', 'sh-wrap');
        for (const i of data.ideas || []) {
            const item = el('div', 'sh-idea');
            item.append(button(el, 'sh-name', i.name, () => ask(i.say || `Tell me about ${i.name}`)));
            item.append(el('div', 'sh-muted', `Start ${i.cost} · first pound ${i.first} · ${i.hours}`));
            item.append(el('div', 'sh-muted', `Skills: ${i.skills}`));
            item.append(el('div', 'sh-risk', `Risk: ${i.risk}`));
            if (i.fit) item.append(el('div', 'sh-fit', i.fit));
            wrap.append(item);
        }
        note(el, wrap, data.note);
        body.append(wrap);
    };

    kinds['sidehustle-compare'] = (card, body, { el }) => {
        const data = card.data || {};
        const wrap = el('div', 'sh-wrap');
        const table = el('table', 'sh-table');
        const head = el('tr');
        head.append(el('th', '', ''));
        for (const n of data.names || []) head.append(el('th', '', n));
        table.append(head);
        for (const r of data.rows || []) {
            const row = el('tr');
            r.forEach((cell, k) => row.append(el(k ? 'td' : 'th', k ? '' : 'sh-rowhead', cell)));
            table.append(row);
        }
        const scroll = el('div', 'sh-scroll');
        scroll.append(table);
        wrap.append(scroll);
        note(el, wrap, data.note);
        body.append(wrap);
    };

    kinds['sidehustle-calc'] = (card, body, { el }) => {
        const data = card.data || {};
        const wrap = el('div', 'sh-wrap');
        wrap.append(el('div', 'sh-big', data.headline || ''));
        if (data.sub) wrap.append(el('div', 'sh-muted', data.sub));
        if ((data.rows || []).length) {
            const table = el('table', 'sh-table');
            for (const [label, value] of data.rows) {
                const row = el('tr');
                row.append(el('th', 'sh-rowhead', label), el('td', 'sh-val', value));
                table.append(row);
            }
            wrap.append(table);
        }
        for (const n of data.notes || []) note(el, wrap, n);
        body.append(wrap);
    };

    kinds['sidehustle-plan'] = (card, body, { el, ask }) => {
        const data = card.data || {};
        const wrap = el('div', 'sh-wrap');
        wrap.append(el('div', 'sh-muted', `${data.done} of ${data.total} done · day ${data.day} · ${data.status}`));
        wrap.append(bar(el, data.total ? (100 * data.done) / data.total : 0));
        for (const w of data.weeks || []) {
            wrap.append(el('h4', 'sh-week', w.title));
            for (const t of w.tasks) {
                const row = button(el, `sh-task${t.done ? ' done' : ''}${t.late ? ' late' : ''}`, '', () => ask(t.say));
                row.append(el('span', 'sh-tick', t.done ? '✓' : '○'), el('span', 'sh-ttext', t.text), el('span', 'sh-due', t.late ? `${t.due} (late)` : t.due));
                wrap.append(row);
            }
        }
        note(el, wrap, data.note);
        body.append(wrap);
    };

    kinds['sidehustle-goal'] = (card, body, { el }) => {
        const data = card.data || {};
        const money = (n) => `£${Number(n).toLocaleString('en-GB', { maximumFractionDigits: 2 })}`;
        const wrap = el('div', 'sh-wrap');
        wrap.append(el('div', 'sh-big', `${money(data.so_far)} of ${money(data.goal)}`));
        wrap.append(bar(el, data.pct));
        wrap.append(el('div', 'sh-muted', `${data.pct}% · ${data.days_left} days left this month · ${data.hours} hours logged`));
        if (data.projected != null) wrap.append(el('div', 'sh-muted', `At this pace: about ${money(data.projected)} (an estimate, not a promise)`));
        for (const h of data.hustles || []) wrap.append(el('div', 'sh-line', `${h.name}: ${money(h.profit)}`));
        note(el, wrap, data.note);
        body.append(wrap);
    };

    kinds['sidehustle-hours'] = (card, body, { el }) => {
        const data = card.data || {};
        const wrap = el('div', 'sh-wrap');
        const peak = Math.max(1, data.target || 0, ...(data.series || []).flatMap((s) => s.values));
        for (const s of data.series || []) {
            wrap.append(el('div', 'sh-hname', s.name));
            (data.weeks || []).forEach((label, k) => {
                const row = el('div', 'sh-hrow');
                row.append(el('span', 'sh-hlabel', label), bar(el, (100 * s.values[k]) / peak), el('span', 'sh-hval', `${s.values[k]} h`));
                wrap.append(row);
            });
        }
        if (data.target) wrap.append(el('div', 'sh-muted', `Your weekly aim: ${data.target} hours`));
        body.append(wrap);
    };

    kinds['sidehustle-review'] = (card, body, { el }) => {
        const data = card.data || {};
        const wrap = el('div', 'sh-wrap');
        wrap.append(el('div', `sh-verdict ${data.verdict || ''}`, data.headline || ''));
        const table = el('table', 'sh-table');
        for (const [label, value] of data.stats || []) {
            const row = el('tr');
            row.append(el('th', 'sh-rowhead', label), el('td', 'sh-val', value));
            table.append(row);
        }
        wrap.append(table);
        for (const r of data.reasons || []) wrap.append(el('div', 'sh-line', r));
        wrap.append(el('h4', 'sh-week', 'Ask yourself'));
        for (const q of data.questions || []) wrap.append(el('div', 'sh-line', q));
        if (data.decision) wrap.append(el('div', 'sh-fit', `Recorded: ${data.decision}`));
        note(el, wrap, data.note);
        body.append(wrap);
    };

    kinds['sidehustle-redflags'] = (card, body, { el }) => {
        const data = card.data || {};
        const wrap = el('div', 'sh-wrap');
        if (data.score != null) {
            wrap.append(el('div', `sh-verdict ${data.score >= 8 ? 'stop' : data.score >= 4 ? 'change' : 'keep'}`, `Risk score ${data.score}: ${data.level}`));
            wrap.append(bar(el, Math.min(100, data.score * 8), data.score >= 4 ? 'warn' : ''));
        }
        if (data.excerpt) wrap.append(el('div', 'sh-quote', `"${data.excerpt}"`));
        for (const f of data.flags || []) {
            const item = el('div', 'sh-flag');
            item.append(el('div', 'sh-fname', f.label), el('div', 'sh-muted', f.why));
            wrap.append(item);
        }
        if (data.score === 0) wrap.append(el('div', 'sh-line', 'No obvious red flags found.'));
        for (const a of data.advice || []) note(el, wrap, a);
        body.append(wrap);
    };
})();
