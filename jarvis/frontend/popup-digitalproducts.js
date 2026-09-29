// Digital products pop-up kinds (digitalproducts_ideas.py, digitalproducts_sell.py): the catalogue board by status and
// the pricing tiers. Text only, never innerHTML; tapping a product asks Alfred to show it.
(() => {
    const kinds = (window.jarvisPopupKinds = window.jarvisPopupKinds || {});

    kinds['digitalproducts-catalogue'] = (card, body, { el, ask }) => {
        const board = el('div', 'dp-board');
        for (const col of (card.data || {}).columns || []) {
            const box = el('div', `dp-col dp-${col.status}`);
            box.append(el('div', 'dp-head', `${col.status} (${col.items.length})`));
            for (const p of col.items) {
                const b = el('button', 'dp-item');
                b.type = 'button';
                b.append(el('span', 'dp-name', p.name), el('span', 'dp-meta', [p.format, p.price].filter(Boolean).join(' · ')));
                b.addEventListener('click', () => ask(p.say));
                box.append(b);
            }
            board.append(box);
        }
        body.append(board);
    };

    kinds['digitalproducts-tiers'] = (card, body, { el }) => {
        const { tiers = [], note = '' } = card.data || {};
        const row = el('div', 'dp-tiers');
        for (const t of tiers) {
            const box = el('div', 'dp-tier');
            box.append(el('div', 'dp-head', t.name), el('div', 'dp-price', t.price), el('div', 'dp-meta', t.what));
            row.append(box);
        }
        body.append(row, el('div', 'dp-meta', note));
    };
})();
