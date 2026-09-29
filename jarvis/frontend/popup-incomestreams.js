// Income streams pop-up kinds (incomestreams_*.py): the stacked month-by-month dashboard and progress bars.
// Text only, never innerHTML; clicking a bar with a say line asks Alfred.
(() => {
    const kinds = (window.jarvisPopupKinds = window.jarvisPopupKinds || {});
    const pounds = (n) => '£' + Math.round(n).toLocaleString('en-GB');
    const shade = (i, n) => (n <= 1 ? 1 : 1 - (i / (n - 1)) * 0.7);

    kinds['incomestreams-dashboard'] = (card, body, { el }) => {
        const { months = [], streams = [], totals = [], summary = [], note = '' } = card.data || {};
        const top = Math.max(1, ...totals);
        const chart = el('div', 'is-stack');
        months.forEach((label, m) => {
            const col = el('div', 'is-col');
            const bar = el('div', 'is-bar');
            bar.style.height = `${(totals[m] / top) * 100}%`;
            streams.forEach((s, i) => {
                const v = s.values[m] || 0;
                if (!v) return;
                const seg = el('div', `is-seg is-${s.type}`);
                seg.style.flexGrow = String(v);
                seg.style.opacity = String(shade(i, streams.length));
                seg.title = `${s.name}: ${pounds(v)}`;
                bar.append(seg);
            });
            col.append(el('div', 'is-total', pounds(totals[m])), bar, el('div', 'is-month', label));
            chart.append(col);
        });
        const legend = el('div', 'is-legend');
        streams.forEach((s, i) => {
            const item = el('span', 'is-key');
            const dot = el('i', `is-dot is-${s.type}`);
            dot.style.opacity = String(shade(i, streams.length));
            item.append(dot, `${s.name} (${s.type})`);
            legend.append(item);
        });
        const lines = el('div', 'is-lines');
        for (const line of summary) lines.append(el('div', 'is-line', line));
        body.append(chart, legend, lines, el('div', 'is-note', note));
    };

    kinds['incomestreams-bars'] = (card, body, { el, ask }) => {
        const { rows = [], note = '' } = card.data || {};
        const wrap = el('div', 'is-bars');
        for (const r of rows) {
            const row = el(r.say ? 'button' : 'div', 'is-row');
            if (r.say) {
                row.type = 'button';
                row.addEventListener('click', () => ask(r.say));
            }
            const track = el('div', 'is-track');
            const fill = el('div', r.warn ? 'is-fill is-warn' : 'is-fill');
            fill.style.width = `${r.max ? Math.min(100, (r.value / r.max) * 100) : 0}%`;
            track.append(fill);
            row.append(el('div', 'is-label', r.label), track, el('div', 'is-text', r.text || ''));
            wrap.append(row);
        }
        body.append(wrap, el('div', 'is-note', note));
    };
})();
