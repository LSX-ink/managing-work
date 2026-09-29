// Language-studio pop-up kinds (languages_study.py, languages_practice.py, languages_progress.py): flip flashcards
// with self-grading, quizzes (choice and typing, with a clock face for time-telling), verb tables, role-play
// dialogues, a "hear it" list and a progress dashboard. Words are spoken with the browser's speechSynthesis in the
// language's voice. Finished flashcards and quizzes send one line to Alfred so the scores and due dates are saved.
(() => {
    const kinds = (window.jarvisPopupKinds = window.jarvisPopupKinds || {});
    const NS = 'http://www.w3.org/2000/svg';

    const speak = (text, lang, rate = 1) => {
        const synth = window.speechSynthesis;
        if (!synth || !text) return false;
        synth.cancel();
        const u = new SpeechSynthesisUtterance(String(text));
        u.lang = lang || 'en-GB';
        u.rate = rate;
        const prefix = u.lang.slice(0, 2).toLowerCase();
        const voice = synth.getVoices().find((v) => v.lang && v.lang.toLowerCase().startsWith(prefix));
        if (voice) u.voice = voice;
        synth.speak(u);
        return true;
    };
    const norm = (s) => String(s).toLowerCase().replace('ß', 'ss').normalize('NFD').replace(/[̀-ͯ]/g, '')
        .replace(/[^\p{L}\p{N}\s]/gu, '').replace(/\s+/g, ' ').trim();
    // Plain accent-free spelling only for comparing answers; the real word is always shown with its accents.

    const rowOf = (el, ...kids) => {
        const r = el('div', 'lg-row');
        r.append(...kids);
        return r;
    };

    function tools(el, root) {
        const button = (label, fn, cls = '') => {
            const b = el('button', `lg-btn ${cls}`.trim(), label);
            b.type = 'button';
            b.addEventListener('click', fn);
            return b;
        };
        const speaker = (getText, speech, rate) => button('Speak', (e) => {
            if (!speak(getText(), speech, rate ? rate() : 1)) e.target.textContent = 'No voice here';
        }, 'lg-speak');
        return { button, speaker };
    }

    // ---- flashcards -----------------------------------------------------------------------------------
    kinds['languages-cards'] = (card, body, { el, ask }) => {
        const d = card.data || {};
        const root = el('div', 'lg');
        root.tabIndex = 0;
        body.append(root);
        const { button, speaker } = tools(el, root);
        let queue, pos, flipped, results;
        const start = () => { queue = (d.cards || []).slice(); pos = 0; flipped = false; results = {}; draw(); };

        function grade(how) {
            const c = queue[pos];
            if (!(c.id in results)) results[c.id] = how;
            if (how === 'again' && !c.again) queue.push({ ...c, again: true });
            pos += 1;
            flipped = false;
            draw();
        }
        function draw() {
            root.replaceChildren();
            if (!queue.length) { root.append(el('div', 'lg-muted', 'No cards to show.')); return; }
            if (pos >= queue.length) return finish();
            const c = queue[pos];
            root.append(el('div', 'lg-muted', `Card ${pos + 1} of ${queue.length}`));
            const face = el('div', `lg-card ${flipped ? 'back' : ''}`);
            face.tabIndex = 0;
            face.setAttribute('role', 'button');
            face.setAttribute('aria-label', 'Flip the card');
            face.append(el('div', 'lg-word', flipped ? c.back : c.front));
            if (c.note && (flipped || !c.reverse)) face.append(el('div', 'lg-muted', c.note));
            face.addEventListener('click', () => { flipped = !flipped; draw(); });
            root.append(face);
            const row = el('div', 'lg-row');
            row.append(speaker(() => c.say, d.speech, () => 1));
            row.append(speaker(() => c.say, d.speech, () => 0.6));
            row.lastChild.textContent = 'Slow';
            if (!flipped) row.append(button('Flip', () => { flipped = true; draw(); }, 'lg-primary'));
            else if (d.track) {
                [['again', 'Again'], ['hard', 'Hard'], ['good', 'Good'], ['easy', 'Easy']]
                    .forEach(([k, label], i) => row.append(button(`${i + 1} ${label}`, () => grade(k), k === 'good' ? 'lg-primary' : '')));
            } else row.append(button('Flip back', () => { flipped = false; draw(); }));
            root.append(row);
            root.focus({ preventScroll: true });
        }
        function finish() {
            const grades = Object.entries(results);
            const count = (k) => grades.filter(([, g]) => g === k).length;
            root.append(el('div', 'lg-big', d.track ? 'Round finished' : 'That is it for today'));
            if (d.track) {
                root.append(el('div', 'lg-muted', `Again ${count('again')}, hard ${count('hard')}, good ${count('good')}, easy ${count('easy')}.`));
                const save = button('Save my review', () => {
                    save.disabled = true;
                    save.textContent = 'Sent to Alfred';
                    ask(`Save my ${d.name} flashcard review: ${grades.map(([k, g]) => `${k}=${g}`).join('; ')}`);
                }, 'lg-primary');
                root.append(rowOf(el, save, button('Go again', start)));
            } else root.append(rowOf(el, button('See it again', start)));
        }
        root.addEventListener('keydown', (e) => {
            if (pos >= queue.length || e.target !== root && e.target.tagName === 'BUTTON') return;
            if (e.key === ' ' || e.key === 'Enter') { e.preventDefault(); flipped = !flipped; draw(); }
            else if (flipped && d.track && '1234'.includes(e.key) && e.key) grade(['again', 'hard', 'good', 'easy'][+e.key - 1]);
        });
        start();
    };

    // ---- hear it --------------------------------------------------------------------------------------
    kinds['languages-say'] = (card, body, { el }) => {
        const d = card.data || {};
        const root = el('div', 'lg');
        body.append(root);
        const { button, speaker } = tools(el, root);
        let slow = false;
        const top = el('div', 'lg-row');
        const speed = button('Normal speed', () => { slow = !slow; speed.textContent = slow ? 'Slow speed' : 'Normal speed'; speed.setAttribute('aria-pressed', String(slow)); });
        speed.setAttribute('aria-pressed', 'false');
        top.append(speed, button('Speak all', () => {
            const items = (d.items || []).map((i) => i.text);
            const synth = window.speechSynthesis;
            if (!synth) return;
            synth.cancel();
            items.forEach((t) => { const u = new SpeechSynthesisUtterance(t); u.lang = d.speech; u.rate = slow ? 0.6 : 1; synth.speak(u); });
        }));
        root.append(top);
        (d.items || []).forEach((i) => {
            const row = el('div', 'lg-line');
            const words = el('div', 'lg-grow');
            words.append(el('div', 'lg-text', i.text));
            if (i.note) words.append(el('div', 'lg-muted', i.note));
            row.append(words, speaker(() => i.text, d.speech, () => (slow ? 0.6 : 1)));
            root.append(row);
        });
    };

    // ---- quiz -----------------------------------------------------------------------------------------
    function clockFace(h, m) {
        const svg = document.createElementNS(NS, 'svg');
        svg.setAttribute('viewBox', '0 0 100 100');
        svg.setAttribute('class', 'lg-clock');
        svg.setAttribute('role', 'img');
        svg.setAttribute('aria-label', `Clock showing ${h}:${String(m).padStart(2, '0')}`);
        const add = (tag, attrs) => {
            const n = document.createElementNS(NS, tag);
            for (const [k, v] of Object.entries(attrs)) n.setAttribute(k, v);
            svg.append(n);
        };
        add('circle', { cx: 50, cy: 50, r: 46, class: 'face' });
        for (let i = 0; i < 12; i++) {
            const a = (i * Math.PI) / 6;
            add('line', { x1: 50 + 38 * Math.sin(a), y1: 50 - 38 * Math.cos(a), x2: 50 + 43 * Math.sin(a), y2: 50 - 43 * Math.cos(a), class: 'tick' });
        }
        const hand = (angle, len, cls) => add('line', { x1: 50, y1: 50, x2: 50 + len * Math.sin(angle), y2: 50 - len * Math.cos(angle), class: cls });
        hand(((h % 12) + m / 60) * (Math.PI / 6), 24, 'hour');
        hand(m * (Math.PI / 30), 36, 'minute');
        add('circle', { cx: 50, cy: 50, r: 2.5, class: 'hub' });
        return svg;
    }

    kinds['languages-quiz'] = (card, body, { el, ask }) => {
        const d = card.data || {};
        const root = el('div', 'lg');
        body.append(root);
        const { button, speaker } = tools(el, root);
        const qs = d.questions || [];
        let i, score, missed;
        const start = () => { i = 0; score = 0; missed = []; draw(); };

        function answer(q, given, box) {
            const options = [q.answer, ...(q.accept || [])].map(norm);
            const right = options.includes(norm(given));
            const exact = [q.answer, ...(q.accept || [])].includes(String(given).trim());
            if (right) score += 1; else missed.push(q);
            box.replaceChildren();
            box.append(el('div', right ? 'lg-ok' : 'lg-bad', right ? (exact || q.kind === 'choice' ? 'Correct!' : `Correct, but mind the accents: ${q.answer}`) : `Not quite. The answer is ${q.answer}`));
            if (q.explain) box.append(el('div', 'lg-muted', q.explain));
            const row = el('div', 'lg-row');
            if (q.say) row.append(speaker(() => q.say, d.speech));
            row.append(button(i + 1 >= qs.length ? 'Finish' : 'Next', () => { i += 1; draw(); }, 'lg-primary'));
            box.append(row);
            box.querySelector('.lg-primary').focus();
        }
        function draw() {
            root.replaceChildren();
            if (i >= qs.length) return finish();
            const q = qs[i];
            root.append(el('div', 'lg-muted', `Question ${i + 1} of ${qs.length}  ·  score ${score}`));
            if (q.clock) root.append(clockFace(q.clock.h, q.clock.m));
            root.append(el('div', 'lg-big', q.prompt));
            if (q.hint) root.append(el('div', 'lg-muted', q.hint));
            const feedback = el('div', 'lg-feedback');
            feedback.setAttribute('aria-live', 'polite');
            if (q.kind === 'type') {
                const input = el('input', 'lg-input');
                input.type = 'text';
                input.autocomplete = 'off';
                input.setAttribute('aria-label', 'Your answer');
                const check = button('Check', () => {
                    if (!input.value.trim()) return;
                    input.disabled = check.disabled = true;
                    answer(q, input.value, feedback);
                }, 'lg-primary');
                input.addEventListener('keydown', (e) => { e.stopPropagation(); if (e.key === 'Enter') check.click(); });
                root.append(rowOf(el, input, check));
                input.focus();
            } else {
                const grid = el('div', 'lg-options');
                (q.options || []).forEach((o) => {
                    const b = button(o, () => {
                        grid.querySelectorAll('button').forEach((x) => { x.disabled = true; if (x.textContent === q.answer) x.classList.add('right'); });
                        if (o !== q.answer) b.classList.add('wrong');
                        answer(q, o, feedback);
                    });
                    grid.append(b);
                });
                root.append(grid);
            }
            root.append(feedback);
        }
        function finish() {
            const pct = qs.length ? Math.round((100 * score) / qs.length) : 0;
            root.append(el('div', 'lg-big', `${score} out of ${qs.length}  (${pct}%)`));
            if (missed.length) {
                const list = el('ul', 'lg-missed');
                missed.forEach((q) => list.append(el('li', '', `${q.prompt}: ${q.answer}`)));
                root.append(el('div', 'lg-muted', 'To review:'), list);
            }
            const save = button('Save my score', () => {
                save.disabled = true;
                save.textContent = 'Sent to Alfred';
                const keys = missed.map((q) => q.key).filter(Boolean).join('; ');
                ask(`Save my ${d.name} quiz result: ${d.label}, ${score} of ${qs.length}.${keys ? ` Missed: ${keys}` : ''}`);
            }, 'lg-primary');
            root.append(rowOf(el, save, button('Go again', start)));
        }
        start();
    };

    // ---- verb table -----------------------------------------------------------------------------------
    kinds['languages-conjugate'] = (card, body, { el }) => {
        const d = card.data || {};
        const root = el('div', 'lg');
        body.append(root);
        const { button, speaker } = tools(el, root);
        const tenses = d.tenses || [];
        let current = 0;
        const rowText = (row) => {
            if (d.lang === 'ja') return row[1].replace(/\s*\(.*\)$/, '');
            return row[0].endsWith("'") ? row[0] + row[1] : `${row[0]} ${row[1]}`;
        };
        function draw() {
            root.replaceChildren();
            root.append(el('div', 'lg-big', `${d.verb}: ${d.meaning}`));
            const tabs = el('div', 'lg-row');
            tenses.forEach((t, n) => {
                const b = button(t.name, () => { current = n; draw(); });
                b.setAttribute('aria-pressed', String(n === current));
                tabs.append(b);
            });
            if (tenses.length > 1) root.append(tabs);
            const t = tenses[current] || { rows: [] };
            const table = el('div', 'lg-verbs');
            t.rows.forEach((r) => {
                const row = el('div', 'lg-line');
                row.append(el('div', 'lg-pron', r[0]), el('div', 'lg-grow lg-text', r[1]), speaker(() => rowText(r), d.speech));
                table.append(row);
            });
            root.append(table);
            root.append(button('Speak all', () => {
                const synth = window.speechSynthesis;
                if (!synth) return;
                synth.cancel();
                t.rows.forEach((r) => { const u = new SpeechSynthesisUtterance(rowText(r)); u.lang = d.speech; synth.speak(u); });
            }));
            if (d.note) root.append(el('div', 'lg-muted', d.note));
        }
        draw();
    };

    // ---- role-play ------------------------------------------------------------------------------------
    kinds['languages-dialogue'] = (card, body, { el, ask }) => {
        const d = card.data || {};
        const root = el('div', 'lg');
        body.append(root);
        const { button, speaker } = tools(el, root);
        const turns = d.turns || [];
        const total = turns.filter((t) => t.who === 'you').length;
        let pos, right, slips, showEnglish;
        const start = () => { pos = 0; right = 0; slips = false; showEnglish = false; draw(); };

        function bubble(text, en, roman, mine) {
            const b = el('div', `lg-bubble ${mine ? 'mine' : ''}`);
            b.append(el('div', 'lg-text', text));
            if (roman) b.append(el('div', 'lg-muted', roman));
            if (en && showEnglish) b.append(el('div', 'lg-muted', en));
            if (!mine) b.append(speaker(() => text, d.speech));
            return b;
        }
        function draw() {
            root.replaceChildren();
            const toggle = button(showEnglish ? 'Hide English' : 'Show English', () => { showEnglish = !showEnglish; draw(); });
            root.append(toggle);
            const log = el('div', 'lg-chat');
            turns.slice(0, pos).forEach((t) => {
                if (t.who === 'them') log.append(bubble(t.text, t.en, t.roman, false));
                else { const o = t.options[t.picked ?? t.correct]; log.append(bubble(o.text, o.en, o.roman, true)); }
            });
            root.append(log);
            if (pos >= turns.length) {
                root.append(el('div', 'lg-big', `Well done: ${right} of ${total} first time`));
                const save = button('Save my result', () => {
                    save.disabled = true;
                    save.textContent = 'Sent to Alfred';
                    ask(`Save my ${d.name} role-play result: ${d.scene}, ${right} of ${total}.`);
                }, 'lg-primary');
                root.append(rowOf(el, save, button('Play again', () => { turns.forEach((t) => delete t.picked); start(); })));
                return;
            }
            const t = turns[pos];
            if (t.who === 'them') {
                log.append(bubble(t.text, t.en, t.roman, false));
                root.append(button('Continue', () => { pos += 1; slips = false; draw(); }, 'lg-primary'));
                return;
            }
            root.append(el('div', 'lg-muted', 'Your reply:'));
            const grid = el('div', 'lg-options');
            t.options.forEach((o, n) => {
                const b = button(o.text, () => {
                    if (n === t.correct) {
                        if (!slips) right += 1;
                        pos += 1;
                        slips = false;
                        draw();
                    } else { slips = true; b.disabled = true; b.classList.add('wrong'); }
                });
                if (showEnglish) b.append(el('span', 'lg-sub', ` ${o.en}`));
                grid.append(b);
            });
            root.append(grid);
        }
        start();
    };

    // ---- dashboard ------------------------------------------------------------------------------------
    kinds['languages-dash'] = (card, body, { el, chart }) => {
        const d = card.data || {};
        const root = el('div', 'lg');
        body.append(root);
        const tiles = el('div', 'lg-tiles');
        const tile = (value, label) => {
            const t = el('div', 'lg-tile');
            t.append(el('div', 'lg-big', String(value)), el('div', 'lg-muted', label));
            tiles.append(t);
        };
        tile(`${d.streak} day${d.streak === 1 ? '' : 's'}`, `streak (best ${d.best})`);
        tile(d.learned, 'words learned');
        tile(d.due, 'cards due');
        tile(d.average === null || d.average === undefined ? '-' : `${d.average}%`, 'recent quiz average');
        root.append(tiles);
        const goal = Math.max(1, d.goal || 10);
        const bar = el('div', 'lg-bar');
        bar.setAttribute('role', 'progressbar');
        bar.setAttribute('aria-valuenow', String(Math.round(d.today || 0)));
        bar.setAttribute('aria-valuemax', String(goal));
        bar.append(el('div', 'lg-fill'));
        bar.firstChild.style.width = `${Math.min(100, ((d.today || 0) / goal) * 100)}%`;
        root.append(el('div', 'lg-muted', `Today: ${d.today || 0} of ${goal} minutes`), bar);
        const week = d.week || { labels: [], values: [] };
        if (week.values.some((v) => v > 0)) root.append(chart({ type: 'bar', labels: week.labels, values: week.values, unit: ' min' }));
        root.append(el('div', 'lg-muted', `${d.seen} words started, ${d.own} of your own`));
        (d.decks || []).forEach((k) => {
            const row = el('div', 'lg-deck');
            row.append(el('div', 'lg-pron', k.name));
            const meter = el('div', 'lg-bar small');
            meter.append(el('div', 'lg-fill'));
            meter.firstChild.style.width = `${k.total ? (100 * k.learned) / k.total : 0}%`;
            row.append(meter, el('div', 'lg-muted', `${k.learned}/${k.total}${k.due ? `, ${k.due} due` : ''}`));
            root.append(row);
        });
    };
})();
