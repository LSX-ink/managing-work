// Work pop-ups (see worktools_*.py): the kanban board, meeting action items and project / weekly summaries.
// The board is drawn from Alfred's saved copy; dragging a card asks Alfred to move it, so Python stays in charge.
(() => {
    const kinds = (window.jarvisPopupKinds = window.jarvisPopupKinds || {});

    kinds['work-kanban'] = (card, body, { el, ask }) => {
        const data = card.data || {};
        const project = data.project || '';
        const columns = data.columns || [];
        const cards = data.cards || [];
        const moveTo = (title, column) => ask(`Move card ${title} to ${column} on the ${project} board`);
        const wrap = el('div', 'wk');
        const board = el('div', 'wk-board');
        const detail = el('div', 'wk-detail');
        detail.hidden = true;

        const showDetail = (c) => {
            detail.replaceChildren(el('div', 'wk-detail-title', c.title));
            if (c.due) detail.append(el('div', 'wk-muted', `Due ${c.due}`));
            detail.append(el('div', 'wk-notes', c.notes || 'No notes yet.'));
            const remove = el('button', 'wk-btn', 'Remove card');
            remove.type = 'button';
            remove.addEventListener('click', () => ask(`Remove card ${c.title} from the ${project} board`));
            detail.append(remove);
            detail.hidden = false;
        };

        columns.forEach((column, index) => {
            const col = el('section', 'wk-col');
            const mine = cards.filter((c) => c.column === column);
            col.append(el('h4', 'wk-col-title', `${column} · ${mine.length}`));
            const list = el('div', 'wk-list');
            col.addEventListener('dragover', (e) => { e.preventDefault(); col.classList.add('over'); });
            col.addEventListener('dragleave', () => col.classList.remove('over'));
            col.addEventListener('drop', (e) => {
                e.preventDefault();
                col.classList.remove('over');
                const title = e.dataTransfer.getData('text/plain');
                const moved = [...board.querySelectorAll('.wk-card')].find((n) => n.dataset.title === title);
                if (!moved || moved.dataset.column === column) return;
                moved.dataset.column = column;
                list.append(moved);  // shown at once; Alfred's reply redraws the board from his copy
                moveTo(title, column);
            });
            for (const c of mine) {
                const item = el('button', 'wk-card');
                item.type = 'button';
                item.draggable = true;
                item.dataset.title = c.title;
                item.dataset.column = c.column;
                item.append(el('span', 'wk-card-title', c.title));
                if (c.due) item.append(el('span', 'wk-due', c.due));
                if (c.notes) item.append(el('span', 'wk-has-notes', '✎'));
                item.title = 'Click for notes; drag to another column. Arrow keys move it too.';
                item.addEventListener('dragstart', (e) => {
                    e.dataTransfer.setData('text/plain', c.title);
                    e.dataTransfer.effectAllowed = 'move';
                    item.classList.add('dragging');
                });
                item.addEventListener('dragend', () => item.classList.remove('dragging'));
                item.addEventListener('click', () => showDetail(c));
                item.addEventListener('keydown', (e) => {
                    const step = e.key === 'ArrowRight' ? 1 : e.key === 'ArrowLeft' ? -1 : 0;
                    const next = columns[index + step];
                    if (step && next) { e.preventDefault(); moveTo(c.title, next); }
                });
                list.append(item);
            }
            col.append(list);
            board.append(col);
        });

        const form = el('form', 'wk-add');
        const input = el('input', 'wk-input');
        input.type = 'text';
        input.maxLength = 80;
        input.placeholder = 'New card…';
        input.setAttribute('aria-label', 'New card title');
        const add = el('button', 'wk-btn', 'Add card');
        add.type = 'submit';
        form.append(input, add);
        form.addEventListener('submit', (e) => {
            e.preventDefault();
            const title = input.value.trim();
            if (!title) return;
            ask(`Add card ${title} to the ${project} board`);
            input.value = '';
        });

        wrap.append(board, detail, form);
        body.append(wrap);
    };

    kinds['work-actions'] = (card, body, { el, ask }) => {
        const items = (card.data || {}).items || [];
        const ul = el('ul', 'wk-actions');
        for (const item of items) {
            const li = el('li', item.done ? 'done' : '');
            const box = el('input');
            box.type = 'checkbox';
            box.checked = !!item.done;
            box.setAttribute('aria-label', `Done: ${item.text}`);
            box.addEventListener('change', () => {
                li.classList.toggle('done', box.checked);
                ask(box.checked ? `Tick off the action item ${item.text}` : `Mark the action item ${item.text} as not done`);
            });
            const text = el('div', 'wk-action-text');
            text.append(el('span', '', item.text), el('span', 'wk-muted', item.meeting || ''));
            const todo = el('button', 'wk-btn wk-small', 'To-do');
            todo.type = 'button';
            todo.title = 'Copy to my to-do list';
            todo.addEventListener('click', () => ask(`add ${item.text} to my to-do list`));
            li.append(box, text, todo);
            ul.append(li);
        }
        if (!items.length) ul.append(el('li', 'wk-muted', 'No action items yet.'));
        body.append(ul);
    };

    kinds['work-summary'] = (card, body, { el }) => {
        const data = card.data || {};
        const stats = el('div', 'wk-stats');
        for (const s of data.stats || []) {
            const box = el('div', 'wk-stat');
            box.append(el('div', 'wk-stat-value', s.value), el('div', 'wk-stat-label', s.label));
            stats.append(box);
        }
        body.append(stats);
        for (const section of data.sections || []) {
            body.append(el('h4', 'wk-heading', section.heading));
            const ul = el('ul', 'wk-section');
            (section.items || []).forEach((i) => ul.append(el('li', '', i)));
            body.append(ul);
        }
    };
})();
