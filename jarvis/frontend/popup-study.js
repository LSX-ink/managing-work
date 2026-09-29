// Study pop-up kinds (study_plan.py, study_topics.py): a week grid for the revision timetable, a red/amber/green
// topic heatmap (every cell also shows a letter and a pattern, so it never relies on colour) and a big formula sheet.
(() => {
    const kinds = window.jarvisPopupKinds = window.jarvisPopupKinds || {};
    const hue = (subjects, name) => Math.max(0, subjects.indexOf(name)) * 47 % 360;

    kinds['study-week'] = (card, body, { el }) => {
        const { days = [], subjects = [], sessions = 3 } = card.data || {};
        const grid = el('div', 'st-week');
        grid.style.setProperty('--st-cols', String(Math.max(1, days.length)));
        for (const d of days) {
            const col = el('div', `st-day${d.today ? ' today' : ''}${d.exam.length ? ' exam' : ''}`);
            col.append(el('div', 'st-dayname', d.label + (d.today ? ' (today)' : '')));
            for (const s of d.exam) col.append(el('div', 'st-chip st-examchip', `EXAM: ${s}`));
            for (let i = 0; i < Math.max(sessions, d.slots.length); i++) {
                const s = d.slots[i];
                const chip = el('div', s ? 'st-chip' : 'st-chip st-empty', s || 'Rest');
                if (s) chip.style.setProperty('--st-hue', String(hue(subjects, s)));
                if (s || !d.slots.length) col.append(chip);
            }
            grid.append(col);
        }
        const legend = el('div', 'st-legend');
        for (const s of subjects) {
            const k = el('span', 'st-chip st-key', s);
            k.style.setProperty('--st-hue', String(hue(subjects, s)));
            legend.append(k);
        }
        body.append(grid, legend, el('div', 'st-hint', `Week ${card.data.week} of ${card.data.weeks}.`));
    };

    const NEXT = { '': 'red', red: 'amber', amber: 'green', green: 'red' };
    const LETTER = { red: 'R', amber: 'A', green: 'G', '': '-' };
    const WORD = { red: 'Red', amber: 'Amber', green: 'Green', '': 'Not rated' };

    kinds['study-heatmap'] = (card, body, { el, ask }) => {
        const legend = el('div', 'st-legend');
        for (const r of ['red', 'amber', 'green', '']) {
            legend.append(el('span', `st-cell st-key rag-${r || 'none'}`, `${LETTER[r]} ${WORD[r]}`));
        }
        body.append(legend);
        for (const c of (card.data || {}).courses || []) {
            const green = c.topics.filter((t) => t.rag === 'green').length;
            const row = el('div', 'st-course');
            row.append(el('div', 'st-coursename', `${c.name}: ${green} of ${c.topics.length} green`));
            const cells = el('div', 'st-cells');
            for (const t of c.topics) {
                const b = el('button', `st-cell rag-${t.rag || 'none'}`);
                b.type = 'button';
                b.append(el('span', 'st-letter', LETTER[t.rag]), el('span', 'st-name', t.name));
                b.title = `${t.name}: ${WORD[t.rag]}. Click to change.`;
                b.addEventListener('click', () => ask(`Set ${t.name} in ${c.name} to ${NEXT[t.rag]}.`));
                cells.append(b);
            }
            row.append(cells);
            body.append(row);
        }
        body.append(el('div', 'st-hint', 'Click a topic to move it to the next confidence level.'));
    };

    kinds['study-formulas'] = (card, body, { el }) => {
        const wrap = el('div', 'st-formulas');
        let size = 26;
        const bar = el('div', 'st-bar');
        const bigger = (d) => () => { size = Math.max(14, Math.min(60, size + d)); wrap.style.setProperty('--st-size', `${size}px`); };
        for (const [label, d] of [['A-', -4], ['A+', 4]]) {
            const b = el('button', 'pop-btn', label);
            b.type = 'button';
            b.addEventListener('click', bigger(d));
            bar.append(b);
        }
        wrap.style.setProperty('--st-size', `${size}px`);
        for (const f of (card.data || {}).items || []) {
            const item = el('div', 'st-formula');
            item.append(el('div', 'st-fname', f.name), el('div', 'st-fbody', f.formula));
            wrap.append(item);
        }
        body.append(bar, wrap);
    };
})();
