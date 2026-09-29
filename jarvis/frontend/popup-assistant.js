// Assistant pop-up kinds (assistant_*.py): "assistant-briefing" is a headline with titled sections of lines, and
// "assistant-timeline" is a day plan drawn on an hour scale. A line with a say line is a button that asks Alfred.
(() => {
    const kinds = (window.jarvisPopupKinds = window.jarvisPopupKinds || {});

    kinds['assistant-briefing'] = (card, body, { el, ask }) => {
        const { headline = '', sections = [] } = card.data || {};
        const wrap = el('div', 'as-brief');
        if (headline) wrap.append(el('div', 'as-headline', headline));
        for (const s of sections) {
            const box = el('section', `as-section${s.tone === 'alert' ? ' alert' : ''}`);
            box.append(el('h4', 'as-title', s.title));
            const ul = el('ul', 'as-lines');
            for (const l of s.lines || []) {
                const text = typeof l === 'string' ? l : l.text;
                const li = el('li');
                if (l && l.say) {
                    const b = el('button', 'as-line', text);
                    b.type = 'button';
                    b.addEventListener('click', () => ask(l.say));
                    li.append(b);
                } else li.append(el('span', 'as-line', text));
                ul.append(li);
            }
            box.append(ul);
            wrap.append(box);
        }
        if (!sections.length) wrap.append(el('div', 'pop-empty', 'Nothing to show.'));
        body.append(wrap);
    };

    kinds['assistant-timeline'] = (card, body, { el }) => {
        const data = card.data || {};
        const blocks = data.blocks || [];
        const mins = (t) => { const [h, m] = t.split(':').map(Number); return h * 60 + m; };
        const from = Math.floor(mins(data.from || '09:00') / 60) * 60;
        const to = Math.ceil(mins(data.to || '17:00') / 60) * 60;
        const PX = 1.1;
        const wrap = el('div', 'as-timeline');
        wrap.style.height = `${(to - from) * PX}px`;
        for (let m = from; m <= to; m += 60) {
            const tick = el('div', 'as-hour', `${String(m / 60).padStart(2, '0')}:00`);
            tick.style.top = `${(m - from) * PX}px`;
            wrap.append(tick);
        }
        for (const b of blocks) {
            const box = el('div', `as-block ${b.kind}`);
            box.style.top = `${(mins(b.start) - from) * PX}px`;
            box.style.height = `${Math.max(18, (mins(b.end) - mins(b.start)) * PX - 2)}px`;
            box.append(el('span', 'as-when', b.start), el('span', 'as-what', b.label));
            box.title = `${b.start} to ${b.end}: ${b.label}`;
            wrap.append(box);
        }
        body.append(wrap);
        if (data.note) body.append(el('div', 'as-note', data.note));
    };
})();
