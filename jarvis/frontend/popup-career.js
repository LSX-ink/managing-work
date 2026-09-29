// Career pop-ups (see career_*.py): the job application board by stage, a STAR answer planner and a side-by-side
// comparison of job offers. Clicks send a line to Alfred, so Python stays the one true copy.
(() => {
    const kinds = (window.jarvisPopupKinds = window.jarvisPopupKinds || {});

    kinds['career-board'] = (card, body, { el, ask }) => {
        const data = card.data || {};
        const stages = data.stages || [];
        const cards = data.cards || [];
        const board = el('div', 'cr-board');
        stages.forEach((stage, index) => {
            const col = el('section', 'cr-col');
            const mine = cards.filter((c) => c.stage === stage);
            col.append(el('h4', 'cr-col-title', `${stage} · ${mine.length}`));
            for (const c of mine) {
                const item = el('div', 'cr-card');
                const name = el('button', 'cr-name', c.label);
                name.type = 'button';
                name.addEventListener('click', () => ask(`Show my ${c.label} application`));
                item.append(name);
                if (c.follow_up) item.append(el('div', 'cr-muted', `Follow up ${c.follow_up}`));
                const next = stages[index + 1];
                if (next && stage !== 'offer') {
                    const go = el('button', 'cr-move', `→ ${next}`);
                    go.type = 'button';
                    go.addEventListener('click', () => ask(`Move my ${c.label} application to ${next}`));
                    item.append(go);
                }
                col.append(item);
            }
            board.append(col);
        });
        body.append(board);
    };

    const STAR_LABELS = [['situation', 'Situation'], ['task', 'Task'], ['action', 'Action'], ['result', 'Result']];

    kinds['career-star'] = (card, body, { el, ask }) => {
        const data = card.data || {};
        const wrap = el('div', 'cr-star');
        wrap.append(el('div', 'cr-question', data.question || ''));
        for (const [key, label] of STAR_LABELS) {
            const box = el('div', 'cr-part' + (data[key] ? '' : ' empty'));
            box.append(el('div', 'cr-part-label', label));
            const text = el('div', 'cr-part-text', data[key] || 'Not planned yet');
            box.append(text);
            if (!data[key]) {
                box.tabIndex = 0;
                box.addEventListener('click', () => ask(`Add the ${key} to my STAR answer for: ${data.question}`));
            }
            wrap.append(box);
        }
        body.append(wrap);
    };

    kinds['career-compare'] = (card, body, { el }) => {
        const data = card.data || {};
        const offers = data.offers || [];
        const table = el('table', 'cr-table');
        const head = el('tr');
        head.append(el('th', '', 'Criterion'));
        for (const o of offers) head.append(el('th', '', o));
        table.append(head);
        for (const row of data.rows || []) {
            const tr = el('tr');
            tr.append(el('td', 'cr-crit', `${row.criterion} (${row.weight}%)`));
            (row.values || []).forEach((v, i) => {
                const td = el('td');
                td.append(el('div', '', v));
                const bar = el('div', 'cr-bar');
                const fill = el('span');
                fill.style.width = `${Math.max(0, Math.min(10, row.scores[i] || 0)) * 10}%`;
                bar.append(fill);
                td.append(bar);
                tr.append(td);
            });
            table.append(tr);
        }
        const totals = el('tr', 'cr-total');
        totals.append(el('td', '', 'Weighted score'));
        const best = Math.max(...(data.totals || [0]));
        (data.totals || []).forEach((t) => {
            totals.append(el('td', t === best ? 'cr-best' : '', `${t} / 10`));
        });
        table.append(totals);
        body.append(table);
    };
})();
