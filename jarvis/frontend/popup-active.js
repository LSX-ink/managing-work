// Active pop-ups (see active_*.py): a guided workout timer (work and rest phases, big countdown, the next exercise, beeps
// made with Web Audio), stretch routines as step cards with an optional timer per move, and a challenge streak calendar.
// Timers and sounds stop when the window closes. Colours follow popup.css's HUD variables.
(() => {
    const kinds = (window.jarvisPopupKinds = window.jarvisPopupKinds || {});
    const pad2 = (n) => String(n).padStart(2, '0');
    const mmss = (s) => `${Math.floor(Math.max(0, s) / 60)}:${pad2(Math.ceil(Math.max(0, s)) % 60)}`;

    const audio = () => {
        let ctx = null;
        const beep = (freq, seconds, level = 0.12, delay = 0) => {
            if (!ctx) {
                const Ctx = window.AudioContext || window.webkitAudioContext;
                if (!Ctx) return;
                ctx = new Ctx();
            }
            if (ctx.state === 'suspended') ctx.resume();
            const osc = ctx.createOscillator(), gain = ctx.createGain(), t = ctx.currentTime + delay;
            osc.type = 'sine';
            osc.frequency.value = freq;
            gain.gain.setValueAtTime(level, t);
            gain.gain.exponentialRampToValueAtTime(0.0001, t + seconds);
            osc.connect(gain).connect(ctx.destination);
            osc.start(t);
            osc.stop(t + seconds + 0.02);
        };
        const close = () => { if (ctx) { ctx.close().catch(() => {}); ctx = null; } };
        return { beep, close };
    };

    // Call tick every 200 ms until the window is gone, then clean up.
    const every = (body, tick, done) => {
        const id = setInterval(() => {
            if (!body.isConnected) { clearInterval(id); done(); return; }
            tick();
        }, 200);
    };

    kinds['active-timer'] = (card, body, { el }) => {
        const steps = (card.data && card.data.steps) || [];
        if (!steps.length) { body.append(el('div', 'pop-empty', 'Nothing to time.')); return; }
        const sound = audio();
        const total = steps.reduce((a, s) => a + s.seconds, 0);
        let at = 0, remaining = steps[0].seconds, endAt = 0, running = false, finished = false, lastWhole = -1;

        const box = el('div', 'ac-wrap');
        const phase = el('div', 'ac-phase'), clock = el('div', 'ac-clock'), name = el('div', 'ac-name');
        const tip = el('div', 'ac-muted'), next = el('div', 'ac-next'), round = el('div', 'ac-muted');
        const bar = el('div', 'ac-bar'), fill = el('span');
        bar.append(fill);
        const row = el('div', 'ac-row');
        const go = el('button', 'pop-action', 'Start'), skip = el('button', 'pop-action', 'Skip'),
            again = el('button', 'pop-action', 'Restart');
        row.append(go, skip, again);
        box.append(phase, clock, name, tip, next, round, bar, row);
        body.append(box);

        const elapsed = () => steps.slice(0, at).reduce((a, s) => a + s.seconds, 0) + (steps[at].seconds - remaining);
        const cue = (s) => {
            if (s.kind === 'work') sound.beep(1000, 0.5, 0.16);
            else if (s.kind === 'rest') sound.beep(600, 0.3);
            else sound.beep(760, 0.25);
        };
        const draw = () => {
            const s = steps[at];
            box.className = `ac-wrap ${finished ? 'done' : s.kind}`;
            phase.textContent = finished ? 'DONE' : { work: 'WORK', rest: 'REST', prep: 'GET READY' }[s.kind] || '';
            clock.textContent = finished ? '0:00' : mmss(remaining);
            name.textContent = finished ? 'Well done!' : s.label;
            tip.textContent = finished ? '' : (s.tip || '');
            next.textContent = finished ? '' : `Next: ${s.next}`;
            round.textContent = finished ? '' : (s.round ? `Round ${s.round} of ${s.rounds}` : '');
            fill.style.width = `${Math.min(100, (finished ? total : elapsed()) / total * 100)}%`;
            go.textContent = running ? 'Pause' : finished ? 'Again' : 'Start';
        };
        const enter = (i) => {
            at = i;
            remaining = steps[i].seconds;
            lastWhole = -1;
            endAt = performance.now() + remaining * 1000;
            cue(steps[i]);
        };
        const advance = () => {
            if (at + 1 >= steps.length) {
                finished = true; running = false;
                [0, 0.25, 0.5].forEach((d) => sound.beep(1200, 0.2, 0.16, d));
            } else enter(at + 1);
        };
        go.addEventListener('click', () => {
            if (finished) { finished = false; at = 0; }
            if (running) { running = false; remaining = Math.max(0, (endAt - performance.now()) / 1000); }
            else { running = true; endAt = performance.now() + remaining * 1000; if (remaining === steps[at].seconds) cue(steps[at]); }
            draw();
        });
        skip.addEventListener('click', () => { if (!finished) { if (running) advance(); else { at = Math.min(at + 1, steps.length - 1); remaining = steps[at].seconds; } draw(); } });
        again.addEventListener('click', () => { finished = false; running = false; at = 0; remaining = steps[0].seconds; draw(); });
        every(body, () => {
            if (!running) return;
            remaining = (endAt - performance.now()) / 1000;
            const whole = Math.ceil(remaining);
            if (whole !== lastWhole && whole > 0 && whole <= 3) sound.beep(880, 0.12, 0.1);
            lastWhole = whole;
            if (remaining <= 0) advance();
            draw();
        }, sound.close);
        draw();
    };

    kinds['active-steps'] = (card, body, { el }) => {
        const steps = (card.data && card.data.steps) || [];
        if (!steps.length) { body.append(el('div', 'pop-empty', 'No steps.')); return; }
        const sound = audio();
        let at = 0, endAt = 0, timing = false;
        const box = el('div', 'ac-wrap');
        const count = el('div', 'ac-muted'), title = el('div', 'ac-name'), text = el('div', 'ac-step');
        const clock = el('div', 'ac-clock small');
        const bar = el('div', 'ac-bar'), fill = el('span');
        bar.append(fill);
        const row = el('div', 'ac-row');
        const back = el('button', 'pop-action', 'Back'), timer = el('button', 'pop-action'),
            next = el('button', 'pop-action', 'Next');
        row.append(back, timer, next);
        box.append(count, title, text, clock, bar, row);
        body.append(box);
        const draw = () => {
            const s = steps[at];
            count.textContent = `Move ${at + 1} of ${steps.length}`;
            title.textContent = s.title;
            text.textContent = s.text;
            clock.textContent = s.seconds ? mmss(timing ? (endAt - performance.now()) / 1000 : s.seconds) : '';
            timer.textContent = timing ? 'Stop timer' : `Start ${s.seconds} seconds`;
            timer.hidden = !s.seconds;
            back.disabled = at === 0;
            next.textContent = at + 1 >= steps.length ? 'Finish' : 'Next';
            fill.style.width = `${(at + 1) / steps.length * 100}%`;
        };
        const move = (to) => { timing = false; at = Math.min(steps.length - 1, Math.max(0, to)); draw(); };
        back.addEventListener('click', () => move(at - 1));
        next.addEventListener('click', () => {
            if (at + 1 >= steps.length) { timing = false; title.textContent = 'All done. Nice work!'; text.textContent = ''; return; }
            move(at + 1);
        });
        timer.addEventListener('click', () => {
            timing = !timing;
            if (timing) endAt = performance.now() + steps[at].seconds * 1000;
            draw();
        });
        every(body, () => {
            if (!timing) return;
            if (endAt - performance.now() <= 0) {
                timing = false;
                [0, 0.2, 0.4].forEach((d) => sound.beep(1000, 0.15, 0.14, d));
            }
            draw();
        }, sound.close);
        draw();
    };

    kinds['active-calendar'] = (card, body, { el }) => {
        const d = card.data || {};
        const days = d.days || [];
        const head = el('div', 'ac-muted', `${d.done || 0} days done. Streak: ${d.streak || 0}.`);
        const grid = el('div', 'ac-cal');
        const detail = el('div', 'ac-detail', 'Tap a day to see its target.');
        days.forEach((day) => {
            const cell = el('button', `ac-day ${day.state}`);
            cell.append(el('span', 'ac-day-n', String(day.n)), el('span', 'ac-day-t', day.target ? String(day.target) : 'rest'));
            cell.addEventListener('click', () => {
                detail.textContent = `Day ${day.n} (${day.date}): ${day.target ? `${day.target} ${d.unit}` : 'rest day'}, ${day.state}.`;
            });
            grid.append(cell);
        });
        const legend = el('div', 'ac-muted', 'Bright: done. Dashed: rest. Outlined: today. Dim: missed.');
        body.append(head, grid, detail, legend);
    };
})();
