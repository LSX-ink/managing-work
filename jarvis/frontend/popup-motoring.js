// Motoring pop-ups (motoring_guide.py, motoring_theory.py): dashboard warning lights as a coloured grid you can click
// for the meaning, and theory test question cards with answer buttons. Everything is drawn with textContent.
(() => {
    const kinds = window.jarvisPopupKinds = window.jarvisPopupKinds || {};

    kinds['motoring-lights'] = (card, body, { el }) => {
        const grid = el('div', 'mo-lights');
        for (const light of (card.data || {}).lights || []) {
            const cell = el('button', `mo-light ${String(light.colour).replace(/[^a-z]/g, '')}`);
            cell.type = 'button';
            cell.append(el('span', 'mo-dot'), el('span', 'mo-name', light.name));
            const more = el('div', 'mo-more', `${light.meaning} ${light.action}`);
            more.hidden = true;
            cell.addEventListener('click', () => { more.hidden = !more.hidden; });
            const wrap = el('div', 'mo-item');
            wrap.append(cell, more);
            grid.append(wrap);
        }
        body.append(grid);
    };

    kinds['motoring-quiz'] = (card, body, { el, ask }) => {
        const data = card.data || {};
        if (data.feedback) body.append(el('div', 'mo-feedback', data.feedback));
        body.append(el('div', 'mo-question', data.question || ''));
        const box = el('div', 'mo-choices');
        (data.choices || []).forEach((choice, i) => {
            const btn = el('button', 'mo-choice', `${'ABCD'[i]}: ${choice.label}`);
            btn.type = 'button';
            btn.addEventListener('click', () => {
                box.querySelectorAll('button').forEach((b) => { b.disabled = true; });
                btn.classList.add('on');
                ask(choice.say);
            });
            box.append(btn);
        });
        body.append(box, el('div', 'mo-score', `Score: ${data.score || '0 of 0'}`));
    };
})();
