// Pets and garden pop-up kinds (petsgarden_records.py): the raised bed planner grid.
// Type a plant, then click a square to plant it; click a square with an empty box to clear it.
(() => {
    const kinds = window.jarvisPopupKinds = window.jarvisPopupKinds || {};

    kinds['petsgarden-bed'] = (card, body, { el, ask }) => {
        const { bed = 'Raised bed', grid = [], plants = [] } = card.data || {};
        if (!grid.length) { body.append(el('div', 'pop-empty', 'This bed has no squares.')); return; }
        const tools = el('div', 'pg-tools');
        const input = el('input');
        input.placeholder = 'Plant to put in a square';
        input.setAttribute('aria-label', 'Plant');
        input.setAttribute('list', 'pg-plants');
        const options = el('datalist');
        options.id = 'pg-plants';
        plants.forEach((p) => { const o = el('option'); o.value = p; options.append(o); });
        tools.append(input, options);
        const cells = el('div', 'pg-grid');
        cells.style.gridTemplateColumns = `repeat(${grid[0].length}, 1fr)`;
        grid.forEach((row, r) => row.forEach((name, c) => {
            const cell = el('button', name ? 'pg-cell full' : 'pg-cell', name);
            cell.title = `Row ${r + 1}, column ${c + 1}`;
            cell.addEventListener('click', () => {
                const plant = input.value.trim();
                ask(plant
                    ? `In my ${bed} bed, plant ${plant} in row ${r + 1}, column ${c + 1}.`
                    : `In my ${bed} bed, clear row ${r + 1}, column ${c + 1}.`);
            });
            cells.append(cell);
        }));
        body.append(tools, cells, el('div', 'pg-hint', 'Type a plant, then click a square. Leave the box empty to clear a square.'));
    };
})();
