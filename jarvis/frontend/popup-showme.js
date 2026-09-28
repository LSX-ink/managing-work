// "Show me" windows (showme.py): several lists, tables, charts, progress bars, live timers or a flashcard in one
// pop-up. card.data.sections holds plain JSON; everything is drawn with textContent.
(() => {
    window.jarvisPopupKinds = window.jarvisPopupKinds || {};

    function list(section, { el, ask }) {
        const ul = el('ul', 'pop-list sm-list');
        for (const item of section.items || []) {
            const li = el('li', item.done ? 'done' : '');
            const text = el('div', 'sm-text');
            text.append(el('span', 'pop-item', item.label || ''));
            if (item.note) text.append(el('span', 'sm-note', item.note));
            li.append(text);
            if (item.say && item.action) {
                const btn = el('button', 'pop-action sm-small', item.action);
                btn.addEventListener('click', () => { btn.disabled = true; li.classList.add('done'); ask(item.say); });
                li.append(btn);
            }
            ul.append(li);
        }
        if (!ul.children.length) ul.append(el('li', 'pop-empty', 'Nothing here.'));
        return ul;
    }

    function bars(section, { el }) {
        const wrap = el('div', 'sm-bars');
        for (const item of section.items || []) {
            const row = el('div', 'sm-bar-row');
            row.append(el('div', 'sm-bar-label', item.label || ''));
            if (typeof item.pct === 'number') {
                const track = el('div', 'sm-track');
                const fill = el('div', 'sm-fill');
                fill.style.width = `${Math.max(0, Math.min(100, item.pct))}%`;
                track.append(fill);
                row.append(track);
            }
            if (item.note) row.append(el('div', 'sm-note', item.note));
            wrap.append(row);
        }
        return wrap;
    }

    function timer(section, { el, ask }) {
        const row = el('div', 'sm-timer-row');
        const face = el('div', 'pop-timer sm-timer');
        row.append(el('div', 'sm-bar-label', section.label || 'timer'), face);
        if (section.say) {
            const btn = el('button', 'pop-action sm-small', 'Cancel');
            btn.addEventListener('click', () => { btn.disabled = true; ask(section.say); });
            row.append(btn);
        }
        const tick = () => {
            if (!face.isConnected && row.dataset.started) return;
            row.dataset.started = '1';
            const ms = (section.ends_at || 0) - Date.now(), s = Math.floor(Math.abs(ms) / 1000);
            const h = Math.floor(s / 3600), m = Math.floor(s / 60) % 60;
            face.textContent = `${ms < 0 ? 'Done ' : ''}${h ? `${h}:` : ''}${String(m).padStart(2, '0')}:${String(s % 60).padStart(2, '0')}`;
            face.classList.toggle('over', ms < 0);
            setTimeout(tick, 250);
        };
        tick();
        return row;
    }

    function flashcard(section, { el }) {
        const box = el('div', 'sm-flash');
        const back = el('div', 'sm-back', section.back || '');
        back.hidden = true;
        const reveal = el('button', 'pop-action', 'Reveal');
        reveal.addEventListener('click', () => { back.hidden = false; reveal.remove(); });
        box.append(el('div', 'sm-front', section.front || ''), back, reveal);
        return box;
    }

    window.jarvisPopupKinds.showme = (card, body, helpers) => {
        const { el, table, chart } = helpers;
        for (const section of (card.data && card.data.sections) || []) {
            const part = el('div', 'sm-section');
            if (section.title) part.append(el('h4', 'sm-heading', section.title));
            if (section.type === 'list') part.append(list(section, helpers));
            else if (section.type === 'table') part.append(table(section.columns || [], section.rows || []));
            else if (section.type === 'chart') part.append(chart(section.chart || {}));
            else if (section.type === 'bars') part.append(bars(section, helpers));
            else if (section.type === 'timer') part.append(timer(section, helpers));
            else if (section.type === 'flashcard') part.append(flashcard(section, helpers));
            else if (section.type === 'text') part.append(el('div', 'pop-text', section.text || ''));
            body.append(part);
        }
    };
})();
