// Tech helper pop-up kinds (techhelp_store.py, techhelp_secure.py).
//   techhelp-steps: a guide or checklist with a progress bar, tick boxes and the current step opened out.
//   techhelp-meter: a password strength meter with the tips. The password itself is never sent to the page.
(() => {
    const kinds = window.jarvisPopupKinds = window.jarvisPopupKinds || {};

    kinds['techhelp-steps'] = (card, body, { el, ask }) => {
        const { steps = [], current = null, done = 0, total = 0 } = card.data || {};
        const bar = el('div', 'th-bar');
        const fill = el('div', 'th-fill');
        fill.style.width = total ? `${Math.round((done / total) * 100)}%` : '0%';
        bar.append(fill);
        body.append(bar, el('div', 'th-count', `${done} of ${total} steps done`));
        const ul = el('ul', 'pop-list th-steps');
        for (const step of steps) {
            const isCurrent = step.n - 1 === current;
            const li = el('li', `${step.done ? 'done' : ''} ${isCurrent ? 'th-current' : ''}`.trim());
            const box = el('input');
            box.type = 'checkbox';
            box.checked = step.done;
            box.setAttribute('aria-label', `Step ${step.n}: ${step.title}`);
            box.addEventListener('change', () => { li.classList.toggle('done', box.checked); ask(step.say); });
            const text = el('div', 'th-text');
            text.append(el('span', 'pop-item', `${step.n}. ${step.title}`));
            if (isCurrent) text.append(el('div', 'th-detail', step.detail));
            li.append(box, text);
            ul.append(li);
        }
        body.append(ul);
        if (current === null && total) body.append(el('div', 'th-finished', 'All done.'));
    };

    kinds['techhelp-meter'] = (card, body, { el }) => {
        const { pct = 0, label = '', bits = 0, crack = '', tips = [], length = 0 } = card.data || {};
        const bar = el('div', 'th-bar th-meter');
        const fill = el('div', `th-fill th-${label.replace(/\s+/g, '-')}`);
        fill.style.width = `${Math.max(4, Math.min(100, pct))}%`;
        bar.append(fill);
        body.append(bar, el('div', 'th-label', `${label} · about ${bits} bits`));
        body.append(el('div', 'th-count', `${length} characters. A fast attacker could crack it in ${crack}.`));
        const ul = el('ul', 'th-tips');
        for (const tip of tips) ul.append(el('li', '', tip));
        body.append(ul);
        body.append(el('div', 'th-count', 'Checked on this PC only. Nothing was saved.'));
    };
})();
