// Discover pop-ups (discover_*.py): the periodic table grid, quiz cards with answer buttons, and Morse or braille
// with a Play button that beeps the Morse through WebAudio. All data is drawn with textContent.
(() => {
    const kinds = window.jarvisPopupKinds = window.jarvisPopupKinds || {};

    // Grid position of an element: groups 1-18 across; lanthanides and actinides in two rows underneath.
    function spot(number, group, period) {
        if (group) return [group, period];
        return [number - (number < 89 ? 57 : 89) + 3, period + 3];
    }

    kinds['discover-periodic'] = (card, body, { el, ask }) => {
        const data = card.data || {};
        const grid = el('div', 'disc-table');
        for (const [number, symbol, name, group, period, category] of data.elements || []) {
            const [col, row] = spot(number, group, period);
            const cell = el('button', `disc-el cat-${String(category).replace(/[^a-z]+/g, '-')}`);
            cell.style.gridColumn = String(col);
            cell.style.gridRow = String(row);
            cell.title = `${number} ${name} (${category})`;
            cell.append(el('span', 'disc-num', String(number)), el('span', 'disc-sym', symbol));
            if (number === data.highlight) cell.classList.add('on');
            cell.addEventListener('click', () => ask(`Tell me about the element ${name}.`));
            grid.append(cell);
        }
        body.append(grid, el('div', 'disc-hint', 'Click an element to hear about it.'));
    };

    kinds['discover-quiz'] = (card, body, { el, ask }) => {
        const data = card.data || {};
        if (data.feedback) body.append(el('div', 'disc-feedback', data.feedback));
        body.append(el('div', 'disc-question', data.question || ''));
        const box = el('div', `disc-choices${data.big ? ' big' : ''}`);
        const picked = [];
        (data.choices || []).forEach((choice, i) => {
            const btn = el('button', 'disc-choice', choice.label);
            btn.addEventListener('click', () => {
                if (!data.order) {
                    box.querySelectorAll('button').forEach((b) => { b.disabled = true; });
                    btn.classList.add('on');
                    ask(choice.say);
                    return;
                }
                if (btn.disabled) return;
                picked.push('ABCD'[i]);
                btn.disabled = true;
                btn.prepend(el('b', 'disc-rank', `${picked.length}`));
                if (picked.length === data.choices.length) ask(`Timeline answer: ${picked.join(', ')}`);
            });
            box.append(btn);
        });
        body.append(box);
        if (data.input) {
            const form = el('form', 'disc-input');
            const input = el('input');
            input.placeholder = 'Type the spelling';
            input.autocomplete = 'off';
            input.spellcheck = false;
            form.append(input, el('button', 'pop-action', 'Check'));
            form.addEventListener('submit', (e) => {
                e.preventDefault();
                if (input.value.trim()) ask(`Quiz answer: my spelling is ${input.value.trim()}`);
                input.value = '';
            });
            body.append(form);
        }
        if (data.score) body.append(el('div', 'disc-hint', `Score: ${data.score}`));
    };

    // Morse timing: a dot is one unit, a dash three, gaps of one, three (letters) and seven (words).
    function playMorse(code, wpm, button) {
        const Audio = window.AudioContext || window.webkitAudioContext;
        if (!Audio) return;
        const ctx = new Audio();
        const unit = 1.2 / (wpm || 15);
        const osc = ctx.createOscillator(), gain = ctx.createGain();
        osc.frequency.value = 650;
        gain.gain.value = 0;
        osc.connect(gain).connect(ctx.destination);
        let t = ctx.currentTime + 0.1;
        for (const ch of code) {
            if (ch === '.' || ch === '-') {
                const len = ch === '.' ? unit : unit * 3;
                gain.gain.setValueAtTime(0.25, t);
                gain.gain.setValueAtTime(0, t + len);
                t += len + unit;
            } else if (ch === ' ') t += unit * 2;
            else if (ch === '/') t += unit * 2;
        }
        osc.start();
        osc.stop(t + 0.1);
        button.disabled = true;
        osc.onended = () => { button.disabled = false; ctx.close(); };
    }

    kinds['discover-code'] = (card, body, { el }) => {
        const data = card.data || {};
        body.append(el('div', 'disc-plain', data.text || ''));
        body.append(el('div', `disc-code ${data.mode === 'braille' ? 'braille' : 'morse'}`, data.code || ''));
        if (data.mode === 'morse') {
            const play = el('button', 'pop-action', 'Play');
            play.addEventListener('click', () => playMorse(data.code || '', data.wpm, play));
            body.append(play);
        }
    };
})();
