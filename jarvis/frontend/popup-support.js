// Everyday support pop-up kinds (support_*.py): big date, six huge buttons, big lines of text, people with photos,
// one-step-at-a-time guides and a zoom-and-pan magnifier. All text is set with textContent.
(() => {
    const kinds = (window.jarvisPopupKinds = window.jarvisPopupKinds || {});

    kinds['support-today'] = (card, body, { el, ask }) => {
        const { weekday = '', date = '', time = '', part = '', plan = [] } = card.data || {};
        const wrap = el('div', 'su-today');
        wrap.append(el('div', 'su-weekday', weekday), el('div', 'su-date', date),
            el('div', 'su-part', `${part.toUpperCase()}  ${time}`));
        const list = el('ul', 'su-plan');
        for (const p of plan) list.append(el('li', p.done ? 'done' : '', `${p.done ? '✓ ' : ''}${p.time ? p.time + '  ' : ''}${p.text}`));
        if (plan.length) wrap.append(el('div', 'su-label', "Today's plan"), list);
        else wrap.append(el('div', 'su-label', 'Nothing planned today'));
        body.append(wrap);
    };

    kinds['support-home'] = (card, body, { el, ask }) => {
        const grid = el('div', 'su-home');
        for (const b of (card.data || {}).buttons || []) {
            const btn = el('button', 'su-huge', b.label);
            btn.type = 'button';
            btn.addEventListener('click', () => ask(b.say));
            grid.append(btn);
        }
        body.append(grid);
    };

    kinds['support-big'] = (card, body, { el }) => {
        const wrap = el('div', 'su-big');
        for (const l of (card.data || {}).lines || []) {
            const row = el('div', 'su-row');
            row.append(el('div', 'su-key', l.label), el('div', 'su-value', l.value));
            wrap.append(row);
        }
        body.append(wrap);
    };

    kinds['support-people'] = (card, body, { el, image }) => {
        const wrap = el('div', 'su-people');
        for (const p of (card.data || {}).people || []) {
            const box = el('div', 'su-person');
            if (p.src) { const img = image(p.src, p.name); img.classList.add('su-photo'); box.append(img); }
            const text = el('div', 'su-about');
            text.append(el('div', 'su-name', p.name));
            if (p.relation) text.append(el('div', 'su-relation', p.relation));
            if (p.note) text.append(el('div', 'su-note', p.note));
            box.append(text);
            wrap.append(box);
        }
        body.append(wrap);
    };

    kinds['support-steps'] = (card, body, { el }) => {
        const { steps = [], index = 0 } = card.data || {};
        if (!steps.length) { body.append(el('div', 'pop-empty', 'This guide has no steps.')); return; }
        let i = Math.min(Math.max(index, 0), steps.length - 1);
        const count = el('div', 'su-count');
        const text = el('div', 'su-step');
        text.setAttribute('aria-live', 'polite');
        const nav = el('div', 'su-nav');
        const back = el('button', 'su-huge', 'Back');
        const next = el('button', 'su-huge', 'Next');
        back.type = next.type = 'button';
        const draw = () => {
            count.textContent = `Step ${i + 1} of ${steps.length}`;
            text.textContent = steps[i];
            back.disabled = i === 0;
            next.textContent = i === steps.length - 1 ? 'Done' : 'Next';
        };
        back.addEventListener('click', () => { if (i > 0) { i -= 1; draw(); } });
        next.addEventListener('click', () => { if (i < steps.length - 1) { i += 1; draw(); } else text.textContent = 'All done. Well done!'; });
        nav.append(back, next);
        body.append(count, text, nav);
        draw();
    };

    kinds['support-magnify'] = (card, body, { el }) => {
        const { src = '', name = '' } = card.data || {};
        let scale = 2, x = 0, y = 0;
        const bar = el('div', 'su-zoombar');
        const view = el('div', 'su-view');
        const img = el('img', 'su-zoomed');
        img.src = src;
        img.alt = name;
        img.draggable = false;
        const apply = () => { img.style.transform = `translate(${x}px, ${y}px) scale(${scale})`; };
        const zoom = (f) => { scale = Math.min(12, Math.max(1, scale * f)); if (scale === 1) { x = 0; y = 0; } apply(); };
        for (const [label, f] of [['−', 1 / 1.5], ['+', 1.5]]) {
            const b = el('button', 'su-huge su-small', label);
            b.type = 'button';
            b.setAttribute('aria-label', f > 1 ? 'Zoom in' : 'Zoom out');
            b.addEventListener('click', () => zoom(f));
            bar.append(b);
        }
        const reset = el('button', 'su-huge su-small', 'Reset');
        reset.type = 'button';
        reset.addEventListener('click', () => { scale = 1; x = 0; y = 0; apply(); });
        bar.append(reset);
        view.addEventListener('pointerdown', (e) => {
            const sx = e.clientX - x, sy = e.clientY - y;
            view.setPointerCapture(e.pointerId);
            const move = (m) => { x = m.clientX - sx; y = m.clientY - sy; apply(); };
            const up = () => { view.removeEventListener('pointermove', move); view.removeEventListener('pointerup', up); };
            view.addEventListener('pointermove', move);
            view.addEventListener('pointerup', up);
        });
        view.addEventListener('wheel', (e) => { e.preventDefault(); zoom(e.deltaY < 0 ? 1.2 : 1 / 1.2); }, { passive: false });
        view.append(img);
        body.append(bar, view);
        apply();
    };
})();
