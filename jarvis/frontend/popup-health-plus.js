// Health-plus pop-up kinds (wellness_*.py): a trend chart with several series and guide lines, and a live
// interval timer that walks through phases (work, rest, moves) with a beep at each change.
(() => {
    const kinds = window.jarvisPopupKinds = window.jarvisPopupKinds || {};
    const NS = 'http://www.w3.org/2000/svg';

    kinds['wellness-trend'] = (card, body, { el }) => {
        const { labels = [], series = [], unit = '', guides = [] } = card.data || {};
        const W = 440, H = 230, L = 44, B = 36, T = 14, R = 10;
        const svg = document.createElementNS(NS, 'svg');
        svg.setAttribute('viewBox', `0 0 ${W} ${H}`);
        svg.setAttribute('class', 'pop-chart wl-trend');
        const add = (tag, attrs, text) => {
            const n = document.createElementNS(NS, tag);
            for (const [k, v] of Object.entries(attrs)) n.setAttribute(k, v);
            if (text !== undefined) n.textContent = text;
            svg.append(n);
            return n;
        };
        const all = series.flatMap((s) => s.values || []).filter((v) => typeof v === 'number');
        if (!all.length) { body.append(el('div', 'pop-empty', 'Nothing to chart yet.')); return; }
        const inView = guides.map((g) => g.value).filter((v) => v >= Math.min(...all) - 15 && v <= Math.max(...all) + 15);
        let min = Math.min(...all, ...inView), max = Math.max(...all, ...inView);
        const pad = (max - min) * 0.1 || 1;
        min -= pad; max += pad;
        const y = (v) => T + (H - T - B) * (1 - (v - min) / (max - min));
        const step = (W - L - R) / Math.max(1, labels.length);
        const x = (i) => L + step * (i + 0.5);
        const fmt = (v) => `${+v.toFixed(1)}${unit ? ` ${unit}` : ''}`;
        [min, (min + max) / 2, max].forEach((v) => {
            add('line', { x1: L, x2: W - R, y1: y(v), y2: y(v), class: 'grid' });
            add('text', { x: L - 6, y: y(v) + 4, 'text-anchor': 'end', class: 'axis' }, +v.toFixed(0));
        });
        guides.filter((g) => g.value > min && g.value < max).forEach((g) => {
            add('line', { x1: L, x2: W - R, y1: y(g.value), y2: y(g.value), class: 'wl-guide' });
            add('text', { x: W - R - 2, y: y(g.value) - 3, 'text-anchor': 'end', class: 'wl-guide-label' }, g.label || '');
        });
        const every = Math.ceil(labels.length / 6);
        labels.forEach((label, i) => {
            if (i % every === 0) add('text', { x: x(i), y: H - 12, 'text-anchor': 'middle', class: 'axis' }, label);
        });
        series.forEach((s, n) => {
            const pts = (s.values || []).map((v, i) => (typeof v === 'number' ? [x(i), y(v), v, i] : null)).filter(Boolean);
            if (s.style !== 'dots' && pts.length > 1) {
                add('polyline', { points: pts.map((p) => `${p[0]},${p[1]}`).join(' '), class: `wl-line wl-s${n}` });
            }
            pts.forEach(([cx, cy, v, i]) => add('circle', { cx, cy, r: s.style === 'dots' ? 3 : 2, class: `wl-dot wl-s${n}` })
                .append(Object.assign(document.createElementNS(NS, 'title'), { textContent: `${labels[i]} ${s.name}: ${fmt(v)}` })));
        });
        body.append(svg);
        const key = el('div', 'wl-key');
        series.forEach((s, n) => {
            const item = el('span', `wl-key-item wl-s${n}`);
            item.append(el('i', `wl-swatch ${s.style === 'dots' ? 'dots' : ''}`), document.createTextNode(s.name));
            key.append(item);
        });
        body.append(key);
    };

    let audio = null;
    function beep(freq = 880, ms = 180) {
        try {
            audio = audio || new (window.AudioContext || window.webkitAudioContext)();
            const osc = audio.createOscillator(), gain = audio.createGain();
            osc.frequency.value = freq;
            gain.gain.setValueAtTime(0.25, audio.currentTime);
            gain.gain.exponentialRampToValueAtTime(0.001, audio.currentTime + ms / 1000);
            osc.connect(gain).connect(audio.destination);
            osc.start();
            osc.stop(audio.currentTime + ms / 1000);
        } catch (e) { /* no sound available */ }
    }

    kinds['wellness-intervals'] = (card, body, { el }) => {
        const phases = ((card.data || {}).phases || []).filter((p) => p.seconds > 0);
        const sound = (card.data || {}).beep !== false;
        if (!phases.length) { body.append(el('div', 'pop-empty', 'No intervals to run.')); return; }
        const total = phases.reduce((a, p) => a + p.seconds, 0);
        const box = el('div', 'wl-timer');
        const label = el('div', 'wl-phase'), face = el('div', 'pop-timer'), next = el('div', 'wl-next');
        const bar = el('div', 'wl-bar'), fill = el('div', 'wl-fill');
        bar.append(fill);
        const controls = el('div', 'wl-controls');
        const pauseBtn = el('button', 'pop-action', 'Pause'), restartBtn = el('button', 'pop-action', 'Restart');
        controls.append(pauseBtn, restartBtn);
        box.append(label, face, next, bar, controls);
        body.append(box);

        let started = Date.now(), pausedAt = 0, last = -1, lastSecond = -1;
        pauseBtn.addEventListener('click', () => {
            if (pausedAt) { started += Date.now() - pausedAt; pausedAt = 0; pauseBtn.textContent = 'Pause'; }
            else { pausedAt = Date.now(); pauseBtn.textContent = 'Resume'; }
        });
        restartBtn.addEventListener('click', () => { started = Date.now(); pausedAt = 0; last = -1; pauseBtn.textContent = 'Pause'; });

        const tick = () => {
            if (!box.isConnected) return;
            const gone = ((pausedAt || Date.now()) - started) / 1000;
            let t = gone, i = 0;
            while (i < phases.length && t >= phases[i].seconds) { t -= phases[i].seconds; i += 1; }
            if (i >= phases.length) {
                label.textContent = 'Finished';
                face.textContent = '00:00';
                next.textContent = 'Well done.';
                fill.style.width = '100%';
                box.dataset.type = 'done';
                if (last !== i && sound) { beep(660, 250); setTimeout(() => beep(990, 400), 300); }
                last = i;
                setTimeout(tick, 200);
                return;
            }
            const p = phases[i], left = Math.ceil(p.seconds - t);
            if (i !== last) { if (sound && last !== -1) beep(p.type === 'work' ? 990 : 660, 300); last = i; }
            if (sound && left <= 3 && left !== lastSecond && !pausedAt) beep(440, 90);
            lastSecond = left;
            label.textContent = `${p.label}  (${i + 1}/${phases.length})`;
            face.textContent = `${String(Math.floor(left / 60)).padStart(2, '0')}:${String(left % 60).padStart(2, '0')}`;
            next.textContent = phases[i + 1] ? `Next: ${phases[i + 1].label}` : 'Last one';
            fill.style.width = `${Math.min(100, (gone / total) * 100)}%`;
            box.dataset.type = p.type || 'work';
            setTimeout(tick, 200);
        };
        if (sound) beep(990, 200);
        tick();
    };
})();
