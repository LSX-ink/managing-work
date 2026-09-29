// Creator content calendar pop-up (creatorstats_plan.py): a month grid; days with videos show a dot per video
// (filled once posted). Tapping a day asks Alfred what is planned on it. Uses textContent only.
(() => {
    const kinds = (window.jarvisPopupKinds = window.jarvisPopupKinds || {});
    const HEAD = ['Mo', 'Tu', 'We', 'Th', 'Fr', 'Sa', 'Su'];

    kinds['creatorstats-calendar'] = (card, body, { el, ask }) => {
        const d = card.data || {};
        const grid = el('div', 'cs-grid');
        HEAD.forEach((h) => grid.append(el('div', 'cs-head', h)));
        for (let i = 0; i < (d.first || 0); i++) grid.append(el('div', 'cs-blank'));
        for (let n = 1; n <= (d.length || 0); n++) {
            const items = (d.days && d.days[String(n)]) || [];
            const cell = el('button', 'cs-day' + (n === d.today ? ' cs-today' : ''));
            cell.type = 'button';
            cell.append(el('span', 'cs-num', String(n)));
            const dots = el('span', 'cs-dots');
            items.slice(0, 4).forEach((it) => dots.append(el('i', it.done ? 'cs-dot cs-done' : 'cs-dot')));
            cell.append(dots);
            if (items.length) cell.title = items.map((it) => `${it.t || ''} ${it.a}: ${it.title}`.trim()).join('\n');
            const iso = `${String(d.year).padStart(4, '0')}-${String(d.month).padStart(2, '0')}-${String(n).padStart(2, '0')}`;
            cell.addEventListener('click', () => ask(`${d.say_prefix || "What's planned on "}${iso}?`));
            grid.append(cell);
        }
        body.append(grid);
        if (card.text) body.append(el('div', 'cs-note', card.text));
    };
})();
