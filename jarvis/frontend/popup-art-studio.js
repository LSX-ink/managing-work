// Art-studio pop-up kinds (see artstudio_*.py): colour swatches that copy their hex code, a pixel art editor that
// saves a scaled-up PNG into a memory folder, ASCII art, and a mood board of pictures with a palette row.
(() => {
    const kinds = (window.jarvisPopupKinds = window.jarvisPopupKinds || {});
    const HEX = /^#[0-9a-f]{6}$/i;

    async function copy(text, status) {
        try {
            await navigator.clipboard.writeText(text);
            status.textContent = `Copied ${text.length > 20 ? 'it' : text}.`;
        } catch (e) {
            status.textContent = "Couldn't copy; select it and press Ctrl+C.";
        }
    }

    function swatchRow(el, swatches, status) {
        const row = el('div', 'art-swatches');
        for (const s of swatches || []) {
            if (!HEX.test(s.hex || '')) continue;
            const b = el('button', 'art-swatch');
            b.type = 'button';
            b.title = `Copy ${s.hex}`;
            const chip = el('span', 'art-chip');
            chip.style.background = s.hex;
            b.append(chip, el('span', 'art-hex', s.hex), el('span', 'art-name', s.name || ''));
            if (typeof s.share === 'number') b.append(el('span', 'art-share', `${s.share}%`));
            b.addEventListener('click', () => copy(s.hex, status));
            row.append(b);
        }
        return row;
    }

    function live(el) {
        const s = el('div', 'art-status');
        s.setAttribute('aria-live', 'polite');
        return s;
    }

    kinds['art-palette'] = (card, body, { el }) => {
        const swatches = (card.data && card.data.swatches) || [];
        const status = live(el);
        const all = el('button', 'pop-action', 'Copy all');
        all.addEventListener('click', () => copy(swatches.map((s) => s.hex).join(', '), status));
        const bar = el('div', 'art-bar');
        bar.append(all, status);
        body.append(swatchRow(el, swatches, status), bar);
    };

    kinds['art-ascii'] = (card, body, { el }) => {
        const text = String((card.data && card.data.text) || '');
        const pre = el('pre', 'art-ascii', text);
        const status = live(el);
        const b = el('button', 'pop-action', 'Copy');
        b.addEventListener('click', () => copy(text, status));
        const smaller = el('button', 'pop-action', 'A−');
        const bigger = el('button', 'pop-action', 'A+');
        let size = 9;
        const resize = (d) => { size = Math.min(16, Math.max(4, size + d)); pre.style.fontSize = `${size}px`; };
        smaller.title = 'Smaller text';
        bigger.title = 'Bigger text';
        smaller.addEventListener('click', () => resize(-1));
        bigger.addEventListener('click', () => resize(1));
        const bar = el('div', 'art-bar');
        bar.append(b, smaller, bigger, status);
        body.append(pre, bar);
    };

    kinds['art-moodboard'] = (card, body, { el, ask }) => {
        const data = card.data || {};
        const grid = el('div', 'art-mood');
        for (const it of data.items || []) {
            const b = el('button', 'art-tile');
            b.type = 'button';
            b.title = it.name;
            const img = el('img');
            img.src = it.src;
            img.alt = it.name;
            img.loading = 'lazy';
            b.append(img);
            b.addEventListener('click', () => ask(it.say));
            grid.append(b);
        }
        const status = live(el);
        body.append(grid, swatchRow(el, data.swatches, status), status);
    };

    // ---- pixel art editor ------------------------------------------------------------------------------
    async function saveToFolder(folder, filename, blob) {
        const r = await fetch('/memory');
        if (!r.ok) throw new Error("Couldn't read the memory folders.");
        const folders = (await r.json()).folders || [];
        const index = folders.findIndex((f) => f.name.toLowerCase() === String(folder).toLowerCase());
        if (index < 0) throw new Error(`There's no ${folder} folder.`);
        const put = await fetch(`/memory/${index}/files/${encodeURIComponent(filename)}`, {
            method: 'PUT', headers: { 'Content-Type': 'image/png' }, body: blob,
        });
        if (!put.ok) throw new Error((await put.text()) || 'Saving failed.');
        return { folder: folders[index].name, name: (await put.json()).name };
    }

    kinds['art-pixel'] = (card, body, { el }) => {
        const d = card.data || {};
        const n = [8, 16, 32].includes(d.size) ? d.size : 16;
        const palette = (d.palette || []).filter((c) => HEX.test(c));
        const cell = Math.floor(480 / n);
        let cells = new Array(n * n).fill(null);
        const undo = [];
        let colour = palette[0] || '#000000', tool = 'pen', grid = true, painting = false;

        const canvas = el('canvas', 'art-canvas');
        canvas.width = canvas.height = n * cell;
        canvas.setAttribute('aria-label', `Pixel art grid, ${n} by ${n}`);
        const g = canvas.getContext('2d');
        const css = (name, fallback) => getComputedStyle(body).getPropertyValue(name).trim() || fallback;

        function draw() {
            for (let i = 0; i < n * n; i++) {
                const x = (i % n) * cell, y = Math.floor(i / n) * cell;
                if (cells[i]) { g.fillStyle = cells[i]; g.fillRect(x, y, cell, cell); continue; }
                const light = ((i % n) + Math.floor(i / n)) % 2 === 0;
                g.fillStyle = light ? '#2b2b2b' : '#202020';   // a checkerboard shows empty (see-through) squares
                g.fillRect(x, y, cell, cell);
            }
            if (!grid) return;
            g.strokeStyle = css('--hud-dim', '#444');
            g.lineWidth = 1;
            g.beginPath();
            for (let k = 0; k <= n; k++) {
                g.moveTo(k * cell + 0.5, 0); g.lineTo(k * cell + 0.5, n * cell);
                g.moveTo(0, k * cell + 0.5); g.lineTo(n * cell, k * cell + 0.5);
            }
            g.stroke();
        }

        const at = (e) => {
            const r = canvas.getBoundingClientRect();
            const x = Math.floor((e.clientX - r.left) / r.width * n), y = Math.floor((e.clientY - r.top) / r.height * n);
            return x >= 0 && y >= 0 && x < n && y < n ? y * n + x : -1;
        };
        const remember = () => { undo.push(cells.slice()); if (undo.length > 50) undo.shift(); };

        function fill(start) {
            const target = cells[start], paint = tool === 'eraser' ? null : colour;
            if (target === paint) return;
            const stack = [start];
            while (stack.length) {
                const i = stack.pop();
                if (cells[i] !== target) continue;
                cells[i] = paint;
                const x = i % n;
                if (x > 0) stack.push(i - 1);
                if (x < n - 1) stack.push(i + 1);
                if (i >= n) stack.push(i - n);
                if (i < n * n - n) stack.push(i + n);
            }
        }

        function act(e) {
            const i = at(e);
            if (i < 0) return;
            if (tool === 'fill') fill(i);
            else cells[i] = tool === 'eraser' ? null : colour;
            draw();
        }

        canvas.addEventListener('pointerdown', (e) => {
            e.preventDefault();
            canvas.setPointerCapture(e.pointerId);
            remember();
            painting = tool !== 'fill';
            act(e);
        });
        canvas.addEventListener('pointermove', (e) => { if (painting) act(e); });
        ['pointerup', 'pointercancel'].forEach((t) => canvas.addEventListener(t, () => { painting = false; }));

        const button = (label, fn, cls = 'pop-action') => {
            const b = el('button', cls, label);
            b.type = 'button';
            b.addEventListener('click', fn);
            return b;
        };
        const tools = el('div', 'art-bar');
        const toolButtons = {};
        const pickTool = (t) => {
            tool = t;
            for (const [k, b] of Object.entries(toolButtons)) b.setAttribute('aria-pressed', String(k === t));
        };
        [['pen', 'Pen'], ['fill', 'Fill bucket'], ['eraser', 'Eraser']].forEach(([k, label]) => {
            toolButtons[k] = button(label, () => pickTool(k));
            tools.append(toolButtons[k]);
        });
        tools.append(
            button('Undo', () => { if (undo.length) { cells = undo.pop(); draw(); } }),
            button('Clear', () => { remember(); cells.fill(null); draw(); }),
            button('Grid', () => { grid = !grid; draw(); }),
        );
        pickTool('pen');

        const swatches = el('div', 'art-palette-pick');
        const choose = (c, b) => {
            colour = c;
            if (tool === 'eraser') pickTool('pen');
            swatches.querySelectorAll('button').forEach((x) => x.setAttribute('aria-pressed', String(x === b)));
        };
        palette.forEach((c, k) => {
            const b = button('', () => choose(c, b), 'art-pick');
            b.style.background = c;
            b.title = c;
            b.setAttribute('aria-label', `Colour ${c}`);
            b.setAttribute('aria-pressed', String(k === 0));
            swatches.append(b);
        });
        const custom = el('input', 'art-custom');
        custom.type = 'color';
        custom.value = colour;
        custom.title = 'Any colour';
        custom.addEventListener('input', () => choose(custom.value, null));
        swatches.append(custom);

        const name = el('input', 'art-name-input');
        name.type = 'text';
        name.value = d.name || 'Pixel art';
        name.maxLength = 50;
        name.setAttribute('aria-label', 'Picture name');
        const clear = el('label', 'art-check');
        const see = el('input');
        see.type = 'checkbox';
        see.checked = true;
        clear.append(see, el('span', '', 'See-through background'));
        const status = live(el);
        const save = button(`Save to ${d.folder || 'Ideas'}`, async () => {
            const scale = Math.max(1, Number(d.scale) || 16);
            const out = document.createElement('canvas');
            out.width = out.height = n * scale;
            const o = out.getContext('2d');
            o.imageSmoothingEnabled = false;
            if (!see.checked) { o.fillStyle = '#ffffff'; o.fillRect(0, 0, out.width, out.height); }
            cells.forEach((c, i) => { if (c) { o.fillStyle = c; o.fillRect((i % n) * scale, Math.floor(i / n) * scale, scale, scale); } });
            const safe = String(name.value || '').replace(/[<>:"/\\|?*\x00-\x1f]/g, '').trim().slice(0, 50) || 'Pixel art';
            status.textContent = 'Saving…';
            try {
                const blob = await new Promise((ok) => out.toBlob(ok, 'image/png'));
                const saved = await saveToFolder(d.folder || 'Ideas', `${safe}.png`, blob);
                status.textContent = `Saved ${saved.name} in ${saved.folder}.`;
                const path = `${saved.folder}/${saved.name}`;
                if (window.jarvisPopup) {
                    window.jarvisPopup({ kind: 'file', id: `file-${path}`.slice(0, 60), title: saved.name, buttons: [],
                        src: `/screen/file?path=${encodeURIComponent(path)}`, mime: 'image/png', name: saved.name });
                }
            } catch (e) {
                status.textContent = e.message || 'Saving failed.';
            }
        });
        const saveRow = el('div', 'art-bar');
        saveRow.append(name, clear, save);
        body.append(tools, swatches, canvas, saveRow, status);
        draw();
    };
})();
