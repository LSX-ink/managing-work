// Web-in-Alfred pop-up kinds (see webview_*.py): webcard, gallery, map, radio, recipe.
// Everything is drawn with textContent; pictures and sound load only from https links.
(() => {
    const kinds = (window.jarvisPopupKinds = window.jarvisPopupKinds || {});
    const isHttps = (u) => typeof u === 'string' && u.startsWith('https://');
    const OSM_EMBED = 'https://www.openstreetmap.org/export/embed.html?';

    function picture(el, src, cls) {
        const img = el('img', cls);
        if (!isHttps(src)) return null;
        img.src = src;
        img.alt = '';
        img.loading = 'lazy';
        img.referrerPolicy = 'no-referrer';
        img.addEventListener('error', () => img.remove());
        return img;
    }

    // A single thing from the web: a link preview or a country with its flag.
    kinds.webcard = (card, body, { el, table }) => {
        const d = card.data || {};
        const wrap = el('div', 'wa-card');
        const img = picture(el, d.image, 'wa-card-img');
        if (img) wrap.append(img);
        if (d.site) wrap.append(el('div', 'pop-site', d.site));
        if (d.heading && d.heading !== card.title) wrap.append(el('h4', 'wa-heading', d.heading));
        if (d.text) wrap.append(el('p', 'wa-text', d.text));
        if (Array.isArray(d.facts) && d.facts.length) wrap.append(table([], d.facts));
        if (isHttps(d.link)) wrap.append(el('div', 'wa-link', d.link));
        body.append(wrap);
    };

    // Tiles with pictures (books, meals, drinks, podcasts); tapping one sends its line to Alfred.
    kinds.webgallery = (card, body, { el, ask }) => {
        const grid = el('div', 'wa-gallery');
        for (const t of (card.data || {}).tiles || []) {
            const tile = el(t.say ? 'button' : 'div', 'wa-tile');
            const img = picture(el, t.image, 'wa-tile-img');
            tile.append(img || el('div', 'wa-tile-img wa-blank', (t.title || '?').charAt(0)));
            tile.append(el('span', 'wa-tile-title', t.title || ''));
            if (t.subtitle) tile.append(el('span', 'wa-tile-sub', t.subtitle));
            if (t.say) {
                tile.title = t.say;
                tile.addEventListener('click', () => ask(t.say));
            }
            grid.append(tile);
        }
        if (!grid.children.length) grid.append(el('div', 'pop-empty', 'Nothing found.'));
        body.append(grid);
    };

    // An OpenStreetMap embed (sandboxed), or a rain radar made of map tiles with radar tiles on top.
    kinds.map = (card, body, { el }) => {
        const d = card.data || {};
        if (d.mode === 'radar') {
            const box = el('div', 'wa-radar');
            for (const t of (d.tiles || []).slice(0, 9)) {
                const cell = el('div', 'wa-radar-cell');
                for (const src of [t.base, t.overlay]) {
                    const img = el('img');
                    if (isHttps(src)) img.src = src;
                    img.alt = '';
                    cell.append(img);
                }
                box.append(cell);
            }
            const pin = el('span', 'wa-pin');
            const m = d.marker || {};
            pin.style.left = `${Math.min(100, Math.max(0, (m.x || 0.5) * 100))}%`;
            pin.style.top = `${Math.min(100, Math.max(0, (m.y || 0.5) * 100))}%`;
            box.append(pin);
            body.append(box);
            if (d.credit) body.append(el('div', 'wa-credit', d.credit));
            return;
        }
        if (d.distance) body.append(el('div', 'wa-distance', d.distance));
        if (typeof d.embed === 'string' && d.embed.startsWith(OSM_EMBED)) {
            const frame = el('iframe', 'pop-frame wa-map');
            frame.src = d.embed;
            frame.title = card.title;
            frame.setAttribute('sandbox', 'allow-scripts allow-same-origin');
            frame.referrerPolicy = 'strict-origin-when-cross-origin';
            frame.loading = 'lazy';
            body.append(frame);
        }
        body.append(el('div', 'wa-credit', '© OpenStreetMap contributors'));
    };

    // A player for radio stations or podcast episodes: tap one to play, Play/Stop, volume.
    kinds.radio = (card, body, { el }) => {
        const d = card.data || {};
        const tracks = (d.tracks || []).filter((t) => isHttps(t.src));
        const audio = el('audio');
        audio.preload = 'none';
        let volume = 0.8;
        try { volume = Number(localStorage.getItem('jarvis-radio-volume') || 0.8); } catch (e) { /* private mode */ }
        audio.volume = Math.min(1, Math.max(0, volume));

        const now = el('div', 'wa-now', 'Nothing playing');
        const art = el('div', 'wa-art');
        const toggle = el('button', 'pop-action', 'Play');
        const slider = el('input', 'wa-volume');
        Object.assign(slider, { type: 'range', min: 0, max: 1, step: 0.05, value: audio.volume, title: 'Volume' });
        slider.addEventListener('input', () => {
            audio.volume = Number(slider.value);
            try { localStorage.setItem('jarvis-radio-volume', slider.value); } catch (e) { /* private mode */ }
        });
        const controls = el('div', 'wa-controls');
        controls.append(toggle, el('span', 'wa-vol-label', 'Volume'), slider);
        const head = el('div', 'wa-player');
        const side = el('div', 'wa-player-side');
        side.append(now, controls);
        head.append(art, side);
        body.append(head, audio);

        const list = el('ul', 'pop-list wa-tracks');
        let current = -1;
        const items = tracks.map((t, i) => {
            const li = el('li');
            const b = el('button', 'pop-item', t.title || `Track ${i + 1}`);
            b.addEventListener('click', () => (i === current && !audio.paused ? stop() : play(i)));
            li.append(b);
            if (t.subtitle) li.append(el('span', 'wa-track-sub', t.subtitle));
            list.append(li);
            return li;
        });
        if (!items.length) list.append(el('li', 'pop-empty', 'Nothing to play.'));
        body.append(list);

        function mark() {
            items.forEach((li, i) => li.classList.toggle('wa-playing', i === current && !audio.paused));
            toggle.textContent = audio.paused ? 'Play' : 'Stop';
        }
        function play(i) {
            const t = tracks[i];
            if (!t) return;
            current = i;
            if (audio.dataset.src !== t.src) { audio.src = t.src; audio.dataset.src = t.src; }
            now.textContent = t.title || '';
            art.replaceChildren(...[picture(el, t.image || d.image, 'wa-art-img')].filter(Boolean));
            audio.play().catch(() => { now.textContent = `${t.title}: couldn't play it.`; mark(); });
        }
        function stop() {
            audio.pause();
            if (d.live) { audio.removeAttribute('src'); audio.dataset.src = ''; audio.load(); }
            mark();
        }
        toggle.addEventListener('click', () => (audio.paused ? play(current < 0 ? 0 : current) : stop()));
        ['play', 'pause', 'ended'].forEach((e) => audio.addEventListener(e, mark));
        audio.addEventListener('error', () => { if (audio.dataset.src) now.textContent = "That stream isn't working."; });
        if (Number.isInteger(d.autoplay) && d.autoplay >= 0) play(d.autoplay);
    };

    // A recipe: picture, ingredients to tick off while cooking, numbered steps.
    kinds.recipe = (card, body, { el }) => {
        const d = card.data || {};
        const img = picture(el, d.image, 'wa-card-img');
        if (img) body.append(img);
        const about = [d.site, d.about].filter(Boolean).join(' · ');
        if (about) body.append(el('div', 'pop-site', about));
        body.append(el('h4', 'wa-heading', 'Ingredients'));
        const ul = el('ul', 'pop-list');
        for (const text of d.ingredients || []) {
            const li = el('li');
            const label = el('label', 'wa-check');
            const box = el('input');
            box.type = 'checkbox';
            box.addEventListener('change', () => li.classList.toggle('done', box.checked));
            label.append(box, el('span', 'pop-item', text));
            li.append(label);
            ul.append(li);
        }
        if (!ul.children.length) ul.append(el('li', 'pop-empty', 'No ingredients listed.'));
        body.append(ul);
        if ((d.steps || []).length) {
            body.append(el('h4', 'wa-heading', 'Method'));
            const ol = el('ol', 'wa-steps');
            d.steps.forEach((s) => ol.append(el('li', '', s)));
            body.append(ol);
        }
    };
})();
