// HUD secrets (docs/hud-secrets.md): command palette, shortcuts, drag-and-drop into memory, sticky notes,
// window tools and pins, focus mode, screensaver, space facts, live theme, zoom, clean screen, spotlight,
// paste pop-ups and a little easter egg. Alfred drives them by voice with "hud" cards (hudplus.py).
(() => {
    const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    const $ = (id) => document.getElementById(id);
    const el = (tag, cls, text) => {
        const e = document.createElement(tag);
        if (cls) e.className = cls;
        if (text !== undefined) e.textContent = text;
        return e;
    };
    const load = (key, fallback) => {
        try { const v = localStorage.getItem(`hudplus-${key}`); return v === null ? fallback : JSON.parse(v); } catch (e) { return fallback; }
    };
    const save = (key, value) => { try { localStorage.setItem(`hudplus-${key}`, JSON.stringify(value)); } catch (e) { /* private window */ } };
    const ask = (text) => { if (text && window.jarvisAsk) window.jarvisAsk(text); };
    const typing = (target) => !!(target && target.closest && target.closest('input, textarea, select, [contenteditable]'));
    const isHud = () => document.body.classList.contains('hud');

    let toastTimer = null;
    function toast(text) {
        let box = $('hudplus-toast');
        if (!box) { box = el('div', 'hudplus-toast'); box.id = 'hudplus-toast'; box.setAttribute('aria-live', 'polite'); document.body.append(box); }
        box.textContent = text;
        box.classList.add('show');
        clearTimeout(toastTimer);
        toastTimer = setTimeout(() => box.classList.remove('show'), 1600);
    }

    // ---- overlays (palette, shortcuts, folder chooser) ------------------------------------------

    let overlay = null;
    function openOverlay(title, build) {
        closeOverlay();
        overlay = el('div', 'hudplus-overlay');
        overlay.setAttribute('role', 'dialog');
        overlay.setAttribute('aria-label', title);
        const box = el('div', 'hudplus-box');
        box.append(el('h2', 'hudplus-title', title));
        overlay.append(box);
        overlay.addEventListener('pointerdown', (e) => { if (e.target === overlay) closeOverlay(); });
        document.body.append(overlay);
        build(box);
        return box;
    }
    function closeOverlay() { if (overlay) { overlay.remove(); overlay = null; } }

    // ---- 1. command palette ---------------------------------------------------------------------

    const EXAMPLES = {
        'Everyday': ['Add call the bank to my to-do list.', "What's on my to-do list?", 'I spent 12 pounds on lunch.', 'How are my streaks?'],
        'Time and dates': ['What time is it in Tokyo?', 'How many days until Christmas?', 'Start a countdown to my holiday on 18 December.', 'Whose birthday is next?'],
        'Live info': ["What's in the news?", 'Do I need an umbrella this afternoon?', "How's the air quality today?", "What's Bitcoin at?"],
        'Calculators': ["What's 15% of 80?", 'How many kilometres is 26.2 miles?', "What's 350 Fahrenheit in Celsius?", 'Add a 12.5% tip to £86.40 and split it three ways.'],
        'Home and life': ['What are we eating this week?', "What's in the pantry?", "What's going off soon?", 'What recipes have I got?'],
        'Learning and goals': ['Quiz me on Spanish verbs.', 'Quiz me on some French.', 'How many hours have I studied this week?', 'New goal: read 20 books by the end of December.'],
        'Fun': ['Give me a trivia question.', 'Tell me a riddle.', 'Tell me a joke.', 'Ask me a would you rather.'],
        'Words': ['What does ubiquitous mean?', 'Give me another word for happy.', 'What rhymes with orange?', 'How do you spell necessary?'],
        'PC': ['Take a screenshot.', 'What windows are open?', 'Turn on dark mode.', 'Set brightness to 60 percent.'],
        'This screen': ['Tidy my windows.', 'Turn on focus mode.', 'Switch to the gold theme.', 'Show me what you can do.'],
    };

    function openPalette() {
        let picked = -1;
        openOverlay('Ask Alfred', (box) => {
            const input = el('input', 'hudplus-input');
            input.type = 'text';
            input.placeholder = 'Type a request or pick one…';
            input.setAttribute('aria-label', 'Request for Alfred');
            const list = el('ul', 'hudplus-list');
            const buttons = () => [...list.querySelectorAll('button')];
            const send = (text) => { closeOverlay(); ask(text); };
            const draw = () => {
                const words = input.value.toLowerCase().split(/\s+/).filter(Boolean);
                list.replaceChildren();
                for (const [group, lines] of Object.entries(EXAMPLES)) {
                    const hits = lines.filter((l) => words.every((w) => `${group} ${l}`.toLowerCase().includes(w)));
                    if (!hits.length) continue;
                    list.append(el('li', 'hudplus-group', group));
                    for (const line of hits) {
                        const li = el('li');
                        const b = el('button', 'hudplus-item', line);
                        b.type = 'button';
                        b.tabIndex = -1;
                        b.addEventListener('click', () => send(line));
                        li.append(b);
                        list.append(li);
                    }
                }
                picked = -1;
                if (!list.children.length) list.append(el('li', 'hudplus-empty', 'Press Enter to ask exactly that.'));
            };
            const mark = () => buttons().forEach((b, i) => {
                b.classList.toggle('picked', i === picked);
                if (i === picked) b.scrollIntoView({ block: 'nearest' });
            });
            input.addEventListener('input', draw);
            input.addEventListener('keydown', (e) => {
                const all = buttons();
                if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
                    e.preventDefault();
                    if (!all.length) return;
                    if (e.key === 'ArrowDown') picked = (picked + 1) % all.length;
                    else picked = picked <= 0 ? all.length - 1 : picked - 1;
                    mark();
                } else if (e.key === 'Enter') {
                    e.preventDefault();
                    const text = picked >= 0 ? all[picked].textContent : input.value.trim() || (all[0] && all[0].textContent);
                    if (text) send(text);
                }
            });
            box.append(input, list, el('p', 'hudplus-hint', '↑ ↓ to pick · Enter to ask · Esc to close'));
            draw();
            input.focus();
        });
    }

    // ---- 2. keyboard shortcuts ------------------------------------------------------------------

    const SHORTCUTS = [
        ['Ctrl + K', 'Command palette (or double-click the wolf)'],
        ['?', 'This list of shortcuts'],
        ['F', 'Focus mode on or off'],
        ['H', 'Hide or show the side panels'],
        ['N', 'New sticky note'],
        ['T', 'Tidy the pop-up windows'],
        ['S', 'Screensaver now'],
        ['Ctrl + =  /  Ctrl + -', 'Make the HUD bigger or smaller'],
        ['Ctrl + 0', 'HUD back to normal size'],
        ['Alt + 1 … 9', 'Bring pop-up window 1 to 9 to the front'],
        ['Esc', 'Close the top pop-up window, or this list'],
        ['Double-click a title bar', 'Maximise or restore that window'],
        ['Ctrl, Ctrl', 'Tap Ctrl twice to find the mouse'],
        ['Ctrl + V', 'Paste text or a picture into a pop-up'],
        ['Drop files', 'Drag files onto the HUD to save them into a memory folder'],
        ['Click the sky', 'A space fact'],
    ];

    function openShortcuts() {
        openOverlay('Keyboard shortcuts', (box) => {
            const table = el('table', 'hudplus-keys');
            for (const [keys, what] of SHORTCUTS) {
                const tr = el('tr');
                tr.append(el('th', '', keys), el('td', '', what));
                table.append(tr);
            }
            box.append(table, el('p', 'hudplus-hint', 'Letter shortcuts work when you are not typing.'));
        });
    }

    // ---- 3. drag and drop files into a memory folder ------------------------------------------

    const MIME = { png: 'image/png', jpg: 'image/jpeg', jpeg: 'image/jpeg', gif: 'image/gif', webp: 'image/webp', bmp: 'image/bmp',
        svg: 'image/svg+xml', pdf: 'application/pdf', mp3: 'audio/mpeg', wav: 'audio/wav', ogg: 'audio/ogg', m4a: 'audio/mp4',
        flac: 'audio/flac', mp4: 'video/mp4', webm: 'video/webm', mov: 'video/quicktime', txt: 'text/plain', md: 'text/markdown',
        csv: 'text/csv', json: 'application/json', log: 'text/plain' };
    const mimeFor = (name) => MIME[(name.split('.').pop() || '').toLowerCase()] || 'application/octet-stream';

    async function folders() {
        const data = await (await fetch('/memory')).json();
        return (data.folders || []).map((f) => f.name);
    }

    async function upload(index, folder, file, name = file.name) {
        const res = await fetch(`/memory/${index}/files/${encodeURIComponent(name)}`, { method: 'PUT', body: file });
        if (!res.ok) throw new Error((await res.text()) || 'That upload failed.');
        const saved = (await res.json()).name;
        return { name: saved, rel: `${folder}/${saved}` };
    }

    function popFile(rel, name) {
        if (!window.jarvisPopup) return;
        window.jarvisPopup({ kind: 'file', id: `file-${rel}`, title: name, name, mime: mimeFor(name),
            src: `/screen/file?path=${encodeURIComponent(rel)}`, buttons: [] });
    }

    function chooseFolder(files) {
        openOverlay(`Save ${files.length === 1 ? files[0].name : `${files.length} files`} into…`, async (box) => {
            const msg = el('p', 'hudplus-hint', 'Loading folders…');
            const row = el('div', 'hudplus-folders');
            box.append(row, msg);
            let names;
            try { names = await folders(); } catch (e) { msg.textContent = "Couldn't reach Alfred."; return; }
            msg.textContent = 'Pick a memory folder.';
            names.forEach((name, i) => {
                const b = el('button', 'hudplus-folder', name);
                b.type = 'button';
                b.addEventListener('click', async () => {
                    row.querySelectorAll('button').forEach((x) => { x.disabled = true; });
                    for (const file of files) {
                        msg.textContent = `Saving ${file.name}…`;
                        try { const saved = await upload(i, name, file); popFile(saved.rel, saved.name); } catch (e) { toast(`${file.name}: ${e.message}`); }
                    }
                    closeOverlay();
                    toast(`Saved into ${name}.`);
                    if (window.HudStars) window.HudStars.load();
                });
                row.append(b);
            });
            const first = row.querySelector('button');
            if (first) first.focus();
        });
    }

    const hasFiles = (e) => e.dataTransfer && [...e.dataTransfer.types].includes('Files');
    const dropHint = el('div', 'hudplus-drop', 'DROP TO SAVE INTO A MEMORY FOLDER');
    addEventListener('dragover', (e) => {
        if (!hasFiles(e)) return;
        e.preventDefault();
        if (!dropHint.isConnected) document.body.append(dropHint);
    });
    addEventListener('dragleave', (e) => { if (!e.relatedTarget) dropHint.remove(); });
    addEventListener('drop', (e) => {
        dropHint.remove();
        if (!hasFiles(e)) return;
        e.preventDefault();
        const files = [...e.dataTransfer.files];
        if (files.length) chooseFolder(files);
    });

    // ---- 4. sticky notes ------------------------------------------------------------------------

    const COLOURS = ['yellow', 'pink', 'blue', 'green', 'white'];
    const notesLayer = el('div');
    notesLayer.id = 'hudplus-notes';
    let notes = load('notes', []).filter((n) => n && n.id).map((n) => ({ ...n, text: String(n.text || ''), x: Number(n.x) || 0, y: Number(n.y) || 0 }));
    const saveNotes = () => save('notes', notes.map(({ id, text, colour, x, y }) => ({ id, text, colour, x, y })));

    function drawNote(note) {
        const card = el('div', `hudplus-note ${note.colour}`);
        card.dataset.id = note.id;
        card.style.left = `${Math.min(Math.max(0, note.x), innerWidth - 60)}px`;
        card.style.top = `${Math.min(Math.max(0, note.y), innerHeight - 40)}px`;
        const bar = el('div', 'hudplus-note-bar');
        const colour = el('button', 'hudplus-note-btn', '●');
        colour.type = 'button';
        colour.title = 'Change colour';
        colour.addEventListener('click', () => {
            card.classList.remove(note.colour);
            note.colour = COLOURS[(COLOURS.indexOf(note.colour) + 1) % COLOURS.length];
            card.classList.add(note.colour);
            saveNotes();
        });
        const del = el('button', 'hudplus-note-btn', '×');
        del.type = 'button';
        del.title = 'Delete note';
        del.addEventListener('click', () => { notes = notes.filter((n) => n.id !== note.id); card.remove(); saveNotes(); });
        bar.append(colour, del);
        const text = el('textarea', 'hudplus-note-text');
        text.value = note.text;
        text.setAttribute('aria-label', 'Sticky note');
        text.maxLength = 500;
        text.addEventListener('input', () => { note.text = text.value; saveNotes(); });
        bar.addEventListener('pointerdown', (e) => {
            if (e.target.closest('button')) return;
            const sx = e.clientX - card.offsetLeft, sy = e.clientY - card.offsetTop;
            notesLayer.append(card);  // on top of the other notes
            const move = (m) => {
                note.x = Math.min(innerWidth - 60, Math.max(0, m.clientX - sx));
                note.y = Math.min(innerHeight - 30, Math.max(0, m.clientY - sy));
                card.style.left = `${note.x}px`;
                card.style.top = `${note.y}px`;
            };
            const up = () => { removeEventListener('pointermove', move); removeEventListener('pointerup', up); saveNotes(); };
            addEventListener('pointermove', move);
            addEventListener('pointerup', up);
        });
        card.append(bar, text);
        notesLayer.append(card);
        return card;
    }

    function addNote(note = {}, focusIt = false) {
        if (note.id && notes.some((n) => n.id === note.id)) return;
        const n = notes.length;
        const made = { id: note.id || `n${Date.now().toString(36)}`, text: note.text || '', colour: COLOURS.includes(note.colour) ? note.colour : 'yellow',
            x: Math.round(innerWidth * 0.3 + (n % 6) * 28), y: Math.round(110 + (n % 6) * 28) };
        notes.push(made);
        saveNotes();
        const card = drawNote(made);
        if (focusIt) card.querySelector('textarea').focus();
    }

    function removeNotes(match) {
        notes = notes.filter((n) => !(match === null || n.text.toLowerCase().includes(match)));
        notesLayer.replaceChildren();
        notes.forEach(drawNote);
        saveNotes();
    }

    function showNotes() {
        if (!window.jarvisPopup) return;
        window.jarvisPopup({ kind: 'list', id: 'hudplus-notes', title: 'Sticky notes', buttons: [],
            items: notes.filter((n) => n.text.trim()).map((n) => ({ label: n.text, done: false, say: '' })) });
    }

    // ---- 5 and 6. window tools and pins ---------------------------------------------------------

    const popLayer = $('popups');
    const wins = () => (popLayer ? [...popLayer.querySelectorAll('.popup')] : []);
    const closeBtn = (win) => win.querySelector('.pop-bar .pop-btn[title="Close"]');

    function restore(win) {
        if (!win.dataset.saved) return;
        const saved = JSON.parse(win.dataset.saved);
        Object.assign(win.style, saved, { maxWidth: '', maxHeight: '' });
        delete win.dataset.saved;
        win.classList.remove('hudplus-max');
    }

    function toggleMax(win) {
        if (win.dataset.saved) { restore(win); return; }
        const { left, top, width, height } = win.style;
        win.dataset.saved = JSON.stringify({ left, top, width, height });
        Object.assign(win.style, { left: '12px', top: '12px', width: `${innerWidth - 24}px`, height: `${innerHeight - 24}px`, maxWidth: 'none', maxHeight: 'none' });
        win.classList.remove('shrunk');
        win.classList.add('hudplus-max');
    }

    function tidy() {
        const all = wins();
        if (!all.length) return;
        const gap = 12, topY = isHud() ? 76 : 12;
        const cols = Math.max(1, Math.min(all.length, Math.ceil(Math.sqrt(all.length)), Math.floor((innerWidth - gap) / (220 + gap))));
        const rows = Math.ceil(all.length / cols);
        const w = (innerWidth - gap * (cols + 1)) / cols, h = Math.max(90, (innerHeight - topY - gap * (rows + 1)) / rows);
        all.forEach((win, i) => {
            restore(win);
            win.classList.remove('shrunk');
            Object.assign(win.style, { left: `${Math.round(gap + (i % cols) * (w + gap))}px`, top: `${Math.round(topY + gap + Math.floor(i / cols) * (h + gap))}px`,
                width: `${Math.round(w)}px`, height: `${Math.round(h)}px`, maxWidth: 'none', maxHeight: 'none' });
        });
    }

    function closeAll() { wins().filter((w) => !w.classList.contains('pinned')).forEach((w) => { const b = closeBtn(w); if (b) b.click(); }); }
    function minimiseAll() { wins().forEach((w) => { restore(w); w.classList.add('shrunk'); }); }
    function bringUp(n) {
        const win = wins()[n];
        if (!win) return;
        win.classList.remove('shrunk');
        win.dispatchEvent(new PointerEvent('pointerdown'));  // popup.js brings it to the front
        win.classList.remove('hudplus-flash');
        void win.offsetWidth;
        win.classList.add('hudplus-flash');
    }

    function decorate(win) {
        if (win.dataset.hudplus) return;
        win.dataset.hudplus = '1';
        const bar = win.querySelector('.pop-bar');
        if (!bar) return;
        const pin = el('button', 'pop-btn hudplus-pin', '⊙');
        pin.type = 'button';
        pin.title = 'Pin: keep on top and open';
        pin.setAttribute('aria-pressed', 'false');
        pin.addEventListener('click', () => {
            const on = win.classList.toggle('pinned');
            pin.setAttribute('aria-pressed', String(on));
            pin.textContent = on ? '◉' : '⊙';
        });
        bar.insertBefore(pin, bar.querySelector('.pop-btn'));
        bar.addEventListener('dblclick', (e) => { if (!e.target.closest('button')) toggleMax(win); });
    }
    if (popLayer) {
        new MutationObserver(() => wins().forEach(decorate)).observe(popLayer, { childList: true });
        wins().forEach(decorate);
    }

    // ---- 7, 12, 13. focus mode, zoom, clean screen ---------------------------------------------

    function setFocus(on) {
        const now = document.body.classList.toggle('hudplus-focus', on === null || on === undefined ? undefined : !!on);
        toast(now ? 'Focus mode on' : 'Focus mode off');
    }

    function setClean(on, quiet = false) {
        const now = document.body.classList.toggle('hudplus-clean', on === null || on === undefined ? undefined : !!on);
        save('clean', now);
        if (!quiet) toast(now ? 'Side panels hidden' : 'Side panels back');
        setTimeout(() => dispatchEvent(new Event('resize')), 350);  // folder stars find open sky again
    }

    let zoom = load('zoom', 1);
    function setZoom(way) {
        zoom = way === 'reset' ? 1 : Math.round(Math.min(1.6, Math.max(0.7, zoom + (way === 'bigger' ? 0.1 : -0.1))) * 10) / 10;
        applyZoom();
        toast(`HUD size ${Math.round(zoom * 100)}%`);
    }
    function applyZoom() {
        document.body.style.setProperty('--hudplus-zoom', String(zoom));
        save('zoom', zoom);
        dispatchEvent(new Event('resize'));
    }

    // ---- 11. live theme -------------------------------------------------------------------------

    const THEMES = ['hud-stars', 'hud-gold', 'hud-purple', 'hud-red', 'hud-green'];
    let baseTheme = '';
    function setTheme(theme) {
        if (!isHud()) { toast('Themes switch on the HUD only.'); return; }
        const current = THEMES.find((t) => document.body.classList.contains(t)) || 'hud';
        const next = theme === 'toggle' ? (current === 'hud-stars' ? 'hud-gold' : 'hud-stars') : theme;
        document.body.classList.remove(...THEMES);
        if (next !== 'hud') document.body.classList.add(next);
        save('theme', { theme: next, base: baseTheme });
        document.dispatchEvent(new Event('jarvis:theme'));
    }

    // ---- 8. screensaver -------------------------------------------------------------------------

    let saverCfg = load('saver', { on: true, minutes: 10 });
    let saver = null, lastActive = Date.now();

    function startSaver() {
        if (saver) return;
        closeOverlay();
        const box = el('div', 'hudplus-saver');
        const canvas = el('canvas');
        const clock = el('div', 'hudplus-saver-clock');
        const date = el('div', 'hudplus-saver-date');
        box.append(canvas, clock, date);
        document.body.append(box);
        saver = { box, since: Date.now(), x: null, y: null };
        const pad = (n) => String(n).padStart(2, '0');
        const colour = getComputedStyle(document.body).getPropertyValue('--hud-idle').trim() || '#d9dee6';
        const frame = (t) => {
            if (!saver || saver.box !== box) return;
            requestAnimationFrame(frame);
            const now = new Date();
            clock.textContent = `${pad(now.getHours())}:${pad(now.getMinutes())}`;
            date.textContent = now.toLocaleDateString('en-GB', { weekday: 'long', day: 'numeric', month: 'long' });
            const dpr = devicePixelRatio || 1, w = innerWidth, h = innerHeight;
            if (canvas.width !== Math.round(w * dpr)) { canvas.width = Math.round(w * dpr); canvas.height = Math.round(h * dpr); }
            const ctx = canvas.getContext('2d');
            ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
            ctx.clearRect(0, 0, w, h);
            if (!window.HudWolf) return;
            const drift = reduceMotion ? 0 : 1;   // wanders slowly so nothing burns in
            ctx.translate(Math.sin(t / 23000) * w * 0.12 * drift, Math.cos(t / 31000) * h * 0.08 * drift);
            window.HudWolf.draw(ctx, w, h * 0.8, t * 0.4, 0.55, colour, true, { stream: 0 });
        };
        requestAnimationFrame(frame);
    }
    function stopSaver() { if (saver) { saver.box.remove(); saver = null; } lastActive = Date.now(); }
    function saverFromVoice(data) {
        if (data.minutes) saverCfg = { on: true, minutes: data.minutes };
        else if (data.on === false) { saverCfg = { ...saverCfg, on: false }; stopSaver(); }
        else { saverCfg = { ...saverCfg, on: true }; setTimeout(startSaver, 1500); }  // after Alfred has answered
        save('saver', saverCfg);
    }
    setInterval(() => {
        const orb = $('orb');
        if (orb && /thinking|speaking/.test(orb.className)) lastActive = Date.now();   // Alfred is busy, so you are here
        if (saverCfg.on && !saver && Date.now() - lastActive > saverCfg.minutes * 60000) startSaver();
    }, 15000);
    const wake = (e) => {
        if (!saver) { lastActive = Date.now(); return; }
        if (e.type === 'pointermove') {
            if (Date.now() - saver.since < 800) return;
            if (saver.x === null) { saver.x = e.clientX; saver.y = e.clientY; return; }
            if (Math.hypot(e.clientX - saver.x, e.clientY - saver.y) < 12) return;
        }
        e.preventDefault();
        e.stopImmediatePropagation();
        stopSaver();
    };
    ['keydown', 'pointerdown', 'pointermove', 'wheel', 'touchstart'].forEach((type) => addEventListener(type, wake, { capture: true, passive: false }));

    // ---- 9. space facts from the sky ------------------------------------------------------------

    const FACTS = [
        'A day on Venus is longer than its year.', 'Neutron stars can spin 600 times a second.',
        'One million Earths would fit inside the Sun.', 'Light from the Sun takes about 8 minutes 20 seconds to reach us.',
        'Footprints on the Moon could last millions of years: there is no wind to blow them away.',
        'Saturn would float in a big enough bath: it is less dense than water.', 'Space is completely silent.',
        'A teaspoon of neutron star would weigh about a billion tonnes.', 'Jupiter has at least 95 moons.',
        'The Milky Way and Andromeda will collide in about 4.5 billion years.', "Olympus Mons on Mars is nearly three times Everest's height.",
        'There are more stars in the universe than grains of sand on all of Earth\'s beaches.', 'A year on Mercury is just 88 Earth days.',
        'The Sun makes up about 99.8% of the mass of the Solar System.', 'Uranus rolls around the Sun on its side.',
        'The Great Red Spot is a storm bigger than Earth, raging for centuries.', 'Astronauts can grow up to 5 cm taller in space.',
        "Sunsets on Mars are blue.", 'The ISS goes round the Earth about every 90 minutes.', 'Halley\'s Comet comes back in 2061.',
        'The Moon is drifting away from Earth by about 3.8 cm a year.', 'Some of the stars you see may no longer exist.',
        'Mercury and Venus are the only planets with no moons.', 'The coldest place known is the Boomerang Nebula, at -272 °C.',
        'It rains diamonds deep inside Neptune and Uranus.', 'Venus spins backwards compared to most planets.',
        'The Voyager 1 probe is more than 24 billion km from home.', 'A black hole the mass of Earth would be the size of a marble.',
        'The Andromeda galaxy is visible to the naked eye on a dark night.', 'Every atom of iron in your blood was made in a dying star.',
    ];
    let factBox = null, factTimer = null;
    function showFact(x, y) {
        if (factBox) factBox.remove();
        factBox = el('div', 'hudplus-fact', FACTS[Math.floor(Math.random() * FACTS.length)]);
        factBox.setAttribute('role', 'status');
        document.body.append(factBox);
        const w = factBox.offsetWidth, h = factBox.offsetHeight;
        factBox.style.left = `${Math.min(innerWidth - w - 8, Math.max(8, x + 12))}px`;
        factBox.style.top = `${Math.min(innerHeight - h - 8, Math.max(8, y + 12))}px`;
        const ring = el('div', 'hudplus-ring');
        ring.style.left = `${x}px`;
        ring.style.top = `${y}px`;
        document.body.append(ring);
        setTimeout(() => ring.remove(), 1200);
        clearTimeout(factTimer);
        const box = factBox;
        factTimer = setTimeout(() => { box.remove(); if (factBox === box) factBox = null; }, 7000);
    }
    document.addEventListener('click', (e) => {
        if (!isHud() || String(getSelection()).length) return;
        const t = e.target;
        if (t === document.body || t === document.documentElement || t.id === 'app') showFact(e.clientX, e.clientY);
    });

    // ---- 10. Konami code -------------------------------------------------------------------------

    const KONAMI = ['arrowup', 'arrowup', 'arrowdown', 'arrowdown', 'arrowleft', 'arrowright', 'arrowleft', 'arrowright', 'b', 'a'];
    const HOWL_LINES = [
        'Awooo. Forgive me, sir; the wolf insisted.', 'Up, up, down, down... I see you are a person of culture, sir.',
        'Thirty extra lives granted. Do use them wisely.', 'The pack is assembled, sir. All one of us.',
    ];
    let konami = 0;
    function howl() {
        document.body.classList.remove('hudplus-howl');
        void document.body.offsetWidth;
        document.body.classList.add('hudplus-howl');
        setTimeout(() => document.body.classList.remove('hudplus-howl'), 3200);
        const word = el('div', 'hudplus-awoo', 'AWOOOOOO');
        document.body.append(word);
        setTimeout(() => word.remove(), 3200);
        if (typeof addLine === 'function') addLine('jarvis', HOWL_LINES[Math.floor(Math.random() * HOWL_LINES.length)]);
        try {   // a soft rising and falling howl, made in the browser
            const audio = new (window.AudioContext || window.webkitAudioContext)();
            const osc = audio.createOscillator(), gain = audio.createGain(), now = audio.currentTime;
            osc.type = 'sine';
            osc.frequency.setValueAtTime(320, now);
            osc.frequency.exponentialRampToValueAtTime(760, now + 0.7);
            osc.frequency.exponentialRampToValueAtTime(520, now + 2.2);
            gain.gain.setValueAtTime(0.0001, now);
            gain.gain.exponentialRampToValueAtTime(0.15, now + 0.3);
            gain.gain.exponentialRampToValueAtTime(0.0001, now + 2.4);
            osc.connect(gain).connect(audio.destination);
            osc.start(now);
            osc.stop(now + 2.5);
            setTimeout(() => audio.close(), 3000);
        } catch (e) { /* no audio */ }
    }

    // ---- 14. spotlight ---------------------------------------------------------------------------

    let mouse = { x: innerWidth / 2, y: innerHeight / 2 }, lastCtrl = 0;
    addEventListener('pointermove', (e) => { mouse = { x: e.clientX, y: e.clientY }; }, { passive: true });
    function spotlight() {
        const spot = el('div', 'hudplus-spot');
        spot.style.left = `${mouse.x}px`;
        spot.style.top = `${mouse.y}px`;
        document.body.append(spot);
        setTimeout(() => spot.remove(), 1300);
    }

    // ---- 15. paste into a pop-up -----------------------------------------------------------------

    const stamp = () => new Date().toISOString().slice(0, 19).replace(/[-:]/g, '').replace('T', '-');
    window.jarvisPopupKinds = window.jarvisPopupKinds || {};
    window.jarvisPopupKinds.hudclip = (card, body, { el: make }) => {
        const file = card.file;
        if (!(file instanceof Blob)) { body.append(make('div', 'pop-empty', 'Nothing to show.')); return; }
        const url = URL.createObjectURL(file);
        const img = make('img', 'pop-image');
        img.src = url;
        img.alt = 'Pasted picture';
        const msg = make('div', 'pop-site', '');
        const row = make('div', 'hudplus-cliprow');
        let saved = null;
        const store = async () => {
            if (saved) return saved;
            const names = await folders();
            let i = names.findIndex((n) => n.toLowerCase() === 'ideas');
            if (i < 0) i = 0;
            saved = await upload(i, names[i], file, `pasted-${stamp()}.${(file.type.split('/')[1] || 'png').replace('jpeg', 'jpg')}`);
            msg.textContent = `Saved as ${saved.rel}`;
            return saved;
        };
        const button = (label, act) => {
            const b = make('button', 'pop-action', label);
            b.type = 'button';
            b.addEventListener('click', async () => { try { await act(); } catch (e) { msg.textContent = e.message; } });
            row.append(b);
        };
        button('Save to Ideas', store);
        button('Summarise', async () => { const s = await store(); ask(`Look at the picture ${s.rel} in my memory folders and tell me what's in it.`); });
        body.append(img, row, msg);
    };

    document.addEventListener('paste', (e) => {
        if (typing(document.activeElement) || typing(e.target) || !window.jarvisPopup) return;
        const data = e.clipboardData;
        if (!data) return;
        const image = [...data.files].find((f) => f.type.startsWith('image/'));
        if (image) {
            e.preventDefault();
            window.jarvisPopup({ kind: 'hudclip', id: `clip-${Date.now()}`, title: 'Pasted picture', file: image, buttons: [] });
            return;
        }
        const text = data.getData('text/plain').trim();
        if (!text) return;
        e.preventDefault();
        const short = text.slice(0, 4000);
        window.jarvisPopup({ kind: 'text', id: `clip-${Date.now()}`, title: 'Pasted text', text: short, buttons: [
            { label: 'Save to Ideas', say: `Save this into my Ideas folder as a note: ${short}` },
            { label: 'Summarise', say: `Summarise this for me: ${short}` },
        ] });
    });

    // ---- keys -------------------------------------------------------------------------------------

    addEventListener('keydown', (e) => {
        const key = (e.key || '').toLowerCase();
        if (overlay && e.key === 'Escape') { e.preventDefault(); e.stopPropagation(); closeOverlay(); return; }
        if (key === 'control') {
            if (!e.repeat && Date.now() - lastCtrl < 400) { spotlight(); lastCtrl = 0; } else if (!e.repeat) lastCtrl = Date.now();
            return;
        }
        lastCtrl = 0;
        if ((e.ctrlKey || e.metaKey) && !e.altKey && key === 'k') { e.preventDefault(); overlay ? closeOverlay() : openPalette(); return; }
        if ((e.ctrlKey || e.metaKey) && !e.altKey && ['=', '+', '-', '_', '0'].includes(key)) {
            e.preventDefault();
            setZoom(key === '0' ? 'reset' : key === '-' || key === '_' ? 'smaller' : 'bigger');
            return;
        }
        if (e.altKey && !e.ctrlKey && /^Digit[1-9]$/.test(e.code)) { e.preventDefault(); bringUp(Number(e.code.slice(5)) - 1); return; }
        if (typing(e.target) || e.isComposing) { konami = 0; return; }
        konami = key === KONAMI[konami] ? konami + 1 : key === KONAMI[0] ? 1 : 0;
        if (konami === KONAMI.length) { konami = 0; howl(); return; }
        if (e.ctrlKey || e.metaKey || e.altKey || overlay) return;
        if (e.key === '?') { e.preventDefault(); openShortcuts(); }
        else if (key === 'f') setFocus(null);
        else if (key === 'h') setClean(null);
        else if (key === 'n') { e.preventDefault(); addNote({}, true); }
        else if (key === 't') tidy();
        else if (key === 's') startSaver();
    }, true);

    // ---- Alfred's "hud" cards --------------------------------------------------------------------

    function perform(data = {}) {
        const act = data.action;
        if (act === 'tidy') tidy();
        else if (act === 'close_all') closeAll();
        else if (act === 'minimise_all') minimiseAll();
        else if (act === 'focus') setFocus(data.on);
        else if (act === 'clean') setClean(data.on);
        else if (act === 'screensaver') saverFromVoice(data);
        else if (act === 'theme') setTheme(data.theme || 'toggle');
        else if (act === 'zoom') setZoom(data.zoom);
        else if (act === 'shortcuts') openShortcuts();
        else if (act === 'palette') openPalette();
        else if (act === 'note_add' && data.note) addNote(data.note);
        else if (act === 'notes_show') showNotes();
        else if (act === 'note_remove' && data.match) removeNotes(String(data.match).toLowerCase());
        else if (act === 'note_clear') removeNotes(null);
    }
    // Handled before popup.js sees them, so no window flashes up; "close all" leaves pinned windows open.
    window.addEventListener('jarvis:popup', (e) => {
        const card = e.detail || {};
        if (card.kind === 'hud') { e.stopImmediatePropagation(); perform(card.data); }
        else if (card.kind === 'close' && card.all) { e.stopImmediatePropagation(); closeAll(); }
    }, true);
    window.jarvisPopupKinds.hud = (card, body) => {   // if a card reaches popup.js some other way
        perform(card.data);
        setTimeout(() => { const win = body.closest('.popup'); if (win && closeBtn(win)) closeBtn(win).click(); }, 0);
    };

    // ---- start -----------------------------------------------------------------------------------

    function start(config) {
        document.body.append(notesLayer);
        notes.forEach(drawNote);
        if (zoom !== 1) applyZoom();
        if (load('clean', false)) setClean(true, true);
        baseTheme = config.theme || '';
        const saved = load('theme', null);
        if (saved && saved.base === baseTheme && isHud()) setTheme(saved.theme);
        const chips = document.querySelector('.hud-chips');
        if (chips && isHud()) {
            const add = el('button', '', 'NOTE +');
            add.type = 'button';
            add.title = 'New sticky note (N)';
            add.addEventListener('click', () => addNote({}, true));
            chips.prepend(add);
        }
        const wrap = $('orb-wrap');
        if (wrap) wrap.addEventListener('dblclick', (e) => { if (!(window.HudMemory && window.HudMemory.open)) { e.preventDefault(); openPalette(); } });
    }
    let started = false;
    document.addEventListener('jarvis:config', (e) => { if (!started) { started = true; start(e.detail || {}); } });
    window.HudPlus = { perform, tidy, closeAll, openPalette, openShortcuts };
})();
