// Creator-ideas pop-up kinds (creator_ideas.py, creator_hooks.py): the idea board with three columns and a phone frame
// that shows TikTok's safe zones with the user's on-screen text placed inside it. Text only, never innerHTML.
(() => {
    const kinds = window.jarvisPopupKinds = window.jarvisPopupKinds || {};

    kinds['creator-board'] = (card, body, { el, ask }) => {
        const wrap = el('div', 'ci-board');
        for (const col of (card.data || {}).columns || []) {
            const box = el('div', 'ci-col');
            box.append(el('div', 'ci-colname', `${col.name} (${col.items.length})`));
            if (!col.items.length) box.append(el('div', 'ci-empty', 'Nothing here'));
            for (const item of col.items) {
                const b = el('button', 'ci-item');
                b.type = 'button';
                b.title = `Move to ${col.next}`;
                b.append(el('span', 'ci-num', `#${item.id}`), el('span', 'ci-text', item.text));
                if (item.tags && item.tags.length) b.append(el('span', 'ci-tags', item.tags.map((t) => `#${t}`).join(' ')));
                b.addEventListener('click', () => ask(item.say));
                box.append(b);
            }
            wrap.append(box);
        }
        body.append(wrap, el('div', 'ci-hint', 'Tap an idea to move it along.'));
    };

    kinds['creator-safe'] = (card, body, { el }) => {
        const { lines = [], zones = {}, issues = [] } = card.data || {};
        const frame = el('div', 'ci-phone');
        for (const side of ['top', 'bottom', 'left', 'right']) {
            const z = el('div', `ci-zone ci-${side}`, side === 'bottom' ? 'caption and buttons' : '');
            z.style[side === 'top' || side === 'bottom' ? 'height' : 'width'] = `${(zones[side] || 0) * 100}%`;
            frame.append(z);
        }
        const text = el('div', 'ci-lines');
        for (const l of lines) text.append(el('div', 'ci-line', l));
        frame.append(text);
        const list = el('ul', 'ci-issues');
        for (const i of issues) list.append(el('li', '', i));
        body.append(frame, list);
    };
})();
