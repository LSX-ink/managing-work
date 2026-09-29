// Party host (partyhost_*.py): a big quiz scoreboard, the question screen, a buzzer where the first press wins, word
// cards with a countdown (charades, Pictionary, Taboo, Heads Up, Scattergories, truth or dare, two truths and a lie),
// a Secret Santa reveal that shows one name at a time, team cards, a musical-stop timer and bingo tickets.
// Timers and key listeners stop once their window closes or is redrawn, and keys only work while the window is on top.
(() => {
    const kinds = window.jarvisPopupKinds = window.jarvisPopupKinds || {};
    let audio;

    function beep(freqs = [880], len = 0.18) {
        try {
            audio = audio || new (window.AudioContext || window.webkitAudioContext)();
            if (audio.state === 'suspended') audio.resume();
            freqs.forEach((f, n) => {
                const t = audio.currentTime + n * len, o = audio.createOscillator(), g = audio.createGain();
                o.frequency.value = f;
                g.gain.setValueAtTime(0.0001, t);
                g.gain.exponentialRampToValueAtTime(0.25, t + 0.02);
                g.gain.exponentialRampToValueAtTime(0.0001, t + len);
                o.connect(g).connect(audio.destination);
                o.start(t);
                o.stop(t + len + 0.05);
            });
        } catch (e) { /* no sound is fine */ }
    }

    const btn = (el, label, fn, cls = '') => {
        const b = el('button', `ph-btn ${cls}`.trim(), label);
        b.type = 'button';
        b.addEventListener('click', fn);
        return b;
    };
    const every = (root, ms, fn) => {
        const id = setInterval(() => (root.isConnected ? fn() : clearInterval(id)), ms);
        return id;
    };
    const typing = (e) => e.target instanceof Element && !!e.target.closest('input, textarea, select');
    function onTop(root) {
        const win = root.closest('.popup');
        if (!win || win.classList.contains('shrunk') || !root.offsetParent) return false;
        const z = Number(win.style.zIndex) || 0;
        return [...document.querySelectorAll('.popup')].every((w) => w === win || (Number(w.style.zIndex) || 0) <= z);
    }
    function keys(root, fn) {
        const on = (e) => {
            if (!root.isConnected) { removeEventListener('keydown', on); return; }
            if (e.ctrlKey || e.altKey || e.metaKey || typing(e) || !onTop(root)) return;
            if (fn(e) !== false) e.preventDefault();
        };
        addEventListener('keydown', on);
    }
    const shuffle = (list) => {
        const a = list.slice();
        for (let i = a.length - 1; i > 0; i--) {
            const buf = new Uint32Array(1);
            crypto.getRandomValues(buf);
            const j = buf[0] % (i + 1);
            [a[i], a[j]] = [a[j], a[i]];
        }
        return a;
    };
    const randomBetween = (lo, hi) => {
        const buf = new Uint32Array(1);
        crypto.getRandomValues(buf);
        return lo + (buf[0] / 4294967296) * (hi - lo);
    };
    const clock = (s) => `${Math.floor(s / 60)}:${String(Math.max(0, s) % 60).padStart(2, '0')}`;

    // A countdown that runs on the page; returns {start, stop, left}.
    function countdown(root, face, seconds, onEnd) {
        let end = 0, id = 0;
        const draw = () => {
            const left = Math.max(0, Math.ceil((end - Date.now()) / 1000));
            face.textContent = clock(left);
            face.classList.toggle('low', left <= 10 && end > 0);
            if (left <= 0 && end) { stop(); beep([660, 880, 660, 880], 0.16); onEnd(); }
        };
        const stop = () => { clearInterval(id); end = 0; };
        face.textContent = clock(seconds);
        return {
            start() { stop(); end = Date.now() + seconds * 1000; draw(); id = every(root, 250, draw); },
            stop,
            running: () => end > 0,
        };
    }

    // ---- Scoreboard -----------------------------------------------------------------------
    kinds['partyhost-scoreboard'] = (card, body, { el }) => {
        const d = card.data || {};
        const rows = d.rows || [];
        const best = Math.max(1, ...rows.map((r) => (d.mode === 'round' ? r.rounds[0] : r.total)));
        const wrap = el('div', 'ph-board');
        if (d.mode === 'final' && rows.length) {
            const winners = rows.filter((r) => r.rank === 1).map((r) => r.name).join(' and ');
            wrap.append(el('div', 'ph-banner', `${winners} ${rows.filter((r) => r.rank === 1).length > 1 ? 'tie' : 'win'}!`));
        } else if (d.mode === 'round') {
            wrap.append(el('div', 'ph-sub', `Round ${d.round} of ${d.rounds}${d.category ? `: ${d.category}` : ''}`));
        } else if (d.rounds) {
            wrap.append(el('div', 'ph-sub', `Round ${d.round} of ${d.rounds}`));
        }
        rows.forEach((r) => {
            const value = d.mode === 'round' ? r.rounds[0] : r.total;
            const line = el('div', `ph-team${r.rank === 1 ? ' lead' : ''}`);
            line.append(el('span', 'ph-rank', String(r.rank || '')), el('span', 'ph-name', r.name));
            const bar = el('span', 'ph-bar');
            const fill = el('span', 'ph-fill');
            fill.style.width = `${Math.max(2, Math.round(Math.max(0, value) / best * 100))}%`;
            bar.append(fill);
            line.append(bar, el('span', 'ph-score', String(value)));
            wrap.append(line);
            if (d.mode !== 'round' && r.rounds && r.rounds.length > 1) {
                wrap.append(el('div', 'ph-rounds', r.rounds.map((n, i) => `R${i + 1}: ${n}`).join('   ')));
            }
        });
        body.append(wrap);
    };

    // ---- Question -------------------------------------------------------------------------
    kinds['partyhost-question'] = (card, body, { el }) => {
        const d = card.data || {};
        const wrap = el('div', 'ph-question');
        wrap.append(el('div', 'ph-sub', d.tiebreak ? 'Tiebreaker' : `${d.label} - question ${d.n} of ${d.total}`),
            el('div', 'ph-cat', d.category || ''), el('div', 'ph-q', d.question || ''));
        if (d.answer) wrap.append(el('div', 'ph-answer', d.answer));
        body.append(wrap);
    };

    // ---- Buzzer ---------------------------------------------------------------------------
    kinds['partyhost-buzzer'] = (card, body, { el, ask }) => {
        const teams = (card.data || {}).teams || [];
        const wrap = el('div', 'ph-buzzer');
        const banner = el('div', 'ph-banner', 'Ready...');
        const grid = el('div', 'ph-buzz-grid');
        let winner = null;
        const press = (t) => {
            if (winner) return;
            winner = t;
            banner.textContent = `${t.name} buzzed first!`;
            wrap.classList.add('locked');
            beep([988, 1319], 0.15);
            ask(`${t.name} buzzed first.`);
        };
        const reset = () => { winner = null; banner.textContent = 'Ready...'; wrap.classList.remove('locked'); };
        const buttons = teams.map((t) => {
            const b = el('button', 'ph-buzz');
            b.type = 'button';
            b.append(el('span', 'ph-buzz-name', t.name), el('span', 'ph-buzz-key', `key ${t.key}`));
            b.addEventListener('click', () => press(t));
            grid.append(b);
            return b;
        });
        keys(wrap, (e) => {
            const t = teams.find((x) => x.key === e.key);
            if (t) { press(t); return true; }
            if (e.key === ' ' || e.key === 'Enter' || e.key === 'r') { reset(); return true; }
            return false;
        });
        wrap.append(banner, grid, el('div', 'ph-note', 'Press your team\'s number or click. Space resets.'),
            btn(el, 'Reset', reset));
        body.append(wrap);
    };

    // ---- Word cards -----------------------------------------------------------------------
    function heads(root, el, cards, seconds, ask, area) {
        let i = 0, right = 0, passed = 0, live = false;
        const word = el('div', 'ph-word big', 'Ready?');
        const face = el('div', 'ph-clock');
        const score = el('div', 'ph-sub', '');
        const row = el('div', 'ph-row');
        const timer = countdown(root, face, seconds, () => finish());
        const showCard = () => {
            word.textContent = (cards[i] || {}).word || 'No more cards';
            score.textContent = `${right} right, ${passed} passed`;
        };
        const next = (good) => {
            if (!live) return;
            if (good) right++; else passed++;
            i++;
            if (i >= cards.length) { finish(); return; }
            showCard();
        };
        const finish = () => {
            if (!live) return;
            live = false;
            timer.stop();
            word.textContent = `Time! ${right} right`;
            row.replaceChildren(btn(el, 'Play again', begin, 'go'));
            ask(`Heads Up round finished: ${right} right and ${passed} passed.`);
        };
        const begin = () => { i = 0; right = 0; passed = 0; live = true; showCard(); timer.start(); row.replaceChildren(
            btn(el, 'Got it', () => next(true), 'go'), btn(el, 'Pass', () => next(false))); };
        keys(root, (e) => {
            if (!live) return false;
            if (e.key === 'ArrowRight' || e.key === 'Enter') { next(true); return true; }
            if (e.key === 'ArrowLeft' || e.key === ' ') { next(false); return true; }
            return false;
        });
        row.append(btn(el, 'Start', begin, 'go'));
        area.append(face, word, score, row);
    }

    function hidden(root, el, card, area, seconds, ask, extra) {
        const first = card.cards[0] || {};
        const word = el('div', 'ph-word', 'Hidden');
        const face = el('div', 'ph-clock');
        const list = el('div', 'ph-forbid');
        const row = el('div', 'ph-row');
        let shown = false;
        const draw = () => {
            word.textContent = shown ? first.word : 'Hidden';
            word.classList.toggle('is-hidden', !shown);
            list.replaceChildren(...(shown && first.forbidden ? first.forbidden.map((w) => el('span', 'ph-bad', w)) : []));
            toggle.textContent = shown ? 'Hide word' : 'Show word';
        };
        const toggle = btn(el, 'Show word', () => { shown = !shown; draw(); });
        const timer = seconds ? countdown(root, face, seconds, () => { word.textContent = 'Time is up!'; list.replaceChildren(); }) : null;
        row.append(toggle);
        if (timer) row.append(btn(el, 'Start timer', () => timer.start(), 'go'));
        if (extra) extra(row);
        area.append(el('div', 'ph-sub', first.category || ''), word, list, timer ? face : '', row);
        draw();
    }

    kinds['partyhost-cards'] = (card, body, { el, ask }) => {
        const d = card.data || {};
        const cards = d.cards || [];
        const wrap = el('div', 'ph-cards');
        if (d.mode === 'heads_up') heads(wrap, el, cards, d.seconds, ask, wrap);
        else if (d.mode === 'charades' || d.mode === 'pictionary' || d.mode === 'taboo') {
            hidden(wrap, el, d, wrap, d.seconds, ask);
        } else if (d.mode === 'prompt') {
            const c = cards[0] || {};
            wrap.append(el('div', 'ph-sub', c.category || ''), el('div', 'ph-word prompt', c.word || ''));
        } else if (d.mode === 'two_truths') {
            wrap.append(el('div', 'ph-sub', 'Which one is the lie? Tap to reveal.'));
            cards.forEach((c) => {
                const b = el('button', 'ph-statement');
                b.type = 'button';
                b.append(el('span', 'ph-rank', c.category), el('span', '', c.word));
                b.addEventListener('click', () => { b.classList.add(c.lie ? 'lie' : 'truth'); b.append(el('span', 'ph-tag', c.lie ? 'LIE' : 'truth')); });
                wrap.append(b);
            });
        } else if (d.mode === 'scattergories') {
            wrap.append(el('div', 'ph-letter', d.letter || ''));
            const face = el('div', 'ph-clock');
            const ul = el('ol', 'ph-cats');
            cards.forEach((c) => ul.append(el('li', '', c.word)));
            const timer = countdown(wrap, face, d.seconds, () => { face.textContent = 'Pens down!'; });
            wrap.append(face, ul, btn(el, 'Start timer', () => timer.start(), 'go'));
        }
        body.append(wrap);
    };

    // ---- Secret Santa ---------------------------------------------------------------------
    kinds['partyhost-santa'] = (card, body, { el, ask }) => {
        const d = card.data || {};
        const wrap = el('div', 'ph-santa');
        const name = el('div', 'ph-word', `${d.giver}, tap to see who you've got`);
        const sub = el('div', 'ph-sub', `${d.step} of ${d.total}${d.budget ? ` - budget ${d.budget}` : ''}`);
        const row = el('div', 'ph-row');
        let revealed = false;
        const show = btn(el, 'Show my name', () => {
            revealed = true;
            name.textContent = d.recipient;
            name.classList.add('revealed');
            row.replaceChildren(done);
        }, 'go');
        const done = btn(el, 'Hide and pass on', () => {
            name.textContent = 'Hidden. Pass the screen on.';
            name.classList.remove('revealed');
            row.replaceChildren();
            ask('Secret Santa: next person.');
        }, 'go');
        row.append(show);
        wrap.append(sub, name, row);
        body.append(wrap);
    };

    // ---- Teams ----------------------------------------------------------------------------
    kinds['partyhost-teams'] = (card, body, { el }) => {
        const wrap = el('div', 'ph-teams');
        ((card.data || {}).teams || []).forEach((t, i) => {
            const box = el('div', `ph-teambox c${i % 10}`);
            box.append(el('div', 'ph-teamname', t.name));
            const ul = el('ul', 'ph-members');
            t.members.forEach((m) => ul.append(el('li', '', t.captain === m ? `${m} (captain)` : m)));
            box.append(ul);
            wrap.append(box);
        });
        body.append(wrap);
    };

    // ---- Musical stop ---------------------------------------------------------------------
    kinds['partyhost-stop'] = (card, body, { el }) => {
        const d = card.data || {};
        const wrap = el('div', 'ph-stop');
        const banner = el('div', 'ph-banner', 'Ready?');
        const row = el('div', 'ph-row');
        let id = 0, round = 0;
        const go = () => {
            clearTimeout(id);
            round++;
            wrap.classList.remove('stopped');
            banner.textContent = `Round ${round}: music playing... keep dancing!`;
            wrap.classList.add('playing');
            const wait = randomBetween(d.min || 8, d.max || 30) * 1000;
            id = setTimeout(() => {
                if (!wrap.isConnected) return;
                wrap.classList.remove('playing');
                wrap.classList.add('stopped');
                banner.textContent = 'STOP!';
                beep([523, 392, 262], 0.25);
            }, wait);
        };
        row.append(btn(el, 'Start', go, 'go'));
        wrap.append(banner, el('div', 'ph-note', `The music stops at a random time between ${d.min} and ${d.max} seconds.`), row);
        body.append(wrap);
    };

    // ---- Bingo tickets --------------------------------------------------------------------
    kinds['partyhost-bingo'] = (card, body, { el }) => {
        const wrap = el('div', 'ph-tickets');
        ((card.data || {}).tickets || []).forEach((ticket) => {
            const grid = el('div', 'ph-ticket');
            ticket.forEach((row) => row.forEach((n) => {
                const cell = el('button', `ph-cell${n === null ? ' blank' : ''}`, n === null ? '' : String(n));
                cell.type = 'button';
                if (n !== null) cell.addEventListener('click', () => cell.classList.toggle('marked'));
                grid.append(cell);
            }));
            wrap.append(grid);
        });
        body.append(wrap);
    };
})();
