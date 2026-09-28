// Sports pop-ups (sports_*.py): football matches with club badges, a score counter that keeps score right here
// (+/- buttons, history, Save sends the final scores to Alfred), and a darts scoreboard with a box for each visit.
// All data is drawn with textContent.
(() => {
    const kinds = window.jarvisPopupKinds = window.jarvisPopupKinds || {};

    // A club badge (https only), or an empty space the same size when there isn't one.
    function badge(el, src, alt) {
        if (!src || !String(src).startsWith('https://')) return el('span', 'sp-badge none');
        const img = el('img', 'sp-badge');
        img.src = src;
        img.alt = alt || '';
        img.loading = 'lazy';
        img.referrerPolicy = 'no-referrer';
        img.addEventListener('error', () => img.replaceWith(el('span', 'sp-badge none')), { once: true });
        return img;
    }

    // ---- Matches: {badge?, sections: [{title, badge?, note?, matches: [...]}]} ------------------------
    kinds['sports-matches'] = (card, body, { el, ask }) => {
        const d = card.data || {};
        if (d.badge) body.append(badge(el, d.badge, card.title));
        for (const s of d.sections || []) {
            const sec = el('section', 'sp-section');
            const head = el('h4', 'sp-head');
            if (s.badge) head.append(badge(el, s.badge, s.title));
            head.append(el('span', '', s.title || ''));
            sec.append(head);
            for (const m of s.matches || []) {
                const row = el(m.say ? 'button' : 'div', 'sp-match');
                if (m.say) row.addEventListener('click', () => ask(m.say));
                const mid = el('span', `sp-score${m.score ? '' : ' later'}`, m.score || m.when || '');
                row.append(
                    el('span', 'sp-team home', m.home || ''), badge(el, m.home_badge, m.home),
                    mid, badge(el, m.away_badge, m.away), el('span', 'sp-team', m.away || ''));
                if (m.outcome) row.append(el('span', `sp-outcome o-${m.outcome}`, m.outcome));
                const meta = el('div', 'sp-meta', [m.score ? m.when : '', m.league].filter(Boolean).join(' · '));
                sec.append(row, meta);
            }
            if (s.note) sec.append(el('div', 'sp-note', s.note));
            body.append(sec);
        }
    };

    // ---- Score counter: {game, start, players: [{name, score}]} -------------------------------------
    kinds['sports-score'] = (card, body, { el, ask }) => {
        const d = card.data || {};
        const players = (d.players || []).map((p) => ({ name: p.name, score: Number(p.score) || 0 }));
        const history = [];
        let step = 1;
        const board = el('div', 'sp-board');
        const log = el('ol', 'sp-history');
        const steps = el('div', 'sp-steps');
        [1, 5, 10].forEach((n) => {
            const b = el('button', `sp-step${n === step ? ' on' : ''}`, `±${n}`);
            b.addEventListener('click', () => {
                step = n;
                steps.querySelectorAll('button').forEach((x) => x.classList.toggle('on', x === b));
            });
            steps.append(b);
        });

        const change = (i, by) => {
            players[i].score += by;
            history.unshift({ i, by });
            draw();
        };
        function draw() {
            const top = Math.max(...players.map((p) => p.score));
            board.replaceChildren(...players.map((p, i) => {
                const row = el('div', `sp-player${p.score === top && history.length ? ' lead' : ''}`);
                const minus = el('button', 'sp-pm', '−');
                const plus = el('button', 'sp-pm', '+');
                minus.title = `Take ${step} from ${p.name}`;
                plus.title = `Add ${step} to ${p.name}`;
                minus.addEventListener('click', () => change(i, -step));
                plus.addEventListener('click', () => change(i, step));
                row.append(el('span', 'sp-name', p.name), minus, el('span', 'sp-points', String(p.score)), plus);
                return row;
            }));
            log.replaceChildren(...history.slice(0, 30).map((h) => el('li', '',
                `${players[h.i].name} ${h.by > 0 ? '+' : '−'}${Math.abs(h.by)}`)));
        }

        const bar = el('div', 'sp-bar');
        const undo = el('button', 'pop-action', 'Undo');
        undo.addEventListener('click', () => {
            const h = history.shift();
            if (h) { players[h.i].score -= h.by; draw(); }
        });
        const reset = el('button', 'pop-action', 'Reset');
        reset.addEventListener('click', () => {
            players.forEach((p) => { p.score = Number(d.start) || 0; });
            history.length = 0;
            draw();
        });
        const save = el('button', 'pop-action', 'Save');
        save.addEventListener('click', () => ask(
            `Save the ${d.game || 'game'} scores: ${players.map((p) => `${p.name} ${p.score}`).join(', ')}.`));
        bar.append(steps, undo, reset, save);
        body.append(board, bar, log);
        draw();
    };

    // ---- Darts: {start, turn, winner, message, players: [{name, remaining, average, last, legs, checkout}]} ----
    kinds['sports-darts'] = (card, body, { el, ask }) => {
        const d = card.data || {};
        const grid = el('div', 'sp-darts');
        (d.players || []).forEach((p, i) => {
            const on = d.winner === null || d.winner === undefined ? i === d.turn : i === d.winner;
            const box = el('div', `sp-dart${on ? ' on' : ''}`);
            box.append(el('div', 'sp-name', `${p.name}${p.legs ? ` (${p.legs} leg${p.legs === 1 ? '' : 's'})` : ''}`),
                el('div', 'sp-left', String(p.remaining)),
                el('div', 'sp-meta', `Avg ${p.average} · ${(p.last || []).join(', ') || 'no throws yet'}`));
            if (p.checkout) box.append(el('div', 'sp-checkout', p.checkout));
            grid.append(box);
        });
        body.append(grid);
        if (d.message) body.append(el('div', 'sp-note', d.message));
        if (d.winner !== null && d.winner !== undefined) return;
        const form = el('form', 'sp-visit');
        const input = el('input');
        input.type = 'number';
        input.min = '0';
        input.max = '180';
        input.placeholder = `${(d.players || [])[d.turn]?.name || 'Visit'} scored…`;
        input.setAttribute('aria-label', 'Score for this visit');
        const go = el('button', 'pop-action', 'Enter');
        form.append(input, go);
        form.addEventListener('submit', (e) => {
            e.preventDefault();
            const n = Number(input.value);
            if (input.value === '' || !Number.isInteger(n) || n < 0 || n > 180) return;
            form.querySelectorAll('input, button').forEach((x) => { x.disabled = true; });
            ask(`Darts visit: ${n}.`);
        });
        body.append(form);
    };
})();
