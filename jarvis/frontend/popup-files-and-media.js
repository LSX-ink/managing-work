// Files-and-media pop-up kinds: a photo gallery, a slideshow and a music player (see media_show.py).
// Each card's data.items is a list of {name, src, mime, rel} for files in the memory folders.
(() => {
    const kinds = (window.jarvisPopupKinds = window.jarvisPopupKinds || {});

    // Arrow keys go to the gallery or slideshow used last; a listener removes itself once its window is gone.
    let active = null;
    function arrows(node, onKey) {
        active = node;
        const win = node.closest('.popup') || node.parentElement;
        if (win) win.addEventListener('pointerdown', () => { active = node; });
        const handler = (e) => {
            if (!node.isConnected) { removeEventListener('keydown', handler); return; }
            if (active !== node) return;
            if (e.target.closest && e.target.closest('input, textarea')) return;
            if (e.key === 'ArrowLeft' || e.key === 'ArrowRight') onKey(e.key === 'ArrowRight' ? 1 : -1);
        };
        addEventListener('keydown', handler);
    }

    function controls(el, specs) {
        const bar = el('div', 'media-controls');
        const buttons = specs.map(([label, title, fn]) => {
            const b = el('button', 'pop-action', label);
            b.title = title;
            b.addEventListener('click', fn);
            bar.append(b);
            return b;
        });
        return { bar, buttons };
    }

    kinds.gallery = (card, body, { el }) => {
        const items = (card.data && card.data.items) || [];
        let current = -1;
        const open = (i) => {
            current = (i + items.length) % items.length;
            const it = items[current];
            if (window.jarvisPopup) {
                window.jarvisPopup({
                    kind: 'file', id: `view-${card.id}`, title: `${it.name} (${current + 1}/${items.length})`,
                    src: it.src, mime: it.mime, name: it.name, buttons: [],
                });
            }
        };
        const grid = el('div', 'media-grid');
        items.forEach((it, i) => {
            const b = el('button', 'media-thumb');
            b.title = it.name;
            const img = el('img');
            img.src = it.src;
            img.alt = it.name;
            img.loading = 'lazy';
            b.append(img);
            b.addEventListener('click', () => open(i));
            grid.append(b);
        });
        if (!items.length) grid.append(el('div', 'pop-empty', 'No pictures here.'));
        const { bar } = controls(el, [
            ['‹ Prev', 'Previous picture (left arrow)', () => open(current < 0 ? items.length - 1 : current - 1)],
            ['Next ›', 'Next picture (right arrow)', () => open(current + 1)],
        ]);
        body.append(grid, bar);
        arrows(grid, (step) => { if (current >= 0 && items.length) open(current + step); });
    };

    kinds.slideshow = (card, body, { el, image }) => {
        const items = (card.data && card.data.items) || [];
        const seconds = Math.max(1, Number(card.data && card.data.seconds) || 5);
        if (!items.length) { body.append(el('div', 'pop-empty', 'No pictures here.')); return; }
        let i = 0, playing = true, timer = null;
        const stage = el('div', 'media-stage');
        const caption = el('div', 'media-caption');
        const draw = () => {
            stage.replaceChildren(image(items[i].src, items[i].name));
            caption.textContent = `${items[i].name} · ${i + 1} of ${items.length}`;
        };
        const go = (step) => { i = (i + step + items.length) % items.length; draw(); restart(); };
        const restart = () => {
            clearInterval(timer);
            if (playing) timer = setInterval(() => {
                if (!stage.isConnected) { clearInterval(timer); return; }
                i = (i + 1) % items.length;
                draw();
            }, seconds * 1000);
        };
        const { bar, buttons } = controls(el, [
            ['‹', 'Previous', () => go(-1)],
            ['Pause', 'Pause or play', () => {
                playing = !playing;
                buttons[1].textContent = playing ? 'Pause' : 'Play';
                restart();
            }],
            ['›', 'Next', () => go(1)],
        ]);
        body.append(stage, caption, bar);
        arrows(stage, go);
        draw();
        restart();
    };

    kinds.playlist = (card, body, { el }) => {
        const items = (card.data && card.data.items) || [];
        if (!items.length) { body.append(el('div', 'pop-empty', 'No music here.')); return; }
        let order = items.map((_, n) => n), pos = 0, shuffled = false;
        if (body.mediaAudio) body.mediaAudio.pause();  // the same window shown again
        const audio = el('audio', 'pop-media');
        body.mediaAudio = audio;
        audio.controls = true;
        const now = el('div', 'media-caption');
        const list = el('ul', 'pop-list media-songs');
        const rows = items.map((it, n) => {
            const li = el('li');
            const b = el('button', 'pop-item', it.name);
            b.addEventListener('click', () => { pos = order.indexOf(n); play(); });
            li.append(b);
            list.append(li);
            return li;
        });
        const play = () => {
            const n = order[pos];
            audio.src = items[n].src;
            audio.play().catch(() => {});
            now.textContent = `Now playing: ${items[n].name}`;
            rows.forEach((r, k) => r.classList.toggle('playing', k === n));
        };
        const shuffle = (on) => {
            const n = order[pos];
            order = items.map((_, k) => k);
            if (on) for (let k = order.length - 1; k > 0; k--) {
                const j = Math.floor(Math.random() * (k + 1));
                [order[k], order[j]] = [order[j], order[k]];
            }
            pos = Math.max(0, order.indexOf(n));
        };
        const { bar, buttons } = controls(el, [
            ['‹', 'Previous song', () => { pos = (pos - 1 + order.length) % order.length; play(); }],
            ['Pause', 'Play or pause', () => { if (audio.paused) audio.play().catch(() => {}); else audio.pause(); }],
            ['›', 'Next song', () => { pos = (pos + 1) % order.length; play(); }],
            ['Shuffle', 'Shuffle on or off', () => {
                shuffled = !shuffled;
                shuffle(shuffled);
                buttons[3].classList.toggle('on', shuffled);
            }],
        ]);
        audio.addEventListener('play', () => { buttons[1].textContent = 'Pause'; });
        audio.addEventListener('pause', () => { buttons[1].textContent = 'Play'; });
        audio.addEventListener('ended', () => { if (pos + 1 < order.length) { pos += 1; play(); } });
        const volume = el('input', 'media-volume');
        volume.type = 'range';
        volume.min = '0';
        volume.max = '1';
        volume.step = '0.05';
        volume.value = '0.8';
        volume.title = 'Volume';
        audio.volume = 0.8;
        volume.addEventListener('input', () => { audio.volume = Number(volume.value); });
        bar.append(volume);
        body.append(now, audio, bar, list);
        if (card.data && card.data.shuffle) { shuffled = true; shuffle(true); pos = 0; buttons[3].classList.add('on'); }
        play();
    };
})();
