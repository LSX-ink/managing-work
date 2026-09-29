// Repurpose pop-up kinds (repurpose_subs.py, repurpose_tracker.py): a subtitle/beat timeline and the video-by-platform
// tracker grid. Text only, never innerHTML; tapping a grid cell asks Alfred about it.
(() => {
    const kinds = (window.jarvisPopupKinds = window.jarvisPopupKinds || {});
    const MARK = { planned: '~', draft: 'D', scheduled: 'S', posted: '✓' };

    kinds['repurpose-timeline'] = (card, body, { el }) => {
        const { total = 1, cues = [] } = card.data || {};
        const list = el('div', 'rp-timeline');
        for (const c of cues) {
            const row = el('div', 'rp-cue');
            const bar = el('span', 'rp-bar');
            bar.style.marginLeft = `${(c.start / (total || 1)) * 100}%`;
            bar.style.width = `${Math.max(1, ((c.end - c.start) / (total || 1)) * 100)}%`;
            row.append(el('span', 'rp-time', `${c.start}s`), el('span', 'rp-text', c.text), bar);
            list.append(row);
        }
        body.append(list);
        if (card.text) body.append(el('div', 'rp-note', card.text));
    };

    kinds['repurpose-matrix'] = (card, body, { el, ask }) => {
        const { platforms = [], rows = [] } = card.data || {};
        const grid = el('div', 'rp-grid');
        grid.style.gridTemplateColumns = `minmax(90px, 1.6fr) repeat(${platforms.length}, minmax(34px, 1fr))`;
        grid.append(el('div', 'rp-head', ''));
        for (const p of platforms) grid.append(el('div', 'rp-head', p));
        for (const r of rows) {
            grid.append(el('div', 'rp-video', r.video));
            for (const c of r.cells) {
                const b = el('button', `rp-cell rp-${c.status || 'none'}`, MARK[c.status] || '+');
                b.type = 'button';
                b.title = c.status || 'not yet';
                b.addEventListener('click', () => ask(c.say));
                grid.append(b);
            }
        }
        body.append(grid, el('div', 'rp-note', '✓ posted, S scheduled, D draft, ~ planned, + nothing yet. Tap a cell.'));
    };
})();
